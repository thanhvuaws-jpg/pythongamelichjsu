"""Đánh giá Huy_Hiệu (Req 21.2, 21.3).

Điều kiện là JSON khai báo trong `badges.condition`:
    {"type": "level_complete", "level_id": "<id>"}
    {"type": "fragments_collected", "count": 20}
    {"type": "first_try_streak", "count": 5}     # N câu liên tiếp gần nhất đúng ngay lần đầu
    {"type": "points", "count": 500}             # Điểm_Kiến_Thức tối thiểu
    {"type": "quest_done", "quest_id": "<id>"}
Loại không hỗ trợ được coi là chưa đạt (không làm hỏng các huy hiệu khác).
"""

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Badge, Notification, QuestionAttempt, UserBadge
from app.play.published import published


def first_try_streak(first_correct: Sequence[int | None]) -> int:
    """`first_correct` sắp theo thời điểm thử gần nhất trước."""
    n = 0
    for v in first_correct:
        if v != 1:
            break
        n += 1
    return n


def is_earned(condition: Mapping[str, Any], stats: Mapping[str, Any]) -> bool:
    try:
        match condition.get("type"):
            case "level_complete":
                return str(condition["level_id"]) in stats["completed_levels"]
            case "quest_done":
                return str(condition["quest_id"]) in stats["done_quests"]
            case "fragments_collected":
                return len(stats["collected_fragments"]) >= int(condition["count"])
            case "first_try_streak":
                return stats["first_try_streak"] >= int(condition["count"])
            case "points":
                return stats["points"] >= int(condition["count"])
    except (KeyError, TypeError, ValueError):
        return False
    return False


async def _stats(
    session: AsyncSession, user_id: uuid.UUID, progress: Mapping[str, Any], need_streak: bool
) -> dict[str, Any]:
    streak = 0
    if need_streak:
        rows = await session.scalars(
            select(QuestionAttempt.first_correct_attempt)
            .where(QuestionAttempt.user_id == user_id)
            .order_by(QuestionAttempt.created_at.desc())
            .limit(200)
        )
        streak = first_try_streak(list(rows))
    return {
        "completed_levels": set(progress.get("completed_levels") or ()),
        "done_quests": set(progress.get("done_quests") or ()),
        "collected_fragments": set(progress.get("collected_fragments") or ()),
        "points": int(progress.get("points") or 0),
        "first_try_streak": streak,
    }


def badge_out(b: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": b["id"],
        "name": b["name"],
        "description": b["description"],
        "media_id": b.get("media_id"),
        "condition": b["condition"],
    }


async def evaluate_badges(
    session: AsyncSession, user_id: uuid.UUID, progress: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Trao Huy_Hiệu mới đạt, tạo thông báo; trả danh sách vừa trao để client hiện ngay."""
    badges = await published(session, Badge)
    owned = {
        str(b)
        for b in await session.scalars(
            select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
        )
    }
    pending = [b for bid, b in badges.items() if bid not in owned]
    if not pending:
        return []
    need_streak = any(b["condition"].get("type") == "first_try_streak" for b in pending)
    stats = await _stats(session, user_id, progress, need_streak)

    awarded: list[dict[str, Any]] = []
    for b in pending:
        if not is_earned(b["condition"], stats):
            continue
        inserted = await session.scalar(
            insert(UserBadge)
            .values(user_id=user_id, badge_id=uuid.UUID(b["id"]))
            .on_conflict_do_nothing()
            .returning(UserBadge.badge_id)
        )
        if inserted is None:
            continue
        out = badge_out(b)
        session.add(
            Notification(
                id=uuid.uuid4(),
                user_id=user_id,
                kind="badge_awarded",
                payload={"badge_id": out["id"], "name": out["name"]},
            )
        )
        awarded.append(out)
    return awarded


async def list_badges(session: AsyncSession, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Huy_Hiệu đã đạt và chưa đạt kèm điều kiện (Req 21.3)."""
    badges = await published(session, Badge)
    owned = {
        str(bid): at
        for bid, at in await session.execute(
            select(UserBadge.badge_id, UserBadge.awarded_at).where(UserBadge.user_id == user_id)
        )
    }
    items = [
        {**badge_out(b), "earned": bid in owned, "awarded_at": owned.get(bid)}
        for bid, b in badges.items()
    ]
    items.sort(key=lambda b: (not b["earned"], b["name"]))
    return items
