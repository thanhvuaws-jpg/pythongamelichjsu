"""`POST /me/export`, `DELETE /me` (Req 25.5, 27.4)."""

import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser
from app.auth.password import verify_password
from app.auth.service import clear_refresh_cookie
from app.db import get_session
from app.errors import AppError
from app.privacy.service import export_user_data, request_deletion
from app.users.router import ensure_not_last_admin

router = APIRouter(prefix="/api/v1/me", tags=["privacy"])
Session = Annotated[AsyncSession, Depends(get_session)]


class DeleteMeIn(BaseModel):
    # Bắt buộc với tài khoản có mật khẩu; tài khoản Google gửi confirm=true
    password: Annotated[str | None, Field(max_length=256)] = None
    confirm: bool = False


class DeleteMeOut(BaseModel):
    status: str
    purge_after: datetime


@router.post("/export")
async def export_me(session: Session, user: CurrentUser) -> Response:
    """Tệp JSON chứa dữ liệu cá nhân, tạo ngay khi yêu cầu (Req 27.4)."""
    data = await export_user_data(session, user)
    body = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode()
    return Response(
        body,
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="du-lieu-ca-nhan.json"',
            "Cache-Control": "no-store",
        },
    )


@router.delete("", response_model=DeleteMeOut)
async def delete_me(
    body: DeleteMeIn, session: Session, user: CurrentUser, response: Response
) -> DeleteMeOut:
    """Yêu cầu xóa tài khoản; job định kỳ xóa dữ liệu cá nhân trong vòng 30 ngày (Req 25.5)."""
    if user.password_hash:
        if not verify_password(body.password or "", user.password_hash):
            raise AppError(401, "INVALID_CREDENTIALS", "Mật khẩu không đúng")
    elif not body.confirm:
        raise AppError(400, "CONFIRM_REQUIRED", "Cần xác nhận yêu cầu xóa tài khoản")
    await ensure_not_last_admin(session, user)
    purge_after = await request_deletion(session, user)
    await session.commit()
    clear_refresh_cookie(response)
    return DeleteMeOut(status=user.status.value, purge_after=purge_after)
