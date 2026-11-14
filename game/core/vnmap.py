"""Bản đồ Việt Nam minh hoạ: dữ liệu đường viền, phép chiếu, camera pan/zoom.

Nền là bản đồ hiện nay vẽ giản lược (không dùng để tra cứu địa lý chính xác), luôn thể hiện
quần đảo Hoàng Sa và Trường Sa của Việt Nam (Req 10.2). Phép chiếu equirectangular.
"""

from __future__ import annotations

import math

import pygame

from core import art, fonts, theme

LAT_TOP, LAT_BOTTOM = 23.8, 8.0
LON_LEFT, LON_RIGHT = 101.6, 117.6
_COS = math.cos(math.radians(16))

# (lon, lat) theo chiều kim đồng hồ từ ngã ba biên giới phía tây bắc
OUTLINE = [
    (102.14, 22.40), (102.45, 22.72), (102.85, 22.62), (103.10, 22.52), (103.55, 22.70), (103.97, 22.50),
    (104.12, 22.77), (104.50, 22.65), (104.72, 22.80), (104.98, 22.92), (105.20, 23.08), (105.32, 23.39),
    (105.55, 23.22), (105.80, 23.08), (106.02, 22.96), (106.36, 22.86), (106.72, 22.86), (106.76, 22.66),
    (106.60, 22.46), (106.56, 22.22), (106.74, 22.02), (107.02, 21.84), (107.40, 21.62), (107.68, 21.60),
    (107.97, 21.53), (108.03, 21.46), (107.55, 21.25), (107.30, 21.00), (107.08, 20.92), (106.78, 20.70),
    (106.62, 20.50), (106.55, 20.25), (106.20, 19.97), (106.08, 19.95), (105.96, 19.92), (105.90, 19.72),
    (105.82, 19.35), (105.72, 19.08), (105.72, 18.82), (105.80, 18.68), (105.92, 18.40), (106.38, 18.08),
    (106.46, 17.75), (106.62, 17.48), (107.12, 17.03), (107.36, 16.75), (107.65, 16.55), (108.00, 16.33),
    (108.25, 16.08), (108.38, 15.87), (108.62, 15.55), (108.84, 15.40), (108.92, 15.12), (109.07, 14.67),
    (109.08, 14.50), (109.20, 14.00), (109.26, 13.75), (109.28, 13.45), (109.33, 13.08), (109.46, 12.90),
    (109.36, 12.60), (109.21, 12.24), (109.20, 11.86), (109.03, 11.58), (108.87, 11.33), (108.55, 11.17),
    (108.12, 10.92), (107.77, 10.65), (107.08, 10.33), (106.95, 10.40), (106.77, 10.32), (106.65, 10.00),
    (106.55, 9.63), (106.20, 9.48), (105.82, 9.24), (105.42, 9.02), (104.98, 8.72), (104.72, 8.60),
    (104.82, 9.02), (104.78, 9.40), (105.07, 9.98), (104.85, 10.20), (104.60, 10.26), (104.47, 10.40),
    (104.95, 10.60), (105.10, 10.95), (105.36, 10.92), (105.72, 10.96), (105.93, 10.85), (106.15, 11.08),
    (105.95, 11.20), (105.90, 11.66), (106.10, 11.76), (106.50, 11.98), (106.62, 11.97), (107.05, 12.25),
    (107.55, 12.32), (107.46, 12.85), (107.50, 13.20), (107.56, 13.80), (107.44, 13.98), (107.55, 14.70),
    (107.60, 15.20), (107.40, 15.75), (107.12, 16.30), (106.60, 16.62), (106.50, 16.90), (106.20, 17.30),
    (105.75, 17.68), (105.10, 18.38), (104.60, 18.80), (104.08, 19.38), (104.70, 19.72), (104.55, 20.25),
    (104.40, 20.45), (103.85, 20.82), (103.40, 20.80), (102.97, 21.20), (102.85, 21.60), (102.40, 22.02),
]

RIVERS = [
    [(103.97, 22.50), (104.42, 22.02), (104.92, 21.70), (105.40, 21.22), (105.86, 21.03), (106.12, 20.68), (106.55, 20.25)],
    [(103.05, 22.05), (103.70, 21.32), (104.60, 21.02), (105.32, 21.22)],
    [(105.02, 22.62), (105.20, 21.92), (105.42, 21.28)],
    [(105.84, 22.14), (105.90, 21.52), (106.10, 21.20), (106.32, 21.10)],
    [(106.32, 21.10), (106.60, 21.00), (106.82, 20.82)],
    [(103.62, 21.12), (104.60, 20.50), (105.30, 20.05), (105.90, 19.78)],
    [(104.22, 19.62), (105.02, 19.02), (105.70, 18.72)],
    [(107.82, 15.62), (108.36, 15.88)],
    [(108.30, 14.02), (109.32, 13.10)],
    [(108.02, 11.72), (107.02, 11.02), (106.90, 10.42)],
    [(105.22, 10.95), (105.82, 10.40), (106.62, 10.02)],
    [(105.08, 10.90), (105.62, 10.22), (106.28, 9.58)],
]

# Đảo ven bờ (lon, lat, bán kính tính theo độ)
ISLANDS = [(104.00, 10.22, 0.13), (106.60, 8.68, 0.05), (107.02, 20.80, 0.07), (107.72, 20.13, 0.03),
           (109.12, 15.38, 0.03), (108.94, 10.53, 0.03), (107.42, 21.05, 0.06)]
HOANG_SA = [(111.20, 16.55), (111.62, 16.48), (111.72, 16.82), (112.10, 16.60), (112.34, 16.90), (112.72, 16.68), (112.26, 16.28), (111.90, 16.20), (111.50, 15.98)]
TRUONG_SA = [(111.92, 8.65), (112.40, 9.40), (113.10, 9.92), (114.10, 10.38), (114.36, 11.05), (114.28, 11.42), (115.02, 10.72), (115.42, 9.92), (115.78, 10.52), (114.72, 9.08), (113.72, 8.82), (113.02, 8.42)]

LABELS = [("Hà Nội", 105.85, 21.03), ("Huế", 107.59, 16.46), ("Đà Nẵng", 108.22, 16.05),
          ("TP. Hồ Chí Minh", 106.68, 10.78), ("Cần Thơ", 105.78, 10.03)]

MOUNTAINS = [(103.4, 21.7), (104.0, 21.1), (104.6, 21.9), (105.4, 22.5), (106.2, 22.2), (103.2, 22.1),
             (105.0, 20.3), (105.2, 19.3), (106.3, 17.5), (107.4, 15.4), (108.0, 14.4), (108.0, 12.7),
             (107.5, 12.9), (107.3, 16.1), (106.7, 21.5), (104.2, 20.7), (107.9, 13.5), (105.6, 18.2)]


class MapView:
    """Camera bản đồ: `zoom` = 1 thấy toàn bộ khung, càng lớn càng gần."""

    MIN_ZOOM, MAX_ZOOM = 1.0, 7.0

    def __init__(self, rect, center=(16.0, 108.0), zoom=1.0):
        self.rect = pygame.Rect(rect)
        self.lat, self.lon = center
        self.zoom = zoom
        self._base = min(self.rect.height / (LAT_TOP - LAT_BOTTOM),
                         self.rect.width / ((LON_RIGHT - LON_LEFT) * _COS))
        self._cache: pygame.Surface | None = None
        self._cache_key = None
        self._drag = None

    @property
    def scale(self) -> float:
        return self._base * self.zoom

    def to_screen(self, lat: float, lon: float) -> tuple[float, float]:
        s = self.scale
        return (self.rect.centerx + (lon - self.lon) * s * _COS, self.rect.centery - (lat - self.lat) * s)

    def to_geo(self, x: float, y: float) -> tuple[float, float]:
        s = self.scale
        return (self.lat - (y - self.rect.centery) / s, self.lon + (x - self.rect.centerx) / (s * _COS))

    def focus(self, lat: float, lon: float, zoom: float | None = None):
        self.lat, self.lon = lat, lon
        if zoom is not None:
            self.zoom = zoom
        self._clamp()

    def _clamp(self):
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom))
        self.lat = max(LAT_BOTTOM, min(LAT_TOP, self.lat))
        self.lon = max(LON_LEFT, min(LON_RIGHT, self.lon))

    def zoom_at(self, factor: float, px: float | None = None, py: float | None = None):
        px = self.rect.centerx if px is None else px
        py = self.rect.centery if py is None else py
        lat0, lon0 = self.to_geo(px, py)
        self.zoom *= factor
        self._clamp()
        lat1, lon1 = self.to_geo(px, py)
        self.lat += lat0 - lat1
        self.lon += lon0 - lon1
        self._clamp()

    def handle(self, event) -> bool:
        """Kéo để di chuyển, cuộn chuột để phóng to. Trả True nếu người chơi đang kéo bản đồ."""
        if event.type == pygame.MOUSEWHEEL:
            self.zoom_at(1.18 if event.y > 0 else 1 / 1.18, *pygame.mouse.get_pos())
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self._drag = {"start": event.pos, "lat": self.lat, "lon": self.lon, "moved": False}
        elif event.type == pygame.MOUSEMOTION and self._drag:
            dx = event.pos[0] - self._drag["start"][0]
            dy = event.pos[1] - self._drag["start"][1]
            if abs(dx) + abs(dy) > 5:
                self._drag["moved"] = True
            if self._drag["moved"]:
                self.lat = self._drag["lat"] + dy / self.scale
                self.lon = self._drag["lon"] - dx / (self.scale * _COS)
                self._clamp()
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self._drag:
            moved = self._drag["moved"]
            self._drag = None
            return moved
        return False

    # ----- vẽ -----
    def _pts(self, seq):
        return [self.to_screen(lat, lon) for lon, lat in seq]

    def _render(self) -> pygame.Surface:
        """Lớp nền tĩnh, chỉ dựng lại khi kéo hoặc phóng to: biển, nước láng giềng, đất liền có núi rừng đồng lúa."""
        r = self.rect
        ox, oy = r.x, r.y
        z = self.zoom
        k = min(2.4, 0.75 + z * 0.28)  # cỡ hình vẽ trang trí theo độ phóng
        s = art.gradient(r.width, r.height, [(64, 128, 142), (92, 156, 164), (78, 140, 154)])

        def shift(p):
            return (p[0] - ox, p[1] - oy)

        def poly(seq):
            return [shift(p) for p in self._pts(seq)]

        # kinh tuyến, vĩ tuyến mờ như bản đồ cổ
        for lon in range(100, 120, 2):
            x = shift(self.to_screen(LAT_TOP, lon))[0]
            if 0 <= x < r.width:
                for y in range(0, r.height, 10):
                    pygame.draw.line(s, (104, 166, 172), (x, y), (x, y + 4))
        for lat in range(6, 26, 2):
            y = shift(self.to_screen(lat, LON_LEFT))[1]
            if 0 <= y < r.height:
                for x in range(0, r.width, 10):
                    pygame.draw.line(s, (104, 166, 172), (x, y), (x + 4, y))
        land = poly(OUTLINE)
        foreign = [poly(p) for p in FOREIGN]
        # vùng nước nông ven bờ
        halo = max(6, int(10 * k))
        for p in [land, *foreign]:
            pygame.draw.lines(s, (124, 182, 182), True, p, halo * 2)
            pygame.draw.lines(s, (146, 198, 192), True, p, halo)
        for p in foreign:
            pygame.draw.polygon(s, (206, 196, 168), p)
            pygame.draw.lines(s, (160, 148, 120), True, p, 1)
        pygame.draw.polygon(s, (114, 92, 60), [(x + 3, y + 4) for x, y in land])
        pygame.draw.polygon(s, (222, 206, 150), land)
        # đồng bằng: thửa ruộng xanh
        forest_pts, paddy_pts, sea_pts = _decor()
        for lon, lat in paddy_pts:
            x, y = shift(self.to_screen(lat, lon))
            if -20 < x < r.width + 20 and -20 < y < r.height + 20:
                w = 5 * k
                pygame.draw.rect(s, (150, 186, 92), (x - w, y - w * 0.6, w * 2, w * 1.2))
                pygame.draw.line(s, (120, 160, 76), (x - w, y), (x + w, y), 1)
        # rừng và núi vùng cao
        for i, (lon, lat) in enumerate(forest_pts):
            x, y = shift(self.to_screen(lat, lon))
            if not (-30 < x < r.width + 30 and -30 < y < r.height + 30):
                continue
            g = (96 + (i * 37) % 30, 140 + (i * 13) % 26, 70)
            rr = 3.2 * k
            pygame.draw.circle(s, (64, 96, 52), (x + 1, y + 1), rr)
            pygame.draw.circle(s, g, (x, y), rr)
            pygame.draw.circle(s, (min(255, g[0] + 40), min(255, g[1] + 40), 96), (x - rr * 0.35, y - rr * 0.35), rr * 0.35)
        for lon, lat in MOUNTAINS + _decor_mountains():
            x, y = shift(self.to_screen(lat, lon))
            if not (-60 < x < r.width + 60 and -60 < y < r.height + 60):
                continue
            for dx, sz in ((0, 9), (-11, 7), (11, 7)):
                m = sz * k
                cx = x + dx * z ** 0.4
                peak, left, right = (cx, y - m), (cx - m, y + m * 0.5), (cx + m, y + m * 0.5)
                pygame.draw.polygon(s, (168, 140, 96), [left, peak, (cx, y + m * 0.5)])
                pygame.draw.polygon(s, (130, 104, 70), [peak, right, (cx, y + m * 0.5)])
                pygame.draw.lines(s, (92, 72, 48), False, [left, peak, right], 1)
                pygame.draw.polygon(s, (236, 226, 200), [peak, (cx - m * 0.28, y - m * 0.58), (cx + m * 0.22, y - m * 0.62)])
        # sông
        width = max(2, int(1.5 + z * 0.45))
        for river in RIVERS:
            pts = [shift(p) for p in self._pts(river)]
            pygame.draw.lines(s, (66, 120, 140), False, pts, width + 2)
            pygame.draw.lines(s, (112, 176, 200), False, pts, width)
        pygame.draw.lines(s, (92, 70, 44), True, land, 2)
        # đảo
        for lon, lat, rad in ISLANDS:
            x, y = shift(self.to_screen(lat, lon))
            rr = max(2, rad * self.scale)
            pygame.draw.circle(s, (146, 198, 192), (x, y), rr + 4)
            pygame.draw.circle(s, (222, 206, 150), (x, y), rr)
            pygame.draw.circle(s, (92, 70, 44), (x, y), rr, 1)
        for group in (HOANG_SA, TRUONG_SA):
            for lon, lat in group:
                x, y = shift(self.to_screen(lat, lon))
                rr = 2 + int(z ** 0.5)
                pygame.draw.circle(s, (146, 198, 192), (x, y), rr + 3)
                pygame.draw.circle(s, (222, 206, 150), (x, y), rr)
                pygame.draw.circle(s, (92, 70, 44), (x, y), rr, 1)
        # nhãn
        f = fonts.font("semi", 13)
        sea = fonts.font("italic", 15 + int(z))
        for text, lat, lon in (("BIỂN ĐÔNG", 13.4, 112.2), ("Vịnh Bắc Bộ", 20.2, 107.6), ("Vịnh Thái Lan", 9.6, 102.6)):
            x, y = shift(self.to_screen(lat, lon))
            fonts.text(s, text, sea, (226, 240, 236), (x + 1, y + 1), "center")
            fonts.text(s, text, sea, (40, 84, 98), (x, y), "center")
        for text, lat, lon in (("Q.Đ. Hoàng Sa (Việt Nam)", 17.25, 112.0), ("Q.Đ. Trường Sa (Việt Nam)", 11.95, 114.0)):
            x, y = shift(self.to_screen(lat, lon))
            fonts.text(s, text, f, (24, 56, 72), (x, y), "center")
        country = fonts.font("italic", 14)
        for text, lat, lon in NEIGHBOR_LABELS:
            x, y = shift(self.to_screen(lat, lon))
            fonts.text(s, text, country, (128, 116, 92), (x, y), "center")
        if z >= 1.5:
            small = fonts.font("ui", 12)
            for name, lon, lat in LABELS:
                x, y = shift(self.to_screen(lat, lon))
                pygame.draw.circle(s, theme.INK, (x, y), 3)
                pygame.draw.circle(s, theme.PAPER, (x, y), 1)
                fonts.text(s, name, small, theme.INK, (x + 6, y + 1))
        return s

    def draw(self, surface: pygame.Surface):
        key = (round(self.lat, 3), round(self.lon, 3), round(self.zoom, 3))
        if key != self._cache_key:
            self._cache = self._render()
            self._cache_key = key
        surface.blit(self._cache, self.rect)

    def draw_life(self, surface: pygame.Surface, t: float):
        """Lớp sống động vẽ mỗi khung hình: sóng lấp lánh, thuyền buồm chạy ven biển, mây trôi, chim bay."""
        r = self.rect
        prev = surface.get_clip()
        surface.set_clip(r)
        k = min(2.0, 0.8 + self.zoom * 0.2)
        for i, (lon, lat) in enumerate(_decor()[2]):
            x, y = self.to_screen(lat, lon)
            if not r.collidepoint(x, y):
                continue
            a = 0.5 + 0.5 * math.sin(t * 1.6 + i * 1.7)
            if a < 0.35:
                continue
            c = (int(150 + 90 * a), int(196 + 50 * a), int(196 + 50 * a))
            w = 9 * k
            pygame.draw.arc(surface, c, (x - w, y - 3, w, 6), 0.2, 2.9, 1)
            pygame.draw.arc(surface, c, (x, y - 3, w, 6), 0.2, 2.9, 1)
        boat = _boat_sprite()
        for j, route in enumerate(SEA_ROUTES):
            u = (t * 0.018 + j * 0.37) % 2.0
            u = u if u <= 1 else 2 - u  # chạy đi rồi chạy về
            lon, lat, heading = _along(route, u)
            x, y = self.to_screen(lat, lon)
            if r.collidepoint(x, y):
                img = boat if heading >= 0 else pygame.transform.flip(boat, True, False)
                bob = math.sin(t * 2.4 + j) * 1.5
                pygame.draw.line(surface, (220, 240, 236), (x - 18 * (1 if heading >= 0 else -1), y + 6), (x, y + 6), 1)
                surface.blit(img, img.get_rect(midbottom=(x, y + 6 + bob)))
        for j, (cy, speed, size) in enumerate(((0.22, 9, 1.0), (0.52, 6, 1.3), (0.78, 11, 0.8), (0.36, 7, 1.1))):
            cloud = _cloud_sprite(size)
            span = r.width + cloud.get_width() * 2
            x = r.x - cloud.get_width() + (t * speed + j * span / 4) % span
            surface.blit(cloud, (x, r.y + r.height * cy))
        cycle = (t % 26) / 26
        if cycle < 0.6:
            bx = r.x - 60 + cycle / 0.6 * (r.width + 120)
            by = r.y + r.height * 0.3 + math.sin(cycle * 6) * 30
            for n, (dx, dy) in enumerate(((0, 0), (-16, -8), (-16, 8), (-32, -16), (-32, 16))):
                flap = 4 if int(t * 6 + n) % 2 else -2
                px, py = bx + dx, by + dy
                pygame.draw.lines(surface, (48, 54, 60), False, [(px - 6, py + flap), (px, py), (px + 6, py + flap)], 2)
        surface.set_clip(prev)


_life: dict = {}


def _boat_sprite() -> pygame.Surface:
    if "boat" not in _life:
        low = pygame.Surface((12, 10), pygame.SRCALPHA)
        pygame.draw.polygon(low, (70, 46, 30), [(0, 7), (11, 7), (9, 9), (2, 9)])
        pygame.draw.line(low, (60, 40, 28), (6, 1), (6, 7))
        pygame.draw.polygon(low, (236, 220, 180), [(7, 1), (11, 6), (7, 6)])
        pygame.draw.polygon(low, (200, 70, 50), [(5, 2), (5, 6), (2, 6)])
        _life["boat"] = pygame.transform.scale(low, (36, 30))
    return _life["boat"]


def _cloud_sprite(size: float) -> pygame.Surface:
    key = ("cloud", size)
    if key not in _life:
        w, h = int(170 * size), int(70 * size)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for cx, cy, rr in ((0.3, 0.6, 0.28), (0.5, 0.45, 0.36), (0.7, 0.6, 0.26), (0.5, 0.7, 0.3)):
            pygame.draw.circle(s, (255, 255, 255, 46), (w * cx, h * cy), h * rr * 1.2)
        _life[key] = s
    return _life[key]


def _along(route, u):
    """Điểm ở vị trí u (0..1) trên một đường gấp khúc, kèm hướng đông/tây để lật thuyền."""
    seg = [math.dist(a, b) for a, b in zip(route, route[1:], strict=False)]
    d = u * sum(seg)
    for (a, b), n in zip(zip(route, route[1:], strict=False), seg, strict=False):
        if d <= n or b is route[-1]:
            f = d / n if n else 0
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, b[0] - a[0]
        d -= n
    return route[-1][0], route[-1][1], 1


def _inside(lon, lat, ring) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=False):
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _coast_dist(lon, lat) -> float:
    best = 9.0
    for (x1, y1), (x2, y2) in zip(COAST, COAST[1:], strict=False):
        dx, dy = x2 - x1, y2 - y1
        f = max(0.0, min(1.0, ((lon - x1) * dx + (lat - y1) * dy) / (dx * dx + dy * dy or 1)))
        best = min(best, math.hypot(lon - x1 - f * dx, lat - y1 - f * dy))
    return best


def _scatter():
    """Chia đất liền thành vùng cao (rừng, núi) và hai châu thổ (ruộng lúa) theo lưới đều, có lệch nhẹ cho tự nhiên."""
    forest, paddy, mountains = [], [], []
    lat = 8.4
    row = 0
    while lat < 23.5:
        lon = 102.0 + (row % 2) * 0.18
        while lon < 109.6:
            jx = ((int(lon * 100) * 7 + row * 13) % 11 - 5) * 0.02
            jy = ((int(lon * 100) * 3 + row * 17) % 9 - 4) * 0.02
            p = (lon + jx, lat + jy)
            if _inside(*p, OUTLINE):
                red = math.hypot(p[0] - 106.15, (p[1] - 20.75) * 1.2) < 0.8
                mekong = p[1] < 10.9 and p[0] > 104.9
                if red or mekong:
                    paddy.append(p)
                elif _coast_dist(*p) > 0.42:
                    (mountains if (row + int(lon * 3)) % 7 == 0 and (p[1] > 20.6 or 11.6 < p[1] < 16.4) else forest).append(p)
            lon += 0.36
        lat += 0.3
        row += 1
    return forest, paddy, mountains


# ----- vùng láng giềng và đường biển, tính một lần từ đường viền Việt Nam -----
_MONG_CAI = OUTLINE.index((108.03, 21.46))
_HA_TIEN = OUTLINE.index((104.47, 10.40))
COAST = OUTLINE[_MONG_CAI:_HA_TIEN + 1]
_NORTH_BORDER = OUTLINE[: _MONG_CAI + 1]
_WEST_BORDER = OUTLINE[_HA_TIEN:] + OUTLINE[:1]
# Nước láng giềng chỉ tô màu nhạt cho Việt Nam nổi lên; bờ biển của họ vẽ phỏng theo, không dùng để tra cứu
_CHINA = [(99.0, 26.5), (119.0, 26.5), (119.0, 23.0), (116.0, 22.9), (113.5, 22.3), (112.2, 21.85), (111.0, 21.5),
          (110.4, 21.3), (110.15, 20.35), (109.85, 20.4), (109.7, 21.0), (109.1, 21.55), (108.5, 21.65),
          *reversed(_NORTH_BORDER), (101.7, 22.5), (99.0, 22.5)]
_WEST = [(99.0, 22.5), (101.7, 22.5), *reversed(_WEST_BORDER), (104.2, 10.55), (103.6, 10.5), (103.1, 11.2),
         (102.9, 11.75), (102.5, 12.25), (101.6, 12.65), (100.9, 12.7), (100.5, 13.5), (99.9, 12.5), (99.6, 10.5),
         (99.2, 9.0), (99.0, 8.0)]
_HAINAN = [(108.62, 19.12), (109.15, 18.4), (109.6, 18.2), (110.1, 18.3), (110.55, 18.8), (111.0, 19.6), (110.7, 20.1),
           (110.2, 20.05), (109.6, 20.0), (109.2, 19.75), (108.7, 19.5)]
FOREIGN = [_CHINA, _WEST, _HAINAN]
NEIGHBOR_LABELS = [("Trung Quốc", 23.2, 107.4), ("Lào", 19.2, 103.3), ("Cam-pu-chia", 12.6, 105.1)]
SEA_ROUTES = [
    [(107.9, 20.4), (107.1, 19.9), (106.6, 19.0)],
    [(108.9, 16.2), (109.5, 14.5), (109.6, 12.6)],
    [(109.0, 11.0), (107.8, 9.9), (106.4, 8.9)],
    [(109.0, 16.0), (110.6, 16.4), (111.6, 16.7)],
    [(104.4, 9.4), (103.6, 10.0), (103.3, 9.0)],
]
_decor_cache: dict = {}


def _decor():
    """Điểm rừng, ruộng, sóng: tính lần đầu cần vẽ để khỏi làm chậm lúc mở game."""
    if "pts" not in _decor_cache:
        forest, paddy, mountains = _scatter()
        sea = []
        lat = 7.6
        while lat < 23.4:
            lon = 102.2 + (int(lat * 10) % 2) * 0.3
            while lon < 117.6:
                if not _inside(lon, lat, OUTLINE) and not any(_inside(lon, lat, f) for f in FOREIGN):
                    sea.append((lon, lat))
                lon += 0.62
            lat += 0.55
        _decor_cache["pts"] = (forest, paddy, sea)
        _decor_cache["mountains"] = mountains
    return _decor_cache["pts"]


def _decor_mountains():
    _decor()
    return _decor_cache["mountains"]
