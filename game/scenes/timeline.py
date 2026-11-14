"""Dựng dòng thời gian bằng kéo thả; sai thì thẻ quay về khay kèm gợi ý nhân quả (Req 15)."""

from __future__ import annotations

import random

import pygame
from core import fonts, theme, ui
from core.scene import Scene

from scenes.review import ReviewScene
from shared.histdate import HistDate
from shared.quest_engine import LevelDone
from shared.timeline_rules import hint_for, is_valid_placement

AXIS_Y = 262
CARD_W, CARD_H = 148, 112
TRAY_Y = 452


class TimelineScene(Scene):
    def __init__(self, app, level_id: str):
        super().__init__(app)
        self.level_id = level_id
        self.bundle = self.state.levels[level_id]
        self.events = [e for e in self.bundle["events"] if e.get("in_timeline")]
        self.dates = {e["id"]: HistDate.from_bundle(e["date"]) for e in self.events}
        self.titles = {e["id"]: e["title"] for e in self.bundle["events"]}
        self.links = self.bundle.get("causal_links", [])
        self.tray = [e["id"] for e in self.events]
        random.shuffle(self.tray)
        self.placed: list[str] = []
        self.mistakes = 0
        self.drag: str | None = None
        self.mouse = (0, 0)
        self.hint = "Kéo từng thẻ sự kiện lên trục thời gian, đặt vào đúng vị trí."
        self.hint_col = theme.PAPER
        self.done = False
        self.result: dict | None = None
        self.t = 0.0
        self.group = ui.ButtonGroup([ui.Button((theme.WIDTH - 150, 14, 136, 40), "Quay lại", self._back, "ghost", size=15)])

    def _back(self):
        if self.result and any(isinstance(e, LevelDone) for e in self.result["effects"]):
            self.app.scenes.replace(LevelSummaryScene(self.app, self.level_id, self.mistakes, self.result["bonus"]))
        else:
            self.app.scenes.pop()

    # ----- bố cục -----
    def _axis_slots(self, count=None):
        """Vị trí x của từng thẻ đã đặt, co giãn để luôn nằm gọn trên trục."""
        n = len(self.placed) if count is None else count
        margin = 40
        avail = theme.WIDTH - 2 * margin
        w = min(CARD_W, (avail - (n - 1) * 8) / max(1, n))
        total = n * w + (n - 1) * 8
        x0 = (theme.WIDTH - total) / 2
        return [x0 + i * (w + 8) for i in range(n)], w

    def _tray_rects(self):
        rects = {}
        per_row = 8
        for i, eid in enumerate(self.tray):
            col, row = i % per_row, i // per_row
            x = 40 + col * ((theme.WIDTH - 80 - CARD_W) / (per_row - 1))
            rects[eid] = pygame.Rect(x, TRAY_Y + row * (CARD_H + 10), CARD_W, CARD_H)
        return rects

    def _gap_index(self, x) -> int:
        slots, w = self._axis_slots()
        for i, sx in enumerate(slots):
            if x < sx + w / 2:
                return i
        return len(slots)

    # ----- sự kiện -----
    def handle(self, event):
        if self.group.handle(event):
            return
        if self.done:
            return
        if event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.mouse = event.pos
            for eid, r in self._tray_rects().items():
                if r.collidepoint(event.pos):
                    self.drag = eid
                    self.app.audio.play("click")
                    break
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag:
            eid, self.drag = self.drag, None
            if event.pos[1] < TRAY_Y - 10:
                self._drop(eid, self._gap_index(event.pos[0]))

    def _drop(self, eid, index):
        placed_dates = [self.dates[e] for e in self.placed]
        if is_valid_placement(placed_dates, self.dates[eid], index):
            self.placed.insert(index, eid)
            self.tray.remove(eid)
            self.app.audio.play("dung")
            label = self.bundle_event(eid)["date"].get("label", "")
            self.hint = f"Đúng rồi: {self.titles[eid]} — {label}"
            self.hint_col = theme.JADE_LIGHT
            if not self.tray:
                self._complete()
        else:
            self.mistakes += 1
            self.app.audio.play("sai")
            neighbors = self.placed[max(0, index - 1):index + 1]
            self.hint = "Chưa đúng vị trí. " + hint_for(eid, neighbors, self.links, self.titles)
            self.hint_col = (240, 170, 130)

    def bundle_event(self, eid):
        return next(e for e in self.bundle["events"] if e["id"] == eid)

    def _complete(self):
        self.done = True
        self.result = self.state.timeline_finished(self.level_id, self.mistakes)
        self.app.audio.play("thang")
        for msg in self.state.effect_messages(self.result["effects"], self.bundle):
            self.app.toast(msg, theme.GOLD_LIGHT, 4.0)
        for msg in self.state.check_badges():
            self.app.toast(msg, theme.GOLD_LIGHT, 4.0)
        self.state.save()
        self.group.clear()
        self.group.add(ui.Button((theme.WIDTH // 2 - 130, theme.HEIGHT - 76, 260, 54), "Hoàn tất", self._back, "gold"))
        complete_text = f"Dòng thời gian đã phục dựng! Sai {self.mistakes} lần"
        if self.result["bonus"]:
            complete_text += f" · thưởng +{self.result['bonus']} điểm"
        self.hint = complete_text
        self.hint_col = theme.GOLD_LIGHT

    def update(self, dt):
        self.t += dt

    # ----- vẽ -----
    def draw(self, screen):
        screen.fill(theme.LACQUER)
        fonts.text(screen, "DỰNG LẠI DÒNG THỜI GIAN", fonts.font("serif", 28), theme.GOLD_LIGHT, (40, 20))
        fonts.text(screen, f"{self.bundle['level']['title']} · {self.bundle['level']['period_label']}", fonts.font("ui", 15), theme.PAPER_3, (40, 62))
        ui.lacquer_panel(screen, (40, 92, theme.WIDTH - 80, 62))
        fonts.paragraph(screen, self.hint, fonts.font("semi", 16), self.hint_col, 60, 104, theme.WIDTH - 120, gap=1)
        # trục thời gian
        pygame.draw.line(screen, theme.GOLD, (30, AXIS_Y + 96), (theme.WIDTH - 30, AXIS_Y + 96), 4)
        pygame.draw.polygon(screen, theme.GOLD, [(theme.WIDTH - 30, AXIS_Y + 86), (theme.WIDTH - 10, AXIS_Y + 96), (theme.WIDTH - 30, AXIS_Y + 106)])
        fonts.text(screen, "Xưa", fonts.font("italic", 15), theme.PAPER_3, (32, AXIS_Y + 126))
        fonts.text(screen, "Nay", fonts.font("italic", 15), theme.PAPER_3, (theme.WIDTH - 62, AXIS_Y + 126))
        slots, w = self._axis_slots()
        for sx, eid in zip(slots, self.placed, strict=False):
            self._card(screen, pygame.Rect(sx, AXIS_Y - 40, w, CARD_H), eid, placed=True)
            pygame.draw.circle(screen, theme.GOLD_LIGHT, (sx + w / 2, AXIS_Y + 96), 7)
            label = self.bundle_event(eid)["date"].get("label", "")
            fonts.text(screen, label, fonts.font("bold", 12 if w < 110 else 14), theme.GOLD_LIGHT, (sx + w / 2, AXIS_Y + 108), "midtop")
        if self.done:
            self._draw_links(screen, slots, w)
            self._draw_lessons(screen)
        if self.drag and self.mouse[1] < TRAY_Y - 10:
            idx = self._gap_index(self.mouse[0])
            gx = (slots[idx] - 4) if idx < len(slots) else (slots[-1] + w + 4 if slots else theme.WIDTH / 2)
            pygame.draw.line(screen, theme.RED_BRIGHT, (gx, AXIS_Y - 48), (gx, AXIS_Y + 106), 4)
        if not self.done:
            fonts.text(screen, f"Khay sự kiện · còn {len(self.tray)} thẻ · sai {self.mistakes} lần (sai tối đa 2 lần để nhận thưởng 50 điểm)", fonts.font("ui", 15), theme.PAPER_3, (40, TRAY_Y - 30))
            for eid, r in self._tray_rects().items():
                if eid != self.drag:
                    self._card(screen, r, eid)
        if self.drag:
            r = pygame.Rect(0, 0, CARD_W, CARD_H)
            r.center = self.mouse
            self._card(screen, r, self.drag, lifted=True)
        self.group.draw(screen)

    def _card(self, screen, rect, eid, placed=False, lifted=False):
        rect = pygame.Rect(rect)
        if lifted:
            ui.alpha_rect(screen, rect.move(4, 8), (0, 0, 0, 120), 6)
        bg = theme.PAPER if not placed else (232, 218, 180)
        pygame.draw.rect(screen, bg, rect, border_radius=6)
        pygame.draw.rect(screen, theme.GOLD_DARK, rect, 2, border_radius=6)
        size = 13 if rect.w >= 120 else 11
        f = fonts.font("semi", size)
        lines = fonts.wrap(self.titles[eid], f, rect.w - 14)
        lh = f.get_linesize()
        max_lines = max(1, (rect.h - 10) // lh)
        lines = lines[:max_lines]
        y = rect.centery - len(lines) * lh / 2
        for line in lines:
            fonts.text(screen, line, f, theme.INK, (rect.centerx, y), "midtop")
            y += lh

    def _draw_lessons(self, screen):
        """Sau khi ghép xong, liệt kê các quan hệ nhân quả để người chơi đọc lại."""
        y = AXIS_Y + 158
        fonts.text(screen, "Vì sao các mốc này nối với nhau?", fonts.font("bold", 17), theme.GOLD_LIGHT, (60, y))
        y += 28
        for link in self.links[:6]:
            line = f"{self.titles[link['from_event_id']]} dẫn tới {self.titles[link['to_event_id']]}: {link.get('note', '')}"
            y = fonts.paragraph(screen, line, fonts.font("ui", 14), theme.PAPER, 60, y, theme.WIDTH - 120, gap=1) + 4

    def _draw_links(self, screen, slots, w):
        """Mũi tên nhân quả giữa các thẻ khi hoàn tất (Req 15.5)."""
        pos = {eid: sx + w / 2 for sx, eid in zip(slots, self.placed, strict=False)}
        y = AXIS_Y - 40
        level = 0
        for link in self.links:
            a, b = pos.get(link["from_event_id"]), pos.get(link["to_event_id"])
            if a is None or b is None:
                continue
            top = y - 16 - (level % 3) * 14
            level += 1
            pygame.draw.lines(screen, theme.RED_BRIGHT, False, [(a, y), (a, top), (b, top), (b, y - 6)], 2)
            pygame.draw.polygon(screen, theme.RED_BRIGHT, [(b - 6, y - 8), (b + 6, y - 8), (b, y)])


class LevelSummaryScene(Scene):
    """Tổng kết sau màn: số liệu học tập, câu cần ôn, màn kế tiếp (đề bài: chế độ ôn tập sau màn)."""

    def __init__(self, app, level_id: str, mistakes: int, bonus: int):
        super().__init__(app)
        self.level_id = level_id
        st = self.state
        bundle = st.levels[level_id]
        self.level = bundle["level"]
        questions = bundle["questions"]
        self.total_q = len(questions)
        self.first = sum(q["id"] in st.first_try for q in questions)
        self.weak = st.weak_questions(level_id)
        self.relics = [r for r in bundle["relics"] if r["id"] in st.stamps]
        self.total_relics = len(bundle["relics"])
        self.stars = sum(st.battle_stars.get(b["id"], 0) for b in bundle["battles"])
        self.max_stars = 3 * len(bundle["battles"])
        self.mistakes = mistakes
        self.bonus = bonus
        idx = st.order.index(level_id)
        self.next = st.levels[st.order[idx + 1]]["level"] if idx + 1 < len(st.order) else None
        self.group = ui.ButtonGroup()
        cx = theme.WIDTH // 2
        label = f"Ôn tập ngay ({len(self.weak)} câu cần xem lại)" if self.weak else "Ôn tập lại màn này"
        self.group.add(ui.Button((cx - 400, 618, 390, 56), label, self._review, "primary", size=17))
        self.group.add(ui.Button((cx + 10, 618, 390, 56), "Về bản đồ", lambda: self.app.scenes.pop(), "gold"))
        self.app.audio.play("thang")

    def _review(self):
        self.app.scenes.push(ReviewScene(self.app, self.level_id))

    def handle(self, event):
        self.group.handle(event)

    def draw(self, screen):
        screen.fill(theme.LACQUER)
        rect = pygame.Rect(170, 30, 940, 660)
        ui.paper_panel(screen, rect)
        x, w = rect.x + 50, rect.w - 100
        ui.tag(screen, "HOÀN THÀNH MÀN", (rect.centerx, rect.y + 24), anchor="midtop")
        fonts.text(screen, self.level["title"], fonts.font("serif", 32), theme.INK, (rect.centerx, rect.y + 56), "midtop")
        f = fonts.font("semi", 18)
        y = rect.y + 120
        rows = [
            f"Di tích đã đóng dấu: {len(self.relics)}/{self.total_relics}",
            f"Câu đúng ngay lần đầu: {self.first}/{self.total_q}",
            f"Sao chỉ huy trận đánh: {self.stars}/{self.max_stars}",
            f"Dòng thời gian: sai {self.mistakes} lần" + (f", thưởng +{self.bonus} điểm" if self.bonus else ""),
            f"Tổng điểm kiến thức: {self.state.total_points}",
        ]
        for row in rows:
            fonts.text(screen, "• " + row, f, theme.INK, (x, y))
            y += 32
        if self.level.get("badge"):
            fonts.text(screen, f"Danh hiệu nhận được: {self.level['badge']}", fonts.font("bold", 19), theme.LACQUER_RED, (x, y + 4))
            y += 40
        if self.weak:
            y = fonts.paragraph(screen, "Nên ôn lại:", fonts.font("bold", 17), theme.INK, x, y, w)
            for q in self.weak[:4]:
                line = fonts.wrap(q["prompt"], fonts.font("ui", 15), w - 20)[0]
                fonts.text(screen, "– " + line, fonts.font("ui", 15), theme.INK_SOFT, (x, y))
                y += 24
        if self.next:
            msg = f"Đã mở khoá màn tiếp theo: {self.next['title']} ({self.next['period_label']})."
        else:
            msg = "Bạn đã phục dựng xong cuốn Sử Ký. Cụ Đồ Sử cảm ơn cháu! Có thể chơi lại để lấy đủ sao."
        fonts.paragraph(screen, msg, fonts.font("serif", 18), theme.INK_SOFT, x, 560, w, gap=3)
        self.group.draw(screen)
