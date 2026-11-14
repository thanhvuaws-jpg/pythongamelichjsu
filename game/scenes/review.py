"""Ôn tập: lặp lại ngắt quãng theo lịch 1-3-7-14-30 ngày, câu sai được ưu tiên (Req 20).

Câu đến hạn thì đúng được điểm ôn tập và giãn lịch. Chưa có câu nào đến hạn vẫn luyện thêm được, để ngay sau khi chơi
xong một màn đã có thể ôn; phần luyện thêm không tính điểm nên không thể ôn đi ôn lại để lấy điểm.
"""

from __future__ import annotations

import pygame
from core import fonts, theme, ui
from core.scene import Scene

from scenes.question import QuestionScene

RECT = pygame.Rect(200, 40, 880, 640)
TAB_Y = RECT.y + 86
WRONG_SHOWN = 3


class ReviewScene(Scene):
    def __init__(self, app, level_id: str | None = None):
        super().__init__(app)
        self.level_id = level_id
        self.scope: str | None = level_id  # None là ôn mọi màn
        self.phase = "menu"  # menu, run, done
        self.queue: list[dict] = []
        self.due_ids: set[str] = set()
        self.total = 0
        self.index = 0
        self.correct = 0
        self.gained = 0
        self.wrong: list[dict] = []
        self.current: dict | None = None
        self.group = ui.ButtonGroup()
        self._plan()

    @property
    def finished(self) -> bool:
        return self.phase == "done"

    # ----- lập phiên ôn -----
    def _plan(self):
        self.plan = self.state.review_plan(self.scope)
        self.queue = [*self.plan["due"], *self.plan["early"]]
        self.due_ids = {q["id"] for q in self.plan["due"]}
        self.total = len(self.queue)
        self.index = self.correct = self.gained = 0
        self.wrong = []
        self.phase = "menu"
        self._layout()

    def _scopes(self) -> list[tuple[str, str | None]]:
        st = self.state
        out: list[tuple[str, str | None]] = [("Tất cả", None)]
        for lid in st.order:
            if st.level_unlocked(lid):
                out.append((st.levels[lid]["level"]["period_label"], lid))
        return out

    def _set_scope(self, scope):
        self.scope = scope
        self.app.audio.play("click")
        self._plan()

    def _layout(self):
        self.group.clear()
        cx = RECT.centerx
        if self.phase == "menu":
            scopes = self._scopes()
            w = min(170, (RECT.w - 80) // len(scopes) - 8)
            x = cx - (len(scopes) * (w + 8) - 8) // 2
            for label, scope in scopes:
                style = "gold" if scope == self.scope else "ghost"
                b = ui.Button((x, TAB_Y, w, 40), label, None, style, size=14)
                b.on_click = lambda s=scope: self._set_scope(s)
                self.group.add(b)
                x += w + 8
            if self.total:
                self.group.add(ui.Button((cx - 170, RECT.bottom - 132, 340, 56), "Bắt đầu ôn tập", self._start, "gold"))
        elif self.phase == "done" and self.state.review_plan(self.scope)["answered"]:
            self.group.add(ui.Button((cx - 170, RECT.bottom - 132, 340, 56), "Ôn tiếp phiên nữa", self._plan, "primary", size=18))
        self.group.add(ui.Button((cx - 170, RECT.bottom - 66, 340, 46), "Quay lại", lambda: self.app.scenes.pop(), "ghost", size=17))

    # ----- chạy phiên -----
    def _start(self):
        self.phase = "run"
        self._next()

    def _next(self):
        if self.queue:
            self.current = self.queue.pop(0)
            self.index += 1
            label = f"Ôn tập {self.index}/{self.total}"
            if self.current["id"] not in self.due_ids:
                label += " · luyện thêm"
            self.app.scenes.push(QuestionScene(self.app, self.current, review=True, label=label))
            return
        self.phase = "done"
        st = self.state
        if "chuyen_can" not in st.badges:
            st.badges.add("chuyen_can")
            self.app.toast("Danh hiệu mới: Sử quan chuyên cần", theme.GOLD_LIGHT, 3.5)
        st.save()
        self.app.audio.play("thang")
        self._layout()

    def on_resume(self, result=None):
        if self.current is None:
            return
        before, self.current = self.current, None
        if result:
            self.correct += 1
            if before["id"] in self.due_ids:
                self.gained += 2
        else:
            self.wrong.append(before)
        self._next()

    def handle(self, event):
        self.group.handle(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.pop()

    # ----- vẽ -----
    def draw(self, screen):
        screen.fill(theme.LACQUER)
        ui.paper_panel(screen, RECT)
        fonts.text(screen, "ÔN TẬP", fonts.font("serif", 34), theme.LACQUER_RED, (RECT.centerx, RECT.y + 26), "midtop")
        if self.phase == "done":
            self._draw_done(screen)
        else:
            self._draw_menu(screen)
        self.group.draw(screen)

    def _draw_menu(self, screen):
        plan = self.plan
        x, w = RECT.x + 60, RECT.w - 120
        y = TAB_Y + 62
        if not plan["answered"]:
            fonts.paragraph(screen, "Chưa có câu nào để ôn. Hãy trả lời câu hỏi đầu tiên ở một di tích rồi quay lại nhé.", fonts.font("serif", 20), theme.INK_SOFT, x, y, w)
            return
        cells = ((plan["answered"], "câu đã gặp"), (plan["due_total"], "câu đến hạn hôm nay"), (plan["mastered"], "câu đã thuộc"))
        cw = w // len(cells)
        for i, (value, label) in enumerate(cells):
            cell = pygame.Rect(x + i * cw, y, cw - 12, 84)
            pygame.draw.rect(screen, theme.PAPER_2, cell)
            fonts.text(screen, value, fonts.font("black", 34), theme.LACQUER_RED if i == 1 and value else theme.INK, (cell.x + 18, cell.y + 6))
            fonts.text(screen, label, fonts.font("ui", 15), theme.INK_SOFT, (cell.x + 18, cell.y + 52))
        y += 104
        n_due, n_early = len(plan["due"]), len(plan["early"])
        parts = []
        if n_due:
            parts.append(f"{n_due} câu đến hạn (đúng mỗi câu được +2 điểm và được giãn lịch ôn)")
        if n_early:
            parts.append(f"{n_early} câu luyện thêm (chưa đến hạn nên không tính điểm, sai thì mai gặp lại)")
        y = fonts.paragraph(screen, f"Phiên này có {self.total} câu: " + ", ".join(parts) + ".", fonts.font("serif", 19), theme.INK, x, y, w, gap=4)
        y = fonts.paragraph(screen, "Thứ tự ưu tiên: câu từng trả lời sai, rồi câu phải thử nhiều lần, rồi câu lâu chưa ôn.", fonts.font("ui", 15), theme.INK_SOFT, x, y + 8, w, gap=2)
        days = plan["next_due_days"]
        if not n_due and days:
            when = "ngày mai" if days <= 1 else f"sau {days} ngày nữa"
            fonts.paragraph(screen, f"Câu đến hạn tiếp theo: {when}.", fonts.font("semi", 15), theme.INK_SOFT, x, y + 6, w)

    def _draw_done(self, screen):
        x, w = RECT.x + 60, RECT.w - 120
        y = RECT.y + 92
        fonts.text(screen, f"Đúng {self.correct}/{self.total} câu", fonts.font("black", 36), theme.INK, (RECT.centerx, y), "midtop")
        y += 56
        note = f"+{self.gained} điểm ôn tập. " if self.gained else ""
        note += "Câu đến hạn mà đúng được giãn lịch ôn, câu sai sẽ quay lại vào ngày mai."
        y = fonts.paragraph(screen, note, fonts.font("serif", 18), theme.INK_SOFT, x, y, w, gap=3)
        if not self.wrong:
            fonts.paragraph(screen, "Không sai câu nào. Giỏi lắm!", fonts.font("semi", 18), theme.JADE, x, y + 10, w)
            return
        y = fonts.paragraph(screen, "Xem lại những câu vừa sai:", fonts.font("bold", 17), theme.INK, x, y + 10, w)
        small = fonts.font("ui", 14)
        for q in self.wrong[:WRONG_SHOWN]:
            if y > RECT.bottom - 210:
                break
            y = fonts.paragraph(screen, q["prompt"], fonts.font("semi", 15), theme.INK, x, y + 6, w, gap=1)
            for line in fonts.wrap(q.get("explanation", ""), small, w - 16)[:2]:
                fonts.text(screen, line, small, theme.INK_SOFT, (x + 16, y))
                y += small.get_linesize()
        more = len(self.wrong) - WRONG_SHOWN
        if more > 0:
            fonts.text(screen, f"và {more} câu nữa, xem lại trong Sổ tay.", fonts.font("italic", 14), theme.INK_SOFT, (x, y + 6))
