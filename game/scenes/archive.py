"""Kho tư liệu: văn bản lịch sử bị xé thành mảnh nằm rải rác trên map, nhặt đủ thì ghép lại cho đúng thứ tự câu chữ.

Mỗi tư liệu là đoạn trích văn bản thật (Chiếu dời đô, Hịch tướng sĩ, Bình Ngô đại cáo, Tuyên ngôn Độc lập...) kèm
tác giả, năm, nguồn; tác giả chưa chắc chắn thì có nhãn "Tương truyền". Ghép đúng thì tư liệu vào kho, được điểm kỹ năng.
"""

from __future__ import annotations

import pygame
from core import art, fonts, theme, ui
from core.scene import Scene

from scenes.question import QuestionScene

RECT = pygame.Rect(60, 26, 1160, 668)
LIST_X, LIST_W = RECT.x + 28, 410
DETAIL_X = RECT.x + 470
DETAIL_W = RECT.right - DETAIL_X - 32
ROW_H = 54


class ArchiveScene(Scene):
    def __init__(self, app, level_id: str | None = None):
        super().__init__(app)
        st = self.state
        self.docs = st.documents()
        here = [d for d in self.docs if d["level"] == level_id] if level_id else []
        ready = [d for d in self.docs if st.doc_ready(d)]
        first = (ready or here or self.docs or [None])[0]
        self.sel = self.docs.index(first) if first else 0
        self.pending: QuestionScene | None = None
        self.group = ui.ButtonGroup()
        self.rows: list[tuple[pygame.Rect, int]] = []
        self.t = 0.0
        self._layout()

    # ----- dựng -----
    def _layout(self):
        self.group.clear()
        st = self.state
        self.rows = []
        y = RECT.y + 96
        last_level = None
        for i, d in enumerate(self.docs):
            if d["level"] != last_level:
                last_level = d["level"]
                y += 26
            self.rows.append((pygame.Rect(LIST_X, y, LIST_W, ROW_H), i))
            y += ROW_H + 6
        doc = self.current
        if doc and st.doc_ready(doc):
            self.group.add(ui.Button((DETAIL_X, RECT.bottom - 82, 300, 54), "Ghép lại tư liệu", self._restore, "gold"))
        self.group.add(ui.Button((RECT.right - 196, RECT.bottom - 76, 164, 46), "Quay lại", lambda: self.app.scenes.pop(), "ghost", size=17))

    @property
    def current(self) -> dict | None:
        return self.docs[self.sel] if self.docs else None

    def _select(self, i: int):
        if 0 <= i < len(self.docs) and i != self.sel:
            self.sel = i
            self.app.audio.play("click")
            self._layout()

    # ----- ghép -----
    def _restore(self):
        doc = self.current
        if not doc or not self.state.doc_ready(doc):
            return
        self.pending = QuestionScene(self.app, doc["question"])
        self.app.scenes.push(self.pending)

    def on_resume(self, result=None):
        scene, self.pending = self.pending, None
        doc = self.current
        if scene is None or doc is None:
            return
        if scene.result and scene.result.get("correct"):
            badge = self.state.restore_doc(doc)
            self.app.audio.play("thang")
            self.app.toast(f"Đã phục dựng: {doc['title']}", theme.GOLD_LIGHT, 3.5)
            if badge:
                self.app.toast("Danh hiệu mới: Người giữ sử", theme.GOLD_LIGHT, 4.0)
        else:
            self.app.toast("Chưa ghép đúng. Đọc lại các mảnh rồi thử lần nữa nhé.", theme.PAPER_3, 3.0)
        self._layout()

    # ----- sự kiện -----
    def handle(self, event):
        if self.group.handle(event):
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for r, i in self.rows:
                if r.collidepoint(event.pos):
                    self._select(i)
                    return
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.scenes.pop()
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._select(self.sel + 1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._select(self.sel - 1)
            elif event.key in (pygame.K_RETURN, pygame.K_e) and self.current and self.state.doc_ready(self.current):
                self._restore()

    def update(self, dt):
        self.t += dt

    # ----- vẽ -----
    def _status(self, doc) -> tuple[str, tuple]:
        st = self.state
        n, got = len(doc["pieces"]), len(set(st.doc_got(doc)))
        if doc["id"] in st.doc_done:
            return "Đã phục dựng", theme.JADE
        if got >= n:
            return "Đủ mảnh, ghép lại được rồi", theme.GOLD_DARK
        if got:
            return f"Đã nhặt {got}/{n} mảnh", theme.INK_SOFT
        return "Chưa tìm thấy mảnh nào", theme.INK_FAINT

    def draw(self, screen):
        st = self.state
        screen.fill(theme.LACQUER)
        ui.paper_panel(screen, RECT)
        fonts.text(screen, "KHO TƯ LIỆU", fonts.font("serif", 32), theme.LACQUER_RED, (RECT.x + 28, RECT.y + 20))
        done = sum(1 for d in self.docs if d["id"] in st.doc_done)
        fonts.text(screen, f"Đã phục dựng {done}/{len(self.docs)} tư liệu. Nhặt mảnh văn bản trên map rồi ghép lại cho đúng.",
                   fonts.font("ui", 15), theme.INK_SOFT, (RECT.x + 30, RECT.y + 64))
        last_level = None
        for r, i in self.rows:
            d = self.docs[i]
            if d["level"] != last_level:
                last_level = d["level"]
                fonts.text(screen, st.levels[d["level"]]["level"]["period_label"], fonts.font("bold", 14), theme.GOLD_DARK, (r.x, r.y - 22))
            active = i == self.sel
            pygame.draw.rect(screen, (234, 214, 170) if active else theme.PAPER_2, r)
            if active:
                pygame.draw.rect(screen, theme.LACQUER_RED, (r.x, r.y, 5, r.h))
            title = fonts.wrap(d["title"], fonts.font("semi", 16), r.w - 30)[0]
            fonts.text(screen, title, fonts.font("semi", 16), theme.INK, (r.x + 16, r.y + 6))
            label, color = self._status(d)
            fonts.text(screen, label, fonts.font("ui", 13), color, (r.x + 16, r.y + 30))
            if st.doc_ready(d) and ui.pulse(self.t, 4) > 0.4:
                pygame.draw.circle(screen, theme.GOLD, (r.right - 18, r.centery), 6)
        pygame.draw.line(screen, theme.PAPER_3, (DETAIL_X - 22, RECT.y + 96), (DETAIL_X - 22, RECT.bottom - 24), 2)
        if self.current:
            self._draw_detail(screen, self.current)
        self.group.draw(screen)

    def _draw_detail(self, screen, doc):
        st = self.state
        x, w = DETAIL_X, DETAIL_W
        y = RECT.y + 100
        tx = ui.tag(screen, f"{doc['kind']}, {doc['year']}", (x, y), theme.LACQUER_RED, theme.GOLD_LIGHT).right + 8
        if doc.get("legend"):
            ui.tag(screen, "Tương truyền", (tx, y), theme.GOLD_DARK, theme.WHITE)
        y = fonts.paragraph(screen, doc["title"], fonts.font("serif", 26), theme.INK, x, y + 30, w, gap=2)
        y = fonts.paragraph(screen, doc["author"], fonts.font("italic", 15), theme.INK_SOFT, x, y + 2, w)
        y += 14
        items = doc["question"]["items"]
        got = set(st.doc_got(doc))
        if doc["id"] in st.doc_done:
            for item in items:
                y = fonts.paragraph(screen, item["text"], fonts.font("serif", 19), theme.INK, x + 14, y, w - 160, gap=4) + 6
            seal = art.stamp("Đã ghép", 112)
            screen.blit(seal, seal.get_rect(topright=(RECT.right - 36, RECT.y + 100)))
            y = fonts.paragraph(screen, doc["note"], fonts.font("ui", 15), theme.INK_SOFT, x, y + 8, w, gap=3)
            cite = st.citation_text(doc.get("cite"))
            if cite:
                fonts.paragraph(screen, "Nguồn: " + cite, fonts.font("italic", 13), theme.INK_FAINT, x, y + 10, w - 200, gap=2)
            return
        # Chưa ghép: hiện các mảnh đã nhặt như những mẩu giấy rách, theo thứ tự nhặt được chứ không phải thứ tự đúng
        order = sorted(got, key=lambda i: (i * 7 + len(doc["id"])) % len(items))
        for i in order:
            text = items[i]["text"]
            hh = fonts.height_of(text, fonts.font("serif", 17), w - 40, 3) + 16
            slip = pygame.Rect(x, y, w, hh)
            pygame.draw.rect(screen, (248, 238, 214), slip)
            pygame.draw.rect(screen, theme.PAPER_3, slip, 1)
            for k in range(0, w, 14):  # mép giấy rách
                pygame.draw.line(screen, theme.PAPER, (x + k, slip.bottom - 1), (x + k + 7, slip.bottom - 4), 2)
            fonts.paragraph(screen, text, fonts.font("serif", 17), theme.INK, x + 18, y + 8, w - 40, gap=3)
            y += hh + 8
        missing = len(items) - len(got)
        if missing:
            y = fonts.paragraph(screen, f"Còn thiếu {missing} mảnh. {doc['hint']}", fonts.font("semi", 15), theme.LACQUER_RED, x, y + 6, w, gap=3)
            fonts.paragraph(screen, "Mảnh tư liệu là cuộn giấy nhỏ nằm trên mặt đất, đi ngang qua là nhặt được.",
                            fonts.font("ui", 14), theme.INK_SOFT, x, y + 6, w, gap=2)
        else:
            fonts.paragraph(screen, "Đã đủ mảnh. Bấm “Ghép lại tư liệu” rồi kéo các câu về đúng thứ tự trong văn bản.",
                            fonts.font("semi", 15), theme.GOLD_DARK, x, y + 6, w, gap=3)
