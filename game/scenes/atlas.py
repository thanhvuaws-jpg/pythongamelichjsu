"""Bản đồ Việt Nam (phím M): xem vị trí thật của các di tích trong màn và đi nhanh tới nơi đã mở (Req 10, 11)."""

from __future__ import annotations

import math

import pygame
from core import fonts, theme, ui
from core.scene import Scene
from core.vnmap import MapView

PIN_R = 11
INFO = pygame.Rect(18, theme.HEIGHT - 240, 480, 222)
LABEL_ZOOM = 3.0


class AtlasScene(Scene):
    def __init__(self, app, level_id: str):
        super().__init__(app)
        self.level_id = level_id
        self.bundle = self.state.levels[level_id]
        self.level = self.bundle["level"]
        v = self.level.get("atlas_view") or self.level.get("map_view", {})
        self.map = MapView((0, 0, theme.WIDTH, theme.HEIGHT), (v.get("lat", 21), v.get("lon", 106)), v.get("zoom", 4))
        self.engine = self.state.engine(level_id)
        self.relics = self.bundle["relics"]
        self.places = {p["id"]: p for p in self.bundle["places"]}
        self.selected = None
        self.hover = None
        self.group = ui.ButtonGroup()
        self.group.add(ui.Button((theme.WIDTH - 136, 14, 122, 40), "Đóng", lambda: self.app.scenes.pop(), "ghost", size=15))
        self.group.add(ui.Button((theme.WIDTH - 62, theme.HEIGHT - 124, 46, 46), "+", lambda: self.map.zoom_at(1.3), "ghost", size=24))
        self.group.add(ui.Button((theme.WIDTH - 62, theme.HEIGHT - 70, 46, 46), "−", lambda: self.map.zoom_at(1 / 1.3), "ghost", size=24))
        self.info_group = ui.ButtonGroup()
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def _relic_at(self, pos):
        for r in reversed(self.relics):
            p = self.places[r["place"]]
            x, y = self.map.to_screen(p["lat"], p["lon"])
            if (x - pos[0]) ** 2 + (y - pos[1]) ** 2 <= (PIN_R + 6) ** 2:
                return r
        return None

    def _state(self, relic) -> str:
        if self.state.relic_done(relic["id"]):
            return "done"
        return "open" if relic["place"] in self.engine.unlocked_places() else "locked"

    def _select(self, relic):
        self.selected = relic
        self.info_group.clear()
        if relic:
            ok = self._state(relic) != "locked"
            self.info_group.add(ui.Button((INFO.x + 20, INFO.bottom - 60, INFO.w - 150, 46), "Đi nhanh tới đây" if ok else "Chưa mở khoá", lambda: self.app.scenes.pop({"travel": relic["id"]}), "gold", ok, 17))
            self.info_group.add(ui.Button((INFO.right - 118, INFO.bottom - 60, 98, 46), "Đóng", lambda: self._select(None), "ghost", size=16))

    def handle(self, event):
        if self.info_group.handle(event) or self.group.handle(event):
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_m):
            self.app.scenes.pop()
            return
        if event.type == pygame.MOUSEMOTION:
            self.hover = self._relic_at(event.pos)
        over = self.selected and event.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONDOWN) and INFO.collidepoint(event.pos)
        if over:
            return
        dragged = self.map.handle(event)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and not dragged:
            self._select(self._relic_at(event.pos))

    def draw(self, screen):
        self.map.draw(screen)
        self.map.draw_life(screen, self.t)
        self._draw_route(screen)
        self._draw_pins(screen)
        self._draw_frame(screen)
        self._draw_title(screen)
        self._draw_compass(screen, theme.WIDTH - 124, theme.HEIGHT - 250)
        if not self.selected:
            self._draw_legend(screen)
        self.group.draw(screen)
        if self.selected:
            self._draw_info(screen)
            self.info_group.draw(screen)

    # ----- trang trí -----
    def _draw_frame(self, screen):
        """Khung sơn mài viền vàng như tấm bản đồ treo tường, góc có hoạ tiết."""
        w, h = theme.WIDTH, theme.HEIGHT
        for i, col in enumerate(((28, 18, 15), (122, 30, 24), (217, 167, 72))):
            pygame.draw.rect(screen, col, (i * 3, i * 3, w - i * 6, h - i * 6), 3)
        for cx, cy in ((14, 14), (w - 14, 14), (14, h - 14), (w - 14, h - 14)):
            pygame.draw.rect(screen, (28, 18, 15), (cx - 9, cy - 9, 18, 18))
            pygame.draw.rect(screen, (217, 167, 72), (cx - 6, cy - 6, 12, 12), 2)
            pygame.draw.rect(screen, (243, 212, 140), (cx - 2, cy - 2, 4, 4))

    def _draw_title(self, screen):
        """Cuộn giấy tiêu đề: tên màn, giai đoạn, hướng dẫn."""
        r = pygame.Rect(22, 18, 520, 86)
        pygame.draw.rect(screen, (28, 18, 15), r.move(4, 5))
        pygame.draw.rect(screen, theme.PAPER, r)
        pygame.draw.rect(screen, theme.LACQUER_RED, r, 3)
        for x in (r.x - 6, r.right - 6):  # hai trục cuộn
            pygame.draw.rect(screen, (92, 54, 30), (x, r.y - 6, 12, r.h + 12))
            pygame.draw.rect(screen, (217, 167, 72), (x + 2, r.y - 6, 8, 5))
            pygame.draw.rect(screen, (217, 167, 72), (x + 2, r.bottom + 1, 8, 5))
        fonts.text(screen, self.level["title"], fonts.font("serif", 22), theme.LACQUER_RED, (r.x + 22, r.y + 10))
        fonts.text(screen, f"Giai đoạn {self.level['period_label']}", fonts.font("semi", 14), theme.INK, (r.x + 22, r.y + 42))
        fonts.text(screen, "Bản đồ minh hoạ. Kéo để di chuyển, cuộn chuột để phóng to.", fonts.font("ui", 12), theme.INK_SOFT, (r.x + 22, r.y + 62))

    def _draw_compass(self, screen, cx, cy):
        """La bàn tám hướng, chữ Bắc ở trên."""
        pygame.draw.circle(screen, (28, 18, 15, 0), (cx + 2, cy + 3), 46)
        pygame.draw.circle(screen, theme.PAPER, (cx, cy), 44)
        pygame.draw.circle(screen, theme.LACQUER_RED, (cx, cy), 44, 2)
        pygame.draw.circle(screen, theme.GOLD_DARK, (cx, cy), 36, 1)
        for i in range(8):
            a = i * math.pi / 4 - math.pi / 2
            length = 34 if i % 2 == 0 else 22
            tip = (cx + math.cos(a) * length, cy + math.sin(a) * length)
            side = (a + math.pi / 2)
            w = 7 if i % 2 == 0 else 5
            l1 = (cx + math.cos(side) * w, cy + math.sin(side) * w)
            l2 = (cx - math.cos(side) * w, cy - math.sin(side) * w)
            col = theme.LACQUER_RED if i == 0 else (theme.INK if i % 2 == 0 else theme.GOLD_DARK)
            pygame.draw.polygon(screen, col, [tip, l1, (cx, cy)])
            pygame.draw.polygon(screen, theme.PAPER_3, [tip, l2, (cx, cy)])
            pygame.draw.polygon(screen, theme.INK, [tip, l1, (cx, cy), l2], 1)
        fonts.text(screen, "B", fonts.font("black", 16), theme.LACQUER_RED, (cx, cy - 58), "center")

    def _draw_legend(self, screen):
        r = pygame.Rect(22, theme.HEIGHT - 132, 300, 112)
        ui.alpha_rect(screen, r, (240, 228, 200, 236), 4)
        pygame.draw.rect(screen, theme.LACQUER_RED, r, 2, border_radius=4)
        fonts.text(screen, "Chú thích", fonts.font("bold", 15), theme.INK, (r.x + 14, r.y + 8))
        y = r.y + 36
        for state, label in (("done", "Di tích đã đóng dấu"), ("open", "Đang mở, đi nhanh tới được"), ("locked", "Chưa mở khoá")):
            self._pin(screen, state, r.x + 28, y + 9, 0.0)
            fonts.text(screen, label, fonts.font("ui", 14), theme.INK_SOFT, (r.x + 50, y))
            y += 24

    def _draw_route(self, screen):
        """Đường hành trình nối các di tích theo thứ tự trong màn, nét đứt chạy chậm như mực đang vẽ."""
        pts = [self.map.to_screen(self.places[r["place"]]["lat"], self.places[r["place"]]["lon"]) for r in self.relics]
        offset = (self.t * 18) % 16
        for (x0, y0), (x1, y1) in zip(pts, pts[1:], strict=False):
            dist = math.hypot(x1 - x0, y1 - y0)
            if dist < 1:
                continue
            ux, uy = (x1 - x0) / dist, (y1 - y0) / dist
            d = offset
            while d < dist:
                e = min(dist, d + 8)
                pygame.draw.line(screen, (122, 30, 24), (x0 + ux * d, y0 + uy * d), (x0 + ux * e, y0 + uy * e), 3)
                d += 16

    def _pin(self, screen, state, x, y, t):
        if state == "done":
            pygame.draw.rect(screen, (28, 18, 15), (x - 10, y - 9, 22, 22))
            pygame.draw.rect(screen, theme.LACQUER_RED, (x - 11, y - 11, 22, 22))
            pygame.draw.rect(screen, theme.GOLD_LIGHT, (x - 8, y - 8, 16, 16), 2)
            pygame.draw.lines(screen, theme.GOLD_LIGHT, False, [(x - 5, y), (x - 1, y + 4), (x + 6, y - 5)], 3)
        elif state == "open":
            ring = 14 + 6 * (0.5 + 0.5 * math.sin(t * 4))
            pygame.draw.circle(screen, (243, 212, 140), (x, y), ring, 2)
            pygame.draw.circle(screen, (28, 18, 15), (x + 1, y + 2), PIN_R + 1)
            pygame.draw.circle(screen, theme.RED_BRIGHT, (x, y), PIN_R)
            pygame.draw.circle(screen, theme.GOLD_LIGHT, (x, y), PIN_R, 2)
            pygame.draw.circle(screen, theme.GOLD_LIGHT, (x, y), 3)
        else:
            pygame.draw.circle(screen, (28, 18, 15), (x + 1, y + 2), PIN_R)
            pygame.draw.circle(screen, (150, 142, 128), (x, y), PIN_R - 1)
            pygame.draw.arc(screen, (40, 32, 26), (x - 5, y - 8, 10, 10), 0, math.pi, 2)  # ổ khoá
            pygame.draw.rect(screen, (40, 32, 26), (x - 6, y - 3, 12, 9))
            pygame.draw.rect(screen, (220, 200, 150), (x - 1, y, 2, 3))

    def _draw_pins(self, screen):
        show_all = self.map.zoom >= LABEL_ZOOM
        f = fonts.font("semi", 14)
        for r in self.relics:
            p = self.places[r["place"]]
            x, y = self.map.to_screen(p["lat"], p["lon"])
            st = self._state(r)
            self._pin(screen, st, x, y, self.t)
            if show_all or r is self.hover or r is self.selected:
                name = fonts.nfc(p["name"])
                w, h = f.size(name)
                label = pygame.Rect(0, 0, w + 12, h + 4)
                side = p.get("label", "right")
                if side == "left":
                    label.midright = (x - PIN_R - 4, y)
                elif side == "top":
                    label.midbottom = (x, y - PIN_R - 4)
                elif side == "bottom":
                    label.midtop = (x, y + PIN_R + 4)
                else:
                    label.midleft = (x + PIN_R + 4, y)
                ui.alpha_rect(screen, label, (28, 18, 15, 215), 3)
                fonts.text(screen, name, f, theme.PAPER, (label.x + 6, label.y + 2))

    def _draw_info(self, screen):
        relic = self.selected
        p = self.places[relic["place"]]
        ui.lacquer_panel(screen, INFO, 244)
        x, w = INFO.x + 20, INFO.w - 40
        y = fonts.paragraph(screen, relic["title"], fonts.font("serif", 21), theme.GOLD_LIGHT, x, INFO.y + 14, w, gap=1)
        fonts.text(screen, "Ngày nay: " + p.get("modern_name", ""), fonts.font("ui", 13), theme.PAPER_3, (x, y))
        fonts.paragraph(screen, relic.get("summary", ""), fonts.font("ui", 14), theme.PAPER, x, y + 22, w, gap=1)
