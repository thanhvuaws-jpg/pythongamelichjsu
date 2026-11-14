"""Chiến mã vẽ riêng: ngựa hồng, bờm và đuôi đen, yên đỏ viền vàng, dây cương đỏ, tua đỏ trước ngực.

Vẽ ở độ phân giải thấp rồi phóng to 4 lần cho cùng độ nét với nhân vật. Bốn hướng, mỗi hướng hai khung phi.
"""

from __future__ import annotations

import pygame

from core import sprites

OUT = (24, 18, 16)
COAT, COAT_D, COAT_L = (128, 70, 40), (92, 48, 28), (162, 98, 60)
MANE = (34, 26, 24)
CLOTH, GOLD = (190, 40, 36), (226, 180, 70)
HOOF = (60, 52, 46)
_cache: dict[str, dict[str, list[pygame.Surface]]] = {}


def _side(frame: int) -> pygame.Surface:
    """Nhìn ngang, đầu quay sang phải."""
    s = pygame.Surface((26, 18), pygame.SRCALPHA)
    pygame.draw.polygon(s, MANE, [(3, 6), (0, 9), (1, 12), (4, 9)])  # đuôi bay
    legs = ((7, 0), (10, 1), (17, 0), (20, 1)) if frame == 0 else ((6, 1), (11, 0), (16, 1), (21, 0))
    for x, lift in legs:  # bốn chân
        pygame.draw.rect(s, OUT, (x - 1, 11, 3, 6 - lift))
        pygame.draw.rect(s, COAT_D, (x, 11, 1, 5 - lift))
        pygame.draw.rect(s, HOOF, (x - 1, 16 - lift, 3, 1))
    pygame.draw.ellipse(s, OUT, (3, 5, 19, 9))  # thân
    pygame.draw.ellipse(s, COAT, (4, 6, 17, 7))
    pygame.draw.line(s, COAT_L, (7, 7), (17, 7))
    pygame.draw.polygon(s, OUT, [(17, 7), (21, 1), (25, 2), (25, 5), (21, 6), (20, 9)])  # cổ và đầu
    pygame.draw.polygon(s, COAT, [(18, 7), (21, 2), (24, 3), (24, 4), (21, 5), (20, 8)])
    pygame.draw.line(s, MANE, (17, 6), (20, 1))  # bờm
    s.set_at((22, 3), OUT)  # mắt
    pygame.draw.line(s, CLOTH, (21, 5), (24, 3))  # dây cương
    pygame.draw.rect(s, CLOTH, (9, 4, 7, 5))  # yên và vải yên
    pygame.draw.rect(s, GOLD, (9, 8, 7, 1))
    pygame.draw.rect(s, OUT, (9, 4, 7, 5), 1)
    pygame.draw.line(s, CLOTH, (19, 9), (19, 11))  # tua đỏ trước ngực
    s.set_at((19, 11), GOLD)
    return s


def _front(frame: int, back: bool) -> pygame.Surface:
    """Nhìn từ trước (`back` là nhìn từ sau, thấy đuôi)."""
    s = pygame.Surface((14, 20), pygame.SRCALPHA)
    for x, lift in ((4, frame), (9, 1 - frame)):
        pygame.draw.rect(s, OUT, (x - 1, 12, 3, 7 - lift))
        pygame.draw.rect(s, COAT_D, (x, 12, 1, 6 - lift))
    pygame.draw.ellipse(s, OUT, (1, 7, 12, 9))
    pygame.draw.ellipse(s, COAT, (2, 8, 10, 7))
    pygame.draw.rect(s, CLOTH, (1, 8, 12, 4))  # vải yên hai bên
    pygame.draw.rect(s, GOLD, (1, 11, 12, 1))
    if back:
        pygame.draw.polygon(s, MANE, [(6, 12), (8, 12), (9, 18), (5, 18)])  # đuôi
    else:
        pygame.draw.rect(s, OUT, (4, 0, 6, 9))  # đầu nhìn thẳng
        pygame.draw.rect(s, COAT, (5, 1, 4, 7))
        pygame.draw.rect(s, MANE, (5, 0, 4, 2))
        s.set_at((5, 3), OUT)
        s.set_at((8, 3), OUT)
        pygame.draw.line(s, CLOTH, (4, 5), (9, 5))
        pygame.draw.line(s, CLOTH, (7, 9), (7, 11))
    return s


def views() -> dict[str, list[pygame.Surface]]:
    """Khung hình theo hướng, cùng dạng với ngựa thường để thay thế được ngay."""
    if "v" not in _cache:
        right = [sprites.scaled(_side(i)) for i in range(2)]
        _cache["v"] = {
            "right": right,
            "left": [pygame.transform.flip(f, True, False) for f in right],
            "down": [sprites.scaled(_front(i, False)) for i in range(2)],
            "up": [sprites.scaled(_front(i, True)) for i in range(2)],
        }
    return _cache["v"]
