"""Trang kỹ năng và tu luyện.

Chỉ số (sức đánh, thể lực, nhanh nhẹn, trí tuệ) mua bằng tiềm năng kiếm khi đánh quái, làm nhiệm vụ. Kỹ năng học bằng
điểm kỹ năng chỉ có khi học sử. Khung cảnh giới cho biết cấp tối đa hiện tại và tinh hoa cần để đột phá.
"""

from __future__ import annotations

import pygame
from core import fonts, progression, rpg, sprites, theme, ui
from core.scene import Scene

W, H = theme.WIDTH, theme.HEIGHT
LEFT = pygame.Rect(30, 112, 500, 590)
RIGHT = pygame.Rect(544, 112, 706, 590)
STAT_H = 76
SKILL_H = 52
REALM = pygame.Rect(LEFT.x + 14, LEFT.y + 444, LEFT.w - 28, 132)


class SkillsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.group = ui.ButtonGroup()
        self.t = 0.0
        self._build()

    def _build(self):
        self.group.clear()
        st = self.state
        self.group.add(ui.Button((W - 150, 14, 136, 40), "Đóng", lambda: self.app.scenes.pop(), "ghost", size=15))
        y = LEFT.y + 48
        for sid in progression.STATS:
            lv = st.stat_levels.get(sid, 0)
            ok = st.tiem_nang >= st.stat_cost(sid) and lv < progression.STAT_MAX
            b = ui.Button((LEFT.right - 66, y + 12, 44, 44), "+", None, "gold" if ok else "ghost", ok, 22)
            b.on_click = lambda s=sid: self._up_stat(s)
            self.group.add(b)
            y += STAT_H
        if st.next_realm():
            ok = st.can_break()
            self.group.add(ui.Button((REALM.right - 132, REALM.bottom - 50, 118, 40), "Đột phá", self._break, "gold" if ok else "ghost", ok, 15))
        y = RIGHT.y + 10
        for sid in progression.SKILLS:
            lv = st.skill_levels.get(sid, 0)
            unlocked = st.skill_unlocked(sid)
            cost = progression.skill_cost(lv + 1)
            can = unlocked and lv < progression.SKILL_MAX and st.skill_points_left() >= cost
            label = "Đã tối đa" if lv >= progression.SKILL_MAX else (f"Học ({cost})" if lv == 0 else f"Nâng ({cost})")
            b = ui.Button((RIGHT.right - 204, y + 7, 100, 38), label, None, "gold" if can else "ghost", can, 13)
            b.on_click = lambda s=sid: self._up_skill(s)
            self.group.add(b)
            if lv > 0:
                equipped = sid in st.equipped_skills()
                e = ui.Button((RIGHT.right - 98, y + 7, 86, 38), "Đang dùng" if equipped else "Trang bị", None, "jade" if equipped else "ghost", True, 12)
                e.on_click = lambda s=sid: self._toggle(s)
                self.group.add(e)
            y += SKILL_H

    def _up_stat(self, sid):
        if self.state.upgrade_stat(sid):
            self.app.audio.play("nang")
        self._build()

    def _up_skill(self, sid):
        if self.state.upgrade_skill(sid):
            self.app.audio.play("nang")
        self._build()

    def _break(self):
        if self.state.breakthrough():
            self.app.audio.play("thang")
            for msg in self.state.events:
                self.app.toast(msg, theme.GOLD_LIGHT, 4.0)
            self.state.events.clear()
        self._build()

    def _toggle(self, sid):
        self.state.toggle_equip(sid)
        self.app.audio.play("click")
        self._build()

    def handle(self, event):
        self.group.handle(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q, pygame.K_k):
            self.app.scenes.pop()

    def update(self, dt):
        self.t += dt

    def draw(self, screen):
        st = self.state
        screen.fill(theme.LACQUER)
        fonts.text(screen, "TU LUYỆN", fonts.font("serif", 28), theme.GOLD_LIGHT, (30, 16))
        left = st.skill_points_left()
        x = 220
        for text, bg in ((f"Điểm kỹ năng: {left}", theme.LACQUER_RED if left else theme.LACQUER_2),
                         (f"Tiềm năng: {st.tiem_nang}", theme.LACQUER_2), (f"Cấp {st.level} · {st.realm_name()}", theme.LACQUER_2)):
            r = ui.tag(screen, text, (x, 22), bg, theme.GOLD_LIGHT, 17)
            x = r.right + 12
        msg = ("Tiềm năng có khi đánh quái, thắng thách đấu, về báo cáo già làng. Điểm kỹ năng chỉ có khi học sử: trả lời đúng "
               "ngay lần đầu, đóng dấu di tích, khám phá, điều tra, ghép tư liệu.")
        fonts.paragraph(screen, msg, fonts.font("ui", 14), theme.PAPER_3, 30, 64, W - 200, gap=0)
        ui.paper_panel(screen, LEFT, shadow=False)
        ui.paper_panel(screen, RIGHT, shadow=False)
        self._draw_stats(screen)
        self._draw_realm(screen)
        self._draw_skills(screen)
        self.group.draw(screen)

    def _draw_stats(self, screen):
        st = self.state
        x = LEFT.x + 20
        fonts.text(screen, "Chỉ số (mua bằng tiềm năng)", fonts.font("bold", 18), theme.INK, (x, LEFT.y + 14))
        y = LEFT.y + 48
        for sid, info in progression.STATS.items():
            lv = st.stat_levels.get(sid, 0)
            screen.blit(sprites.icon(info["icon"], 2), (x, y + 6))
            head = f"{info['name']}: {lv}/{progression.STAT_MAX}"
            fonts.text(screen, head, fonts.font("bold", 15), theme.INK, (x + 58, y))
            if lv < progression.STAT_MAX:
                cost = st.stat_cost(sid)
                col = theme.JADE if st.tiem_nang >= cost else theme.LACQUER_RED
                fonts.text(screen, f"cần {cost} tiềm năng", fonts.font("semi", 12), col, (LEFT.right - 76, y + 4), "topright")
            fonts.paragraph(screen, info["desc"], fonts.font("ui", 12), theme.INK_SOFT, x + 58, y + 21, LEFT.w - 170, gap=0)
            ui.progress_bar(screen, (x + 58, y + 58, LEFT.w - 170, 6), lv / progression.STAT_MAX, theme.GOLD, theme.PAPER_3)
            y += STAT_H
        f = fonts.font("semi", 13)
        fonts.text(screen, f"Máu tối đa: {round(st.max_hp())}", f, theme.INK, (x, y + 2))
        fonts.text(screen, f"Sát thương: x{st.damage_mult():.2f}", f, theme.INK, (x, y + 20))
        fonts.text(screen, f"Tốc độ: x{st.speed_mult():.2f}", f, theme.INK, (x + 170, y + 2))
        fonts.text(screen, f"Hồi kỹ năng: x{st.cd_mult():.2f}", f, theme.INK, (x + 170, y + 20))
        fonts.text(screen, f"Sức mạnh: {st.power_rating()}", fonts.font("bold", 14), theme.LACQUER_RED, (x + 340, y + 10))

    def _draw_realm(self, screen):
        st = self.state
        ui.alpha_rect(screen, REALM, (120, 70, 40, 34), 10)
        pygame.draw.rect(screen, theme.GOLD, REALM, 2, 10)
        x, y = REALM.x + 14, REALM.y + 10
        fonts.text(screen, f"Cảnh giới: {st.realm_name()}", fonts.font("serif", 19), theme.LACQUER_RED, (x, y))
        need = rpg.exp_need(st.level)
        capped = st.level >= st.level_cap()
        exp = "đã tới giới hạn" if capped else f"{st.exp}/{need} kinh nghiệm"
        fonts.text(screen, f"Cấp {st.level}/{st.level_cap()} · {exp}", fonts.font("semi", 13), theme.INK, (x, y + 28))
        ui.progress_bar(screen, (x, y + 48, REALM.w - 28, 7), 1.0 if capped else st.exp / need, theme.JADE, theme.PAPER_3)
        nxt = st.next_realm()
        if nxt is None:
            fonts.text(screen, "Đã ở cảnh giới cao nhất.", fonts.font("ui", 13), theme.INK_SOFT, (x, y + 64))
            return
        ess = st.essence()
        fonts.text(screen, f"Tinh hoa: {ess}/{nxt['need']} để lên {nxt['name']}", fonts.font("bold", 14), theme.INK, (x, y + 62))
        tip = ("Đủ điều kiện, bấm Đột phá!" if st.can_break() else
               "Tinh hoa có khi chìm vào hồi ức, khám phá, ghép tư liệu, điều tra; cần đạt cấp tối đa rồi mới đột phá.")
        fonts.paragraph(screen, tip, fonts.font("ui", 12), theme.INK_SOFT, x, y + 84, REALM.w - 170, gap=0)

    def _draw_skills(self, screen):
        st = self.state
        x = RIGHT.x + 14
        y = RIGHT.y + 10
        for sid, sk in progression.SKILLS.items():
            lv = st.skill_levels.get(sid, 0)
            unlocked = st.skill_unlocked(sid)
            icon = sprites.icon(f"ui/sk_{sid}.png", 2)
            if not unlocked:
                icon = sprites.sepia(icon)
            screen.blit(icon, (x, y + 2))
            col = theme.INK if unlocked else theme.INK_FAINT
            name = sk["name"] + (f"  (cấp {lv})" if lv else "")
            r = fonts.text(screen, name, fonts.font("bold", 15), col, (x + 56, y))
            if not unlocked:
                need = progression.needs_text(sk["needs"]) + f" (có {st.need_progress(sk['needs'])})"
                fonts.text(screen, need, fonts.font("semi", 12), theme.LACQUER_RED, (r.right + 10, y + 3))
            fonts.paragraph(screen, sk["desc"], fonts.font("ui", 12), theme.INK_SOFT, x + 56, y + 19, RIGHT.w - 290, gap=0)
            y += SKILL_H
            if y < RIGHT.bottom - 8:
                pygame.draw.line(screen, theme.PAPER_3, (x, y - 3), (RIGHT.right - 14, y - 3))
