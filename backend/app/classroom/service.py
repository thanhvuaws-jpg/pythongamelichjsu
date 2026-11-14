"""Lớp_Học cho Giáo_Viên (Req 26.1–26.5).

Tỷ lệ trả lời đúng theo Sự_Kiện = số Câu_Hỏi đã trả lời đúng / số lần thử tính đến lần
đúng đầu tiên (lần thử sau khi đã đúng không tính), gom theo `questions.event_id`.
"""

import csv
import io
import secrets
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import has_role
from app.errors import AppError
from app.models import (
    ClassMember,
    Classroom,
    Event,
    Progress,
    Question,
    QuestionAttempt,
    Role,
    ScoreLedger,
    User,
)
from app.play.progress import recompute
from app.play.published import load_levels, published

# Chữ hoa và số, bỏ 0/O/1/I dễ nhầm khi đọc mã trên bảng lớp
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LEN = 6


def new_join_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LEN))


def normalize_code(code: str) -> str:
    return code.strip().upper()


async def create_class(session: AsyncSession, teacher: User, name: str) -> Classroom:
    """Sinh mã tham gia 6 ký tự, thử lại khi trùng (Req 26.1)."""
    for _ in range(10):
        code = new_join_code()
        class_id = await session.scalar(
            insert(Classroom)
            .values(id=uuid.uuid4(), teacher_id=teacher.id, name=name.strip(), join_code=code)
            .on_conflict_do_nothing(index_elements=[Classroom.join_code])
            .returning(Classroom.id)
        )
        if class_id is not None:
            row = await session.get(Classroom, class_id)
            assert row is not None
            return row
    raise AppError(503, "JOIN_CODE_EXHAUSTED", "Không sinh được mã lớp, vui lòng thử lại")


async def join_class(session: AsyncSession, user: User, code: str) -> Classroom:
    """Thêm Người_Chơi vào Lớp_Học theo mã; tham gia lại không lỗi (Req 26.2)."""
    cls = await session.scalar(select(Classroom).where(Classroom.join_code == normalize_code(code)))
    if cls is None:
        raise AppError(404, "CLASS_CODE_INVALID", "Mã lớp không hợp lệ")
    await session.execute(
        insert(ClassMember).values(class_id=cls.id, user_id=user.id).on_conflict_do_nothing()
    )
    return cls


async def get_class(session: AsyncSession, class_id: uuid.UUID) -> Classroom:
    cls = await session.get(Classroom, class_id)
    if cls is None:
        raise AppError(404, "CLASS_NOT_FOUND", "Không tìm thấy lớp học")
    return cls


async def ensure_class_teacher(session: AsyncSession, user: User, class_id: uuid.UUID) -> Classroom:
    """Chỉ Giáo_Viên của lớp (hoặc Quản_Trị_Viên) xem được dữ liệu thành viên (Req 26.5)."""
    cls = await get_class(session, class_id)
    if cls.teacher_id != user.id and not has_role(user, Role.admin):
        raise AppError(403, "NOT_CLASS_TEACHER", "Bạn không phải giáo viên của lớp này")
    return cls


async def ensure_can_view_class(
    session: AsyncSession, user: User, class_id: uuid.UUID
) -> Classroom:
    """Bảng xếp hạng lớp: thành viên, Giáo_Viên của lớp hoặc Quản_Trị_Viên."""
    cls = await get_class(session, class_id)
    if cls.teacher_id == user.id or has_role(user, Role.admin):
        return cls
    member = await session.get(ClassMember, (class_id, user.id))
    if member is None:
        raise AppError(403, "NOT_CLASS_MEMBER", "Bạn không thuộc lớp này")
    return cls


async def my_classes(session: AsyncSession, user: User) -> list[dict[str, Any]]:
    member_count = (
        select(func.count())
        .where(ClassMember.class_id == Classroom.id)
        .correlate(Classroom)
        .scalar_subquery()
    )
    is_member = select(ClassMember.class_id).where(ClassMember.user_id == user.id)
    rows = await session.execute(
        select(Classroom, member_count)
        .where((Classroom.teacher_id == user.id) | Classroom.id.in_(is_member))
        .order_by(Classroom.created_at.desc())
    )
    out = []
    for cls, count in rows:
        teaching = cls.teacher_id == user.id
        out.append(
            {
                "id": cls.id,
                "name": cls.name,
                # Chỉ Giáo_Viên thấy mã để chia sẻ
                "join_code": cls.join_code if teaching else None,
                "is_teacher": teaching,
                "member_count": int(count),
                "created_at": cls.created_at,
            }
        )
    return out


async def class_progress(session: AsyncSession, cls: Classroom) -> dict[str, Any]:
    """Tiến độ Màn_Chơi, Điểm_Kiến_Thức, tỷ lệ đúng theo Sự_Kiện của thành viên (Req 26.3)."""
    members = list(
        await session.execute(
            select(User.id, User.display_name, ClassMember.joined_at)
            .join(ClassMember, ClassMember.user_id == User.id)
            .where(ClassMember.class_id == cls.id)
            .order_by(User.display_name, User.id)
        )
    )
    ids = [m[0] for m in members]
    levels = await load_levels(session)
    level_titles = {str(b["level"]["id"]): b["level"]["title"] for b in levels}
    events = await published(session, Event)

    points: dict[uuid.UUID, int] = {}
    data: dict[uuid.UUID, dict[str, Any]] = {}
    correct: dict[uuid.UUID, set[str]] = {}
    accuracy: dict[uuid.UUID, dict[str, dict[str, int]]] = {}
    if ids:
        for uid, total in await session.execute(
            select(ScoreLedger.user_id, func.sum(ScoreLedger.points))
            .where(ScoreLedger.user_id.in_(ids))
            .group_by(ScoreLedger.user_id)
        ):
            points[uid] = int(total)
        for row in await session.scalars(select(Progress).where(Progress.user_id.in_(ids))):
            data[row.user_id] = row.data or {}
        tries = func.coalesce(QuestionAttempt.first_correct_attempt, QuestionAttempt.attempts)
        for uid, qid, event_id, n_tries, first_ok in await session.execute(
            select(
                QuestionAttempt.user_id,
                QuestionAttempt.question_id,
                Question.event_id,
                tries,
                QuestionAttempt.first_correct_attempt,
            )
            .join(Question, Question.id == QuestionAttempt.question_id)
            .where(QuestionAttempt.user_id.in_(ids), QuestionAttempt.attempts > 0)
        ):
            stat = accuracy.setdefault(uid, {}).setdefault(
                str(event_id), {"correct": 0, "attempts": 0}
            )
            stat["attempts"] += int(n_tries)
            if first_ok is not None:
                stat["correct"] += 1
                correct.setdefault(uid, set()).add(str(qid))

    out_members = []
    for uid, name, joined_at in members:
        p = recompute(levels, data.get(uid, {}), points.get(uid, 0), correct.get(uid, set()))
        by_event = [
            {
                "event_id": eid,
                "event_title": events.get(eid, {}).get("title"),
                "correct": s["correct"],
                "attempts": s["attempts"],
                "accuracy": round(s["correct"] / s["attempts"], 4) if s["attempts"] else None,
            }
            for eid, s in sorted(accuracy.get(uid, {}).items())
        ]
        n_correct = sum(s["correct"] for s in accuracy.get(uid, {}).values())
        n_tries = sum(s["attempts"] for s in accuracy.get(uid, {}).values())
        out_members.append(
            {
                "user_id": uid,
                "display_name": name,
                "joined_at": joined_at,
                "points": points.get(uid, 0),
                "unlocked_levels": p["unlocked_levels"],
                "completed_levels": p["completed_levels"],
                "completed_level_titles": [level_titles[i] for i in p["completed_levels"]],
                "accuracy": round(n_correct / n_tries, 4) if n_tries else None,
                "by_event": by_event,
            }
        )
    return {
        "class_id": cls.id,
        "name": cls.name,
        "level_count": len(levels),
        "levels": [{"id": i, "title": t} for i, t in level_titles.items()],
        "members": out_members,
    }


def _cell(value: Any) -> str:
    """Chặn CSV injection: ô bắt đầu bằng = + - @ bị Excel hiểu là công thức."""
    s = "" if value is None else str(value)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def _pct(v: float | None) -> str:
    return "" if v is None else f"{v * 100:.1f}"


def progress_csv(report: dict[str, Any]) -> bytes:
    """CSV UTF-8 (kèm BOM để Excel đọc đúng tiếng Việt) (Req 26.4)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "Tên hiển thị",
            "Ngày tham gia",
            "Điểm kiến thức",
            f"Số màn hoàn thành (/{report['level_count']})",
            "Màn đã hoàn thành",
            "Tỷ lệ đúng (%)",
            "Tỷ lệ đúng theo sự kiện",
        ]
    )
    for m in report["members"]:
        by_event = "; ".join(
            f"{e['event_title'] or e['event_id']}: {_pct(e['accuracy'])}%" for e in m["by_event"]
        )
        w.writerow(
            [
                _cell(m["display_name"]),
                m["joined_at"].date().isoformat(),
                m["points"],
                len(m["completed_levels"]),
                _cell(", ".join(m["completed_level_titles"])),
                _pct(m["accuracy"]),
                _cell(by_event),
            ]
        )
    return buf.getvalue().encode("utf-8-sig")
