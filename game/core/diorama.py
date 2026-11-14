"""Cảnh pixel art cho phần hồi ức: dựng bằng tile rồi chuyển màu nâu cũ, thay cho tranh vẽ bằng code."""

from __future__ import annotations

import random

import pygame

from core import art, sprites, theme
from core.sprites import TILE
from core.tilemap import PATH, RICE, WATER, TileMap
from core.worldgen import BUSHES, Builder

COLS, ROWS = 27, 15
DEFAULT_GROUND = (330.0, 474.0)
# Dải đất (theo chiều dọc màn hình) trong các cảnh có sông hồ, để lính không đứng trên mặt nước
GROUND = {"bach_dang": (258.0, 312.0), "nhu_nguyet": (330.0, 436.0), "van_don": None, "ho_guom": None}
_scenes: dict[str, pygame.Surface] = {}
_old: dict[str, pygame.Surface] = {}


def _crowd(surface, names, x0, y0, cols, rows, gap=52, facing="up"):
    """Đám đông đứng yên: bô lão họp ở Diên Hồng, quần chúng ở Ba Đình."""
    rng = random.Random(x0 * 7 + y0)
    for j in range(rows):
        for i in range(cols):
            c = sprites.cast(rng.choice(names))
            surface.blit(c.walk[facing][0], (x0 + i * gap + rng.randint(-6, 6), y0 + j * (gap - 10) + rng.randint(-3, 3)))


def render(key: str, cols: int, rows: int, build, shade_water=None) -> pygame.Surface:
    """Dựng một cảnh tĩnh bằng tile, dùng chung cho hồi ức và nền trận đánh.

    `shade_water` nhuộm tối các ô nước để sau khi chuyển màu nâu cũ, mặt nước vẫn tách hẳn khỏi mặt đất.
    """
    spec = {"size": [cols, rows], "spawn": [0, 0], "portal": [0, 0], "mentor": [0, 0], "zones": {}, "roads": []}
    b = Builder(key, spec)
    build(b)
    world = b.world
    surf = pygame.Surface((cols * TILE, rows * TILE))
    tm: TileMap = world.map
    tm.draw(surf, 0, 0)
    if shade_water:
        for y in range(rows):
            for x in range(cols):
                if tm.get(x, y) == WATER:
                    surf.fill(shade_water, (x * TILE, y * TILE, TILE, TILE), special_flags=pygame.BLEND_RGB_MULT)
    tm.forget()
    for p in sorted((p for items in world.props.values() for p in items), key=lambda p: p.sort):
        surf.blit(p.img, (p.x, p.y))
    for an in world.anims:
        surf.blit(an.frames[0], (an.x, an.y))
    return surf


def _lang_co(b):
    b.stroke([(0, 10), (26, 10)], PATH, 2)
    b.stroke([(13, 10), (13, 14)], PATH, 2)
    for name, x, y in (("house", 3, 3), ("house2", 9, 2), ("house", 16, 3), ("hut", 22, 5), ("banyan", 0, 5), ("banyan", 23, 10)):
        b.put(name, x, y)
    b.rice(2, 12, 8, 3)
    b.rice(16, 12, 7, 3)


def _bach_dang(b):
    b.rect(0, 5, COLS, 10, WATER)
    for name, x, y in (("gray_big", 1, 1), ("gray_tall", 6, 1), ("gray_big", 12, 0), ("gray_tall", 18, 1), ("gray_big", 21, 1), ("tree", 9, 2), ("tree", 16, 2)):
        b.put(name, x, y, True)
    for x in (4, 9, 14, 19, 24):
        b._stakes(x, 6, 8)
    b._boat(3, 8)
    b._boat(17, 10)


def _thanh_co(b):
    b.blob(13, 9, 11, 5, PATH)
    for x in range(COLS):
        b.put("wall", x, 2, True)
    b.put("temple", 12, 0, True)
    for name, x, y in (("house3", 3, 0), ("house2", 19, 0), ("pot_stand", 7, 3), ("pot_stand", 18, 3)):
        b.put(name, x, y, True)
    b.flag(10, 4)
    b.flag(16, 4)


def _nhu_nguyet(b):
    b.rect(0, 7, COLS, 5, WATER)
    b.put("temple", 12, 2, True)
    for name, x, y in (("banner_r", 10, 3), ("banner_r", 16, 3), ("banyan", 3, 1), ("banyan", 21, 1), ("tree", 7, 3), ("tree", 18, 3)):
        b.put(name, x, y, True)
    for x in range(0, COLS, 2):
        b.put("fence", x, 12, True)
        b.put("fence", x + 1, 12, True)
    b._boat(4, 8)
    b._boat(18, 9)


def _den_tran(b):
    b.blob(13, 9, 9, 5, PATH)
    b.put("temple", 12, 1, True)
    for name, x, y in (("banner_y", 10, 2), ("banner_y", 16, 2), ("statue", 6, 2), ("statue", 19, 2), ("banyan", 1, 3), ("banyan", 23, 3), ("gate", 12, 12)):
        b.put(name, x, y, True)


def _lam_son(b):
    b.put("rock_big", 1, 1, True)
    b.put("rock_tall", 22, 1, True)
    b.put("hut", 8, 3, True)
    b.put("hut2", 15, 3, True)
    for x, y in ((3, 6), (5, 8), (7, 10), (21, 7), (23, 9), (19, 11), (2, 11), (25, 12), (11, 1), (14, 1)):
        b.put("bamboo", x, y, True)
    b.stroke([(0, 12), (26, 9)], PATH, 2)


def _chi_lang(b):
    b.stroke([(0, 9), (26, 9)], PATH, 3)
    for x, name in ((0, "gray_big"), (5, "gray_tall"), (8, "gray_big"), (13, "gray_tall"), (16, "gray_big"), (21, "gray_tall"), (23, "gray_big")):
        b.put(name, x, 1, True)
        b.put(name, x, 12, True)
    b.put("rock", 12, 6, True)


def _van_don(b):
    b.rect(0, 0, COLS, ROWS, WATER)
    b.blob(5, 3, 6, 4, 0)
    b.put("gray_big", 2, 0, True)
    b.put("hut2", 6, 2, True)
    b._boat(10, 5)
    b._boat(15, 8)
    b._boat(4, 10)
    b._boat(19, 3)


def _ho_guom(b):
    b.blob(13, 8, 11, 6, WATER)
    b.blob(13, 8, 2, 1, 0)
    for dx in (-1, 0, 1):  # gò giữa hồ chỉ có cây cỏ: Tháp Rùa xây cuối thế kỷ XIX
        b.flat(13 + dx, 8, BUSHES[dx % len(BUSHES)])
    for name, x, y in (("banyan", 0, 1), ("banyan", 24, 1), ("tree", 2, 11), ("tree", 23, 11)):
        b.put(name, x, y, True)


def _dien_hong(b):
    b.blob(13, 9, 12, 6, PATH)
    b.put("temple", 12, 0, True)
    for x, name in ((4, "banner_r"), (8, "banner_y"), (18, "banner_y"), (22, "banner_r")):
        b.put(name, x, 1, True)
    b.put("statue", 2, 1, True)
    b.put("statue", 23, 1, True)


def _ba_dinh(b):
    b.blob(13, 9, 14, 6, PATH)
    b.put("temple", 12, 0, True)
    b.put("house3", 3, 0, True)
    b.put("house2", 19, 0, True)
    for x in (9, 17):
        b.flag(x, 3)


def _tan_trao(b):
    b.stroke([(13, 8), (13, 14)], PATH, 2)
    b.put("banyan", 12, 3, True)
    b.put("hut", 5, 4, True)
    b.put("hut2", 18, 4, True)
    b.flag(10, 6)
    for x, y in ((2, 8), (4, 10), (23, 8), (21, 10), (1, 12), (24, 12), (8, 11), (17, 11)):
        b.put("bamboo", x, y, True)


def _dien_bien(b):
    b.blob(13, 10, 13, 6, RICE)
    for x in range(COLS):
        if x % 2 == 0:
            b.map.set(x, 9, PATH)
            b.map.set(x + 1, 9, PATH)
    for x, name in ((0, "gray_big"), (5, "pines"), (10, "gray_big"), (15, "pines"), (20, "gray_big"), (24, "gray_tall")):
        b.put(name, x, 0, True)
    b.put("tent", 4, 3, True)
    b.put("tent3", 19, 3, True)
    b.flag(13, 4)


def _huong_dan(b):
    """Sân khấu của trailer hướng dẫn: con đường ngang chạy trên hộp lời dẫn, nhà cửa phía trên."""
    b.stroke([(0, 7), (26, 7)], PATH, 2)
    b.stroke([(13, 7), (13, 0)], PATH, 2)
    for name, x, y in (("house", 5, 2), ("house3", 16, 2), ("banyan", 9, 3), ("tree", 3, 5), ("tree", 21, 5), ("bamboo", 11, 4), ("bamboo", 15, 5), ("well", 8, 6)):
        b.put(name, x, y, True)


def _vo_dai(b):
    b.rect(0, 0, COLS, ROWS, PATH)
    b.put("temple", 12, -1, True)
    for x, name in ((5, "banner_r"), (9, "banner_y"), (17, "banner_y"), (21, "banner_r")):
        b.put(name, x, 0, True)
    for y in range(2, 11):
        b.put("fence_v", 3, y, True)
        b.put("fence_v", 23, y, True)
    for x in range(3, 24):
        b.put("fence", x, 10, True)


def _trai_quan(b):
    b.stroke([(0, 8), (26, 8)], PATH, 3)
    for name, x, y in (("tent", 4, -1), ("tent2", 9, -1), ("tent3", 15, -1), ("tent", 20, -1), ("tree", 2, 10), ("tree", 22, 10)):
        b.put(name, x, y, True)
    b.flag(8, 1)
    b.flag(18, 1, "yellow")


_BUILDERS = {
    "vo_dai": _vo_dai, "trai_quan": _trai_quan, "huong_dan": _huong_dan,
    "lang_co": _lang_co, "bach_dang": _bach_dang, "thanh_co": _thanh_co, "nhu_nguyet": _nhu_nguyet, "den_tran": _den_tran,
    "dien_hong": _dien_hong, "van_don": _van_don, "lam_son": _lam_son, "chi_lang": _chi_lang, "ho_guom": _ho_guom,
    "ba_dinh": _ba_dinh, "tan_trao": _tan_trao, "dien_bien": _dien_bien, "geneve": _ba_dinh,
}


def scene(name: str) -> pygame.Surface:
    """Cảnh màu, kích thước bằng màn hình."""
    if name in _scenes:
        return _scenes[name]
    full = render("dio_" + name, COLS, ROWS, _BUILDERS.get(name, _lang_co))
    left = (full.get_width() - theme.WIDTH) // 2
    surf = full.subsurface((left, 0, theme.WIDTH, theme.HEIGHT)).copy()
    if name == "dien_hong":
        _crowd(surf, ("Master", "OldMan3", "Monk", "OldMan"), 170, 330, 14, 3, 68)
    elif name == "vo_dai":
        crowd = ("Villager", "Woman", "Boy", "Villager3", "Villager4", "OldMan3")
        _crowd(surf, crowd, 70, 62, 7, 1, 62, "down")
        _crowd(surf, crowd, 770, 62, 7, 1, 62, "down")
    elif name == "ba_dinh":
        _crowd(surf, ("Villager", "Villager3", "Villager4", "Woman", "Boy", "OldMan3"), 90, 300, 16, 3, 68)
    _scenes[name] = surf
    return surf


def to_old(surface: pygame.Surface) -> pygame.Surface:
    """Chuyển một ảnh sang màu nâu cũ của hồi ức."""
    img = pygame.transform.grayscale(surface)
    img.fill((255, 226, 178), special_flags=pygame.BLEND_RGB_MULT)
    img.fill((26, 14, 4), special_flags=pygame.BLEND_RGB_ADD)
    return img


def old(name: str) -> pygame.Surface:
    """Bản màu nâu cũ đã có viền tối, dùng thẳng làm nền hồi ức."""
    if name not in _old:
        img = to_old(scene(name))
        img.blit(art.vignette(), (0, 0))
        _old[name] = img
    return _old[name]


__all__ = ["scene", "old", "TILE"]
