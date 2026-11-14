"""Nạp font nhúng và vẽ chữ tiếng Việt.

Trình duyệt không có font hệ thống nên phải dùng TTF nhúng (Be Vietnam Pro, Noto Serif - SIL OFL).
Mọi chuỗi được chuẩn hoá NFC trước khi vẽ để dấu gõ kiểu tổ hợp không bị tách rời.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pygame

_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_FILES = {
    "ui": "BeVietnamPro-Regular.ttf",
    "semi": "BeVietnamPro-SemiBold.ttf",
    "bold": "BeVietnamPro-Bold.ttf",
    "black": "BeVietnamPro-ExtraBold.ttf",
    "italic": "BeVietnamPro-Italic.ttf",
    "serif": "NotoSerif.ttf",
}
_fonts: dict[tuple[str, int], pygame.font.Font] = {}
_text_cache: dict[tuple, pygame.Surface] = {}
_CACHE_LIMIT = 900


def font(name: str = "ui", size: int = 20) -> pygame.font.Font:
    key = (name, size)
    if key not in _fonts:
        _fonts[key] = pygame.font.Font(str(_DIR / _FILES[name]), size)
    return _fonts[key]


def nfc(s: object) -> str:
    return unicodedata.normalize("NFC", str(s))


def render(s: object, fnt: pygame.font.Font, color: tuple) -> pygame.Surface:
    """Render có cache: vẽ chữ khá tốn trên WebAssembly mà nội dung thường lặp lại."""
    key = (nfc(s), id(fnt), tuple(color))
    cached = _text_cache.get(key)
    if cached is None:
        if len(_text_cache) > _CACHE_LIMIT:
            _text_cache.clear()
        cached = fnt.render(key[0], True, color)
        _text_cache[key] = cached
    return cached


def text(
    surface: pygame.Surface,
    s: object,
    fnt: pygame.font.Font,
    color: tuple,
    pos: tuple,
    anchor: str = "topleft",
    shadow: tuple | None = None,
) -> pygame.Rect:
    img = render(s, fnt, color)
    rect = img.get_rect(**{anchor: (round(pos[0]), round(pos[1]))})
    if shadow:
        surface.blit(render(s, fnt, shadow), rect.move(1, 2))
    surface.blit(img, rect)
    return rect


def wrap(s: object, fnt: pygame.font.Font, width: int) -> list[str]:
    """Ngắt dòng theo độ rộng pixel, giữ các dấu xuống dòng có sẵn."""
    lines: list[str] = []
    for para in nfc(s).split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            test = f"{cur} {w}" if cur else w
            if fnt.size(test)[0] <= width or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def paragraph(
    surface: pygame.Surface,
    s: object,
    fnt: pygame.font.Font,
    color: tuple,
    x: int,
    y: int,
    width: int,
    gap: int = 6,
    align: str = "left",
    max_chars: int | None = None,
) -> int:
    """Vẽ đoạn văn, trả về y của đáy đoạn. `max_chars` dùng cho hiệu ứng chữ chạy."""
    line_h = fnt.get_linesize() + gap
    left = max_chars
    for line in wrap(s, fnt, width):
        shown = line
        if left is not None:
            if left <= 0:
                break
            shown = line[:left]
            left -= len(line)
        if shown:
            if align == "center":
                text(surface, shown, fnt, color, (x + width / 2, y), "midtop")
            else:
                text(surface, shown, fnt, color, (x, y))
        y += line_h
    return y


def height_of(s: object, fnt: pygame.font.Font, width: int, gap: int = 6) -> int:
    return len(wrap(s, fnt, width)) * (fnt.get_linesize() + gap)
