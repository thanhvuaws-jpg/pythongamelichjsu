"""Hợp nhất tiến trình và tính lại mở khóa ở máy chủ (Req 9.2, 9.3, 19.2, 19.4).

Client gửi: completed_objectives, collected_fragments, clues, current_level, map_pos,
timeline_state, tutorial_done, updated_at. Máy chủ không tin dữ liệu mở khóa từ client:
`unlocked_*`, `completed_levels`, `unlocked_levels` luôn được tính lại từ tập Mục_Tiêu
và Mảnh_Ghép hợp lệ. `timeline_done` chỉ do `POST /timeline/complete` ghi.
"""

import uuid
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Progress, QuestionAttempt, ScoreLedger
from app.play.published import Snap, load_levels
from shared.progress_merge import merge
from shared.quest_engine import Progress as EngineProgress
from shared.quest_engine import QuestEngine
from shared.unlock import UnlockContext, evaluate, missing

CLIENT_FIELDS = (
    "completed_objectives",
    "collected_fragments",
    "clues",
    "current_level",
    "map_pos",
    "timeline_state",
    "tutorial_done",
    "updated_at",
)


def recompute(
    levels: list[Snap],
    data: Mapping[str, Any],
    points: int,
    correct_questions: Iterable[str],
) -> dict[str, Any]:
    """Trả về tiến trình đầy đủ: trường client đã lọc hợp lệ + trường máy chủ tính."""
    level_ids = [str(b["level"]["id"]) for b in levels]
    timeline_done = set(data.get("timeline_done") or ()) & set(level_ids)
    correct = set(correct_questions)

    objectives: dict[str, tuple[str, Snap]] = {}
    for b in levels:
        for q in b["quests"]:
            for o in q["objectives"]:
                objectives[o["id"]] = (str(b["level"]["id"]), o)

    def valid(oid: str) -> bool:
        if oid not in objectives:
            return False
        lid, o = objectives[oid]
        if o["kind"] == "answer":  # chỉ tính khi máy chủ đã chấm đúng
            return str(o.get("target_id")) in correct
        if o["kind"] == "timeline":
            return lid in timeline_done
        return True

    def server_verified(oid: str) -> bool:
        # Mục_Tiêu máy chủ tự xác nhận được thì đánh dấu luôn, không chờ client báo
        return objectives[oid][1]["kind"] in ("answer", "timeline") and valid(oid)

    known_fragments = {f["id"] for b in levels for f in b["fragments"]}
    claimed = {o for o in data.get("completed_objectives") or () if valid(o)}
    engine_progress = EngineProgress(
        completed_objectives=claimed | {o for o in objectives if server_verified(o)},
        collected_fragments=set(data.get("collected_fragments") or ()) & known_fragments,
        timeline_done=timeline_done,
        points=points,
    )
    engines = [QuestEngine(b, engine_progress) for b in levels]
    done_quests = frozenset(q for e in engines for q in e.done_quests())

    def ctx(done_levels: set[str]) -> UnlockContext:
        return UnlockContext(
            done_quests=done_quests,
            done_levels=frozenset(done_levels),
            done_objectives=frozenset(engine_progress.completed_objectives),
            points=points,
        )

    # Màn_Chơi theo thứ tự: màn đầu mở sẵn (Req 9.2); màn có `unlock_rule` theo luật,
    # màn không có luật mở khi màn liền trước hoàn thành (Req 9.3)
    unlocked_levels: list[str] = []
    completed_levels: set[str] = set()
    locked_levels: dict[str, list[dict[str, Any]]] = {}
    for i, (b, engine) in enumerate(zip(levels, engines, strict=True)):
        lid, rule = level_ids[i], b["level"].get("unlock_rule")
        if rule:
            is_open = evaluate(rule, ctx(completed_levels))
            reasons = missing(rule, ctx(completed_levels))
        else:
            is_open = i == 0 or level_ids[i - 1] in completed_levels
            reasons = [] if is_open else [{"level_done": level_ids[i - 1]}]
        if not is_open:
            locked_levels[lid] = reasons  # Req 9.4
            continue
        unlocked_levels.append(lid)
        if engine.is_level_complete():
            completed_levels.add(lid)

    final = ctx(completed_levels)
    open_levels = [b for b in levels if str(b["level"]["id"]) in unlocked_levels]
    unlocked_quests = {
        q["id"] for b in open_levels for q in b["quests"] if evaluate(q.get("unlock_rule"), final)
    }
    unlocked_places = {
        p["id"] for b in open_levels for p in b["places"] if evaluate(p.get("unlock_rule"), final)
    }
    # Đủ Mảnh_Ghép của một Sự_Kiện thì mở thẻ Sự_Kiện (Req 13.3)
    frags_by_event: dict[str, set[str]] = {}
    for b in levels:
        for f in b["fragments"]:
            frags_by_event.setdefault(str(f["event_id"]), set()).add(f["id"])
    unlocked_events = {
        e for e, fs in frags_by_event.items() if fs <= engine_progress.collected_fragments
    }

    out = {k: data[k] for k in CLIENT_FIELDS if k in data}
    out.update(
        completed_objectives=sorted(engine_progress.completed_objectives),
        collected_fragments=sorted(engine_progress.collected_fragments),
        clues=sorted(set(data.get("clues") or ())),
        tutorial_done=bool(data.get("tutorial_done")),
        timeline_done=sorted(timeline_done),
        unlocked_levels=unlocked_levels,
        locked_levels=locked_levels,
        completed_levels=sorted(completed_levels),
        done_quests=sorted(done_quests),
        unlocked_quests=sorted(unlocked_quests),
        unlocked_places=sorted(unlocked_places),
        unlocked_events=sorted(unlocked_events),
        points=points,
    )
    return out


# ---------------------------------------------------------------- truy cập DB


async def total_points(session: AsyncSession, user_id: uuid.UUID) -> int:
    total = await session.scalar(
        select(func.coalesce(func.sum(ScoreLedger.points), 0)).where(ScoreLedger.user_id == user_id)
    )
    return int(total or 0)


async def correct_question_ids(session: AsyncSession, user_id: uuid.UUID) -> set[str]:
    rows = await session.scalars(
        select(QuestionAttempt.question_id).where(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.first_correct_attempt.is_not(None),
        )
    )
    return {str(r) for r in rows}


async def lock_progress(session: AsyncSession, user_id: uuid.UUID) -> Progress:
    """Tạo hàng nếu chưa có rồi khóa để hai lần lưu đồng thời không ghi đè nhau."""
    await session.execute(
        insert(Progress).values(user_id=user_id, data={}).on_conflict_do_nothing()
    )
    row = await session.scalar(
        select(Progress).where(Progress.user_id == user_id).with_for_update()
    )
    assert row is not None
    return row


async def computed(
    session: AsyncSession, user_id: uuid.UUID, data: Mapping[str, Any]
) -> dict[str, Any]:
    return recompute(
        await load_levels(session),
        data,
        await total_points(session, user_id),
        await correct_question_ids(session, user_id),
    )


async def read_progress(session: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
    row = await session.get(Progress, user_id)
    return await computed(session, user_id, row.data if row else {})


async def save_progress(
    session: AsyncSession,
    user_id: uuid.UUID,
    client: Mapping[str, Any] | None = None,
    timeline_level: str | None = None,
) -> dict[str, Any]:
    """Hợp nhất `client` (nếu có) với bản máy chủ, đánh dấu Dòng_Thời_Gian (nếu có),
    tính lại và ghi. Commit do router thực hiện."""
    row = await lock_progress(session, user_id)
    server = dict(row.data or {})
    data = merge(server, client) if client is not None else dict(server)
    timeline = set(server.get("timeline_done") or ())
    if timeline_level:
        timeline.add(timeline_level)
    data["timeline_done"] = sorted(timeline)
    result = await computed(session, user_id, data)
    row.data = result
    return result
