"""`GET /leaderboard` (Req 22.1–22.4)."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser
from app.auth.jwt import now_utc
from app.classroom.service import ensure_can_view_class
from app.db import get_session
from app.leaderboard.service import Period, my_standing, period_start, top

router = APIRouter(prefix="/api/v1", tags=["leaderboard"])
Session = Annotated[AsyncSession, Depends(get_session)]


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    display_name: str
    avatar_url: str | None
    points: int


class MyStanding(BaseModel):
    rank: int
    points: int


class LeaderboardOut(BaseModel):
    period: Period
    class_id: uuid.UUID | None
    period_start: datetime | None
    computed_at: datetime
    entries: list[LeaderboardEntry]
    me: MyStanding | None


@router.get("/leaderboard", response_model=LeaderboardOut)
async def leaderboard(
    session: Session,
    user: CurrentUser,
    period: Period = Period.week,
    class_id: uuid.UUID | None = None,
) -> LeaderboardOut:
    if class_id is not None:
        await ensure_can_view_class(session, user, class_id)
    now = now_utc()
    entries, computed_at = await top(session, period, class_id, now)
    me = await my_standing(session, user.id, period, class_id, now)
    await session.commit()  # lưu cache vừa tính
    return LeaderboardOut(
        period=period,
        class_id=class_id,
        period_start=period_start(period, now),
        computed_at=computed_at,
        entries=[LeaderboardEntry(**e) for e in entries],
        me=MyStanding(**me) if me else None,
    )
