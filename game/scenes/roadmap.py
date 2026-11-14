"""Bảng Lộ trình: toàn bộ chặng đường trên một màn hình, để người mới luôn biết mình đang ở đâu và cần làm gì tiếp."""

from __future__ import annotations

import pygame
from core import fonts, sprites, theme, ui
from core.scene import Scene

W, H = theme.WIDTH, theme.HEIGHT
NOW = pygame.Rect(30, 64, 1220, 62)
MAP = pygame.Rect(30, 138, 820, 562)
DETAIL = pygame.Rect(864, 138, 386, 352)
MORE = pygame.Rect(864, 500, 386, 200)
NODE_R = 21
NODE_EDGE = 62  # lề hai bên để tên địa danh ở đầu và cuối hàng không tràn khung
ROW_H = 176
OUTLINE = (24, 16, 14)
STEP_NAMES = {"go_to": "Đến nơi", "dialogue": "Nghe chuyện", "answer": "Trả lời câu hỏi", "collect": "Nhặt mảnh ghép", "battle": "Vào trận"}
END = "end"  # nút cuối mỗi chặng: dựng dòng thời gian rồi qua cổng


class RoadmapScene(Scene):
    def __init__(self, app, level_id: str, doing: str):
        super().__init__(app)
        self.level_id = level_id
        self.doing = doing
        self.t = 0.0
        self.group = ui.ButtonGroup()
        self.group.add(ui.Button((W - 150, 12, 136, 40), "Đóng", self._close, "ghost", size=15))
        self.go = ui.Button((DETAIL.x + 22, DETAIL.bottom - 62, DETAIL.w - 44, 44), "Đi tới đây", self._travel, "gold", size=16)
        self.nodes = self._layout()
        self.sel = self._current_index()

    # ----- dữ liệu -----
    def _layout(self) -> list[dict]:
        out = []
        st = self.state
        for row, lid in enumerate(st.order):
            relics = st.levels[lid]["relics"]
            count = len(relics) + 1
            step = (MAP.w - 2 * NODE_EDGE) / max(1, count - 1)
            y = MAP.y + 76 + row * ROW_H
            for i in range(count):
                out.append({
                    "level": lid, "row": row, "x": int(MAP.x + NODE_EDGE + i * step), "y": y,
                    "relic": relics[i] if i < len(relics) else None,
                })
        return out

    def _status(self, node: dict) -> str:
        """done: xong; now: đang làm; open: mở rồi nhưng chưa tới lượt; locked: chưa mở."""
        st = self.state
        lid = node["level"]
        if not st.level_unlocked(lid):
            return "locked"
        relic = node["relic"]
        if relic is None:
            if lid in st.progress.timeline_done:
                return "done"
            return "now" if st.timeline_ready(lid) else "locked"
        if st.relic_done(relic["id"]):
            return "done"
        if relic["place"] not in st.engine(lid).unlocked_places():
            return "locked"
        nxt = st.next_relic(lid)
        return "now" if nxt is not None and nxt["id"] == relic["id"] else "open"

    def _current_index(self) -> int:
        for i, node in enumerate(self.nodes):
            if node["level"] == self.level_id and self._status(node) == "now":
                return i
        return next((i for i, n in enumerate(self.nodes) if n["level"] == self.level_id), 0)

    def _can_travel(self, node: dict) -> bool:
        if node["relic"] is None:
            return False
        if self.state.is_admin:  # quản trị viên tới được mọi di tích, kể cả chưa mở và ở màn khác
            return True
        return node["level"] == self.level_id and self._status(node) != "locked"

    # ----- thao tác -----
    def _close(self):
        self.app.scenes.pop(None)

    def _travel(self):
        node = self.nodes[self.sel]
        if self._can_travel(node):
            self.app.scenes.pop({"travel": node["relic"]["id"], "level": node["level"]})

    def _rect(self, node: dict) -> pygame.Rect:
        size = NODE_R * 2 + 12
        return pygame.Rect(node["x"] - size // 2, node["y"] - size // 2, size, size)

    def _move_row(self, step: int):
        here = self.nodes[self.sel]
        same = [i for i, n in enumerate(self.nodes) if n["row"] == here["row"] + step]
        if same:
            self.sel = min(same, key=lambda i: abs(self.nodes[i]["x"] - here["x"]))

    def handle(self, event):
        if event.type != pygame.KEYDOWN and self.group.handle(event):
            return
        if self._can_travel(self.nodes[self.sel]) and event.type != pygame.KEYDOWN and self.go.handle(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_j):
                self._close()
            elif event.key == pygame.K_RIGHT:
                self.sel = min(len(self.nodes) - 1, self.sel + 1)
            elif event.key == pygame.K_LEFT:
                self.sel = max(0, self.sel - 1)
            elif event.key == pygame.K_DOWN:
                self._move_row(1)
            elif event.key == pygame.K_UP:
                self._move_row(-1)
            elif event.key == pygame.K_RETURN:
                self._travel()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for i, node in enumerate(self.nodes):
                if self._rect(node).collidepoint(event.pos):
                    self.sel = i
                    self.app.audio.play("click")
                    return

    def update(self, dt):
        self.t += dt

    # ----- vẽ -----
    def draw(self, screen):
        screen.fill(theme.LACQUER)
        fonts.text(screen, "LỘ TRÌNH CỦA BẠN", fonts.font("serif", 28), theme.GOLD_LIGHT, (30, 16))
        ui.lacquer_panel(screen, NOW, 244)
        fonts.text(screen, "Việc cần làm ngay:", fonts.font("semi", 15), theme.PAPER_3, (NOW.x + 22, NOW.centery), "midleft")
        fonts.text(screen, self.doing, fonts.font("bold", 19), theme.GOLD_LIGHT, (NOW.x + 180, NOW.centery), "midleft")
        ui.paper_panel(screen, MAP, shadow=False)
        self._draw_map(screen)
        self._draw_detail(screen)
        self._draw_more(screen)
        self.group.draw(screen)

    def _draw_map(self, screen):
        st = self.state
        for row, lid in enumerate(st.order):
            level = st.levels[lid]["level"]
            y = MAP.y + 22 + row * ROW_H
            col = theme.INK if st.level_unlocked(lid) else theme.INK_FAINT
            r = fonts.text(screen, level["title"], fonts.font("bold", 18), col, (MAP.x + 24, y))
            fonts.text(screen, level["period_label"], fonts.font("ui", 14), theme.INK_SOFT, (r.right + 12, y + 3))
        for a, b in zip(self.nodes, self.nodes[1:], strict=False):
            if a["row"] == b["row"]:
                done = self._status(a) == "done"
                pygame.draw.line(screen, theme.LACQUER_RED if done else theme.PAPER_3, (a["x"], a["y"]), (b["x"], b["y"]), 5)
        names = fonts.font("semi", 11)
        for i, node in enumerate(self.nodes):
            self._draw_node(screen, node, i)
            label = "Dòng thời gian" if node["relic"] is None else (node["relic"].get("stamp") or node["relic"]["title"])
            status = self._status(node)
            color = theme.INK_FAINT if status == "locked" else theme.INK
            yy = node["y"] + NODE_R + 8
            for line in fonts.wrap(label, names, 82)[:2]:
                fonts.text(screen, line, names, color, (node["x"], yy), "midtop")
                yy += names.get_linesize()

    def _draw_node(self, screen, node, index):
        x, y = node["x"], node["y"]
        status = self._status(node)
        if index == self.sel:
            pygame.draw.circle(screen, theme.INK, (x, y), NODE_R + 6, 3)
        radius = NODE_R + (int(3 * ui.pulse(self.t, 5)) if status == "now" else 0)
        fill = {"done": theme.LACQUER_RED, "now": theme.GOLD, "open": theme.PAPER, "locked": theme.GRAY}[status]
        pygame.draw.circle(screen, OUTLINE, (x, y), radius + 3)
        pygame.draw.circle(screen, fill, (x, y), radius)
        if status == "done":
            pygame.draw.lines(screen, theme.WHITE, False, [(x - 10, y), (x - 3, y + 8), (x + 11, y - 8)], 4)
        elif node["relic"] is None:
            pygame.draw.polygon(screen, theme.INK if status != "locked" else theme.PAPER_2, [(x, y - 11), (x + 11, y), (x, y + 11), (x - 11, y)])
        else:
            number = node["relic"] and [r["id"] for r in self.state.levels[node["level"]]["relics"]].index(node["relic"]["id"]) + 1
            fonts.text(screen, number, fonts.font("bold", 16), theme.PAPER if status == "locked" else theme.INK, (x, y), "center")

    def _draw_detail(self, screen):
        ui.lacquer_panel(screen, DETAIL, 244)
        node = self.nodes[self.sel]
        if self._can_travel(node):
            self.go.draw(screen)
        x, w = DETAIL.x + 24, DETAIL.w - 48
        status = self._status(node)
        relic = node["relic"]
        title = relic["title"] if relic else "Dựng dòng thời gian, rồi qua cổng"
        y = fonts.paragraph(screen, title, fonts.font("bold", 19), theme.GOLD_LIGHT, x, DETAIL.y + 22, w, gap=1)
        if relic is None:
            text = {
                "done": "Đã xong. Cổng dịch chuyển đã mở, bước vào là sang giai đoạn mới.",
                "now": "Đã đủ dấu. Về gặp Cụ Đồ Sử để xếp lại các sự kiện theo thứ tự.",
            }.get(status, "Xong hết các di tích của chặng này thì về gặp Cụ Đồ Sử.")
            fonts.paragraph(screen, text, fonts.font("ui", 15), theme.PAPER, x, y + 8, w, gap=2)
            return
        if status == "locked" and node["level"] == self.level_id:
            fonts.paragraph(screen, "Chưa mở. Hãy làm xong di tích trước đó.", fonts.font("ui", 15), theme.PAPER_3, x, y + 8, w, gap=2)
            return
        if self.state.is_admin and node["level"] != self.level_id:
            fonts.paragraph(screen, "Thuộc chặng khác. Quyền quản trị cho phép đi thẳng tới đây.", fonts.font("ui", 15), theme.PAPER_3, x, y + 8, w, gap=2)
            return
        if not self.state.level_unlocked(node["level"]):
            fonts.paragraph(screen, "Chặng này mở khi bạn qua cổng ở cuối chặng trước.", fonts.font("ui", 15), theme.PAPER_3, x, y + 8, w, gap=2)
            return
        y += 10
        done = self.state.progress.completed_objectives
        quest = next(q for q in self.state.engine(node["level"]).quests if q["id"] == relic["id"])
        for obj in quest["objectives"]:
            ok = obj["id"] in done
            box = pygame.Rect(x, y + 2, 16, 16)
            pygame.draw.rect(screen, theme.PAPER_3, box, 2)
            if ok:
                pygame.draw.lines(screen, theme.JADE_LIGHT, False, [(box.x + 3, box.y + 8), (box.x + 7, box.y + 12), (box.x + 14, box.y + 3)], 3)
            fonts.text(screen, STEP_NAMES[obj["kind"]], fonts.font("ui", 15), theme.PAPER_3 if ok else theme.PAPER, (x + 26, y))
            y += 24
            if y > self.go.rect.y - 26:
                break
        if not self._can_travel(node) and node["level"] != self.level_id:
            fonts.paragraph(screen, "Thuộc chặng khác. Quay lại bằng cổng trên map.", fonts.font("ui", 14), theme.PAPER_3, x, DETAIL.bottom - 52, w, gap=1)

    def _guards(self) -> str:
        relics = [r["id"] for r in self.state.levels[self.level_id]["relics"]]
        return f"{sum(r in self.state.bosses_beaten for r in relics)}/{len(relics)}"

    def _more_rows(self) -> list[str]:
        st, lid = self.state, self.level_id
        ex = st.extras

        def row(label, items, done):
            here = [i for i in items if i["level"] == lid]
            if not here:
                return None
            return f"{label}: {sum(i['id'] in done for i in here)}/{len(here)}"

        rows = [
            row("Dấu hỏi trên map", ex["discoveries"], st.discovered),
            row("Vụ điều tra", ex["cases"], st.case_done),
            row("Nhiệm vụ phụ", ex["sides"], st.side_done),
            row("Giao tranh", ex["skirmishes"], st.skirmish_done),
            row("Tư liệu đã ghép (phím T)", ex.get("documents", []), st.doc_done),
            f"Thắng ở võ đài: {len(st.arena_wins)}/{len(ex['arena'])} · thách đấu: {st.duels_won}",
            f"Bóng giặc đã hạ: {st.mobs_killed} · kẻ canh mật thư: {self._guards()}",
            f"Vùng luyện đã mở: {sum(st.relic_done(f['requires']) for f in st.fields.values())}/{len(st.fields)}",
        ]
        return [r for r in rows if r]

    def _draw_more(self, screen):
        ui.paper_panel(screen, MORE, shadow=False)
        x = MORE.x + 22
        fonts.text(screen, "Làm thêm khi muốn", fonts.font("bold", 17), theme.INK, (x, MORE.y + 16))
        y = MORE.y + 44
        for line in self._more_rows():
            fonts.text(screen, line, fonts.font("ui", 14), theme.INK_SOFT, (x, y))
            y += 19
        left = self.state.skill_points_left()
        icon = sprites.icon("ui/sk_suc.png", 1)
        screen.blit(icon, (x, MORE.bottom - 40))
        fonts.text(screen, f"Điểm kỹ năng chưa dùng: {left} (phím K)", fonts.font("semi", 14), theme.LACQUER_RED if left else theme.INK_SOFT, (x + 32, MORE.bottom - 37))
