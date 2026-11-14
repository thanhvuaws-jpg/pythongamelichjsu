"""Hội thoại trong thế giới và hồi ức: đoạn thường hiện hộp thoại đè lên map, đoạn `memory` chuyển sang cảnh pixel nâu cũ.

Hồi ức có hiệu ứng chiến trận theo thẻ `fx` (lính giao đấu, lửa, khói, máu). Lời do nhóm sáng tác luôn có nhãn
"Lời dẫn hư cấu"; đoạn dựa trên tư liệu hiện dòng nguồn (Req 4.2, 14).
"""

from __future__ import annotations

import random

import pygame
from core import diorama, fonts, fx, sprites, theme, ui
from core.cinematic import TideMemory, TurtleMemory
from core.scene import Scene
from core.stage import Stage

BOX = pygame.Rect(36, 492, 1208, 208)
CHARS_PER_SEC = 46
BLIP_EVERY = 8  # mấy chữ thì phát một tiếng lẩm bẩm
# Lời dẫn đầu, lời kết và các đoạn kể thêm không phải hồi ức của di tích nên không cho tinh hoa
NO_ESSENCE = (None, "extra", "d_intro", "d_outro")


class StoryScene(Scene):
    opaque = False

    def __init__(self, app, dialogue: dict, topics_only: list | None = None):
        super().__init__(app)
        self.dialogue = dialogue
        self.queue: list[dict] = list(dialogue.get("nodes", []))
        if topics_only is not None:
            self.queue = [{"topics": topics_only, "exit": "Cảm ơn, tôi hiểu rồi",
                           "speaker": dialogue.get("speaker", ""), "portrait": dialogue.get("portrait", "tu_lieu"),
                           "text": dialogue.get("prompt", "Cháu muốn hỏi thêm điều gì?"), "fiction": True}]
        self.pos = -1
        self.node: dict = {}
        self.fx = fx.Fx(self.state.settings["violence"], old=True)
        self.ambient = fx.Ambient(self.fx)
        self.bg_name = dialogue.get("bg", "lang_co")
        self.memory = False
        self.cine: TideMemory | TurtleMemory | Stage | None = None
        self.t = 0.0
        self.chars = 0.0
        self.flash = 0.0
        self.topic_buttons = ui.ButtonGroup()
        self.skip = ui.Button((1100, 16, 164, 40), "Bỏ qua", self._finish, "ghost", size=16)
        self.topic_stack: list[list[dict]] = []
        self.finished = False
        self._saved_pos = None
        self._advance()

    # ----- điều hướng đoạn truyện -----
    def _advance(self):
        if self.topic_stack and self.pos + 1 >= len(self.queue):
            self.queue, self.pos = self.topic_stack.pop(), self._saved_pos - 1
        self.pos += 1
        if self.pos >= len(self.queue):
            self._finish()
            return
        self.node = self.queue[self.pos]
        self.chars = 0.0
        was_memory = self.memory
        self.memory = bool(self.node.get("memory"))
        self.opaque = self.memory
        self.bg_name = self.node.get("bg", self.bg_name)
        if self.memory != was_memory:
            self.flash = 0.4
        self.ambient.ground = diorama.GROUND.get(self.bg_name, diorama.DEFAULT_GROUND)
        self.ambient.set(self.node.get("fx") if self.memory else None)
        beat = self.node.get("cine")
        stage = self.node.get("stage") if self.memory else None
        if stage:
            # Cảnh tự diễn lo phần giao tranh; hiệu ứng nền chỉ còn mưa, khói, nhịp trống để khỏi vẽ lính ngẫu nhiên
            if not isinstance(self.cine, Stage):
                self.cine = Stage(self.fx, self.app.audio)
            self.cine.set_beat(stage)
            self.ambient.set([k for k in self.node.get("fx", []) if k in ("rain", "smoke", "drum")])
            self.ambient.ground = None
        elif beat in TurtleMemory.BEATS:
            if not isinstance(self.cine, TurtleMemory):
                self.cine = TurtleMemory(self.fx)
            self.cine.set_beat(beat)
        elif beat:
            if not isinstance(self.cine, TideMemory):
                self.cine = TideMemory(self.fx, self.app.audio, bool(self.node.get("cine_dark")))
            self.cine.set_beat(beat)
        else:
            self.cine = None
        if self.node.get("shake"):
            self.fx.shake(self.node["shake"])
        if self.node.get("clue"):
            self.state.clues[self.node["clue"]["id"]] = self.node["clue"]["text"]
            self.app.toast(f"Manh mối mới: {self.node['clue']['text']}", theme.JADE_LIGHT)
        self.state.add_notebook(self.node.get("unlock"))
        self.topic_buttons.clear()
        if self.node.get("fx") and "drum" in self.node["fx"]:
            self.app.audio.play("trong")

    def _build_topics(self):
        self.topic_buttons.clear()
        topics = self.node.get("topics", [])
        total = len(topics) + 1
        h = 54
        y = max(70, BOX.top - 14 - total * (h + 8))
        for tp in topics:
            needs = tp.get("needs")
            ok = not needs or needs in self.state.progress.collected_fragments or needs in self.state.clues
            done = tp["id"] in self.state.done_topics
            label = tp["label"] if ok else "(Khoá) " + tp.get("locked_hint", "Cần thêm manh mối")
            b = ui.Button((BOX.right - 720, y, 720, h), label, None, "ghost" if done else "paper", ok, 16, tp)
            b.on_click = lambda t=tp: self._open_topic(t)
            self.topic_buttons.add(b)
            y += h + 8
        self.topic_buttons.add(ui.Button((BOX.right - 720, y, 720, h), self.node.get("exit", "Đi tiếp"), self._topic_exit, "primary", size=17))

    def _open_topic(self, tp):
        self.state.done_topics.add(tp["id"])
        self.app.audio.play("click")
        self._saved_pos = self.pos
        self.topic_stack.append(self.queue)
        self.queue = list(tp["lines"])
        self.pos = -1
        self._advance()

    def _topic_exit(self):
        self.app.audio.play("click")
        self._saved_pos = None
        self.node = {}
        self._advance()

    def _finish(self):
        if self.finished:
            return
        self.finished = True
        self.state.add_notebook(self.dialogue.get("unlocks"))
        if any(n.get("memory") for n in self.dialogue.get("nodes", [])) and self.dialogue.get("id") not in NO_ESSENCE:
            self.state.remember(self.dialogue["id"])
        self.state.save()
        self.app.scenes.pop(True)

    # ----- vòng lặp -----
    def _text_len(self):
        return len(fonts.nfc(self.node.get("text", "")))

    def _text_done(self):
        return self.chars >= self._text_len()

    def handle(self, event):
        if self.skip.handle(event):
            return
        if self.node.get("topics") and self._text_done():
            if not self.topic_buttons.buttons:
                self._build_topics()
            self.topic_buttons.handle(event)
            return
        go = (event.type == pygame.MOUSEBUTTONUP and event.button == 1) or (
            event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e)
        )
        if go:
            if not self._text_done():
                self.chars = self._text_len()
            else:
                self.app.audio.play("click")
                self._advance()

    def update(self, dt):
        self.t += dt
        speed = CHARS_PER_SEC * self.state.settings.get("text_speed", 1.0)
        before = int(self.chars / BLIP_EVERY)
        self.chars = min(self._text_len(), self.chars + speed * dt)
        if not self.memory and int(self.chars / BLIP_EVERY) != before and not self._text_done():
            # Mỗi kiểu nhân vật một giọng lẩm bẩm riêng khi chữ đang chạy
            self.app.audio.play("giong" + str(1 + sum(map(ord, self.node.get("portrait", ""))) % 4))
        self.flash = max(0.0, self.flash - dt)
        self.ambient.update(dt)
        if self.cine:
            self.cine.update(dt)
        self.fx.update(dt)
        if self.node.get("topics") and self._text_done() and not self.topic_buttons.buttons:
            self._build_topics()

    def draw(self, screen):
        if self.memory:
            self._draw_memory(screen)
        if self.flash > 0:
            ui.veil(screen, (255, 240, 210, int(255 * self.flash / 0.4)))
        self._draw_box(screen)
        self.topic_buttons.draw(screen)
        self.skip.draw(screen)

    def _draw_memory(self, screen):
        screen.fill(theme.LACQUER)
        if self.cine:
            self.cine.draw(screen, self.fx.offset())
        else:
            screen.blit(diorama.old(self.bg_name), self.fx.offset())
        self.ambient.draw(screen)
        self.fx.draw(screen)
        for _ in range(3):  # vết xước phim cũ
            x = random.randint(0, theme.WIDTH)
            pygame.draw.line(screen, (240, 220, 180), (x, 0), (x + random.randint(-2, 2), theme.HEIGHT), 1)

    def _draw_box(self, screen):
        node = self.node
        if not node:
            return
        ui.lacquer_panel(screen, BOX, 246)
        x = BOX.x + 22
        text_x = x
        if node.get("portrait"):
            screen.blit(sprites.portrait(node["portrait"], 3), (x, BOX.y + 30))
            text_x = x + 164
        width = BOX.right - text_x - 28
        y = BOX.y + 20
        if node.get("speaker"):
            r = fonts.text(screen, node["speaker"], fonts.font("bold", 20), theme.GOLD_LIGHT, (text_x, y))
            tx = r.right + 12
        else:
            tx = text_x
        if self.memory:
            label = "TRUYỀN THUYẾT" if self.dialogue.get("legend") else "HỒI ỨC"
            tx = ui.tag(screen, label, (tx, y + 2), theme.GOLD_DARK, theme.WHITE).right + 8
        if node.get("fiction"):
            ui.tag(screen, "Lời dẫn hư cấu", (tx, y + 2), theme.LACQUER_2, theme.PAPER_3)
        fonts.paragraph(
            screen, node.get("text", ""), fonts.font("serif", 21), theme.PAPER, text_x, y + 34, width, gap=5,
            max_chars=int(self.chars),
        )
        cite = self.state.citation_text(node.get("cite"))
        if cite and self._text_done():
            lines = fonts.wrap("Nguồn: " + cite, fonts.font("italic", 13), width - 60)[:2]
            yy = BOX.bottom - 16 - len(lines) * 18
            for line in lines:
                fonts.text(screen, line, fonts.font("italic", 13), theme.PAPER_3, (text_x, yy))
                yy += 18
        if self._text_done() and not node.get("topics") and ui.pulse(self.t, 5) > 0.3:
            ax, ay = BOX.right - 34, BOX.bottom - 30
            pygame.draw.polygon(screen, theme.GOLD, [(ax - 10, ay - 7), (ax + 10, ay - 7), (ax, ay + 7)])
