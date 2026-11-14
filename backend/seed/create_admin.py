"""Tạo hoặc nâng quyền tài khoản quản trị đầu tiên từ biến môi trường ADMIN_EMAIL, ADMIN_PASSWORD.

Chạy tự động mỗi lần máy chủ khởi động. Không đặt hai biến này thì bỏ qua. Tài khoản đã có sẵn
chỉ được nâng quyền, mật khẩu không bị đổi, nên đổi mật khẩu rồi khởi động lại vẫn an toàn.

    python -m seed.create_admin
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.auth.password import MIN_PASSWORD_LENGTH, hash_password
from app.auth.service import current_year, new_user
from app.config import get_settings
from app.db import SessionLocal, engine
from app.models import Role, User, UserStatus
from app.schemas.auth import normalize_email

ADULT_AGE = 30


async def main() -> str:
    settings = get_settings()
    email = settings.admin_email.strip()
    password = settings.admin_password
    if not email or not password:
        return "Chưa đặt ADMIN_EMAIL và ADMIN_PASSWORD, bỏ qua bước tạo quản trị viên"
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"ADMIN_PASSWORD cần tối thiểu {MIN_PASSWORD_LENGTH} ký tự, bỏ qua"
    email = normalize_email(email)
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            user = new_user(
                email=email,
                display_name="Quản trị viên",
                birth_year=current_year() - ADULT_AGE,
                needs_guardian=False,
                password_hash=hash_password(password),
                email_verified=True,
            )
            session.add(user)
            message = "Đã tạo tài khoản quản trị"
        else:
            message = "Tài khoản đã có, chỉ nâng lên quản trị"
        user.role = Role.admin
        user.status = UserStatus.active
        user.email_verified = True
        await session.commit()
    await engine.dispose()
    return message


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # console Windows không in được tiếng Việt
    print(asyncio.run(main()))
