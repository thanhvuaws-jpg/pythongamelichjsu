"""Thách đấu thật giữa hai người chơi: cả hai cùng được đưa tới võ đài, mỗi người tự điều khiển nhân vật của mình.

Mỗi máy chỉ điều khiển nhân vật của chính nó và gửi trạng thái (vị trí, hướng, máu, đang né, đang thủ) khoảng mười lăm lần mỗi
giây qua thế giới chung. Đối thủ trên máy mình là một cái bóng đi theo trạng thái đó, không có bộ não bot nào cả.

Đòn đánh: máy người ra đòn thấy đòn trúng cái bóng thì báo sang, máy bị đánh tự trừ máu của mình, nên né và thế thủ vẫn có
tác dụng. Chiêu của cái bóng vẽ ra trên máy mình chỉ để nhìn, không tự trừ máu. Máy chủ phân xử khi có người gục, rút lui, rời
game hay hết giờ (ai còn nhiều máu hơn thì thắng) và ghi kết quả cho cả hai.
"""

from __future__ import annotations

import math
import random
from types import SimpleNamespace

import pygame
from core import fonts, net, theme, ui, weapons

from scenes.fight import BTN_EAT, BTN_POTION, BURN_TIME, DODGE_TIME, FIELD, SLOW_TIME, FightScene, W

SEND_EVERY = 1 / 15
LERP = 14.0  # cái bóng đuổi theo vị trí đối thủ gửi sang
SNAP = 200  # lệch xa hơn thế (lao tới, đột kích) thì nhảy tới luôn
QUIET = 12.0  # bấy nhiêu giây không nghe thấy đối thủ thì coi như mất liên lạc
WAIT_KO = 4.0  # đã gục: chờ máy chủ báo kết quả bấy nhiêu giây
WAIT_TIME = 9.0  # hết giờ: máy chủ chốt sau tám giây dự phòng
FIRE_TICK = 6.0  # vùng lửa cộng dồn sát thương tới bấy nhiêu rồi mới báo một lần
PUSH_R = 130  # Hào khí hất lùi người đứng gần trong bán kính này
DIRS = ("up", "down", "left", "right")


def _num(v, lo: float, hi: float, default: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(x) else max(lo, min(hi, x))


def duel_spec(vs: dict) -> dict:
    """Hình dáng đối thủ trên máy mình: mặc đúng đồ, cầm đúng vũ khí, đúng máu và kỹ năng họ đang trang bị."""
    c = vs.get("combat") or {}
    gear = vs.get("gear") or {}
    w = gear.get("vu_khi")
    skills = c.get("skills") or {}
    return {
        "name": f"{vs.get('name', 'Đối thủ')} (cấp {vs.get('lv', 1)})", "char": "Villager", "outfit": gear,
        "hp": c.get("hp", 100), "power": c.get("dmg", 1.0), "speed": round(250 * c.get("spd", 1.0)), "skills": list(skills),
        "level": max(skills.values(), default=1), "weapon": w,
        "style": "ranged" if w and weapons.style(w)["move"] == "shoot" else "melee",
    }


class PvpScene(FightScene):
    """`start` là tin pvp_start của máy chủ; `done(result)` được gọi sau khi rời võ đài."""

    def __init__(self, app, start: dict, done=None):
        vs = start.get("vs") if isinstance(start.get("vs"), dict) else {}
        self.vs = vs
        self.room = str(start.get("room", ""))
        self.side = 1 if start.get("side") == 1 else 0
        self.done = done
        self.net = net.get()
        self._applying = False  # đang trừ máu theo đòn máy đối thủ báo sang
        super().__init__(app, [duel_spec(vs)], f"Thách đấu {vs.get('name', '')}", "vo_dai",
                         time_limit=round(_num(start.get("time"), 20, 300, 90)))
        self.ghost = self.foes[0]
        p, g = self.player, self.ghost
        left, right = FIELD.x + 170, FIELD.right - 170
        p.x, g.x = (left, right) if self.side == 0 else (right, left)
        p.y = g.y = FIELD.centery
        p.facing, g.facing = ("right", "left") if self.side == 0 else ("left", "right")
        p.px, p.py, g.px, g.py = p.x, p.y, g.x, g.y
        self.target = (g.x, g.y)
        self.send_t = 0.0
        self.out_ev: list[dict] = []  # động tác vừa làm, gửi kèm trạng thái
        self.out_hits: list[dict] = []  # đòn vừa trúng cái bóng trong khung hình này
        self.quiet = 0.0
        self.wait: float | None = None  # đã gục hoặc hết giờ: chờ máy chủ phân xử
        self.why = ""
        self.draw_game = False

    # ----- nhận tin -----
    def _receive(self, dt: float):
        self.net.poll()
        self.quiet += dt
        for m in self.net.take_duel(self.room):
            self.quiet = 0.0
            kind = m.get("t")
            if kind == "pvp":
                self._remote_state(m)
            elif kind == "pvp_hit":
                self._apply_hit(m)
            elif kind == "pvp_over":
                self._close(bool(m.get("win")), bool(m.get("draw")), str(m.get("why", "")))
        if self.quiet > QUIET and not self.result:
            self._close(False, True, "lost")

    def _remote_state(self, m: dict):
        s = m.get("s") if isinstance(m.get("s"), dict) else {}
        g = self.ghost
        x, y = _num(s.get("x"), FIELD.left, FIELD.right, g.x), _num(s.get("y"), FIELD.top, FIELD.bottom, g.y)
        self.target = (x, y)
        if math.hypot(x - g.x, y - g.y) > SNAP:
            g.x, g.y = x, y
        if s.get("f") in DIRS:
            g.facing = s["f"]
        g.moving = bool(s.get("m"))
        g.max_hp = _num(s.get("mhp"), 1, 100000, g.max_hp)
        g.hp = _num(s.get("hp"), 0, g.max_hp, g.hp)
        g.dead = g.hp <= 0
        g.dodge_t = max(g.dodge_t, 0.12) if s.get("dg") else 0.0
        g.shield_t = max(g.shield_t, 0.15) if s.get("sh") else 0.0
        if s.get("rd"):
            g.ride_t = max(g.ride_t, 0.15)
        for e in m.get("ev") if isinstance(m.get("ev"), list) else ():
            self._replay(e)

    def _replay(self, e):
        """Vẽ lại động tác đối thủ vừa làm. Chỉ để nhìn: đòn thật do máy đối thủ báo sang."""
        g = self.ghost
        if not isinstance(e, dict) or g.dead or self.result:
            return
        kind = e.get("k")
        if kind == "atk":
            g.attack_cd = 0.0
            dodge, g.dodge_t = g.dodge_t, 0.0
            self.attack(g)
            g.dodge_t = dodge
        elif kind == "cast" and isinstance(e.get("sid"), str) and hasattr(self, f"_sk_{e['sid']}"):
            sid = e["sid"]
            g.skills.setdefault(sid, 1)
            g.cds[sid] = 0.0
            self.cast(g, sid)
            g.charge = None  # vị trí do máy đối thủ gửi sang, không tự lao
            g.dash = (0.0, 0.0)
        elif kind == "dodge":
            g.dodge_t = DODGE_TIME

    def _apply_hit(self, m: dict):
        """Đòn của đối thủ trúng mình (theo máy họ thấy): tự trừ máu, né và thế thủ vẫn được tính."""
        p = self.player
        if p.dead or self.result or self.wait is not None:
            return
        dodged = p.dodge_t > 0
        dmg, knock = _num(m.get("dmg"), 0, 400, 0), _num(m.get("knock"), 0, 120, 0)
        src = SimpleNamespace(x=_num(m.get("sx"), 0, 2000, p.x), y=_num(m.get("sy"), 0, 2000, p.y))
        if dmg > 0:
            self._applying = True
            try:
                self._hurt(p, dmg, src, knock)
            finally:
                self._applying = False
        elif knock and not dodged:
            dx, dy = p.x - src.x, p.y - src.y
            d = max(1.0, math.hypot(dx, dy))
            p.x += dx / d * knock
            p.y += dy / d * knock
            self._clamp(p)
        if m.get("burn") and not dodged:
            p.burn_t = BURN_TIME
        if m.get("slow"):
            p.slow_t = max(p.slow_t, SLOW_TIME)
            theirs = [tr for tr in self.traps if tr["team"] != p.team]
            if theirs:  # chông của đối thủ mình vừa giẫm phải: bỏ khỏi sân
                self.traps.remove(min(theirs, key=lambda tr: (tr["x"] - p.x) ** 2 + (tr["y"] - p.y) ** 2))

    # ----- đòn trúng cái bóng: báo sang máy đối thủ -----
    def _hurt(self, target, amount, source=None, knock=0.0):
        if target is self.ghost:
            self._hit_ghost(amount, source, knock)
        elif self._applying:
            super()._hurt(target, amount, source, knock)
        # còn lại là chiêu của cái bóng chạm vào mình: chỉ để nhìn, máu thật do máy đối thủ báo sang

    def _hit_ghost(self, amount, source, knock):
        g = self.ghost
        if g.dead or g.dodge_t > 0 or amount <= 0 or self.wait is not None:
            return
        shown = amount * (0.25 if g.shield_t > 0 else 1.0)
        g.hurt_t = 0.18
        self._pop(str(max(1, round(shown))), g.x + random.randint(-14, 14), g.y - 76, (255, 230, 120))
        self.fx.blood(g.x, g.y - 30, 10)
        self.fx.shake(3 if shown < 15 else 6)
        self.app.audio.play("trung")
        src = source if source is not None else self.player
        self._send_hit(amount, knock, src.x, src.y)

    def _send_hit(self, dmg, knock, sx, sy, **flags):
        self.out_hits.append({"dmg": round(dmg, 1), "knock": round(knock), "sx": round(sx), "sy": round(sy), **flags})

    def _flush_hits(self):
        """Gắn bỏng, chậm (mũi lửa, chông) vào đòn vừa trúng rồi gửi đi. Cái bóng không tự cháy, tự chậm trên máy mình."""
        g, p = self.ghost, self.player
        for key, attr in (("burn", "burn_t"), ("slow", "slow_t")):
            if getattr(g, attr) > 0:
                setattr(g, attr, 0.0)
                if self.out_hits:
                    self.out_hits[-1][key] = True
                else:
                    self._send_hit(0, 0, p.x, p.y, **{key: True})
        for h in self.out_hits:
            self.net.send({"t": "pvp_hit", "room": self.room, **h})
        self.out_hits = []

    # ----- động tác của mình: gửi kèm trạng thái để máy đối thủ vẽ lại -----
    def attack(self, f):
        cd = f.attack_cd
        super().attack(f)
        if f is self.player and f.attack_cd != cd:
            self.out_ev.append({"k": "atk", "a": round(f.shot_angle, 3)})

    def cast(self, f, sid):
        ok = super().cast(f, sid)
        if ok and f is self.player:
            self.out_ev.append({"k": "cast", "sid": sid})
        return ok

    def dodge(self, f, dx=0.0, dy=0.0):
        cd = f.dodge_cd
        super().dodge(f, dx, dy)
        if f is self.player and f.dodge_cd != cd:
            self.out_ev.append({"k": "dodge"})

    def _sk_hao_khi(self, f, target, k, lvl):
        """Hào khí hất lùi người đứng gần: cú hất lên đối thủ phải báo sang; cái bóng hô thì mình không tự bị hất."""
        p, g = self.player, self.ghost
        keep = (p.x, p.y) if f is g else (g.x, g.y)
        super()._sk_hao_khi(f, target, k, lvl)
        if f is g:
            p.x, p.y = keep
            return
        g.x, g.y = keep
        if not g.dead and (g.x - f.x) ** 2 + (g.y - f.y) ** 2 < PUSH_R ** 2:
            self._send_hit(0, 70, f.x, f.y)

    def _step_fires(self, dt):
        """Vùng lửa của mình đốt cái bóng thì báo sang theo từng đợt; lửa của cái bóng chỉ để nhìn."""
        g = self.ghost
        for z in list(self.fires):
            z["t"] -= dt
            if random.random() < dt * 30:
                self.fx.fire(z["x"] + random.uniform(-60, 60), z["y"] + random.uniform(-20, 20), 1, 10)
            if z["team"] == self.player.team and not g.dead and (g.x - z["x"]) ** 2 / 70 ** 2 + (g.y - z["y"]) ** 2 / 36 ** 2 <= 1:
                z["acc"] = z.get("acc", 0.0) + z["dps"] * dt
                if z["acc"] >= FIRE_TICK:
                    self._pop(str(round(z["acc"])), g.x, g.y - 76, (255, 180, 90))
                    self._send_hit(z["acc"], 0, z["x"], z["y"])
                    z["acc"] = 0.0
            if z["t"] <= 0:
                self.fires.remove(z)

    def _step_traps(self, dt):
        """Chỉ chông của mình mới bắt được cái bóng; chông của đối thủ do máy họ thấy mình giẫm phải rồi báo sang."""
        g = self.ghost
        for tr in list(self.traps):
            tr["t"] += dt
            if tr["team"] != self.player.team or tr["t"] < 0.4 or g.dead:
                continue
            if (g.x - tr["x"]) ** 2 + (g.y - tr["y"]) ** 2 < 36 ** 2:
                self._hurt(g, tr["dmg"], tr["src"])
                g.slow_t = SLOW_TIME
                self._pop("Dính chông!", g.x, g.y - 100, (255, 200, 120))
                self.traps.remove(tr)

    def _bot(self, f, dt):
        if f is not self.ghost:
            super()._bot(f, dt)
            return
        k = min(1.0, dt * LERP)
        f.x += (self.target[0] - f.x) * k
        f.y += (self.target[1] - f.y) * k

    # ----- thuốc, đồ ăn: không dùng khi thách đấu -----
    def drink(self) -> bool:
        self.app.toast("Thách đấu không dùng thuốc hay đồ ăn: hai bên đánh bằng sức mình.", theme.PAPER, 2.5)
        return False

    def eat(self) -> bool:
        return self.drink()

    # ----- vòng lặp -----
    def update(self, dt):
        self._receive(dt)
        if self.result:
            super().update(dt)
            return
        if self.wait is not None:  # đã gục hoặc hết giờ: chỉ chờ máy chủ báo kết quả
            self.t += dt
            if self.background:
                self.background(dt)
            self.fx.update(dt)
            for pop in self.pops:
                pop[2] -= 44 * dt
                pop[3] -= dt
            self.pops = [q for q in self.pops if q[3] > 0]
            self.wait -= dt
            if self.wait <= 0:
                self._close(False, True, "lost")
            self._send_state(dt)
            return
        p = self.player
        burn, slow = p.burn_t, p.slow_t
        super().update(dt)
        # chiêu của cái bóng (mũi lửa, chông, sóng) chạm vào mình chỉ để nhìn: bỏ bỏng, chậm mà nó vừa gây ra trên máy mình
        p.burn_t, p.slow_t = min(p.burn_t, burn), min(p.slow_t, slow)
        self._flush_hits()
        self._send_state(dt)

    def _send_state(self, dt: float):
        self.send_t -= dt
        if self.send_t > 0:
            return
        self.send_t = SEND_EVERY
        p = self.player
        s = {"x": round(p.x), "y": round(p.y), "f": p.facing, "m": p.moving, "hp": round(p.hp, 1), "mhp": round(p.max_hp),
             "dg": p.dodge_t > 0, "sh": p.shield_t > 0, "rd": p.ride_t > 0}
        ev, self.out_ev = self.out_ev[:6], self.out_ev[6:]
        self.net.send({"t": "pvp", "room": self.room, "s": s, "ev": ev})

    def _check_end(self):
        if self.result or self.wait is not None:
            return
        if self.player.dead:
            self.net.send({"t": "pvp_dead", "room": self.room})
            self.wait = WAIT_KO
        elif self.left <= 0:
            self.wait = WAIT_TIME

    def _close(self, win: bool, draw: bool, why: str):
        if self.result:
            return
        self.wait = None
        self.why, self.draw_game = why, draw
        self._end(win and not draw)
        self.result.update({"draw": draw, "why": why, "pvp": True})

    def _quit(self):
        if not self.result:
            self.net.send({"t": "pvp_quit", "room": self.room})
        self._leave(self.result or {"win": False, "quit": True, "pvp": True})

    def _finish(self):
        self._leave(self.result)

    def _leave(self, result):
        # Rời võ đài không trả kết quả cho cảnh bên dưới: cảnh đó có thể là túi đồ, câu hỏi... đang chờ việc riêng của nó
        self.app.scenes.pop()
        if self.done:
            self.done(result)

    # ----- vẽ -----
    def draw(self, screen):
        super().draw(screen)
        if not self.result:
            ui.tag(screen, "Đấu thật với người chơi", (W // 2 - 70, 70), theme.LACQUER_RED, theme.GOLD_LIGHT, 13, "midtop")
        if self.wait is not None and not self.result:
            fonts.text(screen, "Đang chờ máy chủ báo kết quả...", fonts.font("bold", 24), theme.WHITE, (W // 2, 330), "center",
                       shadow=(24, 16, 14))

    def _draw_controls(self, screen):
        super()._draw_controls(screen)
        for r in (BTN_POTION, BTN_EAT):
            ui.alpha_rect(screen, r.inflate(-8, -8), (10, 8, 8, 200))
            fonts.text(screen, "không dùng", fonts.font("semi", 12), theme.PAPER_3, r.center, "center")

    def result_text(self) -> tuple[str, str]:
        name = self.vs.get("name") or "Đối thủ"
        win = bool(self.result and self.result.get("win"))
        if self.why == "lost":
            return "TRẬN DỪNG", "Mất liên lạc với đối thủ hoặc máy chủ nên trận này không tính. Hẹn đấu lại nhé."
        if self.draw_game:
            return "HÒA", "Hết giờ, hai bên còn máu ngang nhau."
        if self.why == "quit":
            return ("CHIẾN THẮNG", f"{name} đã rút lui. Bạn thắng trận thách đấu.") if win else ("THUA TRẬN", "Bạn đã rút lui.")
        if self.why == "left":
            return "CHIẾN THẮNG", f"{name} đã rời game. Bạn thắng trận thách đấu."
        if self.why == "time":
            return ("CHIẾN THẮNG", "Hết giờ, bạn còn nhiều máu hơn nên thắng.") if win else (
                "THUA TRẬN", f"Hết giờ, {name} còn nhiều máu hơn. Luyện thêm rồi hẹn đấu lại nhé.")
        return ("CHIẾN THẮNG", f"Bạn đã hạ {name} trong trận thách đấu.") if win else (
            "THUA TRẬN", f"{name} đã hạ bạn. Lên cấp, mua đồ ở lò rèn, học thêm chiêu rồi hẹn đấu lại nhé.")

    def _draw_result(self, screen):
        ui.veil(screen, (10, 6, 4, 150))
        rect = pygame.Rect(W // 2 - 280, 190, 560, 360)
        ui.paper_panel(screen, rect)
        title, msg = self.result_text()
        win = title == "CHIẾN THẮNG"
        fonts.text(screen, title, fonts.font("black", 40), theme.LACQUER_RED if win else theme.INK_SOFT, (rect.centerx, rect.y + 44), "center")
        img = self.player.cast.attack["down"] if win else (self.player.cast.walk["down"][0] if title != "THUA TRẬN" else self.player.cast.dead)
        screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + 130)))
        fonts.paragraph(screen, msg, fonts.font("serif", 18), theme.INK_SOFT, rect.x + 40, rect.y + 186, rect.w - 80, gap=3)
