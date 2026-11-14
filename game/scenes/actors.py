"""Những thứ có mặt trên map: vật thể tương tác được và thú đi lại cho làng xóm có sức sống."""

from __future__ import annotations

import math
import random

import pygame
from core import sprites
from core.sprites import TILE

# Tên -> (ảnh, số khung, độ phóng, tốc độ theo ô/giây)
CRITTERS = {
    "chicken": ("animal/chicken.png", 2, 3, 0.9), "dog": ("animal/dog.png", 2, 3, 1.6),
    "frog": ("animal/frog.png", 2, 3, 1.1), "cow": ("animal/cow.png", 2, 3, 0.4),
}
SCARE_RADIUS = TILE * 1.6
WANDER = 3
HORSE_BODY = (196, 66, 44)
HORSE_TAIL = (84, 96, 84)
OUTLINE = (24, 16, 14)


def _back_view(front: pygame.Surface) -> pygame.Surface:
    """Ngựa nhìn từ sau: gói asset chỉ có mặt trước, nên tô kín mặt bằng màu thân rồi vẽ thêm cái đuôi."""
    w, h = front.get_size()
    back = front.copy()
    for y in range(h):
        for x in range(w):
            r, g, b, a = front.get_at((x, y))
            if not a:
                continue
            around = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
            inside = all(0 <= i < w and 0 <= j < h and front.get_at((i, j))[3] for i, j in around)
            is_face = r > 200 and g > 130  # phần mõm màu da
            is_line = inside and r < 70 and g < 60  # mắt và nét vẽ bên trong mặt
            if y >= h // 3 and (is_face or is_line):
                back.set_at((x, y), HORSE_BODY)
    cx = w // 2
    pygame.draw.rect(back, OUTLINE, (cx - 2, h // 2 - 1, 4, h // 2 - 1))
    pygame.draw.rect(back, HORSE_TAIL, (cx - 1, h // 2, 2, h // 2 - 3))
    return back


def horse_views() -> dict[str, list[pygame.Surface]]:
    """Con ngựa theo bốn hướng, mỗi hướng hai khung hình."""
    side = sprites.strip("animal/horse.png", 2)
    sheet = sprites.image("animal/horse_front.png")
    unit = sheet.get_width() // 2
    front = [sheet.subsurface((i * unit, 0, unit, sheet.get_height())) for i in range(2)]
    return {
        "right": side,
        "left": [pygame.transform.flip(f, True, False) for f in side],
        "down": [sprites.scaled(f) for f in front],
        "up": [sprites.scaled(_back_view(f)) for f in front],
    }


def boat_views(img: pygame.Surface) -> dict[str, pygame.Surface]:
    """Thuyền nhìn từ trên xuống nên xoay được: mũi thuyền trong ảnh gốc hướng sang phải."""
    hull = img.subsurface(img.get_bounding_rect()).copy()
    return {
        "right": hull,
        "left": pygame.transform.flip(hull, True, False),
        "up": pygame.transform.rotate(hull, 90),
        "down": pygame.transform.rotate(hull, -90),
    }


class Actor:
    """Mọi thứ người chơi có thể đi tới và tương tác."""

    def __init__(self, kind, tile, name="", label="", cast=None, img=None, relic=None, objective=None, lines=None, data=None):
        self.kind = kind
        self.x = tile[0] * TILE + TILE / 2
        self.y = tile[1] * TILE + TILE - 8
        self.name, self.label = name, label
        self.cast = cast
        self.img = img
        self.relic = relic
        self.objective = objective
        self.lines = lines or []
        self.data = data
        self.facing = "down"
        self.frame = 0.0
        self.home = (self.x, self.y)
        self.goal = None
        self.wait = random.uniform(0.5, 4)


class Critter:
    """Gà, chó, ếch, bò: lang thang gần chỗ ở, gà và ếch giật mình khi người lại gần."""

    def __init__(self, kind: str, tile: tuple[int, int]):
        name, count, scale, speed = CRITTERS[kind]
        self.kind = kind
        self.frames = sprites.strip(name, count, scale)
        self.flipped = [pygame.transform.flip(f, True, False) for f in self.frames]
        self.x = tile[0] * TILE + TILE / 2
        self.y = tile[1] * TILE + TILE - 8
        self.home = (self.x, self.y)
        self.speed = speed * TILE
        self.goal: tuple[float, float] | None = None
        self.wait = random.uniform(0.2, 3)
        self.frame = 0.0
        self.left = random.random() < 0.5

    def _pick_goal(self, game_map):
        gx = self.home[0] + random.randint(-WANDER, WANDER) * TILE
        gy = self.home[1] + random.randint(-WANDER, WANDER) * TILE
        if not game_map.blocked(int(gx // TILE), int(gy // TILE)):
            self.goal = (gx, gy)

    def update(self, dt: float, game_map, px: float, py: float) -> None:
        if self.kind in ("chicken", "frog") and (self.x - px) ** 2 + (self.y - py) ** 2 < SCARE_RADIUS ** 2:
            ang = math.atan2(self.y - py, self.x - px)
            nx, ny = self.x + math.cos(ang) * TILE * 2, self.y + math.sin(ang) * TILE * 2
            if not game_map.blocked(int(nx // TILE), int(ny // TILE)):
                self.goal = (nx, ny)
        if self.goal is None:
            self.wait -= dt
            if self.wait <= 0:
                self.wait = random.uniform(1.5, 5)
                self._pick_goal(game_map)
            return
        dx, dy = self.goal[0] - self.x, self.goal[1] - self.y
        dist = math.hypot(dx, dy)
        if dist < 4:
            self.goal = None
            return
        step = self.speed * dt
        nx, ny = self.x + dx / dist * step, self.y + dy / dist * step
        if game_map.blocked(int(nx // TILE), int(ny // TILE)):
            self.goal = None
            return
        self.x, self.y = nx, ny
        self.left = dx < 0
        self.frame += dt * 6

    def image(self) -> pygame.Surface:
        frames = self.flipped if self.left else self.frames
        return frames[int(self.frame) % len(frames)]


def make_critters(game_map, specs: list[dict]) -> list[Critter]:
    """Thả thú ở các ô đi được quanh vị trí đã định; dùng số giả ngẫu nhiên cố định để map không đổi giữa các lần chơi."""
    rng = random.Random(len(specs))
    out = []
    for sp in specs:
        ax, ay = sp["at"]
        tiles = [(ax + dx, ay + dy) for dx in range(-3, 4) for dy in range(-3, 4) if not game_map.blocked(ax + dx, ay + dy)]
        rng.shuffle(tiles)
        out.extend(Critter(sp["kind"], tile) for tile in tiles[: sp.get("n", 1)])
    return out
