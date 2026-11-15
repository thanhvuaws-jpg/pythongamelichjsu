"""Vụ điều tra trong nhà: đi trong một căn phòng, xem từng manh mối rồi nêu kết luận bằng một câu hỏi."""

from __future__ import annotations

import pygame
from core import fonts, outfit, progression, sprites, theme, touch, ui
from core.scene import Scene
from core.sprites import TILE

from scenes.question import QuestionScene
from scenes.story import StoryScene

W, H = theme.WIDTH, theme.HEIGHT
COLS, ROWS = 16, 9
OX, OY = (W - COLS * TILE) // 2, (H - ROWS * TILE) // 2 + 20
SPEED = TILE * 4.6
REACH = TILE * 1.5
HIT = TILE * 0.28
DOOR = (7, 8)  # ô cửa, rộng hai ô ở giữa tường dưới
DESK = (8, 3)  # chỗ đứng ghép manh mối, ngay dưới cái bàn
# Khung tường 5x5 ô: tên -> ô góc trên trái của khung trong tiles/int_wall.png
WALLS = {"cream": (0, 0), "orange": (5, 0), "brown": (0, 6), "green": (5, 6)}
# Đồ đạc: tên -> (tileset, cột, hàng, rộng, cao); hàng dưới cùng của đồ vật là chỗ chắn đường
FURNITURE = {
    "shelf": ("element", 3, 7, 1, 2), "shelf_big": ("element", 8, 7, 2, 2), "table": ("element", 2, 10, 3, 1),
    "jar": ("element", 2, 9, 1, 1), "plant": ("element", 0, 7, 1, 2), "curtain": ("element", 7, 9, 1, 1), "crate": ("element", 0, 0, 1, 1),
}


def _bake_room(case: dict) -> tuple[pygame.Surface, set[tuple[int, int]]]:
    """Ghép sẵn sàn, tường và đồ đạc thành một ảnh, đồng thời trả về các ô bị chắn."""
    room = pygame.Surface((W, H))
    room.fill(theme.LACQUER)
    floor = sprites.region("int_floor", *case["floor"])
    wx, wy = WALLS[case["wall"]]
    pieces = {
        "tl": (wx, wy), "tr": (wx + 4, wy), "bl": (wx, wy + 4), "br": (wx + 4, wy + 4),
        "t": (wx + 2, wy), "b": (wx + 2, wy + 4), "l": (wx, wy + 2), "r": (wx + 4, wy + 2),
    }
    wall = {k: sprites.region("int_wall", *v) for k, v in pieces.items()}
    solid: set[tuple[int, int]] = set()
    for y in range(ROWS):
        for x in range(COLS):
            pos = (OX + x * TILE, OY + y * TILE)
            room.blit(floor, pos)
            edge = None
            if y == 0:
                edge = "tl" if x == 0 else "tr" if x == COLS - 1 else "t"
            elif y == ROWS - 1 and x not in (DOOR[0], DOOR[0] + 1):
                edge = "bl" if x == 0 else "br" if x == COLS - 1 else "b"
            elif x == 0 and y < ROWS - 1:
                edge = "l"
            elif x == COLS - 1 and y < ROWS - 1:
                edge = "r"
            if edge:
                room.blit(wall[edge], pos)
                solid.add((x, y))
    for item in sorted(case["props"], key=lambda p: p["at"][1]):
        sheet, c, r, w, h = FURNITURE[item["name"]]
        x, y = item["at"]
        room.blit(sprites.region(sheet, c, r, w, h), (OX + x * TILE, OY + y * TILE))
        solid.update((x + i, y + h - 1) for i in range(w))
    return room, solid


class CaseScene(Scene):
    def __init__(self, app, case: dict):
        super().__init__(app)
        self.case = case
        self.room, self.solid = _bake_room(case)
        self.t = 0.0
        self.cast = outfit.hero_cast(self.state.gear)
        self.x, self.y = self._tile_px(DOOR[0], DOOR[1] - 1)
        self.facing = "up"
        self.frame = 0.0
        self.moving = False
        self.target: tuple[float, float] | None = None
        self.next = None
        self.note = case["intro"]
        self.clues = [dict(c, cast=sprites.cast(c["char"]) if c.get("char") else None, img=sprites.icon(c["icon"]) if c.get("icon") else None) for c in case["clues"]]
        self.group = ui.ButtonGroup()
        self.group.add(ui.Button((W - 150, 8, 136, 40), "Ra ngoài", self._leave, "ghost", size=15))
        self.stick = touch.Stick((104, H - 140))  # điện thoại: giữ cần để đi
        self.act_btn = ui.Button((W - 16 - 170, H - 150, 170, 60), "", None, "gold", size=16)  # điện thoại: xem, kết luận
        self._finger_btns = touch.FingerButtons()
        self.app.audio.ambient(None)

    @staticmethod
    def _tile_px(tx, ty):
        return OX + (tx + 0.5) * TILE, OY + (ty + 1) * TILE - 8

    def _found(self) -> list[int]:
        return self.state.case_clues.setdefault(self.case["id"], [])

    def _all_found(self) -> bool:
        return len(self._found()) >= len(self.clues)

    def _leave(self):
        self.app.scenes.pop(None)

    def _blocked(self, x, y) -> bool:
        for px, py in ((x - HIT, y - HIT / 2), (x + HIT, y - HIT / 2), (x - HIT, y + 2), (x + HIT, y + 2)):
            tile = (int((px - OX) // TILE), int((py - OY) // TILE))
            if tile in self.solid or not (0 <= tile[0] < COLS and 0 <= tile[1] < ROWS):
                return True
        return False

    def _near(self):
        """Thứ gần nhất trong tầm với: manh mối, bàn ghép manh mối hoặc cửa ra."""
        best, best_d = None, REACH ** 2
        for i, c in enumerate(self.clues):
            x, y = self._tile_px(*c["at"])
            d = (x - self.x) ** 2 + (y - self.y) ** 2
            if d < best_d:
                best, best_d = ("clue", i), d
        if self.case["id"] not in self.state.case_done:
            x, y = self._tile_px(*DESK)
            d = (x - self.x) ** 2 + (y - self.y) ** 2
            if d < best_d and self._all_found():
                best, best_d = ("desk", 0), d
        x, y = self._tile_px(DOOR[0], DOOR[1] - 1)
        x += TILE / 2
        if (x - self.x) ** 2 + (y - self.y) ** 2 < min(best_d, (TILE * 1.1) ** 2):
            best = ("door", 0)
        return best

    def _use(self, what):
        kind, i = what
        self.target = None
        if kind == "door":
            self._leave()
        elif kind == "clue":
            self._read(i)
        else:
            self.next = self._concluded
            self.app.scenes.push(QuestionScene(self.app, self.case["question"]))

    def _read(self, i):
        clue = self.clues[i]
        talk = {"id": self.case["id"], "nodes": [{"speaker": clue["title"], "portrait": "tu_lieu", "text": clue["text"], "cite": clue.get("cite")}]}
        self.next = lambda _r: self._clue_read(i)
        self.app.scenes.push(StoryScene(self.app, talk))

    def _clue_read(self, i):
        found = self._found()
        if i not in found:
            found.append(i)
            self.app.audio.play("nhan")
            self.state.save()
        total = len(self.clues)
        self.note = f"Đã xem {len(found)}/{total} manh mối." if len(found) < total else "Đủ manh mối rồi. Đến cái bàn ở giữa phòng để nêu kết luận."

    def _concluded(self, _result):
        st = self.state
        if self.case["id"] not in st.case_done:
            st.case_done.add(self.case["id"])
            st.save()
            self.app.toast(f"Xong vụ điều tra: {self.case['title']}. +{progression.SP_CASE} điểm kỹ năng", theme.GOLD_LIGHT, 4.0)
        self.note = self.case["outro"]

    def on_resume(self, result=None):
        self.stick.reset()
        cont, self.next = self.next, None
        if cont:
            cont(result)

    def _act_buttons(self) -> list:
        """Điện thoại: một nút to cho việc ở ngay cạnh (xem manh mối, nêu kết luận, ra ngoài)."""
        near = self._near() if self.app.scenes.touch else None
        if not near:
            return []
        self.act_btn.label = {"clue": "Xem", "desk": "Nêu kết luận", "door": "Ra ngoài"}[near[0]]
        self.act_btn.on_click = lambda n=near: self._use(n)
        return [self.act_btn]

    def handle(self, event):
        if event.type != pygame.KEYDOWN and self.group.handle(event):
            return
        scenes = self.app.scenes
        if scenes.touch and event.type in touch.FINGER_EVENTS + touch.MOUSE_EVENTS:
            if self.stick.handle(event, scenes.fingers):
                self.target = None
                return
            buttons = self._act_buttons()
            if scenes.fingers:
                if self._finger_btns.handle(event, buttons, True):
                    return
            elif any(b.handle(event) for b in buttons):
                return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._leave()
            elif event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
                near = self._near()
                if near:
                    self._use(near)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            near = self._near()
            if near:
                x, y = self._point_of(near)
                if (x - event.pos[0]) ** 2 + (y - TILE / 2 - event.pos[1]) ** 2 < TILE ** 2:
                    self._use(near)
                    return
            self.target = (float(event.pos[0]), float(event.pos[1]))

    def _point_of(self, what):
        kind, i = what
        if kind == "clue":
            return self._tile_px(*self.clues[i]["at"])
        if kind == "desk":
            return self._tile_px(*DESK)
        x, y = self._tile_px(DOOR[0], DOOR[1])
        return x + TILE / 2, y

    def update(self, dt):
        self.t += dt
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        if not (dx or dy) and self.stick.active:
            dx, dy = self.stick.vector()
        if dx or dy:
            self.target = None
        elif self.target:
            tx, ty = self.target[0] - self.x, self.target[1] - self.y
            if abs(tx) < 6 and abs(ty) < 6:
                self.target = None
            else:
                dx, dy = tx, ty
        self.moving = False
        length = (dx * dx + dy * dy) ** 0.5
        if length:
            step = SPEED * dt / max(1.0, length)  # cần điều khiển kéo chưa hết vòng thì đi chậm lại
            nx, ny = self.x + dx * step, self.y + dy * step
            if not self._blocked(nx, self.y):
                self.x = nx
                self.moving = True
            if not self._blocked(self.x, ny):
                self.y = ny
                self.moving = True
            if not self.moving:
                self.target = None
            self.facing = ("right" if dx > 0 else "left") if abs(dx) > abs(dy) else ("down" if dy > 0 else "up")
        self.frame = self.frame + dt * 8 if self.moving else 0.0

    def draw(self, screen):
        screen.blit(self.room, (0, 0))
        found = self._found()
        items = []
        for i, c in enumerate(self.clues):
            x, y = self._tile_px(*c["at"])
            if c["cast"]:
                img = c["cast"].walk["down"][0]
                items.append((y, img, x - TILE / 2, y - TILE + 8))
            else:
                bob = 0 if i in found else 3 * ui.pulse(self.t, 4)
                items.append((y, c["img"], x - c["img"].get_width() / 2, y - TILE + 8 + bob))
            if i not in found:
                mark = sprites.icon("ui/emote_question.png")
                screen.blit(mark, mark.get_rect(midbottom=(x, y - TILE - 2 + 3 * ui.pulse(self.t, 5))))
        items.append((self.y, self.cast.walk[self.facing][int(self.frame) % 4], self.x - TILE / 2, self.y - TILE + 8))
        for _y, img, x, y in sorted(items, key=lambda it: it[0]):
            screen.blit(img, (x, y))
        if self._all_found() and self.case["id"] not in self.state.case_done:
            x, y = self._tile_px(*DESK)
            mark = sprites.icon("ui/emote_alert.png")
            screen.blit(mark, mark.get_rect(midbottom=(x, y - TILE * 1.4 + 3 * ui.pulse(self.t, 5))))
        self._draw_hud(screen)

    def _draw_hud(self, screen):
        fonts.text(screen, self.case["title"], fonts.font("serif", 22), theme.GOLD_LIGHT, (OX, 14))
        ui.tag(screen, f"Manh mối {len(self._found())}/{len(self.clues)}", (OX + 460, 16))
        self.group.draw(screen)
        box = pygame.Rect(OX + 150, H - 62, COLS * TILE - 300, 54)
        ui.lacquer_panel(screen, box, 240)
        f = fonts.font("semi", 14)
        lines = fonts.wrap(self.note, f, box.w - 36)
        y = box.centery - len(lines) * f.get_linesize() / 2
        for line in lines[:2]:
            fonts.text(screen, line, f, theme.PAPER, (box.x + 18, y))
            y += f.get_linesize()
        near = self._near()
        if near:
            label = {"clue": "Xem", "desk": "Nêu kết luận", "door": "Ra ngoài"}[near[0]]
            x, y = self._point_of(near)
            key = "" if self.app.scenes.touch else "E  "
            ui.tag(screen, f"{key}{label}", (x, min(y + 6, H - 90)), theme.LACQUER, theme.GOLD_LIGHT, 13, "midtop")
        if self.app.scenes.touch:
            self.stick.draw(screen)
            for b in self._act_buttons():
                b.draw(screen)
