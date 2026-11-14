"""Khóa đăng nhập 15 phút sau 5 lần sai trong 15 phút (Req 23.4)."""

from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import now_utc
from app.config import get_settings
from app.models import LoginAttempt


def compute_lock_until(
    failures: Sequence[datetime],
    max_failures: int,
    window: timedelta,
    lockout: timedelta,
) -> datetime | None:
    """failures: thời điểm các lần sai (sau lần đúng gần nhất), sắp tăng dần.

    Khóa khi có `max_failures` lần sai liên tiếp nằm trong `window`; khóa kéo dài
    `lockout` tính từ lần sai cuối của nhóm đó.
    """
    lock_until = None
    for i in range(len(failures) - max_failures + 1):
        first, last = failures[i], failures[i + max_failures - 1]
        if last - first <= window:
            candidate = last + lockout
            lock_until = candidate if lock_until is None else max(lock_until, candidate)
    return lock_until


async def locked_until(session: AsyncSession, email: str) -> datetime | None:
    s = get_settings()
    window = timedelta(minutes=s.lockout_window_minutes)
    lockout = timedelta(minutes=s.lockout_minutes)
    now = now_utc()

    last_success = (
        select(func.max(LoginAttempt.attempted_at))
        .where(LoginAttempt.email == email, LoginAttempt.success.is_(True))
        .scalar_subquery()
    )
    rows = await session.scalars(
        select(LoginAttempt.attempted_at)
        .where(
            LoginAttempt.email == email,
            LoginAttempt.success.is_(False),
            LoginAttempt.attempted_at > now - window - lockout,
            LoginAttempt.attempted_at > func.coalesce(last_success, now - window - lockout),
        )
        .order_by(LoginAttempt.attempted_at)
    )
    until = compute_lock_until(list(rows), s.lockout_max_failures, window, lockout)
    return until if until and until > now else None


async def record_attempt(session: AsyncSession, email: str, success: bool) -> None:
    # Ghi thời điểm phía ứng dụng để so sánh nhất quán với now_utc()
    session.add(LoginAttempt(email=email, success=success, attempted_at=now_utc()))
    await session.flush()
