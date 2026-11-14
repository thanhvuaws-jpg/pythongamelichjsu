"""Cửa kiểm tra: chọn 1, chọn nhiều, sắp xếp, nối cặp, chỉ trên bản đồ (Req 16).

Các kiểu "Đúng/Sai", "Sử hay truyền thuyết?", "Đối chiếu nguồn" là biến thể của `single`, phân biệt
bằng trường `style`. Sai 3 lần thì hiện đáp án, không có điểm và đưa vào danh sách ôn tập.
"""

from __future__ import annotations

import random

import pygame
from core import art, fonts, theme, ui
from core.scene import Scene
from core.vnmap import MapView

PANEL = pygame.Rect(70, 26, 1140, 668)
MAX_TRIES = 3
DIFF_LABEL = {1: "Dễ · 10 điểm", 2: "Vừa · 20 điểm", 3: "Khó · 30 điểm"}
KIND_LABEL = {
    "single": "Chọn một đáp án", "multi": "Chọn tất cả đáp án đúng", "order": "Sắp xếp theo đúng thứ tự",
    "match": "Nối mỗi mục bên trái với mục bên phải", "map_pick": "Bấm vào đúng vị trí trên bản đồ",
}
PAIR_COLORS = [(46, 125, 96), (176, 74, 40), (48, 99, 138), (130, 78, 150), (150, 118, 36), (60, 120, 130)]


class QuestionScene(Scene):
    opaque = False

    def __init__(self, app, question: dict, review: bool = False, label: str = ""):
        super().__init__(app)
        self.q = question
        self.review = review
        self.label = label or "Ôn tập"
        self.kind = question["kind"]
        self.t = 0.0
        self.result: dict | None = None  # {"correct", "points", "final"}
        self.tries = 0
        self.group = ui.ButtonGroup()
        self.opt_rects: list[tuple[pygame.Rect, dict]] = []
        self.selected: set[str] = set()
        self.order: list[dict] = []
        self.pairs: dict[str, str] = {}
        self.pick_left: str | None = None
        self.drag: int | None = None
        self.drag_y = 0
        self.marker: tuple[float, float] | None = None
        self.map: MapView | None = None
        self.hover: str | None = None
        self.prompt_font = fonts.font("semi", 23)
        self.opt_font = fonts.font("ui", 19)
        self.prompt_h = fonts.height_of(question["prompt"], self.prompt_font, PANEL.width - 80, 6)
        self.top = PANEL.y + 58 + self.prompt_h
        self._setup()
        self._bottom_buttons()

    # ----- dựng câu hỏi -----
    def _setup(self):
        q = self.q
        x, w = PANEL.x + 40, PANEL.width - 80
        if self.kind in ("single", "multi"):
            opts = list(q["options"])
            if not q.get("keep_order"):
                random.shuffle(opts)
            y = self.top
            for o in opts:
                h = max(52, fonts.height_of(o["text"], self.opt_font, w - 90, 4) + 18)
                self.opt_rects.append((pygame.Rect(x, y, w, h), o))
                y += h + 10
        elif self.kind == "order":
            self.order = list(q["items"])
            while [i["id"] for i in self.order] == list(q["correct_answer"]):
                random.shuffle(self.order)
        elif self.kind == "match":
            self.left = list(q["left"])
            self.right = list(q["right"])
            random.shuffle(self.left)
            random.shuffle(self.right)
        elif self.kind == "map_pick":
            v = q.get("view", {})
            self.map = MapView((x, self.top, w, PANEL.bottom - self.top - 74),
                               (v.get("lat", 16.0), v.get("lon", 106.0)), v.get("zoom", 1.3))

    def _bottom_buttons(self):
        self.group.clear()
        y = PANEL.bottom - 62
        if self.result is None:
            needs_btn = self.kind != "single"
            if needs_btn:
                self.group.add(ui.Button((PANEL.right - 260, y, 220, 46), "Trả lời", self._submit, "primary", self._can_submit()))
        elif self.result.get("final"):
            self.group.add(ui.Button((PANEL.right - 260, y, 220, 46), "Tiếp tục", self._close, "gold"))
        else:
            self.group.add(ui.Button((PANEL.right - 260, y, 220, 46), "Thử lại", self._retry, "primary"))

    def _can_submit(self) -> bool:
        if self.kind == "multi":
            return bool(self.selected)
        if self.kind == "match":
            return len(self.pairs) == len(self.left)
        if self.kind == "map_pick":
            return self.marker is not None
        return True

    # ----- chấm -----
    def _answer(self):
        if self.kind == "single":
            return next(iter(self.selected), "")
        if self.kind == "multi":
            return sorted(self.selected)
        if self.kind == "order":
            return [i["id"] for i in self.order]
        if self.kind == "match":
            return dict(self.pairs)
        return {"lat": self.marker[0], "lon": self.marker[1]} if self.marker else {}

    def _submit(self):
        answer = self._answer()
        correct = self.state.check(self.q, answer)
        self.tries += 1
        points = 0
        if self.review:
            final = True
            points = self.state.review_answer(self.q, correct)["points"]
        else:
            info = self.state.record_answer(self.q, correct)
            points = info["points"]
            final = correct or self.tries >= MAX_TRIES
            if final and not correct:
                self.state.give_up(self.q)
        self.result = {"correct": correct, "points": points, "final": final}
        self.app.audio.play("dung" if correct else "sai")
        self._bottom_buttons()

    def _retry(self):
        self.result = None
        if self.kind in ("single", "multi"):
            self.selected.clear()
        elif self.kind == "match":
            self.pairs.clear()
            self.pick_left = None
        elif self.kind == "map_pick":
            self.marker = None
        self._bottom_buttons()

    def _close(self):
        self.app.scenes.pop(self.result["correct"] or not self.review)

    # ----- sự kiện -----
    def handle(self, event):
        if self.group.handle(event):
            return
        if self.result is not None:
            return
        if event.type == pygame.MOUSEMOTION:
            self.hover = None
            for rect, o in self.opt_rects:
                if rect.collidepoint(event.pos):
                    self.hover = o["id"]
        if self.kind in ("single", "multi"):
            self._handle_options(event)
        elif self.kind == "order":
            self._handle_order(event)
        elif self.kind == "match":
            self._handle_match(event)
        elif self.kind == "map_pick":
            self._handle_map(event)

    def _handle_options(self, event):
        if event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_9:
            idx = event.key - pygame.K_1
            if idx < len(self.opt_rects):
                self._choose(self.opt_rects[idx][1])
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for rect, o in self.opt_rects:
                if rect.collidepoint(event.pos):
                    self._choose(o)
                    return

    def _choose(self, o):
        self.app.audio.play("click")
        if self.kind == "single":
            self.selected = {o["id"]}
            self._submit()
        else:
            self.selected ^= {o["id"]}
            self._bottom_buttons()

    def _row_rects(self):
        x, w = PANEL.x + 40, PANEL.width - 80
        y = self.top
        h = min(64, (PANEL.bottom - 80 - self.top) // max(1, len(self.order)) - 8)
        return [pygame.Rect(x, y + i * (h + 8), w, h) for i in range(len(self.order))]

    def _handle_order(self, event):
        rects = self._row_rects()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(rects):
                if r.collidepoint(event.pos):
                    up, down = self._arrow_rects(r)
                    if up.collidepoint(event.pos) and i > 0:
                        self._swap(i, i - 1)
                    elif down.collidepoint(event.pos) and i < len(rects) - 1:
                        self._swap(i, i + 1)
                    else:
                        self.drag = i
                        self.drag_y = event.pos[1]
                    return
        elif event.type == pygame.MOUSEMOTION and self.drag is not None:
            self.drag_y = event.pos[1]
            for i, r in enumerate(rects):
                if r.collidepoint(r.centerx, event.pos[1]) and i != self.drag:
                    self._swap(self.drag, i)
                    self.drag = i
                    break
        elif event.type == pygame.MOUSEBUTTONUP:
            self.drag = None

    def _swap(self, a, b):
        self.order[a], self.order[b] = self.order[b], self.order[a]
        self.app.audio.play("click")

    @staticmethod
    def _arrow_rects(r):
        return pygame.Rect(r.right - 92, r.y + 6, 40, r.h - 12), pygame.Rect(r.right - 46, r.y + 6, 40, r.h - 12)

    def _match_rects(self):
        x = PANEL.x + 40
        h = min(66, (PANEL.bottom - 80 - self.top) // max(1, len(self.left)) - 8)
        lefts = {o["id"]: pygame.Rect(x, self.top + i * (h + 8), 470, h) for i, o in enumerate(self.left)}
        rights = {o["id"]: pygame.Rect(PANEL.right - 40 - 470, self.top + i * (h + 8), 470, h) for i, o in enumerate(self.right)}
        return lefts, rights

    def _handle_match(self, event):
        if event.type != pygame.MOUSEBUTTONUP or event.button != 1:
            return
        lefts, rights = self._match_rects()
        for oid, r in lefts.items():
            if r.collidepoint(event.pos):
                self.pairs.pop(oid, None)
                self.pick_left = oid
                self.app.audio.play("click")
                self._bottom_buttons()
                return
        for oid, r in rights.items():
            if r.collidepoint(event.pos) and self.pick_left:
                for k, v in list(self.pairs.items()):
                    if v == oid:
                        del self.pairs[k]
                self.pairs[self.pick_left] = oid
                self.pick_left = None
                self.app.audio.play("click")
                self._bottom_buttons()
                return

    def _handle_map(self, event):
        if self.map.handle(event):
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.map.rect.collidepoint(event.pos):
            self.marker = self.map.to_geo(*event.pos)
            self.app.audio.play("click")
            self._bottom_buttons()

    def update(self, dt):
        self.t += dt

    # ----- vẽ -----
    def backdrop(self, screen):
        ui.veil(screen, (14, 8, 6, 190))

    def draw(self, screen):
        ui.paper_panel(screen, PANEL)
        head = PANEL.x + 40
        style = self.q.get("style") or KIND_LABEL[self.kind]
        r = ui.tag(screen, style, (head, PANEL.y + 20))
        label = self.label if self.review else DIFF_LABEL.get(self.q.get("difficulty", 1), "")
        ui.tag(screen, label, (r.right + 8, PANEL.y + 20), theme.PAPER_3, theme.INK)
        fonts.paragraph(screen, self.q["prompt"], self.prompt_font, theme.INK, head, PANEL.y + 54, PANEL.width - 80)
        if self.kind in ("single", "multi"):
            self._draw_options(screen)
        elif self.kind == "order":
            self._draw_order(screen)
        elif self.kind == "match":
            self._draw_match(screen)
        else:
            self._draw_map(screen)
        if self.result:
            self._draw_result(screen)
        self.group.draw(screen)

    def _option_colors(self, oid):
        correct = self.q["correct_answer"]
        correct_ids = correct if isinstance(correct, list) else [correct]
        bg, border = theme.PAPER_2, theme.PAPER_3
        if oid in self.selected:
            bg, border = (232, 202, 142), theme.GOLD_DARK
        elif oid == self.hover and not self.result:
            bg = (236, 220, 180)
        if self.result:
            if self.result.get("final") and oid in correct_ids:
                bg, border = (178, 218, 186), theme.JADE
            elif oid in self.selected and not self.result["correct"]:
                bg, border = (232, 176, 160), theme.RED
        return bg, border

    def _draw_options(self, screen):
        for i, (rect, o) in enumerate(self.opt_rects):
            bg, border = self._option_colors(o["id"])
            pygame.draw.rect(screen, bg, rect, border_radius=6)
            pygame.draw.rect(screen, border, rect, 2, border_radius=6)
            c = (rect.x + 28, rect.centery)
            if self.kind == "multi":
                box = pygame.Rect(0, 0, 22, 22)
                box.center = c
                pygame.draw.rect(screen, theme.PAPER, box, border_radius=3)
                pygame.draw.rect(screen, theme.INK_SOFT, box, 2, border_radius=3)
                if o["id"] in self.selected:
                    pygame.draw.lines(screen, theme.INK, False, [(box.x + 4, box.centery), (box.centerx - 1, box.bottom - 5), (box.right - 4, box.y + 5)], 3)
            else:
                pygame.draw.circle(screen, theme.LACQUER_RED, c, 15)
                fonts.text(screen, i + 1, fonts.font("bold", 16), theme.GOLD_LIGHT, c, "center")
            h = fonts.height_of(o["text"], self.opt_font, rect.w - 90, 4)
            fonts.paragraph(screen, o["text"], self.opt_font, theme.INK, rect.x + 58, rect.centery - h // 2 + 2, rect.w - 90, gap=4)

    def _draw_order(self, screen):
        correct = list(self.q["correct_answer"])
        for i, (r, item) in enumerate(zip(self._row_rects(), self.order, strict=False)):
            bg, border = theme.PAPER_2, theme.PAPER_3
            if self.drag == i:
                bg, border = (232, 202, 142), theme.GOLD_DARK
            if self.result and self.result.get("final"):
                good = correct[i] == item["id"]
                bg, border = ((178, 218, 186), theme.JADE) if good else ((232, 176, 160), theme.RED)
            pygame.draw.rect(screen, bg, r, border_radius=6)
            pygame.draw.rect(screen, border, r, 2, border_radius=6)
            pygame.draw.circle(screen, theme.LACQUER_RED, (r.x + 26, r.centery), 15)
            fonts.text(screen, i + 1, fonts.font("bold", 16), theme.GOLD_LIGHT, (r.x + 26, r.centery), "center")
            hh = fonts.height_of(item["text"], self.opt_font, r.w - 170, 2)
            fonts.paragraph(screen, item["text"], self.opt_font, theme.INK, r.x + 54, r.centery - hh // 2, r.w - 170, gap=2)
            up, down = self._arrow_rects(r)
            for box, d in ((up, -1), (down, 1)):
                pygame.draw.rect(screen, theme.PAPER_3, box, border_radius=4)
                cx, cy = box.center
                pygame.draw.polygon(screen, theme.INK, [(cx - 8, cy - 5 * d), (cx + 8, cy - 5 * d), (cx, cy + 6 * d)])

    def _draw_match(self, screen):
        lefts, rights = self._match_rects()
        pairs = dict(self.pairs)
        final = self.result and self.result.get("final")
        if final and not self.result["correct"]:
            pairs = dict(self.q["correct_answer"])
        color_of = {}
        for i, (l_id, r_id) in enumerate(pairs.items()):
            col = PAIR_COLORS[i % len(PAIR_COLORS)]
            color_of[l_id], color_of[r_id] = col, col
            a, b = lefts[l_id], rights[r_id]
            pygame.draw.line(screen, col, a.midright, b.midleft, 3)
        for rects, items in ((lefts, self.left), (rights, self.right)):
            for o in items:
                r = rects[o["id"]]
                col = color_of.get(o["id"])
                bg = (232, 202, 142) if o["id"] == self.pick_left else theme.PAPER_2
                pygame.draw.rect(screen, bg, r, border_radius=6)
                pygame.draw.rect(screen, col or theme.PAPER_3, r, 3 if col else 2, border_radius=6)
                f = fonts.font("ui", 17)
                hh = fonts.height_of(o["text"], f, r.w - 24, 2)
                fonts.paragraph(screen, o["text"], f, theme.INK, r.x + 12, r.centery - hh // 2, r.w - 24, gap=2)

    def _draw_map(self, screen):
        m = self.map
        m.draw(screen)
        pygame.draw.rect(screen, theme.GOLD_DARK, m.rect, 2)
        fonts.text(screen, "Cuộn chuột để phóng to, kéo để di chuyển", fonts.font("italic", 13), theme.INK, (m.rect.x + 8, m.rect.y + 6))
        prev = screen.get_clip()
        screen.set_clip(m.rect)
        if self.marker:
            x, y = m.to_screen(*self.marker)
            pygame.draw.circle(screen, theme.RED, (x, y), 9)
            pygame.draw.circle(screen, theme.WHITE, (x, y), 9, 2)
        if self.result and self.result.get("final"):
            c = self.q["correct_answer"]
            x, y = m.to_screen(c["lat"], c["lon"])
            pygame.draw.circle(screen, theme.JADE, (x, y), 11)
            pygame.draw.circle(screen, theme.WHITE, (x, y), 11, 2)
            fonts.text(screen, self.q.get("place_label", ""), fonts.font("bold", 15), theme.INK, (x + 14, y - 10), shadow=theme.PAPER)
        screen.set_clip(prev)

    def _draw_result(self, screen):
        res = self.result
        rect = pygame.Rect(PANEL.x + 24, PANEL.bottom - 222, PANEL.width - 48, 208)
        if not res.get("final"):
            rect = pygame.Rect(PANEL.x + 24, PANEL.bottom - 86, PANEL.width - 300, 72)
        ui.lacquer_panel(screen, rect, 250)
        x, y = rect.x + 22, rect.y + 14
        if res["correct"]:
            title = "Chính xác!" + (f"  +{res['points']} điểm" if res["points"] else "")
            col = theme.JADE_LIGHT
        elif res.get("final"):
            title = "Chưa đúng. Đáp án đúng đã được đánh dấu, câu này sẽ quay lại trong phần ôn tập vào ngày mai."
            col = (240, 150, 120)
        else:
            left = MAX_TRIES - self.tries
            title = f"Chưa đúng. Còn {left} lần thử, điểm nhận được sẽ giảm dần."
            col = (240, 150, 120)
        y = fonts.paragraph(screen, title, fonts.font("bold", 19), col, x, y, rect.w - 44)
        if res.get("final"):
            w = rect.w - 44 - 250
            yy = fonts.paragraph(screen, self.q.get("explanation", ""), fonts.font("ui", 17), theme.PAPER, x, y + 2, w, gap=3)
            cite = self.state.citation_text(self.q.get("citations"))
            if cite:
                fonts.paragraph(screen, "Nguồn: " + cite, fonts.font("italic", 13), theme.PAPER_3, x, yy + 2, w, gap=2)


class FragmentScene(Scene):
    """Nhận mảnh ghép tư liệu: ba mảnh giấy bay lại khớp nhau rồi hiện nội dung (Req 13)."""

    opaque = False

    def __init__(self, app, fragment: dict):
        super().__init__(app)
        self.f = fragment
        self.t = 0.0
        self.rect = pygame.Rect(170, 40, 940, 640)
        self.btn = ui.Button((self.rect.centerx - 130, self.rect.bottom - 66, 260, 48), "Cất vào Sổ tay", self._done, "gold")
        self.app.audio.play("nhan")

    def _done(self):
        self.app.scenes.pop(True)

    def handle(self, event):
        if self.t > 0.7:
            self.btn.handle(event)

    def update(self, dt):
        self.t += dt

    def backdrop(self, screen):
        ui.veil(screen, (14, 8, 6, 200))

    def draw(self, screen):
        rect = self.rect
        k = min(1.0, self.t / 0.7)
        k = 1 - (1 - k) ** 3
        if k < 1:
            # Ba mảnh giấy rách bay vào khớp nhau
            pieces = (((-280, -160), (0, 0, 0.42, 0.55)), ((300, -120), (0.42, 0, 0.58, 0.48)), ((-60, 240), (0, 0.48, 1, 0.52)))
            for (ox, oy), (fx_, fy, fw, fh) in pieces:
                r = pygame.Rect(rect.x + rect.w * fx_ + ox * (1 - k), rect.y + rect.h * fy + oy * (1 - k), rect.w * fw, rect.h * fh)
                pygame.draw.rect(screen, theme.PAPER, r)
                pygame.draw.rect(screen, theme.PAPER_3, r, 2)
            return
        ui.paper_panel(screen, rect)
        r = ui.tag(screen, "MẢNH GHÉP TƯ LIỆU", (rect.x + 34, rect.y + 24))
        kind = self.f.get("kind_label")
        if kind:
            ui.tag(screen, kind, (r.right + 8, rect.y + 24), theme.PAPER_3, theme.INK)
        y = rect.y + 62
        icon = self.f.get("icon")
        tx = rect.x + 34
        w = rect.w - 68
        if icon:
            screen.blit(art.artifact(icon, 120), (rect.right - 158, rect.y + 56))
            w -= 136
        y = fonts.paragraph(screen, self.f["title"], fonts.font("serif", 28), theme.INK, tx, y, w)
        y = fonts.paragraph(screen, self.f["body"], fonts.font("serif", 20), theme.INK_SOFT, tx, y + 8, w, gap=6)
        if self.f.get("quote"):
            y += 8
            h = fonts.height_of(self.f["quote"], fonts.font("italic", 19), rect.w - 110, 5) + 20
            q = pygame.Rect(tx, y, rect.w - 68, h)
            pygame.draw.rect(screen, theme.PAPER_2, q, border_radius=4)
            pygame.draw.rect(screen, theme.LACQUER_RED, (q.x, q.y, 4, q.h))
            fonts.paragraph(screen, self.f["quote"], fonts.font("italic", 19), theme.INK, q.x + 20, q.y + 10, q.w - 34, gap=5)
            y = q.bottom
        cite = self.state.citation_text(self.f.get("citations"))
        if cite:
            fonts.paragraph(screen, "Nguồn: " + cite, fonts.font("italic", 14), theme.INK_FAINT, tx, y + 10, rect.w - 68, gap=2)
        self.btn.draw(screen)
