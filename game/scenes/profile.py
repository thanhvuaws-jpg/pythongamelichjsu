"""Hộ chiếu di sản, bảo vật, danh hiệu, thống kê và cài đặt."""

from __future__ import annotations

import pygame
from core import art, fonts, theme, ui
from core.scene import Scene
from core.state import GLOBAL_BADGES

TABS = ["Hộ chiếu di sản", "Bảo vật", "Danh hiệu", "Cài đặt"]
BODY = pygame.Rect(40, 130, 1200, 570)


class ProfileScene(Scene):
    def __init__(self, app, tab: int = 0):
        super().__init__(app)
        self.tab = tab
        self.group = ui.ButtonGroup()
        self.settings_group = ui.ButtonGroup()
        self.confirm_reset = False
        self._build()

    def _build(self):
        self.group.clear()
        self.group.add(ui.Button((theme.WIDTH - 150, 14, 136, 40), "Đóng", lambda: self.app.scenes.pop(), "ghost", size=15))
        for i, label in enumerate(TABS):
            b = ui.Button((40 + i * 208, 72, 200, 44), label, None, "gold" if i == self.tab else "ghost", size=16)
            b.on_click = lambda n=i: self._switch(n)
            self.group.add(b)
        self._build_settings()

    def _switch(self, n):
        self.tab = n
        self.confirm_reset = False
        self._build()

    def _build_settings(self):
        self.settings_group.clear()
        if self.tab != 3:
            return
        st = self.state.settings
        x, y = BODY.x + 40, BODY.y + 70
        for value, label in (("day_du", "Đầy đủ (có vệt máu)"), ("nhe", "Giảm nhẹ")):
            b = ui.Button((x, y, 250, 46), label, None, "gold" if st["violence"] == value else "ghost", size=16)
            b.on_click = lambda v=value: self._set("violence", v)
            self.settings_group.add(b)
            x += 262
        x, y = BODY.x + 40, BODY.y + 180
        for value, label in ((True, "Bật"), (False, "Tắt")):
            b = ui.Button((x, y, 120, 46), label, None, "gold" if st["sound"] == value else "ghost", size=16)
            b.on_click = lambda v=value: self._set("sound", v)
            self.settings_group.add(b)
            x += 132
        x, y = BODY.x + 40, BODY.y + 290
        for value, label in ((0.7, "Chậm"), (1.0, "Vừa"), (1.6, "Nhanh")):
            b = ui.Button((x, y, 120, 46), label, None, "gold" if st["text_speed"] == value else "ghost", size=16)
            b.on_click = lambda v=value: self._set("text_speed", v)
            self.settings_group.add(b)
            x += 132
        label = "Bấm lần nữa để xoá hẳn" if self.confirm_reset else "Xoá toàn bộ tiến trình"
        self.settings_group.add(ui.Button((BODY.x + 40, BODY.y + 400, 300, 46), label, self._reset, "primary", size=16))

    def _set(self, key, value):
        self.state.settings[key] = value
        self.app.audio.set_enabled(self.state.settings["sound"])
        self.state.save()
        self._build_settings()

    def _reset(self):
        if not self.confirm_reset:
            self.confirm_reset = True
            self._build_settings()
            return
        self.state.reset()
        self.state.save()
        self.app.go_title()

    def handle(self, event):
        if self.group.handle(event) or self.settings_group.handle(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.pop()

    def draw(self, screen):
        screen.fill(theme.LACQUER)
        fonts.text(screen, "HÀNH TRANG SỬ QUAN", fonts.font("serif", 28), theme.GOLD_LIGHT, (40, 18))
        st = self.state
        fonts.text(
            screen,
            f"{st.total_points} điểm · {len(st.stamps)} con dấu · {len(st.owned_artifacts)} bảo vật · {len(st.badges)} danh hiệu",
            fonts.font("ui", 15), theme.PAPER_3, (480, 32),
        )
        self.group.draw(screen)
        ui.paper_panel(screen, BODY, shadow=False)
        {0: self._passport, 1: self._artifacts, 2: self._badges, 3: self._settings}[self.tab](screen)

    def _passport(self, screen):
        relics = [r for lid in self.state.order for r in self.state.levels[lid]["relics"]]
        cols = 8
        cell_w = (BODY.w - 40) / cols
        size = 112
        for i, r in enumerate(relics):
            x = BODY.x + 20 + (i % cols) * cell_w
            y = BODY.y + 18 + (i // cols) * 180
            active = r["id"] in self.state.stamps
            screen.blit(art.stamp(r.get("stamp", r["title"]), size, active=active), (x + (cell_w - size) / 2, y))
            place = self.state.index["places"][r["place"]]
            name = place["name"] if active else "?"
            lines = fonts.wrap(name, fonts.font("semi", 13), int(cell_w - 8))[:2]
            yy = y + size + 4
            for line in lines:
                fonts.text(screen, line, fonts.font("semi", 13), theme.INK if active else theme.INK_FAINT, (x + cell_w / 2, yy), "midtop")
                yy += 18

    def _artifacts(self, screen):
        items = list(self.state.index["artifacts"].values())
        cols = 3
        cw = (BODY.w - 40) / cols
        ch = 86
        for i, a in enumerate(items):
            x = BODY.x + 20 + (i % cols) * cw
            y = BODY.y + 12 + (i // cols) * (ch + 7)
            owned = a["id"] in self.state.owned_artifacts
            rect = pygame.Rect(x + 4, y, cw - 8, ch)
            pygame.draw.rect(screen, theme.PAPER_2 if owned else theme.PAPER_3, rect, border_radius=6)
            pygame.draw.rect(screen, theme.GOLD_DARK, rect, 2, border_radius=6)
            if owned:
                screen.blit(art.artifact(a["icon"], 70), (rect.x + 8, rect.y + 8))
                tx = rect.x + 86
                y2 = fonts.paragraph(screen, a["name"], fonts.font("bold", 15), theme.INK, tx, rect.y + 7, rect.w - 94, gap=0)
                fonts.paragraph(screen, a["desc"], fonts.font("ui", 12), theme.INK_SOFT, tx, y2 + 1, rect.w - 94, gap=0)
            else:
                fonts.text(screen, "?", fonts.font("black", 34), theme.INK_FAINT, rect.center, "center")

    def _badges(self, screen):
        keys = self.state.all_badge_keys()
        cols = 2
        cw = (BODY.w - 40) / cols
        for i, key in enumerate(keys):
            info = self.state.badge_info(key) if key.startswith("man:") else GLOBAL_BADGES[key]
            x = BODY.x + 20 + (i % cols) * cw
            y = BODY.y + 18 + (i // cols) * 118
            got = key in self.state.badges
            rect = pygame.Rect(x + 6, y, cw - 12, 104)
            pygame.draw.rect(screen, theme.PAPER_2 if got else theme.PAPER_3, rect, border_radius=6)
            pygame.draw.rect(screen, theme.GOLD_DARK, rect, 2, border_radius=6)
            icon = art.drum(84, theme.LACQUER_RED if got else (150, 138, 118))
            screen.blit(icon, (rect.x + 10, rect.y + 10))
            fonts.text(screen, info["name"], fonts.font("bold", 19), theme.INK if got else theme.INK_FAINT, (rect.x + 106, rect.y + 16))
            fonts.paragraph(screen, info["desc"], fonts.font("ui", 15), theme.INK_SOFT if got else theme.INK_FAINT, rect.x + 106, rect.y + 48, rect.w - 118, gap=2)

    def _settings(self, screen):
        x = BODY.x + 40
        f = fonts.font("bold", 19)
        note = fonts.font("ui", 14)
        fonts.text(screen, "Hiệu ứng chiến trận", f, theme.INK, (x, BODY.y + 22))
        fonts.text(screen, "“Giảm nhẹ” thay máu bằng bụi đất và bỏ cảnh giao đấu trong hồi ức, phù hợp khi trình chiếu ở lớp.", note, theme.INK_SOFT, (x, BODY.y + 124))
        fonts.text(screen, "Âm thanh", f, theme.INK, (x, BODY.y + 150))
        fonts.text(screen, "Tốc độ chữ chạy", f, theme.INK, (x, BODY.y + 260))
        fonts.text(screen, "Xoá dữ liệu trên máy này", f, theme.INK, (x, BODY.y + 370))
        fonts.text(screen, "Đồ hoạ và nhạc: Ninja Adventure Asset Pack của Pixel-Boy và AAA (giấy phép CC0).", note, theme.INK_SOFT, (x, BODY.y + 480))
        self.settings_group.draw(screen)
