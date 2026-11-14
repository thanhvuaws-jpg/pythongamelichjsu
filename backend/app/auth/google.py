"""Đăng nhập Google OAuth 2.0 (authorization code + PKCE) (Req 23.5).

- Liên kết theo `google_sub`; nếu chưa có thì liên kết với tài khoản cùng email
  (Google đã xác minh email).
- Người dùng mới phải bổ sung năm sinh và đồng ý chính sách (Req 27.1–27.2) qua
  `POST /auth/google/complete` với vé đăng ký ký số, hiệu lực ngắn.
- Phiên đăng nhập được trao qua cookie refresh HttpOnly; Web_Shell gọi /auth/refresh
  để lấy access token, nên token không xuất hiện trên URL.
"""

import base64
import hashlib
import secrets
from datetime import timedelta
from typing import Annotated
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.jwt import now_utc
from app.config import get_settings
from app.db import get_session
from app.email import send_email_safe
from app.errors import AppError
from app.models import AuditLog, User
from app.schemas.auth import Email, TokenOut

router = APIRouter(prefix="/api/v1/auth/google", tags=["auth"])
Session = Annotated[AsyncSession, Depends(get_session)]

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
STATE_COOKIE = "sk_google_state"
STATE_TTL = timedelta(minutes=10)
TICKET_TTL = timedelta(minutes=15)


class GoogleIdentity(BaseModel):
    sub: str
    email: str
    email_verified: bool = False
    name: str | None = None


class GoogleCompleteIn(BaseModel):
    ticket: Annotated[str, Field(max_length=4096)]
    birth_year: int
    accept_policy: bool
    display_name: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    guardian_email: Email | None = None


def _sign(claims: dict, ttl: timedelta, aud: str) -> str:
    s = get_settings()
    payload = {**claims, "aud": aud, "exp": now_utc() + ttl}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def _unsign(token: str, aud: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm], audience=aud)
    except jwt.PyJWTError as exc:
        raise AppError(400, "OAUTH_STATE_INVALID", "Phiên đăng nhập Google không hợp lệ") from exc


def _require_configured() -> None:
    s = get_settings()
    if not s.google_client_id or not s.google_client_secret:
        raise AppError(503, "OAUTH_NOT_CONFIGURED", "Đăng nhập Google chưa được cấu hình")


def _web_redirect(page: str, fragment: dict[str, str]) -> RedirectResponse:
    # Dùng fragment (#) để giá trị không gửi tới máy chủ và không vào log truy cập
    url = f"{get_settings().web_base_url.rstrip('/')}/{page}#{urlencode(fragment)}"
    return RedirectResponse(url, status_code=303)


@router.get("/login")
async def google_login() -> RedirectResponse:
    _require_configured()
    s = get_settings()
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    params = {
        "client_id": s.google_client_id,
        "redirect_uri": s.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": challenge.decode(),
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    resp = RedirectResponse(f"{AUTH_URL}?{urlencode(params)}", status_code=303)
    resp.set_cookie(
        STATE_COOKIE,
        _sign({"state": state, "verifier": verifier}, STATE_TTL, "google-state"),
        max_age=int(STATE_TTL.total_seconds()),
        path="/api/v1/auth/google",
        httponly=True,
        secure=not s.is_dev,
        samesite="lax",  # cookie phải đi kèm khi Google chuyển hướng về (GET top-level)
    )
    return resp


async def fetch_google_identity(code: str, verifier: str) -> GoogleIdentity:
    s = get_settings()
    async with httpx.AsyncClient(timeout=10) as client:
        tok = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "redirect_uri": s.google_redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            },
        )
        if tok.status_code != 200:
            raise AppError(400, "OAUTH_EXCHANGE_FAILED", "Không xác thực được với Google")
        # Access token lấy trực tiếp từ token endpoint qua TLS nên userinfo là đáng tin
        info = await client.get(
            USERINFO_URL, headers={"Authorization": f"Bearer {tok.json()['access_token']}"}
        )
        if info.status_code != 200:
            raise AppError(400, "OAUTH_EXCHANGE_FAILED", "Không xác thực được với Google")
    return GoogleIdentity.model_validate(info.json())


async def link_or_find_user(session: AsyncSession, ident: GoogleIdentity) -> User | None:
    """Trả user đã liên kết/được liên kết, hoặc None nếu cần đăng ký mới."""
    user = await session.scalar(select(User).where(User.google_sub == ident.sub))
    if user is not None:
        return user
    user = await session.scalar(select(User).where(User.email == ident.email))
    if user is None:
        return None
    if not user.email_verified:
        # Chống chiếm trước tài khoản: người khác có thể đã đăng ký bằng email này mà
        # chưa xác minh; chủ email thật (đã qua Google) nhận tài khoản, mật khẩu cũ bị gỡ.
        user.password_hash = None
        user.email_verified = True
    user.google_sub = ident.sub
    session.add(
        AuditLog(actor_id=user.id, action="link_google", target_type="user", target_id=str(user.id))
    )
    return user


@router.get("/callback")
async def google_callback(
    session: Session,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    sk_google_state: Annotated[str | None, Cookie()] = None,
) -> Response:
    _require_configured()
    if error or not code or not state or not sk_google_state:
        return _web_redirect("login.html", {"error": "OAUTH_CANCELLED"})
    saved = _unsign(sk_google_state, "google-state")
    if not secrets.compare_digest(saved["state"], state):
        return _web_redirect("login.html", {"error": "OAUTH_STATE_INVALID"})

    try:
        ident = await fetch_google_identity(code, saved["verifier"])
    except (AppError, httpx.HTTPError):
        return _web_redirect("login.html", {"error": "OAUTH_EXCHANGE_FAILED"})
    if not ident.email_verified:
        return _web_redirect("login.html", {"error": "GOOGLE_EMAIL_NOT_VERIFIED"})
    ident.email = ident.email.strip().lower()

    user = await link_or_find_user(session, ident)
    if user is None:
        ticket = _sign(
            {"sub": ident.sub, "email": ident.email, "name": ident.name or ""},
            TICKET_TTL,
            "google-signup",
        )
        resp: Response = _web_redirect("register-google.html", {"ticket": ticket})
    else:
        try:
            service.ensure_can_login(user)
        except AppError as exc:
            await session.commit()
            return _web_redirect("login.html", {"error": exc.code})
        resp = _web_redirect("play.html", {"login": "google"})
        await service.issue_session(session, user, resp)
    await session.commit()
    resp.delete_cookie(STATE_COOKIE, path="/api/v1/auth/google")
    return resp


@router.post(
    "/complete",
    response_model=TokenOut,
    status_code=201,
    responses={202: {"description": "Chờ người giám hộ xác nhận"}},
)
async def google_complete(
    body: GoogleCompleteIn, session: Session, response: Response, bg: BackgroundTasks
):
    claims = _unsign(body.ticket, "google-signup")
    needs_guardian = service.validate_registration(
        body.birth_year, body.accept_policy, claims["email"], body.guardian_email
    )
    exists = await session.scalar(
        select(User.id).where((User.email == claims["email"]) | (User.google_sub == claims["sub"]))
    )
    if exists is not None:
        raise AppError(409, "ACCOUNT_EXISTS", "Tài khoản đã tồn tại, vui lòng đăng nhập lại")

    name = (body.display_name or claims.get("name") or claims["email"].split("@")[0])[:64]
    user = service.new_user(
        email=claims["email"],
        display_name=name,
        birth_year=body.birth_year,
        needs_guardian=needs_guardian,
        google_sub=claims["sub"],
        email_verified=True,
    )
    session.add(user)
    await session.flush()
    if needs_guardian:
        email = await service.start_guardian_consent(session, user, body.guardian_email)
        await session.commit()
        bg.add_task(send_email_safe, email)
        return JSONResponse(
            {
                "needs_guardian": True,
                "message": "Đã gửi email cho phụ huynh hoặc giáo viên; "
                "tài khoản hoạt động sau khi được xác nhận",
            },
            status_code=202,
            background=bg,
        )
    out = await service.issue_session(session, user, response)
    await session.commit()
    return out
