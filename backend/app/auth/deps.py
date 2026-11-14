"""Dependency xác thực và phân quyền theo ma trận vai trò (Req 24.1–24.3).

Thứ bậc: player < editor < reviewer < admin. Giáo_Viên là cờ `is_teacher` cộng thêm;
Quản_Trị_Viên có toàn quyền nên cũng qua được yêu cầu "teacher".
"""

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import TokenError, decode_access_token
from app.db import get_session
from app.errors import AppError
from app.models import Role, User, UserStatus

ROLE_RANK = {Role.player: 0, Role.editor: 1, Role.reviewer: 2, Role.admin: 3}
TEACHER: Literal["teacher"] = "teacher"
RoleReq = Role | Literal["teacher"]

_bearer = HTTPBearer(auto_error=False)
_WWW = {"WWW-Authenticate": "Bearer"}


def _unauthorized(code: str, message: str) -> AppError:
    return AppError(401, code, message, headers=_WWW)


async def current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise _unauthorized("TOKEN_MISSING", "Cần đăng nhập")
    try:
        claims = decode_access_token(creds.credentials)
        user_id = uuid.UUID(claims["sub"])
    except TokenError as exc:
        msg = "Phiên đăng nhập đã hết hạn" if exc.code == "TOKEN_EXPIRED" else "Token không hợp lệ"
        raise _unauthorized(exc.code, msg) from exc
    except ValueError as exc:
        raise _unauthorized("TOKEN_INVALID", "Token không hợp lệ") from exc

    # Đọc vai trò từ DB để thay đổi vai trò/vô hiệu hóa có hiệu lực ngay
    user = await session.get(User, user_id)
    if user is None or user.status != UserStatus.active:
        raise _unauthorized("TOKEN_INVALID", "Tài khoản không còn hoạt động")
    return user


def has_role(user: User, required: RoleReq) -> bool:
    if required == TEACHER:
        return user.is_teacher or user.role == Role.admin
    return ROLE_RANK[user.role] >= ROLE_RANK[Role(required)]


def require_role(*roles: RoleReq) -> Callable[..., Awaitable[User]]:
    """Cho qua khi người dùng thỏa ít nhất một yêu cầu; ngược lại 403 FORBIDDEN_ROLE."""
    if not roles:
        raise ValueError("require_role cần ít nhất một vai trò")

    async def _dep(user: Annotated[User, Depends(current_user)]) -> User:
        if not any(has_role(user, r) for r in roles):
            raise AppError(403, "FORBIDDEN_ROLE", "Không có quyền thực hiện thao tác này")
        return user

    return _dep


CurrentUser = Annotated[User, Depends(current_user)]
