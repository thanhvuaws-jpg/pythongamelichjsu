"""Sân khấu cho hồi ức: nhân vật, cờ, lửa, thuyền tự diễn theo lời kể, thay cho tranh tĩnh.

Mỗi đoạn hồi ức có thẻ `"stage": "<cảnh>:<nhịp>"`, kịch bản nằm trong `core/stage_scenes.py`. Mọi thứ trên sân khấu
tính vị trí theo thời gian kể từ đầu nhịp chứ không cộng dồn, nên đọc nhanh, đọc chậm hay rớt khung hình đều đúng cảnh.
Hình dựng màu nâu cũ, riêng cờ, lửa, ánh đèn và đồ vật quan trọng giữ màu thật cho nổi lên.

Hộp lời kể che phần dưới màn hình, nên mọi diễn biến đặt trong dải y từ khoảng 60 tới 480.
"""

from __future__ import annotations

import math
import random

import pygame

from core import art, diorama, fleet, fonts, sprites, theme
from core.tilemap import GRASS, PATH, RICE, WATER
from core.worldgen import prop_image

W, H = theme.WIDTH, theme.HEIGHT
S = 3  # cỡ nhân vật thường trên sân khấu, nhân vật chính dùng 4
RED, STAR = (200, 36, 30), (250, 214, 60)
NIGHT = (14, 18, 48)
ALLY = ("LinhDaiViet", "LinhDaiViet2")
# Quân ta theo giai đoạn: thời Ngô, Lý, Trần là lính Đại Việt; khởi nghĩa Lam Sơn chủ yếu là nghĩa quân áo nâu
ERA_ALLIES = {
    "tong": (("LinhDaiViet", "LinhDaiViet2"), "TuongDaiViet"),
    "nguyen": (("LinhDaiViet", "LinhDaiViet2"), "TuongDaiViet"),
    "minh": (("NghiaQuan", "NghiaQuan", "LinhDaiViet2"), "TuongDaiViet"),
    "co": (("LinhDaiViet",), "TuongDaiViet"),
}
# Quân phương Bắc theo giai đoạn: lính thường nhiều, tướng ít. Truyền thuyết Cổ Loa (thời Triệu Đà) không dùng
# trang phục Tống, Nguyên, Minh để khỏi lệch thời, nên dùng nhân vật áo sẫm chung chung.
ERA_FOES = {
    "tong": (("LinhTong",) * 5 + ("TuongTong",), "TuongTong"),
    "nguyen": (("LinhNguyen",) * 5 + ("TuongNguyen",), "TuongNguyen"),
    "minh": (("LinhMinh",) * 5 + ("TuongMinh",), "TuongMinh"),
    "co": (("NinjaGray",), "NinjaGray"),
}
BEAT_ERA = {
    "ai_chau": "tong", "bien": "tong", "tong": "tong", "nhu_nguyet": "tong",
    "ha_song": "nguyen", "dong_bo_dau": "nguyen", "binh_than": "nguyen", "dien_hong": "nguyen", "kiep_bac": "nguyen",
    "thien_mac": "nguyen", "van_don": "nguyen",
    "minh": "minh", "lam_son": "minh", "chi_linh": "minh", "tra_lan": "minh", "tot_dong": "minh", "chi_lang": "minh",
    "xuong_giang": "minh", "hoi_the": "minh", "binh_ngo": "minh", "co_loa": "co",
}
FOE = ERA_FOES["minh"][0]
PEOPLE = ("Villager", "Villager3", "Villager4", "Woman", "OldMan3", "Boy", "OldWoman")
ELDERS = ("OldMan", "OldMan3", "Master", "Monk", "OldWoman")
VIET_MINH = ("BoDoi",)
FRENCH = ("Inspector",)
MAX_FIRES_PER_FRAME = 3
_img: dict = {}


def _dir(dx: float, dy: float) -> str:
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def cached(key, build):
    out = _img.get(key)
    if out is None:
        out = _img[key] = build()
    return out


# ----- đường đi theo thời gian -----
class Track:
    """Các mốc (t, x, y), giữa hai mốc thì đi thẳng đều."""

    __slots__ = ("keys",)

    def __init__(self, x: float, y: float):
        self.keys: list[tuple[float, float, float]] = [(0.0, x, y)]

    def end(self) -> tuple[float, float, float]:
        return self.keys[-1]

    def go(self, t0: float, x: float, y: float, speed: float = 90.0) -> float:
        tl, xl, yl = self.keys[-1]
        if t0 > tl:
            self.keys.append((t0, xl, yl))
        start = max(t0, tl)
        dur = math.hypot(x - xl, y - yl) / max(1.0, speed)
        self.keys.append((start + dur, x, y))
        return start + dur

    def jump(self, t: float, x: float, y: float) -> None:
        """Dịch chuyển tức thì (đi vào nhà này, ra ở nhà khác)."""
        _, xl, yl = self.keys[-1]
        self.keys.append((t, xl, yl))
        self.keys.append((t, x, y))

    def at(self, t: float):
        """Trả về (x, y, đang đi, hướng đi gần nhất, lúc đổi hướng đó)."""
        keys = self.keys
        last_dir, last_t = None, -1.0
        for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:], strict=False):
            moving = x1 != x0 or y1 != y0
            if t < t1:
                if not moving or t1 <= t0:
                    return x0, y0, False, last_dir, last_t
                k = (t - t0) / (t1 - t0)
                return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, True, _dir(x1 - x0, y1 - y0), t
            if moving:
                last_dir, last_t = _dir(x1 - x0, y1 - y0), t1
        return keys[-1][1], keys[-1][2], False, last_dir, last_t


# ----- diễn viên -----
class Actor:
    """Một người trên sân khấu. Tư thế suy ra từ các khoảng thời gian: đánh, reo, đào, quỳ, ngã."""

    def __init__(self, cast, x, y, facing="right", side="ta", seed=0, mount=None):
        self.cast = cast
        self.track = Track(x, y)
        self.facing = facing
        self.side = side
        self.seed = seed
        self.mount = mount
        self.t_in = 0.0
        self.t_out: float | None = None
        self.dead_at: float | None = None
        self.faces: list[tuple[float, str]] = []
        self.modes: list[tuple[float, float | None, str]] = []
        self.gaps: list[tuple[float, float]] = []

    def visible(self, t: float) -> bool:
        if t < self.t_in or (self.t_out is not None and t >= self.t_out):
            return False
        return not any(a <= t < b for a, b in self.gaps)

    def pos(self, t: float) -> tuple[float, float]:
        x, y, *_ = self.track.at(t)
        return x, y

    def _mode(self, t: float) -> str:
        found, start = "idle", -1.0
        for t0, t1, mode in self.modes:
            if t0 <= t and (t1 is None or t < t1) and t0 >= start:
                found, start = mode, t0
        return found

    def _facing(self, t: float, mdir, mdir_t) -> str:
        facing, ft = self.facing, -1.0
        for tf, f in self.faces:
            if ft <= tf <= t:
                facing, ft = f, tf
        if mdir and mdir_t >= ft:
            facing = mdir
        return facing

    def draw(self, s: pygame.Surface, t: float, ox: int, oy: int) -> None:
        x, y, moving, mdir, mdir_t = self.track.at(t)
        x, y = x + ox, y + oy
        cast = self.cast
        if self.dead_at is not None and t >= self.dead_at:
            s.blit(cast.dead, cast.dead.get_rect(midbottom=(x, y)))
            return
        facing = self._facing(t, mdir, mdir_t)
        walk = cast.walk[facing]
        mode = "walk" if moving else self._mode(t)
        lift = 0.0
        if mode == "walk":
            img = walk[int(t * 7 + self.seed) % 4]
        elif mode == "kneel":
            img = _kneel(cast, facing)
        elif mode in ("fight", "work"):
            rate = 5 if mode == "fight" else 3
            img = cast.attack[facing] if int(t * rate + self.seed) % 2 else walk[0]
        elif mode == "cheer":
            img = cast.attack[facing] if int(t * 4 + self.seed) % 2 else walk[0]
            lift = abs(math.sin(t * 7 + self.seed)) * 7
        else:
            img = walk[0]
        if self.mount and mode != "kneel":
            frames = self.mount["left" if facing == "left" else "right"]
            horse = frames[int(t * 6) % 2 if moving else 0]
            s.blit(horse, horse.get_rect(midbottom=(x, y)))
            y -= horse.get_height() * 0.5
        s.blit(img, img.get_rect(midbottom=(x, y - lift)))


def _kneel(cast, facing) -> pygame.Surface:
    def build():
        img = cast.walk[facing][0]
        return pygame.transform.scale(img, (img.get_width(), int(img.get_height() * 0.78)))

    return cached(("kneel", id(cast), facing), build)


class Thing:
    """Đồ vật, cờ, lửa, nhãn chữ. `layer`: 0 xếp theo chiều sâu, -1 nằm sát đất, 1 phát sáng trên lớp đêm, 2 chữ."""

    def __init__(self, frames, x, y, fps=8.0, layer=0, anchor="midbottom", t_in=0.0, t_out=None, pop=False):
        self.frames = frames if isinstance(frames, list) else [frames]
        self.track = Track(x, y)
        self.fps = fps
        self.layer = layer
        self.anchor = anchor
        self.t_in = t_in
        self.t_out = t_out
        self.pop = pop
        self.follow: tuple[Actor, float, float] | None = None
        self.sink: tuple[float, float] | None = None
        self.spin = 0.0
        self.bob = 0.0
        self.beat: tuple[float, float] | None = None  # (chu kỳ, độ phồng) cho trống
        self.paint = None  # hàm vẽ riêng (s, t, ox, oy)
        self.sort_bias = 0.0  # thân thuyền xếp lùi lại để người đứng trên thuyền vẽ đè lên

    def visible(self, t: float) -> bool:
        if t < self.t_in or (self.t_out is not None and t >= self.t_out):
            return False
        return self.follow is None or self.follow[0].visible(t)

    def pos(self, t: float) -> tuple[float, float]:
        if self.follow:
            actor, dx, dy = self.follow
            x, y = actor.pos(t)
            return x + dx, y + dy
        x, y, *_ = self.track.at(t)
        return x, y

    def draw(self, s: pygame.Surface, t: float, ox: int, oy: int) -> None:
        if self.paint:
            self.paint(s, t, ox, oy)
            return
        x, y = self.pos(t)
        x, y = x + ox, y + oy + self.bob * math.sin(t * 2.2 + x * 0.01)
        img = self.frames[int(t * self.fps) % len(self.frames)]
        age = t - self.t_in
        if self.pop and age < 0.28:
            k = 0.35 + 0.65 * (age / 0.28)
            img = pygame.transform.scale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
        if self.beat:
            period, grow = self.beat
            k = 1 + grow * max(0.0, 1 - (t % period) / 0.18)
            img = pygame.transform.scale(img, (int(img.get_width() * k), int(img.get_height() * k)))
        if self.spin:
            img = _rotated(img, int(t * self.spin) // 15 * 15)
        if self.sink and t >= self.sink[0]:
            # Chìm dần: ảnh tụt xuống dưới mặt nước (đáy ảnh cũ), phần dưới mặt nước bị cắt đi
            k = min(1.0, (t - self.sink[0]) / self.sink[1])
            img = _rotated(img, int(-14 * k))
            w, h = img.get_size()
            down = int(h * 0.85 * k)
            s.blit(img.subsurface((0, 0, w, h - down)), (x - w / 2, y - h + down))
            return
        s.blit(img, img.get_rect(**{self.anchor: (x, y)}))


def _rotated(img: pygame.Surface, deg: int) -> pygame.Surface:
    if not deg:
        return img
    return cached(("rot", id(img), deg), lambda: pygame.transform.rotate(img, deg))


# ----- hình vẽ thêm (vẽ ở độ phân giải thấp rồi phóng to cho cùng nét với tile) -----
def old(img: pygame.Surface) -> pygame.Surface:
    return cached(("old", id(img)), lambda: sprites.sepia(img))


def prop(name: str, scale: int = 4) -> pygame.Surface:
    def build():
        return sprites.sepia(prop_image(name, scale))

    return cached(("prop", name, scale), build)


def icon(name: str, scale: int = 3, color: bool = False) -> pygame.Surface:
    return cached(("icon", name, scale, color), lambda: (lambda i: i if color else sprites.sepia(i))(sprites.icon(f"ui/{name}.png", scale)))


def flame_frames(scale: int = 2) -> list[pygame.Surface]:
    return cached(("flame", scale), lambda: sprites.strip("fx/flame.png", 8, scale))


def horse(scale: int = 3) -> dict[str, list[pygame.Surface]]:
    def build():
        side = [sprites.sepia(f) for f in sprites.strip("animal/horse.png", 2, scale)]
        return {"right": side, "left": [pygame.transform.flip(f, True, False) for f in side]}

    return cached(("horse", scale), build)


def chicken() -> list[pygame.Surface]:
    return cached("chicken", lambda: [sprites.sepia(f) for f in sprites.strip("animal/chicken.png", 2, 3)])


def flag_frames(kind: str) -> list[pygame.Surface]:
    """Cờ đỏ của ta giữ màu; cờ địch nhuộm nâu; `vn` là cờ đỏ sao vàng; `qcqt` là lá cờ Quyết chiến Quyết thắng."""

    def build():
        if kind in ("ta", "dich"):
            frames = sprites.strip("fx/flag_red.png" if kind == "ta" else "fx/flag_yellow.png", 4, 3)
            return frames if kind == "ta" else [sprites.sepia(f) for f in frames]
        out = []
        cw, ch = (26, 15) if kind == "qcqt" else (15, 10)
        for wave in range(4):
            low = pygame.Surface((cw + 1, 24), pygame.SRCALPHA)
            pygame.draw.rect(low, (70, 50, 34), (0, 0, 1, 24))
            for x in range(1, cw + 1):
                dy = round(math.sin(x * 0.7 + wave * 1.57) * 0.8)
                pygame.draw.line(low, RED, (x, 1 + dy), (x, ch + dy))
            if kind == "vn":
                _star(low, 8, 5 + round(math.sin(8 * 0.7 + wave * 1.57) * 0.8), 3)
            img = sprites.scaled(low, 4)
            if kind == "qcqt":
                f = fonts.font("black", 13)
                for i, line in enumerate(("QUYẾT CHIẾN", "QUYẾT THẮNG")):
                    txt = fonts.render(line, f, STAR)
                    img.blit(txt, txt.get_rect(center=(4 + cw * 2, 18 + i * 20 + round(math.sin(wave * 1.57) * 2))))
            out.append(img)
        return out

    return cached(("flag", kind), build)


def _star(s, cx, cy, r):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    pygame.draw.polygon(s, STAR, pts)


def banner_six() -> pygame.Surface:
    """Lá cờ đề sáu chữ. Sử không chép màu cờ; ở đây vẽ cờ đỏ chữ vàng theo cách quen thuộc, chữ chỉ vẽ thành nét."""

    def build():
        low = pygame.Surface((14, 30), pygame.SRCALPHA)
        pygame.draw.rect(low, (70, 50, 34), (0, 0, 1, 30))
        pygame.draw.rect(low, RED, (1, 1, 12, 18))
        for i in range(6):
            pygame.draw.rect(low, STAR, (3 + (i % 2) * 5, 3 + (i // 2) * 5, 3, 3))
        return sprites.scaled(low, 4)

    return cached("banner_six", build)


def orange(squashed: bool = False) -> pygame.Surface:
    def build():
        low = pygame.Surface((7, 6), pygame.SRCALPHA)
        if squashed:
            pygame.draw.ellipse(low, (226, 120, 30), (0, 3, 7, 3))
            low.set_at((1, 2), (240, 160, 50))
            low.set_at((5, 2), (240, 160, 50))
        else:
            pygame.draw.circle(low, (40, 24, 12), (3, 3), 3)
            pygame.draw.circle(low, (236, 136, 34), (3, 3), 2)
            low.set_at((3, 0), (80, 150, 60))
        return sprites.scaled(low, 3)

    return cached(("orange", squashed), build)


def drum() -> pygame.Surface:
    def build():
        low = pygame.Surface((14, 14), pygame.SRCALPHA)
        pygame.draw.rect(low, (40, 26, 18), (1, 3, 12, 9))
        pygame.draw.rect(low, (150, 52, 36), (2, 4, 10, 7))
        pygame.draw.ellipse(low, (40, 26, 18), (1, 1, 12, 5))
        pygame.draw.ellipse(low, (232, 206, 160), (2, 2, 10, 3))
        pygame.draw.line(low, (40, 26, 18), (3, 12), (1, 13))
        pygame.draw.line(low, (40, 26, 18), (10, 12), (12, 13))
        return sprites.sepia(sprites.scaled(low, 4))

    return cached("drum", build)


def cannon() -> pygame.Surface:
    def build():
        return sprites.sepia(art.cannon_sprite())

    return cached("cannon", build)


def bunker() -> pygame.Surface:
    def build():
        low = pygame.Surface((30, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(low, (24, 18, 14), (0, 2, 30, 18))
        pygame.draw.ellipse(low, (96, 104, 80), (1, 3, 28, 16))
        pygame.draw.ellipse(low, (120, 128, 98), (5, 4, 18, 6))
        pygame.draw.rect(low, (14, 10, 8), (11, 8, 8, 2))
        return sprites.sepia(sprites.scaled(low, 4))

    return cached("bunker", build)


def bike() -> pygame.Surface:
    """Xe đạp thồ chở bao gạo."""

    def build():
        low = pygame.Surface((22, 16), pygame.SRCALPHA)
        dark = (30, 22, 16)
        for cx in (4, 17):
            pygame.draw.circle(low, dark, (cx, 12), 3, 1)
        pygame.draw.line(low, dark, (4, 12), (10, 8))
        pygame.draw.line(low, dark, (10, 8), (17, 12))
        pygame.draw.line(low, dark, (10, 8), (16, 7))
        pygame.draw.line(low, dark, (16, 7), (18, 5))
        for x, y in ((3, 3), (8, 2), (6, 6)):
            pygame.draw.rect(low, dark, (x, y, 6, 4))
            pygame.draw.rect(low, (210, 190, 150), (x + 1, y + 1, 4, 2))
        return sprites.sepia(sprites.scaled(low, 3))

    return cached("bike", build)


def podium() -> pygame.Surface:
    def build():
        low = pygame.Surface((44, 18), pygame.SRCALPHA)
        pygame.draw.rect(low, (40, 28, 20), (0, 4, 44, 14))
        pygame.draw.rect(low, (176, 140, 96), (1, 5, 42, 4))
        pygame.draw.rect(low, (150, 40, 32), (1, 9, 42, 8))
        for x in range(4, 44, 8):
            pygame.draw.line(low, (120, 30, 24), (x, 10), (x, 16))
        return sprites.scaled(low, 4)

    return cached("podium", build)


def gunboat() -> pygame.Surface:
    def build():
        img = fleet.boat_sprite(170, (120, 124, 132))
        w, h = img.get_size()
        pygame.draw.rect(img, (40, 40, 44), (w // 2 - 22, h // 2 - 22, 44, 22))
        pygame.draw.rect(img, (110, 114, 120), (w // 2 - 19, h // 2 - 19, 38, 16))
        pygame.draw.line(img, (40, 40, 44), (w // 2 + 20, h // 2 - 14), (w // 2 + 54, h // 2 - 22), 4)
        return sprites.sepia(img)

    return cached("gunboat", build)


def boat(width: int = 130, side: str = "ta", sail: bool = False) -> dict[str, pygame.Surface]:
    """Thuyền nhìn ngang, hai chiều. Thuyền ta cắm cờ đỏ giữ màu."""

    def build():
        if side == "ta":
            img = sprites.sepia(fleet.boat_sprite(width))
            fleet.add_flag(img, RED)
        elif side == "dan":
            img = sprites.sepia(fleet.boat_sprite(width))
        else:
            img = sprites.sepia(fleet.boat_sprite(width, (150, 136, 150), sail=(150, 62, 50) if sail else None))
        return {"right": img, "left": pygame.transform.flip(img, True, False)}

    return cached(("boat", width, side, sail), build)


def glow(radius: int, color=(255, 214, 120), alpha: int = 110) -> pygame.Surface:
    def build():
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for i in range(radius, 0, -max(1, radius // 8)):
            a = int(alpha * (1 - i / radius) ** 0.7)
            pygame.draw.circle(s, (*color, a), (radius, radius), i)
        return s

    return cached(("glow", radius, color, alpha), build)


def label_img(text: str, style: str = "paper") -> pygame.Surface:
    """Nhãn địa danh, mốc thời gian: giấy dó viền đỏ; `big` là chữ lớn viền tối; `dark` là nhãn sơn mài."""

    def build():
        if style == "big":
            f = fonts.font("black", 60)
            body = fonts.render(text, f, theme.GOLD_LIGHT)
            out = pygame.Surface((body.get_width() + 8, body.get_height() + 8), pygame.SRCALPHA)
            shade = fonts.render(text, f, theme.LACQUER)
            for dx, dy in ((0, 0), (8, 0), (0, 8), (8, 8), (4, 0), (0, 4), (8, 4), (4, 8)):
                out.blit(shade, (dx, dy))
            out.blit(body, (4, 4))
            return out
        f = fonts.font("bold", 18)
        fg, bg, edge = (theme.GOLD_LIGHT, theme.LACQUER, theme.GOLD_DARK) if style == "dark" else (theme.LACQUER_RED, theme.PAPER, theme.LACQUER_RED)
        body = fonts.render(text, f, fg)
        out = pygame.Surface((body.get_width() + 24, body.get_height() + 10))
        out.fill(edge)
        out.fill(bg, out.get_rect().inflate(-4, -4))
        out.blit(body, (12, 5))
        return out

    return cached(("label", text, style), build)


# ----- phông nền -----
_bgs: dict[str, pygame.Surface] = {}
COLS, ROWS, CROP = 21, 12, 32  # 21 cột để vật rộng 3 ô đứng đúng giữa màn hình (cột 9-11)


def _san_dien(b):
    b.rect(1, 3, 19, 9, PATH)
    b.put("cung_dien", 8, -1, True)
    b.put("house3", 2, 0, True)
    b.put("house2", 15, 0, True)
    for x, n in ((7, "banner_r"), (8, "banner_y"), (12, "banner_y"), (13, "banner_r")):
        b.put(n, x, 1, True)
    b.put("statue", 1, 4, True)
    b.put("statue", 18, 4, True)
    b.put("tree", 0, 1, True)
    b.put("tree", 19, 1, True)


def _thanh(b):
    b.stroke([(10, 11), (10, 4)], PATH, 2)
    for x in range(COLS):
        if x not in (8, 9, 10, 11, 12):
            b.put("tuong_thanh", x, 2, True)
    b.put("cong_thanh", 8, 0, True)
    b.put("house3", 1, 0, True)
    b.put("house2", 15, 0, True)
    b.put("tree", 6, 0, True)
    b.put("tree", 12, 0, True)


def _song(b):
    b.rect(0, 2, COLS, 3, WATER)
    for x in (1, 5, 9, 14, 18):
        b.put("tree", x, 0, True)
    for x, y in ((0, 6), (1, 7), (19, 6), (20, 7)):
        b.put("bamboo", x, y, True)


def _song_nui(b):
    b.rect(0, 2, COLS, 3, WATER)
    for name, x in (("gray_big", 0), ("gray_tall", 5), ("pines", 7), ("gray_big", 12), ("pines", 16)):
        b.put(name, x, -1, True)
    for x, y in ((0, 6), (1, 7), (19, 6), (20, 7)):
        b.put("bamboo", x, y, True)


def _nhu_nguyet(b):
    b.rect(0, 2, COLS, 2, WATER)
    for x in range(0, 15):
        b.put("fence", x, 4, True)
    b.put("temple", 16, 4, True)
    for name, x in (("tent", 1), ("tent2", 6), ("tent3", 11), ("tent", 16)):
        b.put(name, x, -1, True)
    b.put("banyan", 19, 5, True)


def _bien(b):
    b.rect(0, 0, COLS, ROWS, WATER)
    b.blob(1, 0, 3, 2, GRASS)
    b.put("gray_big", 0, -1, True)
    b.put("pine", 3, 0, True)
    b.blob(19, 1, 3, 2, GRASS)
    b.put("gray_tall", 18, -1, True)
    b.put("pine", 16, 0, True)


def _rung(b):
    b.stroke([(0, 6), (20, 5)], PATH, 2)
    for name, x in (("pines", 0), ("rock_big", 5), ("pines", 13), ("rock_tall", 17)):
        b.put(name, x, -1, True)
    for x, y in ((0, 3), (1, 4), (19, 3), (20, 4), (4, 2), (16, 2)):
        b.put("bamboo", x, y, True)
    b.put("hut", 9, 2, True)


def _dinh(b):
    b.rect(4, 0, 2, ROWS, WATER)
    b.stroke([(7, 5), (20, 5)], PATH, 1)
    b.put("banyan", 9, 1, True)  # cây đa; đình vẽ riêng trong kịch bản
    b.put("nha_san", 17, 1, True)
    for name, x, y in (("pines", 0, -1), ("bamboo", 1, 3), ("bamboo", 2, 5), ("bamboo", 7, 0), ("tree", 19, 0)):
        b.put(name, x, y, True)


def _lang(b):
    b.stroke([(0, 5), (20, 5)], PATH, 2)
    for name, x, y in (("house", 2, 1), ("house2", 7, 0), ("house", 13, 1), ("hut", 17, 2), ("tree", 0, 0), ("tree", 11, 0)):
        b.put(name, x, y, True)
    b.put("well", 11, 3, True)
    b.rect(1, 7, 8, 4, RICE)
    b.rect(12, 7, 8, 4, RICE)


def _pho(b):
    b.rect(0, 4, COLS, 8, PATH)
    for x in (0, 3, 6, 9, 12, 15, 18):
        b.put("nha_pho", x, 1, True)
    b.put("tree", 19, 1, True)


def _quang_truong(b):
    b.rect(0, 2, COLS, 10, PATH)
    for x in (0, 3, 6, 13, 16, 19):
        b.put("tree", x, 0, True)


def _doc_nui(b):
    b.stroke([(0, 8), (8, 5), (14, 3), (20, 2)], PATH, 2)
    for name, x, y in (("gray_big", 0, -1), ("pines", 4, -1), ("gray_tall", 10, -1), ("pines", 16, 5), ("gray_big", 12, 6), ("rock", 3, 3), ("pines", 18, -1)):
        b.put(name, x, y, True)


def _canh_dong(b):
    for x0, y0, w, h in ((0, 2, 7, 3), (8, 6, 6, 4), (14, 2, 7, 3), (0, 6, 6, 4), (15, 6, 6, 4)):
        b.rect(x0, y0, w, h, RICE)
    b.stroke([(0, 5), (20, 5)], PATH, 1)
    b.stroke([(10, 11), (10, 2)], PATH, 1)
    for name, x in (("gray_big", 0), ("pines", 5), ("gray_big", 14), ("pines", 17)):
        b.put(name, x, -1, True)


def _hem_nui(b):
    b.rect(0, 3, COLS, 3, PATH)
    for name, x in (("gray_big", 0), ("gray_tall", 4), ("pines", 6), ("gray_big", 10), ("gray_tall", 14), ("pines", 16)):
        b.put(name, x, -1, True)
    for name, x in (("gray_big", 1), ("pines", 6), ("gray_big", 12), ("gray_tall", 17)):
        b.put(name, x, 6, True)


def _dong_lay(b):
    b.rect(0, 1, COLS, ROWS - 1, RICE)
    b.rect(0, 4, COLS, 1, PATH)
    b.rect(13, 0, 2, ROWS, WATER)
    for name, x in (("tree", 1), ("bamboo", 6), ("tree", 9), ("bamboo", 17), ("tree", 18)):
        b.put(name, x, 0, True)


def _trai(b):
    b.stroke([(0, 6), (20, 6)], PATH, 2)
    for name, x in (("tent", 1), ("tent2", 5), ("tent3", 9), ("tent2", 13), ("tent", 17)):
        b.put(name, x, -1 if x != 9 else 0, True)
    b.flag(8, 2)
    b.flag(12, 2)
    b.put("thap_canh", 0, 2, True)
    b.put("thap_canh", 19, 2, True)


def _thanh_dat(b):
    """Thành đất Cổ Loa: luỹ đất đắp cao, có lối vào ở giữa."""
    b.stroke([(10, 11), (10, 4)], PATH, 2)
    for x in range(COLS):
        if x not in (9, 10, 11):
            b.put("luy_dat", x, 2, True)
    b.put("temple", 9, -1, True)
    b.put("tree", 4, 0, True)
    b.put("tree", 15, 0, True)


BACKDROPS = {
    "san_dien": _san_dien, "thanh": _thanh, "song": _song, "song_nui": _song_nui, "nhu_nguyet": _nhu_nguyet, "bien": _bien,
    "rung": _rung, "dinh": _dinh, "lang": _lang, "pho": _pho, "quang_truong": _quang_truong, "doc_nui": _doc_nui,
    "canh_dong": _canh_dong, "hem_nui": _hem_nui, "dong_lay": _dong_lay, "trai": _trai, "thanh_dat": _thanh_dat,
}


def backdrop(name: str) -> pygame.Surface:
    if name not in _bgs:
        full = diorama.render("stg_" + name, COLS, ROWS, BACKDROPS[name], shade_water=(118, 138, 160))
        img = diorama.to_old(full.subsurface((CROP, 0, W, H)).copy())
        img.blit(art.vignette(), (0, 0))
        _bgs[name] = img
    return _bgs[name]


# ----- đạo diễn -----
class Stage:
    """Một nhịp hồi ức. Kịch bản gọi các hàm dựng (`troop`, `thing`, `label`...) và các hàm diễn (`shift`, `fight`...)."""

    def __init__(self, fx, audio):
        self.fx = fx
        self.audio = audio
        self.key = ""
        self._clear()

    @property
    def gore(self) -> bool:
        return self.fx.violence == "day_du"

    def _clear(self):
        self.t = 0.0
        self.bg: pygame.Surface | None = None
        self.actors: list[Actor] = []
        self.things: list[Thing] = []
        self.events: list[list] = []
        self.repeats: list[list] = []
        self.dims: list[tuple[float, float, float, float]] = []
        self.flashes: list[tuple[float, float]] = []
        self._seed = 0

    def set_beat(self, key: str):
        from core.stage_scenes import BEATS

        if key == self.key:
            return
        self.key = key
        self._clear()
        era = BEAT_ERA.get(key.split(":")[0], "minh")
        self.foe, self.foe_lead = ERA_FOES[era]
        self.ally, self.ally_lead = ERA_ALLIES[era]
        bg, script = BEATS[key]
        self.bg = backdrop(bg)
        random.seed(hash(key) & 0xFFFF)
        script(self)

    # ----- dựng -----
    def actor(self, name, x, y, facing="right", side="ta", scale=S, t_in=0.0, mount=False) -> Actor:
        self._seed += 1
        a = Actor(sprites.cast(name, scale, old=True), x, y, facing, side, self._seed % 7, horse(scale) if mount else None)
        a.t_in = t_in
        self.actors.append(a)
        return a

    def troop(self, names, x, y, cols, rows, gap=(44, 30), facing="right", side="ta", jitter=5, t_in=0.0, scale=S) -> list[Actor]:
        """Một đội người xếp hàng; (x, y) là góc trên bên trái của đội hình."""
        rng = random.Random(int(x * 31 + y * 7 + cols))
        out = []
        for j in range(rows):
            for i in range(cols):
                name = names[(i + j * 3) % len(names)] if len(names) > 1 else names[0]
                px = x + i * gap[0] + (j % 2) * gap[0] / 2 + rng.uniform(-jitter, jitter)
                py = y + j * gap[1] + rng.uniform(-jitter / 2, jitter / 2)
                out.append(self.actor(name, px, py, facing, side, scale, t_in))
        return out

    def thing(self, img, x, y, **kw) -> Thing:
        th = Thing(img, x, y, **kw)
        self.things.append(th)
        return th

    def paint(self, fn, layer=-1, t_in=0.0) -> Thing:
        th = Thing([pygame.Surface((1, 1))], 0, 0, layer=layer, t_in=t_in)
        th.paint = fn
        self.things.append(th)
        return th

    def label(self, text, x, y, t, style="paper", t_out=None) -> Thing:
        th = self.thing(label_img(text, style), x, y, layer=2, anchor="center", t_in=t, t_out=t_out, pop=True)
        th.text = text
        return th

    def flag(self, x, y, kind="ta", t_in=0.0, pop=False, follow: Actor | None = None, t_out=None) -> Thing:
        th = self.thing(flag_frames(kind), x, y, fps=7, t_in=t_in, pop=pop, t_out=t_out)
        if follow is not None:
            th.follow = (follow, 10, -26)
        return th

    def carry(self, actor: Actor, img, dy=-46, dx=0, t_in=0.0, t_out=None, layer=0, pop=False) -> Thing:
        th = self.thing(img, 0, 0, t_in=t_in, t_out=t_out, layer=layer, pop=pop)
        th.follow = (actor, dx, dy)
        return th

    def fire(self, x, y, t0=0.0, t1=None, scale=2, smoke=True, follow: Actor | None = None) -> Thing:
        th = self.thing(flame_frames(scale), x, y, fps=10, layer=1, t_in=t0, t_out=t1)
        if follow is not None:
            th.follow = (follow, x, y)
        if smoke:
            def puff():
                if th.visible(self.t):
                    px, py = th.pos(self.t)
                    self.fx.smoke(px + random.uniform(-14, 14), py - 20 * scale, 1, 14)

            self.every(t0, t1, 0.35, puff)
        return th

    def boat(self, x, y, side="ta", width=130, facing="right", crew=(), sail=False, t_in=0.0):
        """Thuyền kèm người trên thuyền; trả về (thuyền, danh sách người). Di chuyển bằng `shift` cả cụm."""
        views = boat(width, side, sail)
        hull = self.thing(views[facing], x, y + 10, t_in=t_in)
        hull.bob = 2.0
        hull.sort_bias = -40
        people = []
        span = width * 0.5
        for i, name in enumerate(crew):
            off = -span / 2 + span * (i + 0.5) / max(1, len(crew))
            people.append(self.actor(name, x + off, y - 10, facing, side, t_in=t_in))
        return hull, people

    # ----- diễn -----
    def shift(self, items, t, dx, dy, speed=90.0, stagger=0.0) -> float:
        end = t
        for i, it in enumerate(items):
            _, x, y = it.track.end()
            end = max(end, it.track.go(t + i * stagger, x + dx, y + dy, speed))
        return end

    def goto(self, items, t, x, y, speed=90.0, stagger=0.0) -> float:
        if not items:
            return t
        ends = [it.track.end() for it in items]
        cx = sum(e[1] for e in ends) / len(ends)
        cy = sum(e[2] for e in ends) / len(ends)
        return self.shift(items, t, x - cx, y - cy, speed, stagger)

    def path(self, items, t, points, speed=90.0, stagger=0.0) -> float:
        end = t
        for i, it in enumerate(items):
            tt = t + i * stagger
            for px, py in points:
                tt = it.track.go(tt, px, py, speed)
            end = max(end, tt)
        return end

    def face(self, items, t, facing):
        for it in items:
            it.faces.append((t, facing))

    def _mode(self, items, t0, t1, mode, stagger=0.0):
        for i, it in enumerate(items):
            it.modes.append((t0 + i * stagger, t1, mode))

    def fight(self, items, t0, t1=None):
        self._mode(items, t0, t1, "fight")

    def cheer(self, items, t0, t1=None, stagger=0.04):
        self._mode(items, t0, t1, "cheer", stagger)

    def work(self, items, t0, t1=None):
        self._mode(items, t0, t1, "work")

    def kneel(self, items, t0, t1=None, stagger=0.0):
        self._mode(items, t0, t1, "kneel", stagger)

    def hide(self, items, t):
        for it in items:
            it.t_out = t

    def show(self, items, t):
        for it in items:
            it.t_in = t

    def fall(self, items, t, stagger=0.25, away=(1, 0), principal=False):
        """Ngã xuống giữa trận. Chế độ giảm nhẹ thì lính địch tháo chạy theo hướng `away`, còn người phe ta
        và nhân vật chính (`principal`) quỳ xuống, không vẽ cảnh ngã."""
        for i, a in enumerate(items):
            tt = t + i * stagger
            if self.gore:
                a.dead_at = tt
                self.at(tt, lambda a=a, tt=tt: self._hurt(a, tt))
            elif a.side == "dich" and not principal:
                _, x, y = a.track.end()
                a.track.go(tt, x + away[0] * 1600, y + away[1] * 1600, 230)
            else:
                a.modes.append((tt, None, "kneel"))

    def _hurt(self, a: Actor, t: float):
        x, y = a.pos(t)
        self.fx.blood(x, y - 26, 10)

    def at(self, t, fn):
        self.events.append([t, fn, False])

    def every(self, t0, t1, period, fn):
        self.repeats.append([t0, t1, period, fn, t0])

    def sound(self, t, name):
        self.at(t, lambda: self.audio.play(name))

    def shake(self, t, power):
        self.at(t, lambda: self.fx.shake(power))

    def clash(self, x0, x1, y0, y1, t0, t1=None, period=0.32, sound=True):
        def hit():
            x, y = random.uniform(x0, x1), random.uniform(y0, y1)
            self.fx.burst(x, y, 9, [(255, 236, 170), (255, 190, 90), (250, 250, 230)], 240, 0.3, 3, 300, kind="spark")
            self.fx.blood(x, y, 8)
            if sound and random.random() < 0.35:
                self.audio.play("kiem")

        self.every(t0, t1, period, hit)

    def volley(self, src, x0, x1, y0, y1, t0, t1=None, period=0.3):
        right = sprites.sepia(sprites.icon("fx/arrow.png", 3))
        left = pygame.transform.flip(right, True, False)

        def shoot():
            alive = [a for a in src if a.visible(self.t) and (a.dead_at is None or self.t < a.dead_at)]
            if not alive:
                return
            a = random.choice(alive)
            sx, sy = a.pos(self.t)
            tx, ty = random.uniform(x0, x1), random.uniform(y0, y1)
            self.fx.shoot(right if tx >= sx else left, sx, sy - 34, tx, ty, 640, 40)

        self.every(t0, t1, period, shoot)

    def blasts(self, x0, x1, y0, y1, t0, t1=None, period=0.7, power=0.9):
        def boom():
            self.fx.explosion(random.uniform(x0, x1), random.uniform(y0, y1), power)
            if random.random() < 0.5:
                self.audio.play("no")

        self.every(t0, t1, period, boom)

    def smoke(self, x0, x1, y0, y1, t0=0.0, t1=None, period=0.35):
        self.every(t0, t1, period, lambda: self.fx.smoke(random.uniform(x0, x1), random.uniform(y0, y1), 1, 30))

    def waves(self, y0, y1, n=12, drift=-30.0):
        """Vệt sóng trôi trên mặt nước, giống cảnh Bạch Đằng."""
        rows = [(y0 + (y1 - y0) * (i + 0.5) / n, i * 137 % W, 0.7 + (i % 5) * 0.12) for i in range(n)]

        def draw(s, t, ox, oy):
            for y, x0, k in rows:
                x = (x0 + drift * k * t) % (W + 80) - 40
                pygame.draw.rect(s, (246, 228, 192), (x + ox, y + oy, 36, 3))

        self.paint(draw, -1)

    def dim(self, t0, t1, a0, a1):
        self.dims.append((t0, t1, a0, a1))

    def flash(self, t, dur=0.5):
        self.flashes.append((t, dur))

    # ----- vòng lặp -----
    def update(self, dt: float):
        self.t += dt
        t = self.t
        for ev in self.events:
            if not ev[2] and t >= ev[0]:
                ev[2] = True
                ev[1]()
        for r in self.repeats:
            fired = 0
            while t >= r[4] and (r[1] is None or r[4] <= r[1]) and fired < MAX_FIRES_PER_FRAME:
                r[3]()
                r[4] += r[2] * random.uniform(0.7, 1.3)
                fired += 1
            if fired == MAX_FIRES_PER_FRAME and t >= r[4]:
                r[4] = t + r[2]

    def _night(self, t: float) -> float:
        alpha = 0.0
        for t0, t1, a0, a1 in self.dims:
            if t >= t0:
                k = 1.0 if t1 <= t0 else min(1.0, (t - t0) / (t1 - t0))
                alpha = a0 + (a1 - a0) * k
        return alpha

    def draw(self, s: pygame.Surface, offset=(0, 0)):
        t = self.t
        ox, oy = offset
        s.blit(self.bg, offset)
        for th in self.things:
            if th.layer == -1 and th.visible(t):
                th.draw(s, t, ox, oy)
        items = [it for it in self.actors if it.visible(t)]
        items += [th for th in self.things if th.layer == 0 and th.visible(t)]
        items.sort(key=lambda it: it.pos(t)[1] + getattr(it, "sort_bias", 0.0))
        for it in items:
            it.draw(s, t, ox, oy)
        night = self._night(t)
        if night > 0:
            veil = cached("night_veil", lambda: _veil(NIGHT))
            veil.set_alpha(int(255 * night))
            s.blit(veil, (0, 0))
        for th in self.things:
            if th.layer == 1 and th.visible(t):
                th.draw(s, t, ox, oy)
        for t0, dur in self.flashes:
            if t0 <= t < t0 + dur:
                white = cached("white_veil", lambda: _veil((255, 246, 226)))
                white.set_alpha(int(255 * (1 - (t - t0) / dur)))
                s.blit(white, (0, 0))
        for th in self.things:
            if th.layer == 2 and th.visible(t):
                th.draw(s, t, ox, oy)


def _veil(color) -> pygame.Surface:
    v = pygame.Surface((W, H))
    v.fill(color)
    return v


# ----- công trình vẽ riêng: gói asset không có kiến trúc Việt Nam thời cận đại -----
def _low_building(key, w, h, paint) -> pygame.Surface:
    def build():
        low = pygame.Surface((w, h), pygame.SRCALPHA)
        paint(low)
        return sprites.sepia(sprites.scaled(low, 4))

    return cached(key, build)


def opera_house() -> pygame.Surface:
    """Nhà hát Lớn Hà Nội: mặt tiền kiểu Pháp, mái vòm giữa, hàng cột và cửa vòm, bậc thềm."""
    ink, wall, shade, slate, glass = (34, 26, 22), (236, 214, 160), (196, 170, 120), (92, 96, 104), (70, 80, 96)

    def paint(s):
        pygame.draw.polygon(s, slate, [(2, 16), (68, 16), (64, 11), (6, 11)])  # mái hai cánh
        pygame.draw.rect(s, wall, (3, 16, 64, 24))
        pygame.draw.rect(s, slate, (24, 7, 22, 6))  # mái phần giữa
        pygame.draw.ellipse(s, slate, (28, 1, 14, 12))  # vòm
        pygame.draw.rect(s, ink, (34, 0, 2, 2))
        pygame.draw.rect(s, wall, (23, 12, 24, 28))  # phần giữa nhô ra
        pygame.draw.rect(s, shade, (23, 12, 24, 3))
        for x in range(25, 47, 5):  # hàng cột
            pygame.draw.rect(s, (250, 236, 200), (x, 17, 2, 18))
        for x in (27, 32, 37, 42):  # cửa vòm
            pygame.draw.rect(s, glass, (x, 21, 3, 8))
            pygame.draw.circle(s, glass, (x + 1, 21), 1)
        for x in list(range(6, 21, 5)) + list(range(50, 66, 5)):  # cửa sổ hai cánh
            pygame.draw.rect(s, glass, (x, 20, 3, 5))
            pygame.draw.rect(s, glass, (x, 30, 3, 5))
        pygame.draw.rect(s, shade, (3, 27, 64, 1))
        pygame.draw.rect(s, (170, 160, 150), (19, 40, 32, 3))  # bậc thềm
        pygame.draw.rect(s, ink, (3, 16, 64, 24), 1)
        pygame.draw.rect(s, ink, (23, 12, 24, 28), 1)

    return _low_building("opera_house", 70, 44, paint)


def bac_bo_phu() -> pygame.Surface:
    """Bắc Bộ phủ: dinh thự hai tầng kiểu Pháp, mái ngói đỏ, cửa chớp, cổng sắt và hàng rào phía trước."""
    ink, wall, roof, shut = (34, 26, 22), (234, 206, 128), (176, 76, 52), (72, 110, 76)

    def paint(s):
        pygame.draw.polygon(s, roof, [(4, 12), (56, 12), (50, 4), (10, 4)])
        pygame.draw.polygon(s, ink, [(4, 12), (56, 12), (50, 4), (10, 4)], 1)
        pygame.draw.rect(s, wall, (6, 12, 48, 20))
        pygame.draw.rect(s, (214, 184, 104), (6, 21, 48, 1))
        for x in range(9, 52, 6):
            for y in (14, 24):
                pygame.draw.rect(s, shut, (x, y, 3, 5))
        pygame.draw.rect(s, (110, 70, 44), (27, 24, 6, 8))  # cửa chính
        pygame.draw.rect(s, ink, (6, 12, 48, 20), 1)
        for x in range(0, 60, 3):  # hàng rào sắt
            pygame.draw.line(s, ink, (x, 33), (x, 39))
        pygame.draw.line(s, ink, (0, 34), (60, 34))
        pygame.draw.rect(s, (200, 190, 170), (23, 31, 2, 9))  # trụ cổng
        pygame.draw.rect(s, (200, 190, 170), (35, 31, 2, 9))

    return _low_building("bac_bo_phu", 60, 40, paint)


def dinh_lang() -> pygame.Surface:
    """Đình làng (như đình Tân Trào): nhà gỗ ba gian, mái lớn đầu đao cong vút, cột gỗ, nền đất nện."""
    ink, roof, roof2, wood, floor = (34, 26, 22), (92, 72, 56), (120, 96, 72), (150, 96, 56), (190, 160, 120)

    def paint(s):
        pygame.draw.polygon(s, roof, [(2, 16), (50, 16), (44, 4), (8, 4)])
        pygame.draw.polygon(s, roof2, [(10, 6), (42, 6), (44, 10), (8, 10)])
        for x0 in (0, 47):  # đầu đao cong
            pygame.draw.polygon(s, roof, [(x0, 13), (x0 + 5, 16), (x0 + 5, 12)] if x0 == 0 else [(x0 + 5, 13), (x0, 16), (x0, 12)])
        pygame.draw.line(s, ink, (2, 16), (50, 16))
        pygame.draw.line(s, ink, (8, 4), (44, 4))
        for y in range(7, 16, 3):
            pygame.draw.line(s, (76, 58, 44), (9 + (16 - y) // 3, y), (43 - (16 - y) // 3, y))
        pygame.draw.rect(s, (110, 74, 44), (6, 16, 40, 12))
        for x in (6, 16, 26, 36, 45):  # cột gỗ
            pygame.draw.rect(s, wood, (x, 16, 2, 12))
        pygame.draw.rect(s, (60, 40, 26), (18, 18, 16, 10))  # gian giữa tối
        pygame.draw.rect(s, floor, (3, 28, 46, 4))
        pygame.draw.rect(s, ink, (3, 28, 46, 4), 1)

    return _low_building("dinh_lang", 52, 34, paint)
