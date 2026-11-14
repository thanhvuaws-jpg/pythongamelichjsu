"""Băm mật khẩu bằng argon2 (Req 23.2)."""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_hasher = PasswordHash((Argon2Hasher(),))

MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password, password_hash)
    except Exception:  # noqa: BLE001 - hash hỏng coi như sai mật khẩu
        return False


# Hash giả để so sánh khi email không tồn tại, giữ thời gian phản hồi đồng đều
DUMMY_HASH = hash_password("dummy-password-for-timing")
