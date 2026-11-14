"""Võ đài: chọn đối thủ là bot, ôn bài lấy khí thế trước khi đấu. Đấu với người thật sẽ làm sau cùng backend."""

from __future__ import annotations

import random

import pygame
from core import fonts, progression, rpg, sprites, theme, ui
from core.scene import Scene

from scenes.fight import FightScene
from scenes.question import QuestionScene
from scenes.skills import SkillsScene

W, H = theme.WIDTH, theme.HEIGHT
LIST = pygame.Rect(30, 90, 740, 610)
SIDE = pygame.Rect(786, 90, 464, 610)
ROW_H = 64
QUIZ_BUFF = 1.15


class ArenaScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.group = ui.ButtonGroup()
        self.buff = 1.0
        self.pending = None
        self.quiz: dict | None = None
        self.msg = ""
        self._build()

    def _build(self):
        st = self.state
        self.group.clear()
        self.group.add(ui.Button((W - 150, 14, 136, 40), "Rời võ đài", lambda: self.app.scenes.pop(), "ghost", size=15))
        y = LIST.y + 14
        for bot in st.extras["arena"]:
            ok = st.arena_unlocked(bot)
            won = bot["id"] in st.arena_wins
            b = ui.Button((LIST.right - 140, y + 12, 122, 40), "Đấu lại" if won else "Thách đấu", None, "ghost" if won else "gold", ok, 14)
            b.on_click = lambda s=bot: self._fight(s)
            self.group.add(b)
            y += ROW_H
        x, w = SIDE.x + 22, SIDE.w - 44
        self.group.add(ui.Button((x, SIDE.y + 196, w, 50), "Kỹ năng và chỉ số", self._skills, "primary", size=16))
        can_quiz = bool(self._quiz_pool()) and self.buff == 1.0
        self.group.add(ui.Button((x, SIDE.y + 256, w, 50), "Ôn bài lấy khí thế (+15% sức mạnh)", self._warmup, "gold" if can_quiz else "ghost", can_quiz, 14))
        self.group.add(ui.Button((x, SIDE.y + 316, w, 50), "Đấu với người (sắp có)", None, "ghost", False, 15))

    def _quiz_pool(self):
        st = self.state
        return [st.index["questions"][q] for q in st.solved if q in st.index["questions"]]

    def _skills(self):
        self.app.scenes.push(SkillsScene(self.app))

    def _warmup(self):
        pool = self._quiz_pool()
        if not pool:
            return
        self.quiz = random.choice(pool)
        self.app.scenes.push(QuestionScene(self.app, self.quiz, review=True))

    def _fight(self, bot):
        self.pending = bot
        spec = {"name": bot["name"], "char": bot["char"], "hp": bot["hp"], "power": bot["power"], "speed": bot["speed"], "skills": bot.get("skills", []),
                "level": bot.get("level", 1), "aggro": bot.get("aggro", 0.5), "smart": bot.get("smart", 0.3), "style": bot.get("style", "melee"),
                "weapon": rpg.BOT_WEAPONS.get(bot["id"])}
        self.app.scenes.push(FightScene(self.app, [spec], bot["name"], "vo_dai", self.buff))

    def on_resume(self, result=None):
        self.app.audio.music("temple")
        if self.quiz is not None:
            self.quiz = None
            if result:
                self.buff = QUIZ_BUFF
                self.msg = "Khí thế dâng cao: trận tới được +15% sức mạnh."
            else:
                self.msg = "Chưa đúng. Ôn lại trong Sổ tay rồi thử câu khác nhé."
        elif self.pending is not None:
            bot, self.pending = self.pending, None
            self.buff = 1.0
            if isinstance(result, dict) and result.get("win"):
                if bot["id"] not in self.state.arena_wins:
                    self.state.arena_wins.add(bot["id"])
                    self.msg = f"Thắng {bot['name']} lần đầu: +1 điểm kỹ năng."
                    self.app.toast(self.msg, theme.GOLD_LIGHT, 3.5)
                else:
                    self.msg = f"Lại thắng {bot['name']}."
                self.state.save()
            elif isinstance(result, dict) and not result.get("quit"):
                self.msg = "Chưa thắng. Đi trả lời thêm câu hỏi để có điểm kỹ năng nhé."
        self._build()

    def on_enter(self):
        self.app.audio.music("temple")

    def handle(self, event):
        self.group.handle(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.pop()

    def draw(self, screen):
        st = self.state
        screen.fill(theme.LACQUER)
        fonts.text(screen, "VÕ ĐÀI", fonts.font("serif", 30), theme.GOLD_LIGHT, (30, 18))
        fonts.text(screen, "Mini game để thử sức. Muốn mạnh thì đi khám phá và trả lời lịch sử trước.", fonts.font("italic", 16), theme.PAPER_3, (160, 30))
        ui.paper_panel(screen, LIST, shadow=False)
        y = LIST.y + 14
        for bot in st.extras["arena"]:
            ok = st.arena_unlocked(bot)
            won = bot["id"] in st.arena_wins
            cast = sprites.cast(bot["char"], 3)
            img = cast.walk["down"][0]
            if not ok:
                img = sprites.sepia(img)
            screen.blit(img, (LIST.x + 18, y + 6))
            col = theme.INK if ok else theme.INK_FAINT
            title = bot["name"] + ("  (đã thắng)" if won else "")
            fonts.text(screen, title, fonts.font("bold", 16), col, (LIST.x + 80, y + 4))
            moves = ", ".join(progression.skill_info(s)["name"] for s in bot.get("skills", [])) or "chưa có chiêu"
            desc = fonts.wrap(bot["desc"], fonts.font("ui", 12), LIST.w - 250)[0]
            fonts.text(screen, desc + ("…" if desc != bot["desc"] else ""), fonts.font("ui", 12), theme.INK_SOFT, (LIST.x + 80, y + 25))
            if ok:
                fonts.text(screen, f"Máu {bot['hp']}, lực x{bot['power']:.2f}. Chiêu: {moves}", fonts.font("semi", 12), theme.INK_FAINT, (LIST.x + 80, y + 43))
            else:
                fonts.text(screen, st.arena_need_text(bot), fonts.font("semi", 12), theme.LACQUER_RED, (LIST.x + 80, y + 43))
            pygame.draw.line(screen, theme.PAPER_3, (LIST.x + 14, y + ROW_H - 3), (LIST.right - 14, y + ROW_H - 3))
            y += ROW_H
        ui.lacquer_panel(screen, SIDE, 240)
        x, w = SIDE.x + 22, SIDE.w - 44
        fonts.text(screen, "Sức mạnh của bạn", fonts.font("bold", 19), theme.GOLD_LIGHT, (x, SIDE.y + 18))
        rows = (f"Máu tối đa: {round(st.max_hp())}", f"Sát thương: x{st.damage_mult():.2f}", f"Tốc độ: x{st.speed_mult():.2f}", f"Hồi kỹ năng: x{st.cd_mult():.2f}")
        yy = SIDE.y + 52
        for row in rows:
            fonts.text(screen, row, fonts.font("semi", 15), theme.PAPER, (x, yy))
            yy += 24
        fonts.text(screen, f"Điểm kỹ năng còn: {st.skill_points_left()}", fonts.font("bold", 15), theme.GOLD, (x, yy + 4))
        if self.buff > 1.0:
            ui.tag(screen, "Khí thế +15%", (SIDE.right - 22, SIDE.y + 22), theme.JADE, theme.WHITE, 13, "topright")
        self.group.draw(screen)
        ix = x
        for sid in st.equipped_skills():
            screen.blit(sprites.icon(f"ui/sk_{sid}.png", 2), (ix, SIDE.y + 382))
            ix += 56
        if not st.equipped_skills():
            fonts.paragraph(screen, "Chưa có kỹ năng nào: mở trang Kỹ năng để học.", fonts.font("ui", 14), theme.PAPER_3, x, SIDE.y + 388, w, gap=1)
        fonts.paragraph(screen, self.msg, fonts.font("semi", 14), theme.GOLD_LIGHT, x, SIDE.y + 440, w, gap=2)
        fonts.paragraph(screen, "Đấu với người chơi khác sẽ mở khi nối máy chủ. Hiện tại bạn đấu với bot.", fonts.font("italic", 13), theme.PAPER_3, x, SIDE.bottom - 66, w, gap=1)
