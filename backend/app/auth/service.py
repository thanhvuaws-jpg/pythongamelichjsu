"""Nghiệp vụ xác thực dùng chung cho router mật khẩu và Google OAuth."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import (
    create_access_token,
    hash_token,
    issue_refresh_token,
    new_raw_token,
    now_utc,
)
from app.config import get_settings
from app.email import Email
from app.errors import AppError
from app.models import AuditLog, GuardianConsent, OneTimeToken, TokenPurpose, User, UserStatus
from app.schemas.auth import TokenOut

REFRESH_COOKIE_PATH = "/api/v1/auth"


def current_year() -> int:
    return datetime.now(UTC).year


def validate_registration(
    birth_year: int, accept_policy: bool, email: str, guardian_email: str | None
) -> bool:
    """Kiểm tra đồng ý chính sách, năm sinh, email người giám hộ (Req 27.1–27.2).

    Trả về True nếu cần xác nhận người giám hộ.
    """
    if not accept_policy:
        raise AppError(400, "POLICY_NOT_ACCEPTED", "Cần đồng ý chính sách quyền riêng tư")
    year = current_year()
    if not 1900 <= birth_year <= year:
        raise AppError(400, "INVALID_BIRTH_YEAR", "Năm sinh không hợp lệ")
    # Chỉ biết năm sinh: coi là dưới 16 khi chưa chắc đã đủ 16 tuổi
    needs_guardian = year - birth_year <= get_settings().min_age_without_guardian
    if needs_guardian:
        if not guardian_email:
            raise AppError(
                400,
                "GUARDIAN_EMAIL_REQUIRED",
                "Người dùng dưới 16 tuổi cần email phụ huynh hoặc giáo viên",
            )
        if guardian_email == email:
            raise AppError(
                400, "GUARDIAN_EMAIL_INVALID", "Email người giám hộ phải khác email tài khoản"
            )
    return needs_guardian


def new_user(
    *,
    email: str,
    display_name: str,
    birth_year: int,
    needs_guardian: bool,
    password_hash: str | None = None,
    google_sub: str | None = None,
    email_verified: bool = False,
) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        email_verified=email_verified,
        password_hash=password_hash,
        google_sub=google_sub,
        display_name=display_name.strip(),
        birth_year=birth_year,
        status=UserStatus.pending_guardian if needs_guardian else UserStatus.active,
        consent_version=get_settings().consent_version,
        consent_at=now_utc(),
    )


async def create_one_time_token(
    session: AsyncSession, user_id: uuid.UUID, purpose: TokenPurpose, ttl: timedelta
) -> str:
    # Vô hiệu token cùng mục đích chưa dùng để chỉ liên kết mới nhất còn hiệu lực
    await session.execute(
        update(OneTimeToken)
        .where(
            OneTimeToken.user_id == user_id,
            OneTimeToken.purpose == purpose,
            OneTimeToken.used_at.is_(None),
        )
        .values(used_at=now_utc())
    )
    raw = new_raw_token()
    session.add(
        OneTimeToken(
            user_id=user_id, purpose=purpose, token_hash=hash_token(raw), expires_at=now_utc() + ttl
        )
    )
    return raw


async def consume_one_time_token(session: AsyncSession, raw: str, purpose: TokenPurpose) -> User:
    row = (
        await session.execute(
            select(OneTimeToken)
            .where(OneTimeToken.token_hash == hash_token(raw), OneTimeToken.purpose == purpose)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None or row.used_at is not None:
        raise AppError(400, "TOKEN_INVALID", "Liên kết không hợp lệ hoặc đã được sử dụng")
    if row.expires_at <= now_utc():
        raise AppError(400, "TOKEN_EXPIRED", "Liên kết đã hết hạn")
    row.used_at = now_utc()
    user = await session.get(User, row.user_id)
    if user is None:
        raise AppError(400, "TOKEN_INVALID", "Liên kết không hợp lệ hoặc đã được sử dụng")
    return user


def _link(path: str, token: str) -> str:
    return f"{get_settings().web_base_url.rstrip('/')}/{path}?token={token}"


async def start_email_verification(session: AsyncSession, user: User) -> Email:
    ttl = timedelta(hours=get_settings().verify_email_hours)
    raw = await create_one_time_token(session, user.id, TokenPurpose.verify_email, ttl)
    return Email(
        to=user.email,
        subject="Xác minh email - Sử Ký Điều Tra",
        body=(
            f"Chào {user.display_name},\n\nMở liên kết sau để xác minh email:\n"
            f"{_link('verify-email.html', raw)}\n\nLiên kết có hiệu lực "
            f"{get_settings().verify_email_hours} giờ."
        ),
    )


async def start_guardian_consent(session: AsyncSession, user: User, guardian_email: str) -> Email:
    raw = new_raw_token()
    session.add(
        GuardianConsent(
            user_id=user.id,
            guardian_email=guardian_email,
            token_hash=hash_token(raw),
            expires_at=now_utc() + timedelta(days=get_settings().guardian_consent_days),
        )
    )
    return Email(
        to=guardian_email,
        subject="Xác nhận tài khoản cho học sinh - Sử Ký Điều Tra",
        body=(
            f'Một tài khoản tên hiển thị "{user.display_name}" đã đăng ký và khai báo dưới '
            "16 tuổi, ghi email này là phụ huynh hoặc giáo viên.\n\nNếu bạn đồng ý, mở liên kết:\n"
            f"{_link('guardian-consent.html', raw)}\n\nNếu không, hãy bỏ qua email này."
        ),
    )


async def confirm_guardian(session: AsyncSession, raw: str) -> User:
    row = (
        await session.execute(
            select(GuardianConsent)
            .where(GuardianConsent.token_hash == hash_token(raw))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None or row.confirmed_at is not None:
        raise AppError(400, "TOKEN_INVALID", "Liên kết không hợp lệ hoặc đã được sử dụng")
    if row.expires_at <= now_utc():
        raise AppError(400, "TOKEN_EXPIRED", "Liên kết đã hết hạn")
    user = await session.get(User, row.user_id)
    if user is None:
        raise AppError(400, "TOKEN_INVALID", "Liên kết không hợp lệ hoặc đã được sử dụng")
    row.confirmed_at = now_utc()
    if user.status == UserStatus.pending_guardian:
        user.status = UserStatus.active
    session.add(
        AuditLog(
            actor_id=None,
            action="guardian_consent",
            target_type="user",
            target_id=str(user.id),
            after={"guardian_consent_id": str(row.id)},
        )
    )
    return user


def ensure_can_login(user: User) -> None:
    """Gọi sau khi đã xác thực đúng, để không lộ trạng thái tài khoản cho người lạ."""
    if user.status == UserStatus.pending_guardian:
        raise AppError(
            403, "GUARDIAN_CONSENT_PENDING", "Tài khoản đang chờ phụ huynh hoặc giáo viên xác nhận"
        )
    if user.status != UserStatus.active:
        raise AppError(403, "ACCOUNT_DISABLED", "Tài khoản đã bị vô hiệu hóa")
    if not user.email_verified:
        raise AppError(403, "EMAIL_NOT_VERIFIED", "Vui lòng xác minh email trước khi đăng nhập")


def set_refresh_cookie(response: Response, raw: str, expires_at: datetime) -> None:
    s = get_settings()
    response.set_cookie(
        s.refresh_cookie_name,
        raw,
        expires=expires_at,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=not s.is_dev or s.refresh_cookie_samesite == "none",
        samesite=s.refresh_cookie_samesite,  # type: ignore[arg-type]
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(get_settings().refresh_cookie_name, path=REFRESH_COOKIE_PATH)


async def issue_session(session: AsyncSession, user: User, response: Response) -> TokenOut:
    refresh = await issue_refresh_token(session, user.id)
    set_refresh_cookie(response, refresh.raw, refresh.expires_at)
    return TokenOut(
        access_token=create_access_token(user),
        expires_in=get_settings().access_token_minutes * 60,
        refresh_expires_at=refresh.expires_at,
    )
