"""Xuất và xóa dữ liệu cá nhân (Req 25.5, 27.4).

Xóa tài khoản gồm hai bước:
1. `DELETE /me`: chuyển `status=deleting`, ghi `deleted_request_at`, thu hồi mọi refresh
   token, ẩn khỏi Bảng_Xếp_Hạng. Tài khoản không đăng nhập được nữa.
2. Job định kỳ `purge_deleted_accounts` xóa hẳn hàng `users` sau
   `account_purge_after_days` ngày. Các bảng tham chiếu users đều CASCADE (dữ liệu chơi,
   lớp học, thông báo) hoặc SET NULL (nội dung đã soạn, báo cáo). `login_attempts` lưu
   theo email nên xóa riêng. Sự_Kiện_Phân_Tích dùng `anon_id` không có khóa ngoại nên
   được giữ ở dạng ẩn danh; `audit_log`/`content_versions` chỉ giữ id, không có email.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import now_utc, revoke_all_refresh_tokens
from app.config import get_settings
from app.leaderboard.service import invalidate_cache
from app.models import (
    AuditLog,
    ClassMember,
    Classroom,
    ErrorReport,
    GuardianConsent,
    LoginAttempt,
    Notification,
    Progress,
    QuestionAttempt,
    ReviewItem,
    ReviewPoints,
    ScoreLedger,
    User,
    UserBadge,
    UserStatus,
)

EXPORT_FORMAT = 1


def _iso(v: Any) -> Any:
    return v.isoformat() if isinstance(v, datetime) else v


def _row(obj: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    out = {}
    for f in fields:
        v = getattr(obj, f)
        out[f] = str(v) if isinstance(v, uuid.UUID) else _iso(v)
    return out


async def export_user_data(session: AsyncSession, user: User) -> dict[str, Any]:
    """Toàn bộ dữ liệu cá nhân của người dùng ở dạng JSON (Req 27.4)."""
    uid = user.id

    async def rows(model: Any, *conds: Any, fields: tuple[str, ...]) -> list[dict[str, Any]]:
        return [_row(r, fields) for r in await session.scalars(select(model).where(*conds))]

    progress = await session.get(Progress, uid)
    review_points = await session.get(ReviewPoints, uid)
    teaching = await rows(
        Classroom, Classroom.teacher_id == uid, fields=("id", "name", "join_code", "created_at")
    )
    member_of = [
        {"class_id": str(cid), "name": name, "joined_at": _iso(at)}
        for cid, name, at in await session.execute(
            select(ClassMember.class_id, Classroom.name, ClassMember.joined_at)
            .join(Classroom, Classroom.id == ClassMember.class_id)
            .where(ClassMember.user_id == uid)
        )
    ]
    return {
        "format": EXPORT_FORMAT,
        "exported_at": now_utc().isoformat(),
        "account": _row(
            user,
            (
                "id",
                "email",
                "email_verified",
                "display_name",
                "birth_year",
                "avatar_media_id",
                "role",
                "is_teacher",
                "status",
                "consent_version",
                "consent_at",
                "created_at",
                "updated_at",
            ),
        )
        | {"google_linked": user.google_sub is not None},
        "guardian_consents": await rows(
            GuardianConsent,
            GuardianConsent.user_id == uid,
            fields=("guardian_email", "confirmed_at", "created_at"),
        ),
        "progress": progress.data if progress else None,
        "question_attempts": await rows(
            QuestionAttempt,
            QuestionAttempt.user_id == uid,
            fields=("question_id", "attempts", "first_correct_attempt", "scored", "created_at"),
        ),
        "score_ledger": await rows(
            ScoreLedger,
            ScoreLedger.user_id == uid,
            fields=("points", "reason", "ref_id", "created_at"),
        ),
        "review_items": await rows(
            ReviewItem,
            ReviewItem.user_id == uid,
            fields=("question_id", "stage", "due_at", "last_result", "last_reviewed_at"),
        ),
        "review_points": review_points.total if review_points else 0,
        "badges": await rows(
            UserBadge, UserBadge.user_id == uid, fields=("badge_id", "awarded_at")
        ),
        "notifications": await rows(
            Notification,
            Notification.user_id == uid,
            fields=("kind", "payload", "read_at", "created_at"),
        ),
        "classes_teaching": teaching,
        "classes_joined": member_of,
        "error_reports": await rows(
            ErrorReport,
            ErrorReport.reporter_id == uid,
            fields=(
                "entity_type",
                "entity_id",
                "description",
                "counter_source",
                "status",
                "resolution",
                "created_at",
            ),
        ),
    }


async def request_deletion(session: AsyncSession, user: User) -> datetime:
    """Đánh dấu xóa; trả thời điểm sớm nhất job xóa hẳn dữ liệu."""
    now = now_utc()
    before = user.status.value
    user.status = UserStatus.deleting
    user.deleted_request_at = now
    await revoke_all_refresh_tokens(session, user.id)
    await invalidate_cache(session)
    session.add(
        AuditLog(
            actor_id=user.id,
            action="account_delete_request",
            target_type="users",
            target_id=str(user.id),
            before={"status": before},
            after={"status": user.status.value},
        )
    )
    return now + timedelta(days=get_settings().account_purge_after_days)


async def purge_deleted_accounts(session: AsyncSession, now: datetime | None = None) -> int:
    """Xóa hẳn tài khoản đã yêu cầu xóa quá hạn chờ. Commit do người gọi thực hiện."""
    cutoff = (now or now_utc()) - timedelta(days=get_settings().account_purge_after_days)
    users = list(
        await session.execute(
            select(User.id, User.email).where(
                User.status == UserStatus.deleting, User.deleted_request_at <= cutoff
            )
        )
    )
    for uid, email in users:
        await session.execute(delete(LoginAttempt).where(LoginAttempt.email == email))
        await session.execute(delete(User).where(User.id == uid))
        session.add(
            AuditLog(
                actor_id=None,
                action="account_purged",
                target_type="users",
                target_id=str(uid),
            )
        )
    return len(users)
