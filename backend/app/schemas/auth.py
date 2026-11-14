"""Schema Pydantic cho các endpoint xác thực."""

import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 320 or not _EMAIL_RE.match(value):
        raise ValueError("Email không hợp lệ")
    return value


Email = Annotated[str, AfterValidator(normalize_email)]
# Độ dài tối thiểu kiểm tra trong router để trả mã PASSWORD_TOO_SHORT (Req 23.1)
Password = Annotated[str, Field(max_length=256)]


class RegisterIn(BaseModel):
    email: Email
    password: Password
    display_name: Annotated[str, Field(min_length=1, max_length=64)]
    birth_year: int
    accept_policy: bool
    guardian_email: Email | None = None


class RegisterOut(BaseModel):
    # Phản hồi giống nhau dù email đã tồn tại hay chưa, tránh dò email
    needs_guardian: bool
    message: str
    # True khi đăng nhập được ngay, không phải chờ email
    ready: bool = False


class TokenIn(BaseModel):
    token: Annotated[str, Field(min_length=10, max_length=256)]


class LoginIn(BaseModel):
    email: Email
    password: Password


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_at: datetime


class PasswordResetRequestIn(BaseModel):
    email: Email


class PasswordResetConfirmIn(BaseModel):
    token: Annotated[str, Field(min_length=10, max_length=256)]
    new_password: Password


class MessageOut(BaseModel):
    message: str


class MeOut(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    is_teacher: bool
