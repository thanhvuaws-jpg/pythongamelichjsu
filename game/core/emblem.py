"""Mặt trống đồng kiểu Đông Sơn để trang trí màn tựa đề: ngôi sao nhiều cánh ở tâm, các vành hoa văn hình học, vành chim
bay quanh. Đây là hình trang trí phỏng theo, không phải bản vẽ lại một chiếc trống cụ thể.

Mặt trống vẽ một lần rồi cất; đàn chim vẽ mỗi khung từ một con chim đã xoay sẵn theo 36 hướng, nên nhẹ khi chạy trên web.
"""

from __future__ import annotations

import math

import pygame

BRONZE, BRONZE_D, BRONZE_L, LINE = (168, 124, 66), (112, 78, 40), (214, 172, 104), (86, 58, 30)
STAR = (240, 204, 120)
_cache: dict = {}


def _ring_dots(s, c, r, n, size, color):
    for i in range(n):
        a = math.tau * i / n
        x, y = c + math.cos(a) * r, c + math.sin(a) * r
        pygame.draw.circle(s, color, (x, y), size, 1)
        pygame.draw.circle(s, color, (x, y), max(1, size // 3))


def _hatch(s, c, r0, r1, n, color):
    for i in range(n):
        a = math.tau * i / n
        pygame.draw.line(s, color, (c + math.cos(a) * r0, c + math.sin(a) * r0), (c + math.cos(a + 0.05) * r1, c + math.sin(a + 0.05) * r1))


def _zigzag(s, c, r0, r1, n, color):
    pts = []
    for i in range(n * 2 + 1):
        a = math.tau * i / (n * 2)
        r = r0 if i % 2 else r1
        pts.append((c + math.cos(a) * r, c + math.sin(a) * r))
    pygame.draw.lines(s, color, False, pts, 2)


def face(radius: int) -> pygame.Surface:
    """Mặt trống tĩnh (không có chim)."""
    key = ("face", radius)
    if key in _cache:
        return _cache[key]
    size = radius * 2 + 4
    c = size / 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(s, BRONZE_D, (c, c), radius + 2)
    pygame.draw.circle(s, BRONZE, (c, c), radius)
    # ánh sáng loang nhẹ phía trên bên trái
    for i in range(8):
        pygame.draw.circle(s, (*BRONZE_L, 14), (c - radius * 0.25, c - radius * 0.25), radius * (0.9 - i * 0.1))
    for frac in (0.18, 0.27, 0.37, 0.63, 0.87, 0.97):
        pygame.draw.circle(s, LINE, (c, c), radius * frac, 2)
    _ring_dots(s, c, radius * 0.225, 16, max(3, radius // 40), LINE)
    _zigzag(s, c, radius * 0.29, radius * 0.35, 28, LINE)
    _hatch(s, c, radius * 0.39, radius * 0.61, 72, (*LINE, 160))
    _ring_dots(s, c, radius * 0.92, 40, max(3, radius // 45), LINE)
    # ngôi sao nhiều cánh ở tâm
    rays = 14
    pts = []
    for i in range(rays * 2):
        a = math.tau * i / (rays * 2) - math.pi / 2
        r = radius * (0.165 if i % 2 == 0 else 0.055)
        pts.append((c + math.cos(a) * r, c + math.sin(a) * r))
    pygame.draw.polygon(s, STAR, pts)
    pygame.draw.polygon(s, LINE, pts, 1)
    pygame.draw.circle(s, BRONZE_L, (c, c), radius * 0.05)
    _cache[key] = s
    return s


def _bird(length: int) -> pygame.Surface:
    """Chim mỏ dài, đuôi dài, cánh dang, bay sang phải; nét đúc nổi màu đồng sẫm."""
    w, h = length, max(8, length // 2)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cy = h / 2
    body = [(w * 0.15, cy), (w * 0.55, cy - h * 0.12), (w * 0.72, cy), (w * 0.55, cy + h * 0.12)]
    pygame.draw.polygon(s, LINE, body)
    pygame.draw.line(s, LINE, (w * 0.72, cy), (w, cy - h * 0.05), 2)  # mỏ dài
    pygame.draw.polygon(s, LINE, [(w * 0.35, cy), (w * 0.5, 0), (w * 0.58, cy - h * 0.1)])  # cánh
    pygame.draw.polygon(s, LINE, [(w * 0.38, cy), (w * 0.52, h), (w * 0.6, cy + h * 0.1)])
    pygame.draw.polygon(s, LINE, [(w * 0.18, cy), (0, cy - h * 0.3), (0, cy + h * 0.3)])  # đuôi xoè
    return s


def birds(radius: int) -> list[pygame.Surface]:
    """Con chim xoay sẵn theo 36 hướng (mỗi hướng 10 độ)."""
    key = ("birds", radius)
    if key not in _cache:
        base = _bird(max(16, int(radius * 0.2)))
        _cache[key] = [pygame.transform.rotate(base, -a * 10) for a in range(36)]
    return _cache[key]


def draw(surface: pygame.Surface, center: tuple[int, int], radius: int, t: float, count: int = 18, alpha: int = 255) -> None:
    """Vẽ mặt trống cùng đàn chim bay ngược chiều kim đồng hồ quanh vành."""
    f = face(radius)
    if alpha < 255:
        f = f.copy()
        f.set_alpha(alpha)
    surface.blit(f, f.get_rect(center=center))
    frames = birds(radius)
    ring = radius * 0.75
    spin = -t * 0.12
    for i in range(count):
        a = math.tau * i / count + spin
        x, y = center[0] + math.cos(a) * ring, center[1] + math.sin(a) * ring
        heading = math.degrees(a) - 90  # bay theo tiếp tuyến, ngược chiều kim đồng hồ
        img = frames[int(round(heading / 10)) % 36]
        surface.blit(img, img.get_rect(center=(x, y)))
