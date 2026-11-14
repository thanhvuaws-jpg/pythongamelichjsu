"""Bảng_Xếp_Hạng theo tuần/tháng/toàn thời gian/Lớp_Học (Req 22.1–22.4, 25.3).

- Mốc tuần bắt đầu 00:00 thứ Hai giờ Việt Nam; tháng bắt đầu 00:00 ngày 1. Việt Nam dùng
  UTC+7 cố định, không có giờ mùa hè, nên dùng offset cố định thay cho tzdata.
- Top 100 lưu trong `leaderboard_cache`, làm mới khi cũ hơn 60 giây hoặc đã sang kỳ mới
  (Req 22.3). Hạng của Người_Chơi hiện tại tính trực tiếp, không cache.
- Chỉ tính tài khoản `active`: tài khoản bị vô hiệu hóa/đang xóa bị loại (Req 25.3).
- Đầu ra chỉ có tên hiển thị và ảnh đại diện, không có email (Req 22.4).
"""

import uuid
from datetime import UTC, datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

from sqlalchemy import ColumnElement, Select, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClassMember, LeaderboardCache, Media, ScoreLedger, User, UserStatus
from app.storage import get_storage

VN_TZ = timezone(timedelta(hours=7), "Asia/Ho_Chi_Minh")
TOP_N = 100
CACHE_TTL = timedelta(seconds=60)


class Period(StrEnum):
    week = "week"
    month = "month"
    all = "all"


def period_start(period: Period, now: datetime) -> datetime | None:
    """Thời điểm bắt đầu kỳ (UTC) theo giờ Việt Nam; None với toàn thời gian."""
    if period == Period.all:
        return None
    local = now.astimezone(VN_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    if period == Period.week:
        local -= timedelta(days=local.weekday())  # thứ Hai = 0
    else:
        local = local.replace(day=1)
    return local.astimezone(UTC)


def cache_key(period: Period, class_id: uuid.UUID | None) -> str:
    return f"class:{class_id}:{period.value}" if class_id else period.value


def rank_rows(rows: list[tuple[uuid.UUID, str, str | None, int]]) -> list[dict[str, Any]]:
    """Xếp hạng kiểu thi đấu: cùng điểm cùng hạng (1, 2, 2, 4)."""
    out: list[dict[str, Any]] = []
    prev_points, prev_rank = None, 0
    for i, (uid, name, avatar, points) in enumerate(rows, start=1):
        rank = prev_rank if points == prev_points else i
        prev_points, prev_rank = points, rank
        out.append(
            {
                "rank": rank,
                "user_id": str(uid),
                "display_name": name,
                "avatar_url": avatar,
                "points": points,
            }
        )
    return out


def _filters(start: datetime | None, class_id: uuid.UUID | None) -> list[ColumnElement[bool]]:
    conds: list[ColumnElement[bool]] = [User.status == UserStatus.active]
    if start is not None:
        conds.append(ScoreLedger.created_at >= start)
    if class_id is not None:
        conds.append(
            ScoreLedger.user_id.in_(
                select(ClassMember.user_id).where(ClassMember.class_id == class_id)
            )
        )
    return conds


def _totals(start: datetime | None, class_id: uuid.UUID | None) -> Select:
    total = func.sum(ScoreLedger.points).label("points")
    return (
        select(ScoreLedger.user_id, total)
        .join(User, User.id == ScoreLedger.user_id)
        .where(*_filters(start, class_id))
        .group_by(ScoreLedger.user_id)
    )


async def _compute_top(
    session: AsyncSession, start: datetime | None, class_id: uuid.UUID | None
) -> list[dict[str, Any]]:
    totals = _totals(start, class_id).subquery()
    rows = await session.execute(
        select(User.id, User.display_name, Media.storage_path, totals.c.points)
        .join(totals, totals.c.user_id == User.id)
        .outerjoin(Media, Media.id == User.avatar_media_id)
        .order_by(totals.c.points.desc(), User.display_name, User.id)
        .limit(TOP_N)
    )
    storage = get_storage()
    return rank_rows(
        [
            (uid, name, storage.public_url(path) if path else None, int(points))
            for uid, name, path, points in rows
        ]
    )


async def top(
    session: AsyncSession, period: Period, class_id: uuid.UUID | None, now: datetime
) -> tuple[list[dict[str, Any]], datetime]:
    """Top 100 từ cache; tính lại khi cache hết hạn hoặc đã sang kỳ mới."""
    key = cache_key(period, class_id)
    start = period_start(period, now)
    cached = await session.get(LeaderboardCache, key)
    if cached and cached.period_start == start and now - cached.computed_at < CACHE_TTL:
        return cached.data, cached.computed_at
    data = await _compute_top(session, start, class_id)
    values = {"period_start": start, "data": data, "computed_at": now}
    await session.execute(
        insert(LeaderboardCache)
        .values(key=key, **values)
        .on_conflict_do_update(index_elements=[LeaderboardCache.key], set_=values)
    )
    return data, now


async def my_standing(
    session: AsyncSession,
    user_id: uuid.UUID,
    period: Period,
    class_id: uuid.UUID | None,
    now: datetime,
) -> dict[str, int] | None:
    """Hạng và điểm của Người_Chơi hiện tại; None khi chưa có điểm trong kỳ (Req 22.1)."""
    start = period_start(period, now)
    totals = _totals(start, class_id).subquery()
    mine = await session.scalar(select(totals.c.points).where(totals.c.user_id == user_id))
    if mine is None:
        return None
    higher = await session.scalar(
        select(func.count()).select_from(totals).where(totals.c.points > mine)
    )
    return {"rank": int(higher or 0) + 1, "points": int(mine)}


async def invalidate_cache(session: AsyncSession) -> None:
    """Xóa cache để thay đổi trạng thái tài khoản có hiệu lực ngay (Req 25.3)."""
    await session.execute(delete(LeaderboardCache))
