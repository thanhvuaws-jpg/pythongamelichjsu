"""Sổ tay sử quan: nhân vật, sự kiện, địa danh, tư liệu, nguồn; tìm kiếm không dấu (Req 17)."""

from __future__ import annotations

import unicodedata

import pygame
from core import fonts, sprites, theme, ui
from core.scene import Scene

TABS = [("persons", "Nhân vật"), ("events", "Sự kiện"), ("places", "Địa danh"), ("fragments", "Tư liệu"), ("sources", "Nguồn")]
LIST_RECT = pygame.Rect(40, 134, 400, 560)
DETAIL_RECT = pygame.Rect(460, 134, 780, 560)
ROW_H = 46


def bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt và về chữ thường để tìm kiếm."""
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _title(kind: str, item: dict) -> str:
    if kind in ("persons", "places"):
        return item["name"]
    return item["title"]


class NotebookScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.tab = 0
        self.query = ""
        self.scroll = 0
        self.selected = None
        self.group = ui.ButtonGroup()
        self.group.add(ui.Button((theme.WIDTH - 150, 14, 136, 40), "Đóng", lambda: self.app.scenes.pop(), "ghost", size=15))
        for i, (_, label) in enumerate(TABS):
            b = ui.Button((40 + i * 128, 74, 122, 44), label, None, "ghost", size=16, data=i)
            b.on_click = lambda n=i: self._switch(n)
            self.group.add(b)
        self.tab_buttons = self.group.buttons[1:]
        self._reload()

    def _switch(self, n):
        self.tab = n
        self.scroll = 0
        self.selected = None
        self._reload()

    def _reload(self):
        kind = TABS[self.tab][0]
        st = self.state
        q = bo_dau(self.query)
        rows = []
        if kind == "sources":
            for sid, s in st.sources["sources"].items():
                rows.append({"id": sid, "item": s, "open": True, "title": s["title"]})
        else:
            for item in st.index[kind].values():
                opened = item["id"] in st.notebook or (kind == "fragments" and item["id"] in st.progress.collected_fragments)
                rows.append({"id": item["id"], "item": item, "open": opened, "title": _title(kind, item)})
        if kind == "fragments":
            for cid, text in st.clues.items():
                rows.append({"id": cid, "item": {"title": "Manh mối", "body": text}, "open": True, "title": "Manh mối: " + text[:34]})
        if q:
            rows = [r for r in rows if r["open"] and q in bo_dau(r["title"])]
        rows.sort(key=lambda r: not r["open"])
        self.rows = rows

    def handle(self, event):
        if self.group.handle(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.scenes.pop()
            elif event.key == pygame.K_BACKSPACE:
                self.query = self.query[:-1]
                self._reload()
            elif event.unicode and event.unicode.isprintable() and len(self.query) < 30:
                self.query += event.unicode
                self._reload()
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(max(0, len(self.rows) * ROW_H - LIST_RECT.h + 16), self.scroll - event.y * 40))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and LIST_RECT.collidepoint(event.pos):
            idx = (event.pos[1] - LIST_RECT.y - 8 + self.scroll) // ROW_H
            if 0 <= idx < len(self.rows) and self.rows[idx]["open"]:
                self.selected = self.rows[idx]
                self.app.audio.play("click")

    def draw(self, screen):
        screen.fill(theme.LACQUER)
        fonts.text(screen, "SỔ TAY SỬ QUAN", fonts.font("serif", 28), theme.GOLD_LIGHT, (40, 18))
        for i, b in enumerate(self.tab_buttons):
            b.style = "gold" if i == self.tab else "ghost"
        self.group.draw(screen)
        fonts.text(screen, "Gõ để tìm (không cần dấu): " + (self.query or "..."), fonts.font("italic", 15), theme.PAPER_3, (700, 88))
        ui.paper_panel(screen, LIST_RECT, shadow=False)
        prev = screen.get_clip()
        screen.set_clip(LIST_RECT.inflate(-8, -8))
        y = LIST_RECT.y + 8 - self.scroll
        f = fonts.font("semi", 16)
        for row in self.rows:
            rect = pygame.Rect(LIST_RECT.x + 10, y, LIST_RECT.w - 20, ROW_H - 6)
            if self.selected and self.selected["id"] == row["id"]:
                pygame.draw.rect(screen, (232, 202, 142), rect, border_radius=4)
            if row["open"]:
                lines = fonts.wrap(row["title"], f, rect.w - 16)
                fonts.text(screen, lines[0] + (" …" if len(lines) > 1 else ""), f, theme.INK, (rect.x + 8, rect.centery), "midleft")
            else:
                fonts.text(screen, "?  Chưa khám phá", fonts.font("italic", 15), theme.INK_FAINT, (rect.x + 8, rect.centery), "midleft")
            y += ROW_H
        screen.set_clip(prev)
        ui.paper_panel(screen, DETAIL_RECT, shadow=False)
        if self.selected:
            self._draw_detail(screen)
        else:
            fonts.paragraph(screen, "Chọn một mục đã khám phá để đọc chi tiết. Mục chưa khám phá hiện dấu “?” — hãy thăm thêm di tích để mở khoá.",
                            fonts.font("serif", 19), theme.INK_FAINT, DETAIL_RECT.x + 40, DETAIL_RECT.y + 40, DETAIL_RECT.w - 80)

    def _draw_detail(self, screen):
        kind = TABS[self.tab][0]
        it = self.selected["item"]
        r = DETAIL_RECT
        x = r.x + 30
        w = r.w - 60
        y = r.y + 24
        y = fonts.paragraph(screen, self.selected["title"], fonts.font("serif", 27), theme.INK, x, y, w, gap=2)
        small = fonts.font("italic", 15)
        body = fonts.font("serif", 19)
        if kind == "persons":
            if it.get("portrait"):
                screen.blit(sprites.portrait(it["portrait"], 3), (r.right - 172, r.y + 24))
                w -= 160
            y = fonts.paragraph(screen, it.get("years", ""), small, theme.INK_SOFT, x, y + 2, w)
            y = fonts.paragraph(screen, it.get("bio", ""), body, theme.INK_SOFT, x, y + 8, w, gap=5)
        elif kind == "events":
            y = fonts.paragraph(screen, it["date"].get("label", ""), fonts.font("bold", 16), theme.LACQUER_RED, x, y + 2, w)
            y = fonts.paragraph(screen, it.get("summary", ""), body, theme.INK_SOFT, x, y + 8, w, gap=5)
            if it.get("significance"):
                y = fonts.paragraph(screen, "Ý nghĩa: " + it["significance"], body, theme.INK_SOFT, x, y + 6, w, gap=5)
            if it.get("historian_note"):
                ui.tag(screen, "GHI CHÚ SỬ HỌC", (x, y + 8), theme.BLUE, theme.WHITE)
                y = fonts.paragraph(screen, it["historian_note"], fonts.font("ui", 16), theme.INK_SOFT, x, y + 38, w, gap=4)
        elif kind == "places":
            for n in it.get("names", []):
                y = fonts.paragraph(screen, f"{n['period']}: {n['name']}", small, theme.INK_SOFT, x, y + 2, w, gap=1)
            y = fonts.paragraph(screen, "Ngày nay: " + it.get("modern_name", ""), small, theme.INK_SOFT, x, y + 2, w)
            y = fonts.paragraph(screen, it.get("summary", ""), body, theme.INK_SOFT, x, y + 8, w, gap=5)
        elif kind == "fragments":
            y = fonts.paragraph(screen, it.get("body", ""), body, theme.INK_SOFT, x, y + 8, w, gap=5)
            if it.get("quote"):
                y = fonts.paragraph(screen, it["quote"], fonts.font("italic", 18), theme.INK, x + 14, y + 8, w - 14, gap=5)
        else:
            lines = [it.get("authors"), it.get("translators"), it.get("publisher"), it.get("note")]
            for line in lines:
                if line:
                    y = fonts.paragraph(screen, line, fonts.font("ui", 17), theme.INK_SOFT, x, y + 6, w, gap=4)
            ui.tag(screen, f"Cấp nguồn {it.get('tier', '?')}", (x, y + 12), theme.LACQUER_RED, theme.GOLD_LIGHT)
            return
        cite = self.state.citation_text(it.get("citations"))
        if cite:
            fonts.paragraph(screen, "Nguồn: " + cite, fonts.font("italic", 14), theme.INK_FAINT, x, max(y + 12, r.bottom - 74), r.w - 60, gap=2)
