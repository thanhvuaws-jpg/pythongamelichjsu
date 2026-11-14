"""Endpoint /api/v1/auth: đăng ký, xác minh, đăng nhập, refresh, logout, đặt lại mật khẩu."""

import math
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import lockout, service
from app.auth.deps import CurrentUser
from app.auth.jwt import (
    TokenError,
    create_access_token,
    now_utc,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.auth.password import DUMMY_HASH, MIN_PASSWORD_LENGTH, hash_password, verify_password
from app.config import get_settings
from app.db import get_session
from app.email import Email, send_email_safe
from app.errors import AppError
from app.models import AuditLog, TokenPurpose, User
from app.schemas.auth import (
    LoginIn,
    MeOut,
    MessageOut,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    RegisterIn,
    RegisterOut,
    TokenIn,
    TokenOut,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
Session = Annotated[AsyncSession, Depends(get_session)]
RefreshCookie = Annotated[str | None, Cookie(alias=get_settings().refresh_cookie_name)]


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AppError(
            400,
            "PASSWORD_TOO_SHORT",
            f"Mật khẩu cần tối thiểu {MIN_PASSWORD_LENGTH} ký tự",
            {"min_length": MIN_PASSWORD_LENGTH},
        )


def _locked_error(until) -> AppError:
    retry = max(1, math.ceil((until - now_utc()).total_seconds()))
    return AppError(
        423,
        "ACCOUNT_LOCKED",
        "Đăng nhập tạm khóa do nhập sai nhiều lần, vui lòng thử lại sau",
        {"retry_after": retry},
        headers={"Retry-After": str(retry)},
    )


@router.post("/register", response_model=RegisterOut, status_code=201)
async def register(body: RegisterIn, session: Session, bg: BackgroundTasks) -> RegisterOut:
    _check_password(body.password)
    needs_guardian = service.validate_registration(
        body.birth_year, body.accept_policy, body.email, body.guardian_email
    )
    skip_email = get_settings().skip_email_verification
    if skip_email:
        message = (
            "Đã tạo tài khoản. Vì bạn dưới 16 tuổi, giáo viên hoặc quản trị viên "
            "cần kích hoạt trước khi đăng nhập."
            if needs_guardian
            else "Đã tạo tài khoản, mời bạn đăng nhập."
        )
    else:
        message = (
            "Đã gửi email xác minh. Tài khoản sẽ hoạt động sau khi phụ huynh "
            "hoặc giáo viên xác nhận."
            if needs_guardian
            else "Đã gửi email xác minh, vui lòng kiểm tra hộp thư."
        )
    ready = skip_email and not needs_guardian

    existing = await session.scalar(select(User).where(User.email == body.email))
    if existing is not None:
        bg.add_task(
            send_email_safe,
            Email(
                to=body.email,
                subject="Có yêu cầu đăng ký bằng email của bạn - Sử Ký Điều Tra",
                body="Email này đã có tài khoản. Nếu quên mật khẩu, hãy dùng chức năng đặt lại.",
            ),
        )
        return RegisterOut(needs_guardian=needs_guardian, message=message, ready=ready)

    user = service.new_user(
        email=body.email,
        display_name=body.display_name,
        birth_year=body.birth_year,
        needs_guardian=needs_guardian,
        password_hash=hash_password(body.password),
        email_verified=skip_email,
    )
    session.add(user)
    await session.flush()
    emails = [] if skip_email else [await service.start_email_verification(session, user)]
    if needs_guardian and not skip_email:
        emails.append(await service.start_guardian_consent(session, user, body.guardian_email))
    await session.commit()
    for email in emails:
        bg.add_task(send_email_safe, email)
    return RegisterOut(needs_guardian=needs_guardian, message=message, ready=ready)


@router.post("/verify-email", response_model=MessageOut)
async def verify_email(body: TokenIn, session: Session) -> MessageOut:
    user = await service.consume_one_time_token(session, body.token, TokenPurpose.verify_email)
    user.email_verified = True
    await session.commit()
    return MessageOut(message="Email đã được xác minh")


@router.post("/guardian-consent/{token}", response_model=MessageOut)
async def guardian_consent(token: str, session: Session) -> MessageOut:
    await service.confirm_guardian(session, token)
    await session.commit()
    return MessageOut(message="Cảm ơn bạn đã xác nhận, tài khoản đã được kích hoạt")


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, session: Session, response: Response) -> TokenOut:
    until = await lockout.locked_until(session, body.email)
    if until:
        raise _locked_error(until)

    user = await session.scalar(select(User).where(User.email == body.email))
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not ok or user is None:
        await lockout.record_attempt(session, body.email, success=False)
        await session.commit()
        until = await lockout.locked_until(session, body.email)
        if until:
            raise _locked_error(until)
        raise AppError(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu không đúng")

    await lockout.record_attempt(session, body.email, success=True)
    await session.commit()
    service.ensure_can_login(user)
    out = await service.issue_session(session, user, response)
    await session.commit()
    return out


@router.post("/refresh", response_model=TokenOut)
async def refresh(session: Session, response: Response, sk_refresh: RefreshCookie = None):
    if not sk_refresh:
        raise AppError(401, "TOKEN_MISSING", "Cần đăng nhập")
    try:
        user_id, issued = await rotate_refresh_token(session, sk_refresh)
    except TokenError as exc:
        await session.commit()  # lưu việc thu hồi hàng loạt khi phát hiện dùng lại token
        service.clear_refresh_cookie(response)
        raise AppError(401, exc.code, "Phiên đăng nhập không hợp lệ hoặc đã hết hạn") from exc

    user = await session.get(User, user_id)
    if user is None:
        raise AppError(401, "TOKEN_INVALID", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn")
    try:
        service.ensure_can_login(user)
    except AppError:
        await revoke_all_refresh_tokens(session, user.id)
        await session.commit()
        raise
    await session.commit()
    service.set_refresh_cookie(response, issued.raw, issued.expires_at)
    return TokenOut(
        access_token=create_access_token(user),
        expires_in=get_settings().access_token_minutes * 60,
        refresh_expires_at=issued.expires_at,
    )


@router.post("/logout", status_code=204)
async def logout(session: Session, sk_refresh: RefreshCookie = None) -> Response:
    if sk_refresh:
        await revoke_refresh_token(session, sk_refresh)
        await session.commit()
    response = Response(status_code=204)
    service.clear_refresh_cookie(response)
    return response


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser) -> MeOut:
    return MeOut(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=user.role.value,
        is_teacher=user.is_teacher,
    )


@router.post("/password-reset/request", response_model=MessageOut)
async def password_reset_request(
    body: PasswordResetRequestIn, session: Session, bg: BackgroundTasks
) -> MessageOut:
    user = await session.scalar(select(User).where(User.email == body.email))
    if user is not None:
        minutes = get_settings().password_reset_minutes
        raw = await service.create_one_time_token(
            session, user.id, TokenPurpose.reset_password, timedelta(minutes=minutes)
        )
        await session.commit()
        link = f"{get_settings().web_base_url.rstrip('/')}/reset-password.html?token={raw}"
        bg.add_task(
            send_email_safe,
            Email(
                to=user.email,
                subject="Đặt lại mật khẩu - Sử Ký Điều Tra",
                body=(
                    f"Mở liên kết sau để đặt mật khẩu mới:\n{link}\n\n"
                    f"Liên kết có hiệu lực {minutes} phút và chỉ dùng được một lần. "
                    "Nếu bạn không yêu cầu, hãy bỏ qua email này."
                ),
            ),
        )
    return MessageOut(message="Nếu email tồn tại, liên kết đặt lại mật khẩu đã được gửi")


@router.post("/password-reset/confirm", response_model=MessageOut)
async def password_reset_confirm(body: PasswordResetConfirmIn, session: Session) -> MessageOut:
    _check_password(body.new_password)
    user = await service.consume_one_time_token(session, body.token, TokenPurpose.reset_password)
    user.password_hash = hash_password(body.new_password)
    user.email_verified = True  # người dùng đã chứng minh sở hữu email
    await revoke_all_refresh_tokens(session, user.id)
    session.add(
        AuditLog(
            actor_id=user.id, action="password_reset", target_type="user", target_id=str(user.id)
        )
    )
    await session.commit()
    return MessageOut(message="Đã đặt lại mật khẩu, vui lòng đăng nhập lại")
