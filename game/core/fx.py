"""Hiệu ứng: hạt (lửa, khói, nước, mảnh vỡ, máu), tên bay, rung màn hình, lớp phủ hồi ức.

Cài đặt "Hiệu ứng chiến trận": chế độ 'nhe' thay vệt máu bằng bụi đất, phù hợp người chơi nhỏ tuổi.
"""

from __future__ import annotations

import math
import random

import pygame

from core import sprites, theme

MAX_PARTICLES = 420
MAX_STAINS = 60
STAIN_LIFE = 5.0
DUEL_TIME = 1.9
DUEL_HIT = 0.95
DUEL_SCALE = 5


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "total", "size", "color", "gravity", "kind", "grow")

    def __init__(self, x, y, vx, vy, life, size, color, gravity=0.0, kind="dot", grow=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.total = life
        self.size, self.color, self.gravity, self.kind, self.grow = size, color, gravity, kind, grow


class Arrow:
    __slots__ = ("x", "y", "vx", "vy", "life", "color")

    def __init__(self, x, y, vx, vy, life, color=(60, 40, 26)):
        self.x, self.y, self.vx, self.vy, self.life, self.color = x, y, vx, vy, life, color


class Shot:
    """Đạn bay theo đường vòng cung: mũi tên, cầu lửa, giáo. Tới đích thì gọi `on_hit`."""

    __slots__ = ("frames", "x0", "y0", "x1", "y1", "t", "dur", "arc", "on_hit")

    def __init__(self, frames, x0, y0, x1, y1, dur, arc, on_hit):
        self.frames = frames
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.t, self.dur, self.arc, self.on_hit = 0.0, dur, arc, on_hit


class Fx:
    def __init__(self, violence: str = "nhe", old: bool = False):
        self.violence = violence
        self.old = old
        self.plays: list[list] = []
        self.shots: list[Shot] = []
        self.items: list[Particle] = []
        self.arrows: list[Arrow] = []
        self.stains: list[list[float]] = []
        self.shake_power = 0.0

    # ----- sinh hạt -----
    def _add(self, *args, **kw):
        if len(self.items) < MAX_PARTICLES:
            self.items.append(Particle(*args, **kw))

    def burst(self, x, y, n, colors, speed=160, life=0.7, size=4, gravity=240, up=False, kind="dot"):
        for _ in range(n):
            a = random.uniform(math.pi, 2 * math.pi) if up else random.uniform(0, 2 * math.pi)
            s = random.uniform(speed * 0.3, speed)
            self._add(
                x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(life * 0.5, life),
                random.uniform(size * 0.5, size), random.choice(colors), gravity, kind,
            )

    def blood(self, x, y, n=14):
        if self.violence == "day_du":
            self.burst(x, y, n, [(150, 16, 18), (118, 10, 14), (178, 28, 24)], 190, 0.7, 4, 460)
            if len(self.stains) < MAX_STAINS:
                for _ in range(3):
                    self.stains.append([x + random.uniform(-26, 26), y + random.uniform(4, 30), random.uniform(3, 8), STAIN_LIFE])
        else:
            self.burst(x, y, n // 2, [(150, 130, 100), (120, 104, 82)], 90, 0.5, 4, 120)

    def clash(self, x, y):
        """Đao kiếm va nhau: tia lửa và (nếu bật) vệt máu."""
        self.burst(x, y, 10, [(255, 236, 170), (255, 190, 90), (250, 250, 230)], 260, 0.3, 3, 300, kind="spark")
        self.slash(x, y)
        self.blood(x, y, 14)

    def slash(self, x, y):
        """Vệt chém loé lên rồi tắt rất nhanh."""
        self.play("fx/slash.png", 6, x, y, 18, random.random() < 0.5, 3 if self.old else 2)

    def shoot(self, img, x0, y0, x1, y1, speed=620, arc=0.0, on_hit=None):
        """Bắn một viên đạn; ảnh gốc phải quay đầu sang phải."""
        frames = img if isinstance(img, list) else [img]
        angle = math.degrees(math.atan2(y0 - y1, x1 - x0))
        turned = [pygame.transform.rotate(f, angle) for f in frames]
        dur = max(0.05, math.hypot(x1 - x0, y1 - y0) / speed)
        self.shots.append(Shot(turned, x0, y0, x1, y1, dur, arc, on_hit))

    def debris(self, x, y, n=10):
        """Ván thuyền vỡ văng ra, dùng mảnh gỗ của gói asset."""
        frames = sprites.strip("fx/wood.png", 6, 3)
        for _ in range(n):
            a = random.uniform(math.pi, 2 * math.pi)
            s = random.uniform(90, 300)
            self._add(x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(0.5, 1.0), 1, random.choice(frames), 560, "img")

    def play(self, name, count, x, y, fps=14, flip=False, scale=sprites.SCALE):
        """Chạy một lần dải hiệu ứng lấy từ gói asset."""
        frames = sprites.strip(name, count, scale)
        self.plays.append([frames, x, y, 0.0, fps, flip])

    def fall(self, x, y, n=1):
        """Người ngã khỏi thuyền hoặc bị hất văng; chế độ giảm nhẹ thì không vẽ."""
        if self.violence != "day_du":
            return
        for _ in range(n):
            self._add(x, y, random.uniform(-80, 80), random.uniform(-190, -80), random.uniform(0.7, 1.1), 8, (24, 18, 14), 520, "body")

    def fire(self, x, y, n=3, spread=16):
        for _ in range(n):
            self._add(
                x + random.uniform(-spread, spread), y, random.uniform(-14, 14), random.uniform(-110, -50),
                random.uniform(0.35, 0.8), random.uniform(5, 11),
                random.choice([(255, 196, 80), (246, 134, 40), (214, 70, 30)]), -30, "dot", -8,
            )

    def smoke(self, x, y, n=2, spread=16):
        for _ in range(n):
            g = random.randint(46, 92)
            self._add(
                x + random.uniform(-spread, spread), y, random.uniform(-16, 22), random.uniform(-52, -22),
                random.uniform(1.0, 2.1), random.uniform(7, 15), (g, g - 4, g - 8), -6, "soft", 13,
            )

    def splash(self, x, y, n=14):
        self.burst(x, y, n, [(214, 234, 236), (168, 208, 214), (240, 248, 248)], 170, 0.6, 4, 460, up=True)

    def splinters(self, x, y, n=18):
        self.burst(x, y, n, [(96, 62, 34), (130, 90, 50), (70, 44, 26)], 270, 0.95, 6, 420, kind="shard")

    def explosion(self, x, y, power=1.0):
        self.play("fx/explosion.png", 9, x, y, 16)
        self.burst(x, y, int(22 * power), [(255, 224, 150), (250, 150, 60), (214, 70, 30)], 310 * power, 0.55, 7, 120)
        self.burst(x, y, int(14 * power), [(70, 60, 50), (50, 44, 38), (92, 84, 72)], 180 * power, 0.9, 5, 330)
        self.smoke(x, y, int(6 * power), 26)
        self.shake(9 * power)

    def volley(self, x0, y0, x1, y1, n=8, spread=70, speed=520, color=(60, 40, 26)):
        """Một loạt tên bay từ (x0, y0) tới (x1, y1)."""
        for _ in range(n):
            tx = x1 + random.uniform(-spread, spread)
            ty = y1 + random.uniform(-spread * 0.4, spread * 0.4)
            sx = x0 + random.uniform(-spread * 0.6, spread * 0.6)
            sy = y0 + random.uniform(-14, 14)
            d = max(1.0, math.hypot(tx - sx, ty - sy))
            s = random.uniform(speed * 0.8, speed * 1.15)
            self.arrows.append(Arrow(sx, sy, (tx - sx) / d * s, (ty - sy) / d * s, d / s, color))

    def shake(self, power: float):
        self.shake_power = max(self.shake_power, power)

    # ----- cập nhật / vẽ -----
    def update(self, dt: float):
        for p in self.items:
            p.life -= dt
            p.vy += p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.size = max(0.5, p.size + p.grow * dt)
        self.items = [p for p in self.items if p.life > 0]
        for a in self.arrows:
            a.life -= dt
            a.x += a.vx * dt
            a.y += a.vy * dt
        self.arrows = [a for a in self.arrows if a.life > 0]
        for shot in list(self.shots):
            shot.t += dt / shot.dur
            if shot.t >= 1.0:
                self.shots.remove(shot)
                if shot.on_hit:
                    shot.on_hit()
        for pl in self.plays:
            pl[3] += dt
        self.plays = [pl for pl in self.plays if pl[3] * pl[4] < len(pl[0])]
        for st in self.stains:
            st[3] -= dt
        self.stains = [st for st in self.stains if st[3] > 0]
        self.shake_power = self.shake_power * (0.02 ** dt) if self.shake_power > 0.3 else 0.0

    def offset(self) -> tuple[int, int]:
        if not self.shake_power:
            return (0, 0)
        p = int(self.shake_power)
        return (random.randint(-p, p), random.randint(-p, p))

    def draw(self, surface: pygame.Surface):
        for x, y, r, life in self.stains:
            pygame.draw.circle(surface, (96, 12, 14), (x, y), r * min(1.0, life / 1.5))
        for a in self.arrows:
            n = max(1.0, math.hypot(a.vx, a.vy))
            dx, dy = a.vx / n, a.vy / n
            pygame.draw.line(surface, a.color, (a.x - dx * 24, a.y - dy * 24), (a.x, a.y), 2)
        for p in self.items:
            ratio = p.life / p.total
            if p.kind == "soft":
                r = int(p.size)
                if r < 1:
                    continue
                lop = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(lop, (*p.color, int(120 * ratio)), (r, r), r)
                surface.blit(lop, (p.x - r, p.y - r))
            elif p.kind == "shard":
                s = p.size
                pygame.draw.polygon(
                    surface, p.color,
                    [(p.x - s, p.y - s * 0.3), (p.x + s, p.y - s * 0.5), (p.x + s * 0.5, p.y + s * 0.5)],
                )
            elif p.kind == "spark":
                pygame.draw.line(surface, p.color, (p.x, p.y), (p.x - p.vx * 0.03, p.y - p.vy * 0.03), 2)
            elif p.kind == "img":
                surface.blit(p.color, (p.x - 12, p.y - 12))
            elif p.kind == "body":
                a = p.life * 9
                dx, dy = math.cos(a) * p.size, math.sin(a) * p.size
                pygame.draw.line(surface, p.color, (p.x - dx, p.y - dy), (p.x + dx, p.y + dy), 3)
                pygame.draw.circle(surface, p.color, (p.x + dx * 1.3, p.y + dy * 1.3), 3)
            else:
                r = max(1, int(p.size * (0.4 + 0.6 * ratio)))
                pygame.draw.circle(surface, p.color, (int(p.x), int(p.y)), r)
        for shot in self.shots:
            k = shot.t
            x = shot.x0 + (shot.x1 - shot.x0) * k
            y = shot.y0 + (shot.y1 - shot.y0) * k - shot.arc * 4 * k * (1 - k)
            img = shot.frames[int(k * 10) % len(shot.frames)]
            surface.blit(img, img.get_rect(center=(x, y)))
        for frames, x, y, t, fps, flip in self.plays:
            img = frames[min(len(frames) - 1, int(t * fps))]
            if flip:
                img = pygame.transform.flip(img, True, False)
            surface.blit(img, img.get_rect(center=(x, y)))


class Duel:
    """Một cặp lính giao đấu trong hồi ức: áp sát, chém, một người ngã xuống."""

    __slots__ = ("x", "y", "t", "loser", "hit", "left", "right")

    def __init__(self, x, y):
        self.x, self.y, self.t = x, y, 0.0
        self.loser = random.choice((-1, 1))
        self.hit = False
        self.left = sprites.cast(random.choice(("LinhDaiViet", "LinhDaiViet2", "NghiaQuan")), DUEL_SCALE, old=True)
        self.right = sprites.cast(random.choice(("LinhTong", "LinhNguyen", "LinhMinh")), DUEL_SCALE, old=True)

    def _one(self, surface, cast, x, facing, fallen):
        if fallen:
            surface.blit(cast.dead, (x - cast.size / 2, self.y - cast.size * 0.6))
            return
        if self.t > DUEL_HIT - 0.32 and int(self.t * 12) % 2 == 0:
            img = cast.attack[facing]
        else:
            img = cast.walk[facing][int(self.t * 10) % 4]
        surface.blit(img, (x - cast.size / 2, self.y - cast.size))

    def draw(self, surface):
        gap = max(36.0, 130 - self.t * 100)
        down = self.t >= DUEL_HIT
        self._one(surface, self.left, self.x - gap, "right", down and self.loser == -1)
        self._one(surface, self.right, self.x + gap, "left", down and self.loser == 1)


class Ambient:
    """Hiệu ứng nền lặp lại trong hồi ức, chọn theo thẻ `fx` của từng đoạn truyện."""

    def __init__(self, fx: Fx):
        self.fx = fx
        self.kinds: set[str] = set()
        self.t = 0.0
        self._next = 0.0
        self.rain = [(random.randint(0, theme.WIDTH), random.randint(0, theme.HEIGHT)) for _ in range(90)]
        self.duels: list[Duel] = []
        self.ground: tuple[float, float] | None = (330.0, 474.0)  # dải đất có thể đứng trong cảnh, None là toàn nước

    def set(self, kinds):
        self.kinds = set(kinds or [])

    def update(self, dt: float):
        self.t += dt
        self._next -= dt
        fx = self.fx
        w, h = theme.WIDTH, theme.HEIGHT
        floor = int(h * 0.62)
        self._update_duels(dt)
        if "fire" in self.kinds:
            for x in (130, 340, 930, 1150):
                fx.fire(x + random.uniform(-40, 40), floor + random.uniform(10, 60), 1, 26)
            if random.random() < 0.3:
                fx.smoke(random.uniform(0, w), floor, 1, 40)
        if "smoke" in self.kinds and random.random() < 0.3:
            fx.smoke(random.uniform(0, w), floor + 20, 1, 40)
        if self._next > 0:
            return
        if "arrows" in self.kinds:
            fx.volley(-20, floor - 90, w * 0.72, floor + 40, 6, 170, 640)
            fx.volley(w + 20, floor - 110, w * 0.25, floor + 30, 4, 170, 640)
            self._next = 0.65
        if "clash" in self.kinds and self.ground is not None:
            x, y = random.uniform(w * 0.15, w * 0.85), random.uniform(self.ground[0] - 40, self.ground[1] - 40)
            fx.clash(x, y)
            fx.shake(4)
            self._next = random.uniform(0.3, 0.7)
        if "blast" in self.kinds:
            fx.explosion(random.uniform(w * 0.1, w * 0.9), random.uniform(floor - 40, floor + 50), 0.9)
            self._next = random.uniform(0.5, 1.1)
        if "drum" in self.kinds:
            fx.shake(3)
            self._next = 0.85

    def _update_duels(self, dt: float):
        """Giảm nhẹ thì chỉ còn tia lửa, không vẽ cảnh người ngã xuống."""
        fx = self.fx
        wanted = "clash" in self.kinds and fx.violence == "day_du" and self.ground is not None
        if wanted and len(self.duels) < 3 and random.random() < dt * 2.2:
            self.duels.append(Duel(random.uniform(theme.WIDTH * 0.12, theme.WIDTH * 0.88), random.uniform(*self.ground)))
        for d in self.duels:
            d.t += dt
            if d.t >= DUEL_HIT and not d.hit:
                d.hit = True
                fx.clash(d.x, d.y - 40)
                fx.blood(d.x + d.loser * 16, d.y - 34, 20)
                fx.shake(4)
        self.duels = [d for d in self.duels if d.t < DUEL_TIME]

    def draw(self, surface: pygame.Surface):
        for d in self.duels:
            d.draw(surface)
        if "rain" in self.kinds:
            for x, y in self.rain:
                yy = (y + self.t * 620) % theme.HEIGHT
                xx = (x - self.t * 90) % theme.WIDTH
                pygame.draw.line(surface, (190, 200, 205), (xx, yy), (xx - 3, yy + 14), 1)
