"""Cấu hình chung cho các bộ test của game."""

import pytest


@pytest.fixture(autouse=True)
def _fresh_fonts():
    """Một bộ test tắt pygame lúc kết thúc làm font đã lưu sẵn hỏng; xoá bộ nhớ font để bộ sau tự nạp lại."""
    from core import fonts

    fonts._fonts.clear()
    fonts._text_cache.clear()
    yield
