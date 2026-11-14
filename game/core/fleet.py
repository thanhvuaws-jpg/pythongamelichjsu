"""Thuyền và doi bùn quanh cọc, dùng chung cho trận Bạch Đằng và cảnh hồi ức."""

from __future__ import annotations

import pygame

from core import sprites

OUTLINE = (40, 30, 26)
_shoals: dict[int, pygame.Surface] = {}


def shoal(level: int) -> pygame.Surface:
    """Doi bùn lộ ra quanh chân cọc khi triều rút; vẽ nhỏ rồi phóng to để cùng nét với tile."""
    if level not in _shoals:
        w, h = 14 + level * 8, 5 + level * 3
        low = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(low, (226, 240, 240), low.get_rect())
        pygame.draw.ellipse(low, (112, 86, 60), low.get_rect().inflate(-2, -2))
        pygame.draw.ellipse(low, (156, 124, 86), (w // 4, h // 4, w // 2, max(1, h // 2)))
        _shoals[level] = sprites.scaled(low, 3)
    return _shoals[level]


def add_flag(canvas: pygame.Surface, color) -> None:
    """Cắm cờ lên thuyền; tách riêng để cờ vẫn giữ màu đỏ trên cảnh nâu cũ."""
    width = canvas.get_width()
    hull_h = int(width * 0.4)
    deck = canvas.get_height() - hull_h
    pygame.draw.rect(canvas, (60, 40, 28), (width // 3, deck - 16, 3, 24))
    pygame.draw.polygon(canvas, color, [(width // 3 + 3, deck - 16), (width // 3 + 20, deck - 10), (width // 3 + 3, deck - 4)])


def boat_sprite(width, tint=None, sail=None, flag=None) -> pygame.Surface:
    """Thuyền lấy từ gói asset; thuyền địch nhuộm tối hơn và có buồm."""
    src = sprites.image("tiles/boat.png")
    k = width / src.get_width()
    hull = pygame.transform.scale(src, (width, int(src.get_height() * k)))
    h = hull.get_height()
    canvas = pygame.Surface((width, h + int(width * 0.3)), pygame.SRCALPHA)
    deck = canvas.get_height() - h
    canvas.blit(hull, (0, deck))
    if tint:
        canvas.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
    if sail:
        mast = width // 2 - 4
        pygame.draw.rect(canvas, (60, 40, 28), (mast + 2, 0, 4, canvas.get_height() - h // 2))
        pygame.draw.polygon(canvas, OUTLINE, [(mast - 26, 8), (mast + 32, 2), (mast + 38, deck + 4), (mast - 32, deck + 6)])
        pygame.draw.polygon(canvas, sail, [(mast - 22, 12), (mast + 28, 6), (mast + 33, deck), (mast - 27, deck + 2)])
    if flag:
        add_flag(canvas, flag)
    return canvas
