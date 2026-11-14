"""Màn hình tựa đề.

Nền là chính thế giới trong game, camera trôi chậm qua làng và sông, phủ màu sơn mài. Giữa là mặt trống đồng có đàn chim bay
quanh, tên game đặt trên đó. Bên trái là menu có biểu tượng, sáng lên và trượt nhẹ khi rê chuột hay chọn bằng phím. Bên phải
là thẻ nhân vật mặc đúng bộ đồ đang có. Dải dưới cùng lần lượt kể một mốc sử lấy từ dữ liệu có nguồn của game.
"""

from __future__ import annotations

import math

import pygame
from core import art, emblem, fonts, outfit, theme, ui, weapons
from core.scene import Scene
from core.sprites import TILE

from scenes.ending import EndingScene
from scenes.notebook import NotebookScene
from scenes.profile import ProfileScene
from scenes.review import ReviewScene
from scenes.story import StoryScene
from scenes.trailer import TrailerScene
from scenes.world import WorldScene, get_world

W, H = theme.WIDTH, theme.HEIGHT
PANEL = pygame.Rect(48, 138, 400, 470)  # vẫn giữ tên PANEL cho các phần khác đọc
DRUM = (790, 268)
DRUM_R = 196
CARD = pygame.Rect(1014, 404, 222, 248)
TICKER = pygame.Rect(48, 660, 1188, 46)
FACT_TIME = 7.0
ICONS = {
    "Bắt đầu hành trình": "ui/sword.png", "Tiếp tục hành trình": "ui/sword.png", "Sổ tay sử quan": "ui/book.png",
    "Hành trang và thành tựu": "ui/stamp.png", "Ôn tập": "ui/scroll.png", "Xem hướng dẫn": "ui/emote_question.png", "Cài đặt": "ui/gem.png",
    "Xem lại đoạn kết": "ui/cup.png",
}


class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.t = 0.0
        self.world = get_world(self.state, "man1")
        self.group = ui.ButtonGroup()
        self.awaiting: str | None = None  # việc làm tiếp khi scene đang mở đóng lại
        self.slide: dict[int, float] = {}
        self.facts = self._facts()
        self._shade = None
        self._build()

    def _facts(self) -> list[str]:
        """Các mốc sử trong dòng thời gian của game, xếp theo năm."""
        out = []
        for lid in self.state.order:
            for e in self.state.levels[lid].get("events", []):
                out.append((e["date"]["start"], f"{e['date']['label']}: {e['title']}."))
        return [text for _d, text in sorted(out)] or ["Mỗi câu chuyện trong game đều có nguồn."]

    def on_enter(self):
        self.app.audio.music("title")

    def _build(self):
        self.group.clear()
        x, w = PANEL.x + 24, PANEL.w - 48
        y = PANEL.y + 24
        started = bool(self.state.progress.completed_objectives)
        items = [
            ("Tiếp tục hành trình" if started else "Bắt đầu hành trình", self._start, "gold"),
            ("Sổ tay sử quan", lambda: self.app.scenes.push(NotebookScene(self.app)), "primary"),
            ("Hành trang và thành tựu", lambda: self.app.scenes.push(ProfileScene(self.app)), "primary"),
            ("Ôn tập", lambda: self.app.scenes.push(ReviewScene(self.app)), "primary"),
            ("Xem hướng dẫn", lambda: self.app.scenes.push(TrailerScene(self.app)), "primary"),
            ("Cài đặt", lambda: self.app.scenes.push(ProfileScene(self.app, 3)), "ghost"),
        ]
        if self.state.finished:  # đi hết ba màn thì xem lại được đoạn kết
            items.insert(5, ("Xem lại đoạn kết", lambda: self.app.scenes.push(EndingScene(self.app)), "primary"))
        small = 50 if len(items) > 6 else 58  # bảy nút vẫn nằm gọn trong khung
        for label, fn, style in items:
            h = 74 if style == "gold" else small
            self.group.add(ui.Button((x, y, w, h), label, fn, style, size=20 if style == "gold" else 16))
            y += h + 10

    def on_resume(self, result=None):
        self.app.audio.music("title")
        step, self.awaiting = self.awaiting, None
        if step == "trailer":
            self._after_intro()
        elif step == "world":
            self._enter_world()
        else:
            self._build()

    def _start(self):
        self.app.audio.play("trong")
        if not self.state.intro_done:
            self.state.intro_done = True
            self.state.save()
            self.awaiting = "trailer"
            self.app.scenes.push(StoryScene(self.app, self.state.sources["intro"]))
        else:
            self._after_intro()

    def _after_intro(self):
        """Người mới được xem trailer một lần; bản lưu cũ đã có tiến độ thì không làm phiền."""
        st = self.state
        if st.tutorial_seen or st.stamps:
            self._enter_world()
            return
        st.tutorial_seen = True
        st.save()
        self.awaiting = "world"
        self.app.scenes.push(TrailerScene(self.app))

    def _enter_world(self):
        st = self.state
        level = st.current_level if st.current_level in st.levels else st.order[0]
        self.app.scenes.push(WorldScene(self.app, level))

    def handle(self, event):
        self.group.handle(event)

    def update(self, dt):
        self.t += dt
        ui.ease_slide(self.group.buttons, self.slide, dt)

    # ----- vẽ -----
    def _backdrop(self, screen):
        world = self.world
        cx = (world.spawn[0] + 12) * TILE + math.sin(self.t * 0.12) * 260
        cy = 16 * TILE + math.cos(self.t * 0.09) * 150
        cam_x, cam_y = int(max(0, cx - W / 2)), int(max(0, cy - H / 2))
        world.map.draw(screen, cam_x, cam_y)
        for p in sorted(world.visible_props(cam_x, cam_y, W, H), key=lambda p: p.sort):
            screen.blit(p.img, (p.x - cam_x, p.y - cam_y))
        if self._shade is None:  # phủ màu sơn mài cho nền lùi lại phía sau
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((34, 18, 12, 120))
            self._shade = shade
        screen.blit(self._shade, (0, 0))
        screen.blit(art.vignette(), (0, 0))

    def _draw_menu(self, screen):
        ui.lacquer_panel(screen, PANEL, 226)
        ui.fancy_menu(screen, self.group.buttons, self.slide, ICONS)
        start = self.group.buttons[0].rect.move(self.slide.get(0, 0.0), 0)
        fonts.text(screen, "Enter", fonts.font("semi", 12), theme.INK_SOFT, (start.right - 16, start.centery), "midright")

    def _draw_title(self, screen):
        glow = 0.5 + 0.5 * math.sin(self.t * 1.6)
        ui.alpha_rect(screen, pygame.Rect(0, 0, DRUM_R * 2 + 60, DRUM_R * 2 + 60).move(DRUM[0] - DRUM_R - 30, DRUM[1] - DRUM_R - 30),
                      (240, 190, 90, int(26 + 24 * glow)), DRUM_R + 30)
        emblem.draw(screen, DRUM, DRUM_R, self.t)
        big = fonts.font("black", 64)
        for line, dy in (("SỬ KÝ", -44), ("ĐIỀU TRA", 30)):
            fonts.text(screen, line, big, (40, 20, 12), (DRUM[0] + 3, DRUM[1] + dy + 4), "center")
            fonts.text(screen, line, big, theme.GOLD_LIGHT, (DRUM[0], DRUM[1] + dy), "center", shadow=(90, 40, 20))
        fonts.text(screen, "Game nhập vai học lịch sử Việt Nam", fonts.font("italic", 20), theme.PAPER, (DRUM[0], DRUM[1] + DRUM_R + 30), "center",
                   shadow=(24, 16, 14))

    def _draw_card(self, screen):
        st = self.state
        ui.lacquer_panel(screen, CARD, 232)
        fonts.text(screen, "Nhân vật của bạn", fonts.font("bold", 15), theme.GOLD_LIGHT, (CARD.centerx, CARD.y + 14), "midtop")
        foot = (CARD.centerx, CARD.y + 136 + int(3 * math.sin(self.t * 2.4)))
        pygame.draw.ellipse(screen, (20, 12, 8), (foot[0] - 34, foot[1] - 8, 68, 14))
        hero = outfit.hero_cast(st.gear, 6).walk["down"][int(self.t * 3) % 4]
        screen.blit(hero, hero.get_rect(midbottom=foot))
        weapons.blit(screen, st.gear.get("vu_khi"), 6, weapons.hand_at("down", foot, 6), weapons.held("down")[0])
        fonts.text(screen, f"Cấp {st.level} · {st.realm_name()}", fonts.font("bold", 15), theme.PAPER, (CARD.centerx, CARD.y + 172), "midtop")
        fonts.text(screen, f"Sức mạnh {st.power_rating()}", fonts.font("semi", 13), theme.RED_BRIGHT, (CARD.centerx, CARD.y + 194), "midtop")
        total = sum(len(st.levels[lid]["relics"]) for lid in st.order)
        fonts.text(screen, f"Di tích {len(st.stamps)}/{total} · {st.total_points} điểm", fonts.font("ui", 13), theme.PAPER_3,
                   (CARD.centerx, CARD.y + 216), "midtop")

    def _draw_ticker(self, screen):
        ui.lacquer_panel(screen, TICKER, 222)
        i = int(self.t / FACT_TIME) % len(self.facts)
        phase = (self.t % FACT_TIME) / FACT_TIME
        alpha = min(1.0, phase * 6, (1 - phase) * 6)
        ui.tag(screen, "Biết không?", (TICKER.x + 14, TICKER.centery), theme.LACQUER_RED, theme.GOLD_LIGHT, 14, "midleft")
        img = fonts.render(self.facts[i], fonts.font("semi", 16), theme.PAPER).copy()  # ảnh chữ dùng chung, chép ra rồi mới làm mờ
        img.set_alpha(int(255 * alpha))
        screen.blit(img, img.get_rect(midleft=(TICKER.x + 132, TICKER.centery + int((1 - alpha) * 8))))

    def draw(self, screen):
        self._backdrop(screen)
        self._draw_title(screen)
        self._draw_menu(screen)
        self._draw_card(screen)
        self._draw_ticker(screen)
        fonts.text(screen, "Bóng giặc, cảnh giới, tiền quan là phần trò chơi; mọi câu chuyện sử đều có nguồn.", fonts.font("ui", 13),
                   theme.PAPER_3, (PANEL.x, PANEL.y - 30))
