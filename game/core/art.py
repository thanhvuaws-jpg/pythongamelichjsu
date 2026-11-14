"""Tranh minh hoạ vẽ bằng code: cảnh di tích, chân dung, con dấu, bảo vật, mặt trống đồng.

Không dùng ảnh ngoài nên không vướng bản quyền và tải nhanh trên web. Mọi tranh đều là
"Tranh minh họa" (Req 14), không phải hình ảnh tư liệu.
"""

from __future__ import annotations

import math

import pygame

from core import fonts, sprites, theme

W, H = theme.WIDTH, theme.HEIGHT
_misc: dict[tuple, pygame.Surface] = {}


# ---------- nét vẽ cơ bản ----------
def gradient(w, h, stops) -> pygame.Surface:
    s = pygame.Surface((w, h))
    n = len(stops) - 1
    for y in range(h):
        t = y / max(1, h - 1) * n
        i = min(int(t), n - 1)
        k = t - i
        a, b = stops[i], stops[i + 1]
        pygame.draw.line(s, [int(a[j] + (b[j] - a[j]) * k) for j in range(3)], (0, y), (w, y))
    return s


def _stakes(s, x0, x1, base, rng, n=16, h=70):
    for _ in range(n):
        x = rng.uniform(x0, x1)
        hh = rng.uniform(h * 0.6, h)
        lean = rng.uniform(4, 16)
        pygame.draw.polygon(s, (54, 36, 24), [(x - 5, base), (x + 5, base), (x + lean, base - hh)])
        pygame.draw.polygon(s, (120, 124, 130), [(x + lean * 0.78 - 2, base - hh * 0.8), (x + lean * 0.78 + 3, base - hh * 0.8), (x + lean, base - hh)])


def _boat(s, x, y, size, hull=(62, 40, 26), sail=None, flag=None):
    pygame.draw.polygon(s, hull, [(x - size, y - size * 0.14), (x + size, y - size * 0.2), (x + size * 0.7, y + size * 0.18), (x - size * 0.72, y + size * 0.18)])
    pygame.draw.rect(s, (92, 64, 42), (x - size * 0.34, y - size * 0.38, size * 0.68, size * 0.22))
    if sail:
        pygame.draw.line(s, (50, 34, 24), (x, y - size * 0.3), (x, y - size * 1.12), 3)
        pygame.draw.polygon(s, sail, [(x, y - size * 1.1), (x + size * 0.62, y - size * 0.86), (x + size * 0.62, y - size * 0.4), (x, y - size * 0.34)])
    if flag:
        pygame.draw.line(s, (50, 34, 24), (x - size * 0.7, y - size * 0.16), (x - size * 0.7, y - size * 0.72), 2)
        pygame.draw.polygon(s, flag, [(x - size * 0.7, y - size * 0.72), (x - size * 0.34, y - size * 0.62), (x - size * 0.7, y - size * 0.5)])


def _flag(s, x, y, h, color=(176, 44, 32), w=None):
    w = w or h * 0.5
    pygame.draw.line(s, (60, 40, 28), (x, y), (x, y - h), 3)
    pygame.draw.polygon(s, color, [(x, y - h), (x + w, y - h * 0.9), (x + w * 0.84, y - h * 0.74), (x + w, y - h * 0.58), (x, y - h * 0.62)])


def _star(s, cx, cy, r, color, points=5, inner=0.42):
    pts = []
    for i in range(points * 2):
        a = -math.pi / 2 + i * math.pi / points
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    pygame.draw.polygon(s, color, pts)


def vignette() -> pygame.Surface:
    """Viền tối bốn góc: vẽ trên ảnh nhỏ rồi phóng to cho mịn và nhanh."""
    key = ("vignette",)
    if key not in _misc:
        sw, sh = 160, 90
        small = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for y in range(sh):
            for x in range(sw):
                d = math.hypot((x - sw / 2) / (sw / 2), (y - sh / 2) / (sh / 2))
                a = max(0.0, min(1.0, (d - 0.55) / 0.75))
                small.set_at((x, y), (12, 6, 2, int(215 * a * a)))
        _misc[key] = pygame.transform.smoothscale(small, (W, H))
    return _misc[key]


# ---------- mặt trống đồng ----------
def drum(size: int, line=theme.GOLD, alpha: int = 255) -> pygame.Surface:
    """Hoa văn mặt trống đồng Đông Sơn: ngôi sao 14 cánh, các vành hoa văn, chim Lạc."""
    key = ("drum", size, line, alpha)
    if key in _misc:
        return _misc[key]
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    col = (*line, alpha)
    _star_alpha = 14
    pts = []
    r0 = size * 0.12
    for i in range(_star_alpha * 2):
        a = i * math.pi / _star_alpha
        rr = r0 if i % 2 == 0 else r0 * 0.42
        pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr))
    pygame.draw.polygon(s, col, pts)
    rings = [0.16, 0.2, 0.26, 0.31, 0.43, 0.47]
    for k in rings:
        pygame.draw.circle(s, col, (c, c), int(size * k), max(1, size // 300))
    # vành hoa văn gạch chéo
    for r1, r2, n in ((0.2, 0.26, 56), (0.43, 0.47, 110)):
        for i in range(n):
            a = i * 2 * math.pi / n
            b = a + 2 * math.pi / n * 0.8
            pygame.draw.line(
                s, col,
                (c + math.cos(a) * size * r1, c + math.sin(a) * size * r1),
                (c + math.cos(b) * size * r2, c + math.sin(b) * size * r2), 1,
            )
    # chim Lạc bay quanh vành giữa
    birds = 10
    r = size * 0.37
    for i in range(birds):
        a = i * 2 * math.pi / birds
        bx, by = c + math.cos(a) * r, c + math.sin(a) * r
        t = a + math.pi / 2
        ux, uy = math.cos(t), math.sin(t)
        nx, ny = -uy, ux
        b = size * 0.04
        body = [
            (bx + ux * b * 1.3, by + uy * b * 1.3),
            (bx + nx * b * 0.35, by + ny * b * 0.35),
            (bx - ux * b * 1.1, by - uy * b * 1.1),
            (bx - nx * b * 0.35, by - ny * b * 0.35),
        ]
        pygame.draw.polygon(s, col, body)
        pygame.draw.line(s, col, (bx, by), (bx + nx * b * 1.2 - ux * b * 0.5, by + ny * b * 1.2 - uy * b * 0.5), 2)
        pygame.draw.line(s, col, (bx, by), (bx - nx * b * 1.2 - ux * b * 0.5, by - ny * b * 1.2 - uy * b * 0.5), 2)
    _misc[key] = s
    return s


# ---------- con dấu ----------
def stamp(label: str, size: int = 120, color=(166, 38, 28), active: bool = True) -> pygame.Surface:
    """Con dấu son của Hộ chiếu di sản. Chưa đến thì hiện dạng mờ."""
    key = ("stamp", label, size, color, active)
    if key in _misc:
        return _misc[key]
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    col = color if active else (150, 138, 118)
    a = 255 if active else 110
    rgba = (*col, a)
    pygame.draw.circle(s, rgba, (c, c), c - 3, 4)
    pygame.draw.circle(s, rgba, (c, c), c - 10, 1)
    for i in range(24):
        ang = i * 2 * math.pi / 24
        pygame.draw.circle(s, rgba, (c + math.cos(ang) * (c - 15), c + math.sin(ang) * (c - 15)), 1)
    f = fonts.font("bold", max(10, size // 8))
    lines = fonts.wrap(label, f, int(size * 0.68))
    lh = f.get_linesize()
    y = c - len(lines) * lh / 2
    for line in lines:
        img = f.render(fonts.nfc(line), True, col)
        if not active:
            img.set_alpha(120)
        s.blit(img, img.get_rect(midtop=(c, y)))
        y += lh
    _misc[key] = s
    return s


def _scroll_icon(s, size):
    u = size / 150
    r = pygame.Rect(0, 0, 74 * u, 86 * u)
    r.center = (size / 2, size / 2)
    pygame.draw.rect(s, (246, 234, 204), r)
    pygame.draw.rect(s, theme.GOLD_DARK, (r.x - 6 * u, r.y - 7 * u, r.w + 12 * u, 10 * u), border_radius=3)
    pygame.draw.rect(s, theme.GOLD_DARK, (r.x - 6 * u, r.bottom - 3 * u, r.w + 12 * u, 10 * u), border_radius=3)
    for i in range(5):
        y = r.y + 14 * u + i * 13 * u
        pygame.draw.line(s, (90, 70, 50), (r.x + 10 * u, y), (r.right - 10 * u, y), max(1, int(2 * u)))


# ---------- biểu tượng bảo vật ----------
def artifact(kind: str, size: int = 96) -> pygame.Surface:
    key = ("artifact", kind, size)
    if key in _misc:
        return _misc[key]
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    u = size / 100
    wood, dark, metal = (112, 74, 42), (70, 44, 26), (150, 156, 162)
    if kind == "coc":
        pygame.draw.polygon(s, wood, [(c - 10 * u, 90 * u), (c + 10 * u, 90 * u), (c + 8 * u, 26 * u), (c, 8 * u), (c - 8 * u, 26 * u)])
        pygame.draw.polygon(s, metal, [(c - 8 * u, 26 * u), (c + 8 * u, 26 * u), (c, 8 * u)])
        pygame.draw.rect(s, (86, 140, 150), (8 * u, 72 * u, 84 * u, 5 * u))
        pygame.draw.rect(s, (120, 170, 176), (14 * u, 82 * u, 72 * u, 4 * u))
    elif kind in ("hich", "sach"):
        _scroll_icon(s, size)
    elif kind == "guom":
        pygame.draw.polygon(s, (214, 222, 226), [(c - 5 * u, 66 * u), (c + 5 * u, 66 * u), (c + 3 * u, 16 * u), (c, 6 * u), (c - 3 * u, 16 * u)])
        pygame.draw.rect(s, theme.GOLD, (c - 18 * u, 64 * u, 36 * u, 6 * u), border_radius=2)
        pygame.draw.rect(s, dark, (c - 4 * u, 70 * u, 8 * u, 18 * u))
        pygame.draw.circle(s, theme.GOLD, (c, 91 * u), 5 * u)
    elif kind == "co":
        pygame.draw.line(s, dark, (28 * u, 92 * u), (28 * u, 8 * u), max(2, int(4 * u)))
        pygame.draw.polygon(s, theme.RED, [(30 * u, 10 * u), (88 * u, 18 * u), (74 * u, 34 * u), (88 * u, 50 * u), (30 * u, 54 * u)])
        pygame.draw.circle(s, theme.GOLD_LIGHT, (50 * u, 32 * u), 7 * u)
    elif kind == "co_sao":
        pygame.draw.line(s, dark, (20 * u, 94 * u), (20 * u, 8 * u), max(2, int(4 * u)))
        pygame.draw.rect(s, (190, 40, 34), (22 * u, 10 * u, 68 * u, 46 * u))
        _star(s, 56 * u, 33 * u, 16 * u, (250, 214, 60))
    elif kind == "an":
        pygame.draw.rect(s, theme.GOLD, (22 * u, 44 * u, 56 * u, 40 * u), border_radius=3)
        pygame.draw.rect(s, theme.GOLD_DARK, (22 * u, 44 * u, 56 * u, 40 * u), 2, border_radius=3)
        pygame.draw.circle(s, theme.GOLD, (c, 32 * u), 14 * u)
        pygame.draw.circle(s, theme.GOLD_DARK, (c, 32 * u), 14 * u, 2)
    elif kind == "phao":
        pygame.draw.line(s, (54, 58, 56), (24 * u, 70 * u), (86 * u, 30 * u), max(3, int(12 * u)))
        pygame.draw.circle(s, (34, 34, 34), (34 * u, 74 * u), 16 * u)
        pygame.draw.circle(s, (110, 106, 96), (34 * u, 74 * u), 6 * u)
    elif kind == "thuyen":
        _boat(s, c, 66 * u, 40 * u, sail=(170, 60, 44))
    elif kind == "qua_cam":
        pygame.draw.circle(s, (232, 134, 40), (c, 56 * u), 30 * u)
        pygame.draw.circle(s, (248, 176, 90), (c - 10 * u, 46 * u), 8 * u)
        pygame.draw.line(s, dark, (c, 28 * u), (c + 3 * u, 14 * u), max(2, int(3 * u)))
        pygame.draw.polygon(s, (70, 120, 60), [(c + 2 * u, 22 * u), (c + 26 * u, 10 * u), (c + 22 * u, 28 * u)])
    elif kind == "no":
        pygame.draw.line(s, wood, (c, 12 * u), (c, 92 * u), max(3, int(8 * u)))
        pygame.draw.arc(s, dark, (14 * u, 22 * u, 72 * u, 50 * u), 0.2, math.pi - 0.2, max(2, int(5 * u)))
        pygame.draw.line(s, (220, 214, 196), (17 * u, 42 * u), (83 * u, 42 * u), 1)
    else:
        return drum(size)
    _misc[key] = s
    return s


_cannon_cache: dict[int, pygame.Surface] = {}


def cannon_sprite(turn: float = 0.0) -> pygame.Surface:
    """Lựu pháo dã chiến: nòng dài, bộ phận giảm giật dưới nòng, tấm chắn, hai bánh lớn có nan, càng pháo chạm đất,
    cành lá ngụy trang gài trên tấm chắn. `turn` là góc bánh xe (radian) để bánh quay khi kéo."""
    step = int(turn * 4) % 8  # 8 góc quay là đủ mượt ở độ phân giải này
    if step in _cannon_cache:
        return _cannon_cache[step]
    out, olive, olive_d, olive_l = (24, 22, 18), (92, 104, 66), (64, 72, 46), (128, 140, 92)
    tire, hub, leaf = (34, 30, 26), (150, 140, 110), (70, 120, 56)
    low = pygame.Surface((46, 28), pygame.SRCALPHA)
    pygame.draw.polygon(low, out, [(1, 25), (16, 17), (19, 19), (4, 27)])  # càng pháo
    pygame.draw.polygon(low, olive_d, [(2, 25), (16, 18), (18, 19), (4, 26)])
    pygame.draw.polygon(low, out, [(16, 12), (44, 3), (45, 6), (17, 15)])  # nòng
    pygame.draw.polygon(low, olive, [(17, 12), (44, 4), (44, 5), (18, 14)])
    pygame.draw.line(low, olive_l, (18, 12), (43, 4))
    pygame.draw.rect(low, out, (42, 2, 4, 5))  # miệng nòng
    pygame.draw.polygon(low, out, [(15, 14), (31, 9), (32, 12), (16, 17)])  # bộ phận giảm giật
    pygame.draw.polygon(low, olive_d, [(16, 14), (30, 10), (31, 12), (17, 16)])
    pygame.draw.polygon(low, out, [(18, 6), (24, 4), (25, 18), (19, 20)])  # tấm chắn
    pygame.draw.polygon(low, olive, [(19, 7), (23, 5), (24, 17), (20, 19)])
    for x, y in ((19, 5), (22, 4), (24, 6), (20, 3)):  # lá ngụy trang
        pygame.draw.line(low, leaf, (x, y), (x - 2, y - 2))
        low.set_at((x - 2, y - 2), (96, 150, 70))
    cx, cy, r = 21, 21, 6  # bánh xe lớn có nan
    pygame.draw.circle(low, out, (cx, cy), r + 1)
    pygame.draw.circle(low, tire, (cx, cy), r)
    pygame.draw.circle(low, olive_d, (cx, cy), r - 2)
    for k in range(4):
        ang = turn + k * math.pi / 4
        dx, dy = math.cos(ang) * (r - 2), math.sin(ang) * (r - 2)
        pygame.draw.line(low, hub, (cx - dx, cy - dy), (cx + dx, cy + dy))
    pygame.draw.circle(low, hub, (cx, cy), 1)
    img = sprites.scaled(low, 3)
    _cannon_cache[step] = img
    return img
