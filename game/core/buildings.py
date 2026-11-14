"""Công trình kiến trúc Việt vẽ riêng: nhà tranh, nhà ngói, chùa, cổng làng, đình, nhà sàn, cung điện, cổng thành,
tường thành, luỹ đất, tháp canh, nhà phố thời Pháp.

Gói Ninja Adventure chỉ có nhà kiểu Nhật nên các công trình được vẽ bằng code ở độ phân giải 16 px một ô rồi phóng to 4
lần, cùng độ nét với tile. Chỉ vẽ những nét chung, phổ biến của kiến trúc truyền thống, không mô phỏng một công trình cụ
thể nào để khỏi sai chi tiết. Cổ Loa là thành đất nên có luỹ đất riêng, không dùng tường gạch.
"""

from __future__ import annotations

import pygame

from core import sprites

OUT = (20, 27, 27)
THATCH, THATCH_D, THATCH_L = (206, 170, 96), (160, 122, 62), (232, 204, 138)
EARTH, EARTH_D = (198, 150, 104), (160, 112, 74)
WOOD, WOOD_D, WOOD_L = (138, 88, 52), (96, 58, 34), (176, 122, 76)
TILE, TILE_D, TILE_L = (178, 84, 58), (130, 56, 40), (210, 118, 84)
DARK_TILE, DARK_TILE_D, DARK_TILE_L = (110, 96, 88), (80, 68, 62), (146, 130, 118)
BRICK, BRICK_D, BRICK_L = (176, 96, 72), (140, 72, 54), (204, 128, 96)
STONE, STONE_D, STONE_L = (176, 172, 160), (132, 128, 120), (210, 206, 196)
LACQUER, GOLD = (176, 40, 34), (226, 180, 70)
PLASTER, PLASTER_D, SHUTTER = (236, 206, 128), (204, 170, 96), (72, 110, 76)
DOOR = (52, 36, 28)
GRASS, GRASS_D = (120, 160, 72), (90, 126, 54)

_cache: dict[tuple, pygame.Surface] = {}


def _rect(s, color, r, outline=True):
    pygame.draw.rect(s, color, r)
    if outline:
        pygame.draw.rect(s, OUT, r, 1)


def _poly(s, color, pts, outline=True):
    pygame.draw.polygon(s, color, pts)
    if outline:
        pygame.draw.polygon(s, OUT, pts, 1)


def _roof(s, x0, x1, y_top, y_eave, inset, base, dark, light, stripes="h", curl=True):
    """Mái hình thang có đường viền, sọc ngói hoặc rơm, hai đầu đao cong lên."""
    pts = [(x0, y_eave), (x1, y_eave), (x1 - inset, y_top), (x0 + inset, y_top)]
    _poly(s, base, pts)
    if stripes == "h":  # rơm, lá: sọc ngang so le
        for y in range(y_top + 2, y_eave - 1, 3):
            k = (y - y_top) / max(1, y_eave - y_top)
            a, b = x0 + inset * (1 - k) + 1, x1 - inset * (1 - k) - 1
            pygame.draw.line(s, dark if (y // 3) % 2 else light, (a, y), (b, y))
    else:  # ngói: sọc dọc
        for x in range(x0 + 2, x1 - 1, 3):
            pygame.draw.line(s, dark, (x, y_top + 2), (x, y_eave - 1))
    pygame.draw.line(s, dark, (x0 + 1, y_eave - 1), (x1 - 1, y_eave - 1))
    pygame.draw.line(s, light, (x0 + inset + 1, y_top + 1), (x1 - inset - 1, y_top + 1))
    if curl:  # đầu đao
        for x, d in ((x0, -1), (x1, 1)):
            _poly(s, base, [(x, y_eave), (x + d * 3, y_eave - 4), (x - d * 1, y_eave - 2)])


def _bricks(s, r, base=BRICK, dark=BRICK_D):
    x0, y0, w, h = r
    pygame.draw.rect(s, base, r)
    for y in range(y0 + 3, y0 + h, 4):
        pygame.draw.line(s, dark, (x0, y), (x0 + w - 1, y))
    for row, y in enumerate(range(y0, y0 + h, 4)):
        for x in range(x0 + (2 if row % 2 else 0), x0 + w, 5):
            pygame.draw.line(s, dark, (x, y), (x, min(y0 + h - 1, y + 2)))
    pygame.draw.rect(s, OUT, r, 1)


# ----- từng công trình (vẽ ở 16 px một ô) -----
def nha_tranh(s):
    """Nhà tranh vách đất của làng quê Bắc Bộ."""
    _roof(s, 1, 46, 5, 24, 9, THATCH, THATCH_D, THATCH_L, "h", curl=False)
    pygame.draw.line(s, THATCH_D, (10, 5), (37, 5), 2)  # nóc rơm dày
    _rect(s, EARTH, (6, 24, 36, 18))
    pygame.draw.line(s, EARTH_D, (7, 25), (40, 25))
    _rect(s, DOOR, (20, 29, 8, 13))
    pygame.draw.rect(s, WOOD, (19, 28, 10, 1))
    for wx in (10, 32):
        _rect(s, DOOR, (wx, 29, 6, 5))
        for k in range(1, 6, 2):
            pygame.draw.line(s, WOOD_L, (wx + k, 30), (wx + k, 32))
    _rect(s, (186, 160, 120), (3, 42, 42, 4))


def nha_ngoi(s, gable=False, roof=(TILE, TILE_D, TILE_L)):
    """Nhà ngói ba gian, cửa bức bàn; `gable` là nhà có tường hồi bít đốc hai đầu."""
    _roof(s, 2, 61, 6, 25, 7, *roof, stripes="v")
    pygame.draw.line(s, roof[2], (9, 4), (54, 4), 2)  # bờ nóc
    for x, d in ((7, -1), (56, 1)):
        _poly(s, roof[0], [(x, 5), (x + d * 3, 1), (x + d * 1, 5)])
    _rect(s, WOOD, (6, 25, 52, 19))
    for px in (6, 23, 40, 56):  # cột
        pygame.draw.rect(s, WOOD_D, (px, 25, 2, 19))
    for bx in (9, 26, 43):  # cửa bức bàn
        _rect(s, WOOD_L, (bx, 28, 12, 16), False)
        for k in range(bx + 1, bx + 12, 2):
            pygame.draw.line(s, WOOD_D, (k, 28), (k, 43))
    _rect(s, DOOR, (28, 29, 8, 15))
    if gable:
        for gx in (1, 57):
            _bricks(s, (gx, 10, 6, 34))
            _rect(s, BRICK_L, (gx, 7, 6, 3))
    _rect(s, STONE, (4, 44, 56, 4))


def chua(s):
    """Chùa, đền: hai tầng mái chồng diêm đầu đao cong, cột son, bậc đá."""
    _rect(s, WOOD, (14, 14, 20, 5))
    _roof(s, 9, 39, 4, 16, 6, DARK_TILE, DARK_TILE_D, DARK_TILE_L, "v")
    _rect(s, GOLD, (22, 1, 4, 3))  # đỉnh nóc
    _roof(s, 1, 47, 18, 30, 8, DARK_TILE, DARK_TILE_D, DARK_TILE_L, "v")
    _rect(s, WOOD_D, (6, 30, 36, 12))
    for px in (7, 17, 29, 39):
        pygame.draw.rect(s, LACQUER, (px, 30, 2, 12))
    for dx in (11, 21, 32):
        _rect(s, DOOR, (dx, 33, 5, 9), False)
    _rect(s, STONE, (3, 42, 42, 3))
    _rect(s, STONE_L, (17, 44, 14, 4))


def cong_lang(s):
    """Cổng làng xây gạch có mái ngói nhỏ, ô giữa để trống cho người đi qua."""
    _roof(s, 3, 44, 1, 8, 4, TILE, TILE_D, TILE_L, "v")
    _bricks(s, (6, 8, 36, 7))
    _rect(s, STONE_L, (18, 9, 12, 4))
    pygame.draw.line(s, OUT, (20, 11), (27, 11))
    _bricks(s, (6, 15, 8, 17))
    _bricks(s, (34, 15, 8, 17))
    pygame.draw.arc(s, OUT, (14, 12, 20, 8), 3.14, 6.28, 1)


def dinh(s):
    """Đình làng: nhà gỗ lớn, mái rộng đầu đao cong vút, nền đá."""
    _roof(s, 1, 62, 3, 24, 9, DARK_TILE, DARK_TILE_D, DARK_TILE_L, "v")
    pygame.draw.line(s, DARK_TILE_L, (11, 2), (52, 2), 2)
    _rect(s, WOOD_D, (5, 24, 54, 16))
    for px in (6, 17, 28, 35, 46, 56):
        pygame.draw.rect(s, WOOD_L, (px, 24, 2, 16))
    _rect(s, DOOR, (19, 27, 26, 13), False)
    _rect(s, STONE, (2, 40, 60, 5))
    _rect(s, STONE_L, (24, 45, 16, 3))


def nha_san(s):
    """Nhà sàn vùng núi: mái lá lớn, vách tre đan, sàn gỗ trên hàng cột, cầu thang bên hông."""
    _roof(s, 0, 63, 2, 22, 10, THATCH, THATCH_D, THATCH_L, "h", curl=False)
    _rect(s, (168, 128, 78), (6, 22, 52, 12))
    for x in range(8, 57, 3):
        for y in range(23, 33, 3):
            pygame.draw.line(s, (130, 96, 56), (x, y), (x + 1, y + 1))
    _rect(s, DOOR, (28, 24, 8, 10))
    _rect(s, WOOD_D, (4, 33, 56, 2))
    for px in (8, 20, 32, 44, 54):
        _rect(s, WOOD, (px, 35, 2, 13), False)
    for k in range(5):  # cầu thang
        pygame.draw.line(s, WOOD_D, (58 + k // 2, 36 + k * 3), (62, 36 + k * 3))
    pygame.draw.line(s, WOOD_D, (58, 35), (62, 47))


def cung_dien(s):
    """Điện trong hoàng cung: nền đá cao có bậc thềm và lan can, hàng cột son, hai tầng mái lớn."""
    _rect(s, STONE, (2, 46, 76, 10))
    for x in range(4, 76, 4):
        pygame.draw.line(s, STONE_D, (x, 47), (x, 49))
    pygame.draw.line(s, STONE_D, (3, 50), (76, 50))
    _rect(s, STONE_L, (30, 54, 20, 10))
    for y in range(56, 64, 2):
        pygame.draw.line(s, STONE_D, (31, y), (48, y))
    for x in (28, 50):  # lan can bậc thềm
        _rect(s, STONE_D, (x, 50, 3, 14))
    _rect(s, (60, 40, 30), (8, 30, 64, 16))
    for px in range(9, 72, 9):
        pygame.draw.rect(s, LACQUER, (px, 30, 3, 16))
        pygame.draw.rect(s, GOLD, (px, 30, 3, 1))
    _rect(s, DOOR, (34, 34, 12, 12), False)
    _rect(s, LACQUER, (18, 17, 44, 4))
    _roof(s, 13, 66, 5, 18, 8, DARK_TILE, DARK_TILE_D, DARK_TILE_L, "v")
    pygame.draw.line(s, GOLD, (22, 4), (57, 4), 2)
    for x in (21, 58):
        _rect(s, GOLD, (x - 1, 1, 3, 3))
    _roof(s, 0, 79, 21, 31, 9, DARK_TILE, DARK_TILE_D, DARK_TILE_L, "v")


def cong_thanh(s):
    """Cổng thành xây gạch, cửa vòm ở giữa, trên có vọng lâu mái ngói."""
    _bricks(s, (2, 24, 76, 40))
    for x in range(2, 78, 8):  # răng cưa trên mặt thành
        _bricks(s, (x, 19, 5, 5))
    _rect(s, DOOR, (30, 40, 20, 24), False)
    pygame.draw.ellipse(s, DOOR, (30, 34, 20, 14))
    pygame.draw.arc(s, OUT, (29, 33, 22, 16), 0, 3.14, 1)
    _rect(s, STONE_L, (34, 27, 12, 5))
    _rect(s, WOOD_D, (22, 10, 36, 10))
    for px in (23, 32, 46, 55):
        pygame.draw.rect(s, LACQUER, (px, 10, 2, 10))
    _roof(s, 15, 65, 1, 12, 7, DARK_TILE, DARK_TILE_D, DARK_TILE_L, "v")


def tuong_thanh(s):
    """Một đoạn tường thành gạch có lỗ châu mai, ghép liền thành hàng."""
    _bricks(s, (0, 10, 16, 22))
    _bricks(s, (0, 5, 6, 5))
    _bricks(s, (10, 5, 6, 5))


def tuong_thanh_doc(s):
    _bricks(s, (2, 0, 12, 16))
    pygame.draw.line(s, BRICK_L, (3, 1), (12, 1))


def luy_dat(s):
    """Luỹ đất (như vòng thành Cổ Loa): gò đất đắp cao, cỏ phủ trên mặt."""
    _poly(s, EARTH, [(0, 31), (16, 31), (16, 9), (0, 9)], False)
    pygame.draw.rect(s, GRASS, (0, 6, 16, 6))
    for x in range(0, 16, 3):
        pygame.draw.line(s, GRASS_D, (x, 6), (x + 1, 10))
    for y in range(15, 31, 5):
        pygame.draw.line(s, EARTH_D, (0, y), (15, y))
    pygame.draw.line(s, OUT, (0, 6), (15, 6))
    pygame.draw.line(s, OUT, (0, 31), (15, 31))


def luy_dat_doc(s):
    pygame.draw.rect(s, EARTH, (2, 0, 12, 16))
    pygame.draw.rect(s, GRASS, (4, 0, 8, 16))
    pygame.draw.line(s, OUT, (2, 0), (2, 15))
    pygame.draw.line(s, OUT, (13, 0), (13, 15))


def thap_canh(s):
    """Chòi canh bằng gỗ: bốn cột, sàn có lan can, mái lá."""
    _roof(s, 1, 30, 1, 12, 6, THATCH, THATCH_D, THATCH_L, "h", curl=False)
    _rect(s, WOOD, (5, 12, 22, 8))
    for x in range(6, 26, 4):
        pygame.draw.line(s, WOOD_D, (x, 13), (x, 18))
    _rect(s, WOOD_D, (3, 20, 26, 3))
    for px in (6, 24):
        _rect(s, WOOD, (px, 23, 2, 41), False)
    for y in range(28, 62, 8):  # giằng chéo
        pygame.draw.line(s, WOOD_D, (7, y), (24, y + 6))
        pygame.draw.line(s, WOOD_D, (24, y), (7, y + 6))


def nha_pho(s):
    """Nhà phố Hà Nội thời Pháp: hai tầng tường vàng, mái ngói, ban công, cửa chớp xanh, tầng dưới bày hàng."""
    _roof(s, 2, 45, 2, 10, 4, TILE, TILE_D, TILE_L, "v", curl=False)
    _rect(s, PLASTER, (4, 10, 40, 34))
    pygame.draw.line(s, PLASTER_D, (5, 26), (42, 26))
    for wx in (9, 21, 33):  # cửa sổ tầng trên
        _rect(s, SHUTTER, (wx, 13, 6, 9))
        pygame.draw.line(s, OUT, (wx + 3, 13), (wx + 3, 21))
    _rect(s, WOOD_D, (6, 23, 36, 2), False)  # ban công
    for x in range(7, 42, 2):
        pygame.draw.line(s, OUT, (x, 21), (x, 23))
    for dx in (7, 19, 31):  # cửa hàng tầng dưới
        _rect(s, WOOD, (dx, 30, 10, 14))
        pygame.draw.line(s, WOOD_D, (dx + 5, 30), (dx + 5, 43))
    _rect(s, STONE, (2, 44, 44, 3))


# Tên vật thể -> (hàm vẽ, rộng, cao tính theo ô). Mấy tên cũ của gói asset được thay bằng kiểu nhà Việt.
DRAW = {
    "house": (nha_tranh, 3, 3), "house2": (nha_ngoi, 4, 3), "house3": (lambda s: nha_ngoi(s, True, (DARK_TILE, DARK_TILE_D, DARK_TILE_L)), 4, 3),
    "temple": (chua, 3, 3), "gate": (cong_lang, 3, 2),
    "dinh": (dinh, 4, 3), "nha_san": (nha_san, 4, 3), "cung_dien": (cung_dien, 5, 4), "cong_thanh": (cong_thanh, 5, 4),
    "tuong_thanh": (tuong_thanh, 1, 2), "tuong_thanh_doc": (tuong_thanh_doc, 1, 1), "luy_dat": (luy_dat, 1, 2),
    "luy_dat_doc": (luy_dat_doc, 1, 1), "thap_canh": (thap_canh, 2, 4), "nha_pho": (nha_pho, 3, 3),
}


def image(name: str, scale: int = sprites.SCALE) -> pygame.Surface:
    key = (name, scale)
    if key not in _cache:
        fn, w, h = DRAW[name]
        low = pygame.Surface((w * 16, h * 16), pygame.SRCALPHA)
        fn(low)
        _cache[key] = sprites.scaled(low, scale)
    return _cache[key]
