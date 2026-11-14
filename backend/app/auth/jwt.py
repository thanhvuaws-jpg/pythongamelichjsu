"""Access token JWT và refresh token ngẫu nhiên lưu băm SHA-256 (Req 23.3, 25.3)."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import RefreshToken, User


class TokenError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code  # TOKEN_EXPIRED | TOKEN_INVALID


def now_utc() -> datetime:
    return datetime.now(UTC)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_raw_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(user: User) -> str:
    s = get_settings()
    iat = now_utc()
    claims = {
        "sub": str(user.id),
        "role": user.role.value,
        "is_teacher": user.is_teacher,
        "type": "access",
        "iat": iat,
        "exp": iat + timedelta(minutes=s.access_token_minutes),
    }
    return jwt.encode(claims, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    try:
        claims = jwt.decode(
            token, s.jwt_secret, algorithms=[s.jwt_algorithm], options={"require": ["exp", "sub"]}
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("TOKEN_EXPIRED") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("TOKEN_INVALID") from exc
    if claims.get("type") != "access":
        raise TokenError("TOKEN_INVALID")
    return claims


@dataclass
class IssuedRefresh:
    raw: str
    expires_at: datetime


async def issue_refresh_token(session: AsyncSession, user_id: uuid.UUID) -> IssuedRefresh:
    raw = new_raw_token()
    expires = now_utc() + timedelta(days=get_settings().refresh_token_days)
    session.add(RefreshToken(user_id=user_id, token_hash=hash_token(raw), expires_at=expires))
    return IssuedRefresh(raw, expires)


async def rotate_refresh_token(session: AsyncSession, raw: str) -> tuple[uuid.UUID, IssuedRefresh]:
    """Thu hồi token cũ, cấp token mới. Dùng lại token đã thu hồi → thu hồi mọi token của user."""
    row = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)).with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        raise TokenError("TOKEN_INVALID")
    if row.revoked_at is not None:
        # Dấu hiệu token bị đánh cắp: thu hồi toàn bộ phiên của user
        await revoke_all_refresh_tokens(session, row.user_id)
        raise TokenError("TOKEN_INVALID")
    if row.expires_at <= now_utc():
        raise TokenError("TOKEN_EXPIRED")
    row.revoked_at = now_utc()
    return row.user_id, await issue_refresh_token(session, row.user_id)


async def revoke_refresh_token(session: AsyncSession, raw: str) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(raw), RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now_utc())
    )


async def revoke_all_refresh_tokens(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now_utc())
    )
