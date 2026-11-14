"""Đối kháng thời gian thực: dùng cho võ đài đấu bot và giao tranh trên map.

Đi bằng WASD hoặc phím mũi tên, bấm chuột trái để chém (giữ chuột thì chém liên tục, phím cách cũng chém được), Shift để
né, 1 đến 4 để tung kỹ năng. Giữ chuột phải để đi theo con trỏ; trên điện thoại thì chạm giữ để đi tới, bấm các nút dưới màn
hình để đánh. Lực chiến lấy từ chỉ số và kỹ năng kiếm được khi học sử.
"""

from __future__ import annotations

import math
import random

import pygame
from core import (
    art,
    chienma,
    diorama,
    fonts,
    fx,
    mobart,
    outfit,
    progression,
    rpg,
    sprites,
    theme,
    ui,
    weapons,
)
from core.scene import Scene

W, H = theme.WIDTH, theme.HEIGHT
FIELD = pygame.Rect(90, 150, 1100, 440)
BODY = 26
REACH = 92
ATTACK_CD = 0.42
ATTACK_DMG = 9.0
DODGE_CD = 1.3
DODGE_TIME = 0.22
DODGE_SPEED = 720
BASE_SPEED = 250
TIME_LIMIT = 75
COUNTDOWN = 2.4
BURN_DPS = 3.0
BURN_TIME = 3.0
SLOW_TIME = 1.6
MAX_TRAPS = 3
RAIN_DELAY = 0.95
RAIN_R = 62
WAVE_SPEED = 430
WAVE_MAX = 380
CHARGE_SPEED = 900
# Khoảng cách bot muốn giữ theo lối đánh
PREFER = {"melee": REACH * 0.8, "tank": REACH * 0.75, "assassin": REACH * 0.7, "ranged": 300}
BTN_ATTACK = pygame.Rect(W - 150, H - 112, 130, 96)
BTN_DODGE = pygame.Rect(W - 276, H - 88, 112, 72)
BTN_POTION = pygame.Rect(W - 392, H - 88, 104, 72)
BTN_EAT = pygame.Rect(W - 504, H - 88, 104, 72)
SLOT_W = 104


class _StaticCast:
    """Đối thủ là công trình (lô cốt): mọi khung hình là cùng một ảnh, khi bị phá thì thành đống đổ nát."""

    def __init__(self, img: pygame.Surface, ruin: pygame.Surface):
        self.walk = {d: [img] * 4 for d in ("down", "up", "left", "right")}
        self.attack = dict.fromkeys(("down", "up", "left", "right"), img)
        self.dead = ruin
        self.size = img.get_height()


def _bunker_cast(scale: int) -> _StaticCast:
    """Lô cốt bê tông có lỗ châu mai, vẽ ở độ phân giải thấp."""
    low = pygame.Surface((30, 20), pygame.SRCALPHA)
    pygame.draw.ellipse(low, (24, 22, 18), (0, 4, 30, 18))
    pygame.draw.ellipse(low, (128, 132, 120), (1, 5, 28, 16))
    pygame.draw.ellipse(low, (160, 164, 150), (5, 6, 18, 6))
    pygame.draw.rect(low, (14, 12, 10), (10, 11, 10, 3))
    for x, y in ((4, 6), (24, 8), (14, 5)):  # bao cát
        pygame.draw.ellipse(low, (150, 130, 96), (x - 3, y - 2, 7, 4))
    ruin = pygame.Surface((30, 20), pygame.SRCALPHA)
    for x, y, r in ((6, 15, 5), (14, 13, 6), (23, 15, 5), (18, 17, 4)):
        pygame.draw.circle(ruin, (24, 22, 18), (x, y), r + 1)
        pygame.draw.circle(ruin, (110, 112, 102), (x, y), r)
    return _StaticCast(sprites.scaled(low, scale), sprites.scaled(ruin, scale))


STATIC_CASTS = {"LoCot": _bunker_cast}


class Fighter:
    def __init__(self, name, char, x, y, hp, power, speed, team, skills=None, level=1, scale=4):
        self.name, self.team = name, team
        self.char = char
        if char in STATIC_CASTS:
            self.cast = STATIC_CASTS[char](scale)
        elif mobart.has(char):  # kỵ binh, xe tăng, ụ súng
            self.cast = mobart.cast(char, scale)
        else:
            self.cast = sprites.cast(char, scale)
        self.anchored = char in STATIC_CASTS or getattr(self.cast, "anchored", False)  # công trình, cỗ máy không bị đẩy lùi
        self.x, self.y = float(x), float(y)
        self.max_hp = self.hp = float(hp)
        self.power, self.speed = power, speed
        self.skills: dict[str, int] = skills or {}
        self.level = level
        self.cds: dict[str, float] = {}
        self.cd_mult = 1.0
        self.facing = "down"
        self.moving = False
        self.frame = 0.0
        self.attack_cd = 0.0
        self.attack_t = 0.0
        self.dodge_cd = 0.0
        self.dodge_t = 0.0
        self.dash = (0.0, 0.0)
        self.hurt_t = 0.0
        self.shield_t = 0.0
        self.burn_t = 0.0
        self.slow_t = 0.0
        self.dead = False
        # dành cho bot
        self.windup = 0.0
        self.pending = None
        self.think = random.uniform(0.2, 0.6)
        self.strafe = random.choice((-1, 1))
        self.style = "melee"
        self.smart = 0.3
        self.aggro = 0.6
        self.aim = (0.0, 0.0)
        self.combo = 0
        self.combo_t = 0.0
        self.hidden_t = 0.0
        self.charge: dict | None = None
        self.vx = self.vy = 0.0
        self.px, self.py = self.x, self.y
        self.volley_n = 0  # số mũi tên Nỏ liên châu còn phải bắn
        self.volley_t = 0.0
        self.rage_t = 0.0  # Hào khí
        self.base = (power, speed)
        self.ride_t = 0.0  # đang cưỡi chiến mã lao tới
        self.weapon: str | None = None  # mã vũ khí đang cầm, vẽ và vung theo loại
        self.shot_angle = 0.0


class FightScene(Scene):
    """`foes` là danh sách mô tả đối thủ; kết thúc trả về {"win": bool} cho scene đã mở nó."""

    def __init__(self, app, foes: list[dict], title: str, scene: str = "vo_dai", buff: float = 1.0, time_limit: int = TIME_LIMIT,
                 backdrop: pygame.Surface | None = None):
        super().__init__(app)
        self.background = None  # hàm gọi mỗi khung hình khi trận đang che map (gửi vị trí cho người cùng map)
        self.foe_spec, self.title, self.scene_name, self.buff = foes, title, scene, buff
        self.time_limit = time_limit
        st = self.state
        self.fx = fx.Fx(st.settings["violence"])
        if backdrop is not None:  # đánh ngay trên map: lấy chính khung cảnh đang đứng làm sân đấu
            self.bg = backdrop.copy()
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((20, 12, 8, 70))
            self.bg.blit(shade, (0, 0))
            self.bg.blit(art.vignette(), (0, 0))
        else:
            self.bg = diorama.scene(scene)
        self.fires: list[dict] = []  # vùng lửa Hoả công
        self.world = pygame.Surface((W, H))
        self.t = 0.0
        self.left = float(time_limit)
        self.intro = COUNTDOWN
        self.result: dict | None = None
        self.shots: list[dict] = []
        self.traps: list[dict] = []
        self.zones: list[dict] = []  # vòng mưa tên báo trước
        self.waves: list[dict] = []  # sóng chấn địa
        self.pops: list[list] = []
        self.player = Fighter(
            "Bạn", "SamuraiBlue", FIELD.x + 170, FIELD.centery, st.max_hp(), st.damage_mult() * buff,
            BASE_SPEED * st.speed_mult(), 0, {s: st.skill_levels.get(s, 1) for s in st.equipped_skills()},
        )
        self.player.cd_mult = st.cd_mult()
        self.player.cast = outfit.hero_cast(st.gear, 4)  # mặc gì thì ra trận trông như thế
        self.player.weapon = st.gear.get("vu_khi")
        self.foes = self._make_foes(foes)
        self.fighters = [self.player, *self.foes]
        self.group = ui.ButtonGroup()
        self.group.add(ui.Button((W - 130, 12, 116, 36), "Rút lui", self._quit, "ghost", size=14))
        self.slots = list(self.player.skills)
        self.slot_rects = [pygame.Rect(16 + i * (SLOT_W + 10), H - 92, SLOT_W, 78) for i in range(progression.SLOTS)]
        self.mouse_down = False  # đang giữ chuột phải (hay chạm giữ trên điện thoại) để đi theo con trỏ
        self.move_button = 0
        self.attack_held = False  # đang giữ chuột trái trên sân: chém liên tục theo nhịp hồi đòn
        self.mouse = (0, 0)
        self.app.audio.music("fight")
        self.app.audio.ambient(None)

    def _make_foes(self, specs):
        foes = []
        for i, sp in enumerate(specs):
            x = FIELD.right - 170 - (i % 2) * 90
            y = FIELD.centery + (i - (len(specs) - 1) / 2) * 92
            f = Fighter(sp["name"], sp["char"], x, y, sp["hp"], sp.get("power", 1.0), sp.get("speed", 190), 1,
                        dict.fromkeys(sp.get("skills", ()), sp.get("level", 1)), sp.get("level", 1), sp.get("scale", 4))
            f.facing = "left"
            f.aggro = sp.get("aggro", 0.6)
            f.smart = sp.get("smart", 0.3)
            f.style = sp.get("style", "melee")
            f.weapon = sp.get("weapon")
            if sp.get("outfit") is not None:  # người chơi khác khi thách đấu: mặc đúng đồ của họ
                f.cast = outfit.hero_cast(sp["outfit"], sp.get("scale", 4))
            foes.append(f)
        return foes

    def _quit(self):
        self.app.scenes.pop({"win": False, "quit": True})

    def drink(self) -> bool:
        """Uống một bát thuốc nam: hồi một phần máu. Hết thuốc thì mua thêm ở lò rèn."""
        p = self.player
        if p.dead or self.intro > 0 or self.result or p.hp >= p.max_hp or not self.state.use_potion():
            return False
        heal = p.max_hp * rpg.POTION_HEAL
        p.hp = min(p.max_hp, p.hp + heal)
        self._pop(f"+{round(heal)}", p.x, p.y - 100, (140, 230, 140))
        self.app.audio.play("nhan")
        self.state.save()
        return True

    def eat(self) -> bool:
        """Ăn một xiên cá nướng tự câu, tự nướng: hồi ít máu hơn thuốc nam."""
        p = self.player
        if p.dead or self.intro > 0 or self.result or p.hp >= p.max_hp or not self.state.eat_fish():
            return False
        heal = p.max_hp * rpg.GRILL_HEAL
        p.hp = min(p.max_hp, p.hp + heal)
        self._pop(f"+{round(heal)}", p.x, p.y - 100, (240, 200, 120))
        self.app.audio.play("nhan")
        self.state.save()
        return True

    # ----- tiện ích -----
    def _alive_foes(self, who):
        return [f for f in self.fighters if f.team != who.team and not f.dead]

    def _nearest(self, who):
        foes = self._alive_foes(who)
        return min(foes, key=lambda f: (f.x - who.x) ** 2 + (f.y - who.y) ** 2) if foes else None

    @staticmethod
    def _dir_name(dx, dy):
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        return "down" if dy > 0 else "up"

    def _clamp(self, f):
        f.x = max(FIELD.left, min(FIELD.right, f.x))
        f.y = max(FIELD.top, min(FIELD.bottom, f.y))

    def _pop(self, text, x, y, color=theme.WHITE):
        self.pops.append([text, x, y, 0.8, color])

    def _hurt(self, target, amount, source=None, knock=0.0):
        if target.dead or target.dodge_t > 0:
            return
        if target.shield_t > 0:
            amount *= 0.25
            self.app.audio.play("kiem")
        target.hp -= amount
        target.hurt_t = 0.18
        self._pop(str(max(1, round(amount))), target.x + random.randint(-14, 14), target.y - 76, (255, 230, 120) if target.team else (255, 150, 130))
        self.fx.blood(target.x, target.y - 30, 10)
        self.fx.shake(3 if amount < 15 else 6)
        self.app.audio.play("trung")
        if source is not None and knock and not getattr(target, "anchored", False):
            dx, dy = target.x - source.x, target.y - source.y
            d = max(1.0, math.hypot(dx, dy))
            target.x += dx / d * knock
            target.y += dy / d * knock
            self._clamp(target)
        if target.hp <= 0:
            target.hp = 0.0
            target.dead = True
            self.fx.blood(target.x, target.y - 30, 26)
            self.fx.fall(target.x, target.y - 30)
            self.app.audio.play("no")

    # ----- đòn đánh, né -----
    def attack(self, f):
        if f.dead or f.attack_cd > 0 or f.dodge_t > 0 or self.intro > 0 or self.result:
            return
        st = weapons.style(f.weapon)
        f.attack_cd = st["cd"]
        f.attack_t = st["time"]
        target = self._nearest(f)
        if target:
            f.facing = self._dir_name(target.x - f.x, target.y - f.y)
        move, kind = st["move"], weapons.kind(f.weapon)
        if move == "shoot":  # cung, nỏ: bắn mũi tên bay thật về phía đối thủ
            if target:
                f.shot_angle = math.atan2(target.y - f.y, target.x - f.x)
            else:
                f.shot_angle = -math.radians(weapons.FACING_ANGLE[f.facing])
            self._shoot(f, weapons.arrow(f.weapon), f.shot_angle, st["speed"], ATTACK_DMG * f.power * st["dmg"], hit="spark")
            self.app.audio.play("ban")
            return
        ox, oy = {"left": (-52, -24), "right": (52, -24), "up": (0, -62), "down": (0, 10)}[f.facing]
        flip = f.facing == "left"
        if move == "cleave":  # đại đao bổ rộng
            self.fx.play("fx/circle_slash.png", 4, f.x, f.y - 30, 16, flip, 5)
            self.fx.shake(4)
        elif move == "thrust":  # giáo đâm thẳng
            self.fx.play("fx/cut.png", 4, f.x + ox * 1.4, f.y + oy, 22, flip, 3)
        elif kind in ("kiem", "bao_kiem"):
            self.fx.play("fx/slash_double.png", 4, f.x + ox, f.y + oy, 20, flip, 3)
        elif kind == "gay":
            self.fx.play("fx/cut_double.png", 5, f.x + ox, f.y + oy, 20, flip, 3)
        else:
            self.fx.play("fx/curved.png", 4, f.x + ox, f.y + oy, 18, flip, 3)
        self.app.audio.play("chem")
        reach = REACH * st["reach"]
        for g in self._alive_foes(f):
            if (g.x - f.x) ** 2 + (g.y - f.y) ** 2 <= reach ** 2:
                self._hurt(g, ATTACK_DMG * f.power * st["dmg"], f, 22 * st["knock"])
                self._hit_fx(kind, g)

    def _hit_fx(self, kind, g):
        """Hiệu ứng riêng khi vũ khí trúng người."""
        x, y = g.x, g.y - 34
        if kind == "gay":
            self.fx.burst(x, y, 8, [(150, 98, 56), (190, 136, 84), (232, 214, 150)], 220, 0.45, 4, 400)
        elif kind == "dai_dao":
            self.fx.burst(x, y + 26, 10, [(120, 96, 70), (160, 130, 96)], 200, 0.5, 5, 500, up=True)
            self.fx.shake(7)
        elif kind == "bao_kiem":
            self.fx.burst(x, y, 14, [(255, 226, 120), (255, 246, 200), (240, 180, 60)], 280, 0.45, 3, 120, kind="spark")
        elif kind in ("dao", "kiem", "giao"):
            self.fx.burst(x, y, 7, [(255, 246, 220), (220, 232, 255)], 240, 0.3, 3, 260, kind="spark")

    def _reach(self, f) -> float:
        """Tầm ra đòn thường: cung nỏ bắn từ xa, giáo với dài hơn."""
        return REACH * weapons.style(f.weapon)["reach"]

    def dodge(self, f, dx=0.0, dy=0.0):
        if f.dead or f.dodge_cd > 0 or self.intro > 0 or self.result or f.anchored:
            return
        if not (dx or dy):
            dx, dy = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}[f.facing]
        d = max(0.01, math.hypot(dx, dy))
        f.dash = (dx / d * DODGE_SPEED, dy / d * DODGE_SPEED)
        f.dodge_t, f.dodge_cd = DODGE_TIME, DODGE_CD
        self.app.audio.play("ban")

    # ----- kỹ năng -----
    def cast(self, f, sid):
        lvl = f.skills.get(sid)
        if lvl is None or f.dead or f.cds.get(sid, 0) > 0 or self.intro > 0 or self.result:
            return False
        target = self._nearest(f)
        if target is None:
            return False
        base = progression.skill_info(sid)["cd"]
        f.cds[sid] = base * f.cd_mult * (1 - 0.08 * (lvl - 1))
        f.attack_t = 0.28
        f.facing = self._dir_name(target.x - f.x, target.y - f.y)
        getattr(self, f"_sk_{sid}")(f, target, 1 + 0.3 * (lvl - 1), lvl)
        return True

    def _shoot(self, f, img, angle, speed, dmg, burn=False, hit="boom"):
        vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
        frames = img if isinstance(img, list) else [img]
        turned = [pygame.transform.rotate(i, -math.degrees(angle)) for i in frames]
        self.shots.append({"x": f.x, "y": f.y - 30, "vx": vx, "vy": vy, "frames": turned, "dmg": dmg, "team": f.team, "src": f,
                           "burn": burn, "life": 1.6, "hit": hit})

    def _sk_phong_lao(self, f, target, k, _lvl):
        angle = math.atan2(target.y - f.y, target.x - f.x)
        lance = pygame.transform.rotate(sprites.icon("fx/lance.png", 3), -90)
        self._shoot(f, lance, angle, 820, 16 * k * f.power)
        self.app.audio.play("ban")

    def _sk_ten_lua(self, f, target, k, _lvl):
        angle = math.atan2(target.y - f.y, target.x - f.x)
        balls = sprites.strip("fx/fireball.png", 4, 3)
        for off in (-0.26, 0, 0.26):
            self._shoot(f, balls, angle + off, 560, 8 * k * f.power, True)
        self.app.audio.play("lua")

    def _sk_dot_kich(self, f, target, k, _lvl):
        dx, dy = target.x - f.x, target.y - f.y
        d = max(1.0, math.hypot(dx, dy))
        reach = min(d - 30, 300)
        f.x += dx / d * reach
        f.y += dy / d * reach
        self._clamp(f)
        f.dash = (0.0, 0.0)
        f.dodge_t = 0.1
        self.fx.play("fx/cutx.png", 4, target.x, target.y - 30, 16, False, 4)
        self.fx.shake(5)
        self.app.audio.play("chem")
        if (target.x - f.x) ** 2 + (target.y - f.y) ** 2 < (REACH + 20) ** 2:
            self._hurt(target, 15 * k * f.power, f, 40)

    def _sk_xoay_kiem(self, f, _target, k, _lvl):
        self.fx.play("fx/circle_slash.png", 4, f.x, f.y - 30, 14, False, 7)
        self.fx.shake(6)
        self.app.audio.play("kiem")
        for g in self._alive_foes(f):
            if (g.x - f.x) ** 2 + (g.y - f.y) ** 2 <= 150 ** 2:
                self._hurt(g, 14 * k * f.power, f, 60)

    def _sk_the_thu(self, f, _target, _k, lvl):
        f.shield_t = 1.6 + 0.5 * lvl
        self.app.audio.play("phep")

    def _sk_hoi_khi(self, f, _target, k, _lvl):
        amount = f.max_hp * 0.16 * k
        f.hp = min(f.max_hp, f.hp + amount)
        self.fx.play("fx/boost.png", 8, f.x, f.y - 40, 14, False, 3)
        self._pop(f"+{round(amount)}", f.x, f.y - 90, theme.JADE_LIGHT)
        self.app.audio.play("hoi")

    def _sk_chong_ngam(self, f, _target, k, _lvl):
        own = [tr for tr in self.traps if tr["team"] == f.team]
        if len(own) >= MAX_TRAPS:
            self.traps.remove(own[0])
        self.traps.append({"x": f.x, "y": f.y, "team": f.team, "src": f, "dmg": 12 * k * f.power, "t": 0.0})
        self.app.audio.play("va")

    # ----- chiêu riêng của bot: chiêu nào cũng có dấu hiệu để người chơi kịp né -----
    def _sk_mua_ten(self, f, target, k, _lvl):
        """Đánh dấu ba vòng tròn quanh chỗ đối thủ sắp tới, chưa đầy một giây sau tên trút xuống."""
        lead = 0.5 + 0.4 * f.smart
        cx, cy = target.x + target.vx * lead, target.y + target.vy * lead
        for i in range(3):
            a = i * 2.1 + random.uniform(-0.4, 0.4)
            rr = 0 if i == 0 else random.uniform(60, 110)
            x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
            x = max(FIELD.x + 20, min(FIELD.right - 20, x))
            y = max(FIELD.y + 20, min(FIELD.bottom - 10, y))
            self.zones.append({"x": x, "y": y, "t": 0.0, "dmg": 10 * k * f.power, "team": f.team, "src": f})
        self.app.audio.play("ban")

    def _sk_chan_dia(self, f, _target, k, _lvl):
        """Dậm đất: sóng chấn động lan ra thành vòng; né lúc sóng đi qua thì không sao."""
        self.waves.append({"x": f.x, "y": f.y, "r": 30.0, "hit": set(), "dmg": 13 * k * f.power, "team": f.team, "src": f})
        self.fx.shake(7)
        self.fx.burst(f.x, f.y - 6, 18, [(150, 120, 80), (110, 88, 60)], 260, 0.5, 5, 400)
        self.app.audio.play("no")

    def _sk_lien_hoan(self, f, _target, _k, _lvl):
        f.combo, f.combo_t = 3, 0.0

    def _sk_phi_tieu(self, f, target, k, _lvl):
        lead = 0.25 * f.smart
        angle = math.atan2(target.y + target.vy * lead - f.y, target.x + target.vx * lead - f.x)
        dart = sprites.icon("fx/arrow.png", 3)
        for off in (-0.12, 0.12):
            self._shoot(f, dart, angle + off, 900, 6 * k * f.power)
        self.app.audio.play("ban")

    def _sk_khoi_mu(self, f, target, _k, _lvl):
        """Ném khói rồi biến mất, hiện ra sau lưng đối thủ và chém ngay."""
        self.fx.smoke(f.x, f.y - 30, 14, 40)
        dx, dy = f.x - target.x, f.y - target.y
        d = max(1.0, math.hypot(dx, dy))
        f.x, f.y = target.x - dx / d * 70, target.y - dy / d * 70
        self._clamp(f)
        f.hidden_t = 0.55
        f.combo, f.combo_t = 1, 0.6
        self.app.audio.play("phep")

    def _sk_xung_phong(self, f, _target, k, _lvl):
        """Lao thẳng theo hướng đã ngắm lúc lấy đà, đi qua ai thì người đó trúng."""
        dx, dy = f.aim[0] - f.x, f.aim[1] - f.y
        d = max(1.0, math.hypot(dx, dy))
        f.charge = {"vx": dx / d * CHARGE_SPEED, "vy": dy / d * CHARGE_SPEED, "t": min(0.48, (d + 80) / CHARGE_SPEED), "hit": False, "dmg": 16 * k * f.power}
        self.app.audio.play("ban")

    # ----- kỹ năng mới của người chơi (bot cũng dùng được) -----
    def _sk_no_lien_chau(self, f, _target, _k, _lvl):
        f.volley_n, f.volley_t = 5, 0.0

    def _sk_hoa_cong(self, f, target, k, _lvl):
        """Vùng lửa đặt giữa mình và đối thủ, cháy trong bốn giây."""
        dx, dy = target.x - f.x, target.y - f.y
        d = max(1.0, math.hypot(dx, dy))
        reach = min(d, 160)
        self.fires.append({"x": f.x + dx / d * reach, "y": f.y + dy / d * reach, "t": 4.0, "dps": 9 * k * f.power, "team": f.team, "src": f})
        self.app.audio.play("lua")

    def _sk_hao_khi(self, f, _target, _k, lvl):
        """Hô vang khí thế: tăng sức và tốc độ, hất lùi đối thủ ở sát bên."""
        if f.rage_t <= 0:
            f.power, f.speed = f.base[0] * (1.3 + 0.05 * lvl), f.base[1] * 1.2
        f.rage_t = 6.0
        self._pop("Hào khí!", f.x, f.y - 100, (255, 214, 120))
        self.fx.play("fx/boost.png", 8, f.x, f.y - 40, 14, False, 3)
        self.fx.shake(4)
        self.app.audio.play("trong")
        for g in self._alive_foes(f):
            if (g.x - f.x) ** 2 + (g.y - f.y) ** 2 < 130 ** 2 and not getattr(g, "anchored", False):
                dx, dy = g.x - f.x, g.y - f.y
                d = max(1.0, math.hypot(dx, dy))
                g.x += dx / d * 70
                g.y += dy / d * 70
                self._clamp(g)

    def _sk_phi_ma(self, f, target, k, _lvl):
        """Chiến mã phi thẳng về phía đối thủ, húc ngã mọi người trên đường."""
        dx, dy = target.x - f.x, target.y - f.y
        d = max(1.0, math.hypot(dx, dy))
        f.charge = {"vx": dx / d * 1000, "vy": dy / d * 1000, "t": min(0.5, (d + 120) / 1000), "hit": False, "dmg": 18 * k * f.power, "multi": set()}
        f.ride_t = f.charge["t"] + 0.15
        f.dodge_t = f.charge["t"]  # đang phi thì không trúng đòn
        self.app.audio.play("ban")

    def _step_volley(self, f, dt):
        if f.volley_n <= 0 or f.dead:
            return
        f.volley_t -= dt
        if f.volley_t > 0:
            return
        target = self._nearest(f)
        f.volley_n -= 1
        f.volley_t = 0.09
        if target is None:
            return
        angle = math.atan2(target.y - f.y, target.x - f.x) + random.uniform(-0.05, 0.05)
        lvl = f.skills.get("no_lien_chau", 1)
        self._shoot(f, sprites.icon("fx/arrow.png", 3), angle, 900, 6 * (1 + 0.3 * (lvl - 1)) * f.power)
        self.app.audio.play("ban")

    def _step_fires(self, dt):
        for z in list(self.fires):
            z["t"] -= dt
            if random.random() < dt * 30:
                self.fx.fire(z["x"] + random.uniform(-60, 60), z["y"] + random.uniform(-20, 20), 1, 10)
            for g in self.fighters:
                if g.team != z["team"] and not g.dead and (g.x - z["x"]) ** 2 / 70 ** 2 + (g.y - z["y"]) ** 2 / 36 ** 2 <= 1:
                    g.hp -= z["dps"] * dt * (0.25 if g.shield_t > 0 else 1.0)
                    if random.random() < dt * 3:
                        self._pop(str(max(1, round(z["dps"] / 3))), g.x, g.y - 76, (255, 180, 90))
                    if g.hp <= 0:
                        g.hp = 0.0
                        g.dead = True
            if z["t"] <= 0:
                self.fires.remove(z)

    def _step_combo(self, f, dt):
        if f.combo <= 0 or f.dead:
            return
        f.combo_t -= dt
        if f.combo_t > 0:
            return
        target = self._nearest(f)
        f.combo -= 1
        f.combo_t = 0.2
        if target is None:
            return
        dx, dy = target.x - f.x, target.y - f.y
        d = max(1.0, math.hypot(dx, dy))
        step = min(36.0, max(0.0, d - REACH * 0.6))
        f.x += dx / d * step
        f.y += dy / d * step
        self._clamp(f)
        f.attack_cd = 0.0
        self.attack(f)

    def _step_charge(self, f, dt):
        c = f.charge
        if not c or f.dead:
            return
        c["t"] -= dt
        f.x += c["vx"] * dt
        f.y += c["vy"] * dt
        self._clamp(f)
        f.moving = True
        f.facing = self._dir_name(c["vx"], c["vy"])
        if random.random() < dt * 30:
            self.fx.burst(f.x, f.y - 4, 2, [(160, 130, 90)], 80, 0.4, 4, 200)
        if "multi" in c:  # Phi mã: húc mọi người trên đường, mỗi người một lần
            for g in self._alive_foes(f):
                if id(g) not in c["multi"] and (g.x - f.x) ** 2 + (g.y - f.y) ** 2 < (BODY * 2 + 20) ** 2:
                    c["multi"].add(id(g))
                    self._hurt(g, c["dmg"], f, 90)
        elif not c["hit"]:
            for g in self._alive_foes(f):
                if (g.x - f.x) ** 2 + (g.y - f.y) ** 2 < (BODY * 2 + 10) ** 2:
                    c["hit"] = True
                    self._hurt(g, c["dmg"], f, 70)
                    break
        if c["t"] <= 0:
            f.charge = None

    def _step_zones(self, dt):
        for z in list(self.zones):
            z["t"] += dt
            if z["t"] < RAIN_DELAY:
                continue
            self.fx.volley(z["x"] - 140, z["y"] - 260, z["x"], z["y"] - 10, 6, 40, 900)
            self.fx.burst(z["x"], z["y"], 8, [(150, 120, 80)], 140, 0.4, 4, 300)
            for f in self.fighters:
                if f.team != z["team"] and not f.dead and (f.x - z["x"]) ** 2 + (f.y - z["y"]) ** 2 < RAIN_R ** 2:
                    self._hurt(f, z["dmg"], z["src"])
            self.zones.remove(z)

    def _step_waves(self, dt):
        for w in list(self.waves):
            w["r"] += WAVE_SPEED * dt
            for f in self.fighters:
                if f.team == w["team"] or f.dead or id(f) in w["hit"]:
                    continue
                d = math.hypot(f.x - w["x"], f.y - w["y"])
                if abs(d - w["r"]) < 26:
                    w["hit"].add(id(f))
                    if f.dodge_t <= 0:
                        self._hurt(f, w["dmg"], w["src"], 50)
                        f.slow_t = max(f.slow_t, 0.8)
            if w["r"] > WAVE_MAX:
                self.waves.remove(w)

    # ----- bot -----
    def _incoming(self, f):
        """Viên đạn của đối thủ đang bay về phía mình và sẽ trúng nếu đứng yên."""
        for s in self.shots:
            if s["team"] == f.team:
                continue
            rx, ry = f.x - s["x"], f.y - 30 - s["y"]
            speed2 = s["vx"] ** 2 + s["vy"] ** 2
            t = (rx * s["vx"] + ry * s["vy"]) / max(1.0, speed2)
            if 0 < t < 0.45:
                cx, cy = s["x"] + s["vx"] * t, s["y"] + s["vy"] * t
                if (cx - f.x) ** 2 + (cy - (f.y - 30)) ** 2 < (BODY + 26) ** 2:
                    return s
        return None

    def _danger_push(self, f):
        """Lực đẩy khỏi chông và vòng mưa tên của đối thủ."""
        px = py = 0.0
        for tr in self.traps:
            if tr["team"] != f.team:
                dx, dy = f.x - tr["x"], f.y - tr["y"]
                d = math.hypot(dx, dy)
                if d < 90:
                    px += dx / max(1.0, d) * (90 - d) / 90
                    py += dy / max(1.0, d) * (90 - d) / 90
        for z in self.zones:
            if z["team"] != f.team:
                dx, dy = f.x - z["x"], f.y - z["y"]
                d = math.hypot(dx, dy)
                if d < RAIN_R + 30:
                    px += dx / max(1.0, d) * 1.5
                    py += dy / max(1.0, d) * 1.5
        return px, py

    def _score_skill(self, f, sid, p, dist) -> float:
        """Điểm hợp lý của từng chiêu trong tình huống hiện tại; bot ít khôn thì điểm bị nhiễu nhiều hơn."""
        hp = f.hp / f.max_hp
        opening = p.attack_cd > 0.2 or p.dodge_cd > DODGE_CD - 0.4  # người chơi vừa chém hoặc vừa né xong
        table = {
            "phong_lao": 0.6 + 0.3 * (dist > 250) if dist > 150 and p.dodge_t <= 0 else 0.0,
            "phi_tieu": 0.55 + 0.25 * opening if dist > 120 else 0.1,
            "ten_lua": 0.7 if 150 < dist < 460 else 0.1,
            "dot_kich": (0.7 + 0.3 * opening) if 140 < dist < 360 else 0.0,
            "xung_phong": 0.85 if 200 < dist < 430 else 0.0,
            "xoay_kiem": 0.9 if dist < 150 else 0.0,
            "lien_hoan": (0.85 + 0.2 * opening) if dist < REACH * 1.4 else 0.0,
            "chan_dia": 0.8 if dist < 300 else 0.0,
            "mua_ten": 0.75 if dist > 170 else 0.25,
            "khoi_mu": 0.65 if (dist < 220 and hp < 0.6) or dist > 380 else 0.15,
            "the_thu": 0.95 if dist < 220 and (p.attack_t > 0 or p.windup > 0 or self._incoming(f)) else 0.0,
            "hoi_khi": (1.0 if dist > 200 else 0.55) if hp < 0.45 else 0.0,
            "chong_ngam": 0.55 if 90 < dist < 260 else 0.1,
            "no_lien_chau": 0.7 if dist > 140 else 0.2,
            "hoa_cong": 0.7 if dist < 260 else 0.15,
            "hao_khi": 0.65 if f.rage_t <= 0 and dist < 260 else 0.0,
            "phi_ma": 0.85 if 200 < dist < 460 else 0.0,
        }
        base = table.get(sid, 0.4)
        return base * random.uniform(1 - 0.6 * (1 - f.smart), 1 + 0.2 * (1 - f.smart))

    def _bot(self, f, dt):
        p = self._nearest(f)
        if p is None or f.dead:
            return
        if f.windup > 0:  # đang lấy đà: có dấu hiệu báo trước để người chơi kịp né
            f.windup -= dt
            f.moving = False
            if f.windup <= 0 and f.pending:
                self.cast(f, f.pending)
                f.pending = None
            return
        if f.charge or f.combo > 0:
            return  # đang lao hoặc đang chém liên hoàn
        dx, dy = p.x - f.x, p.y - f.y
        dist = max(1.0, math.hypot(dx, dy))
        # 1. Né đạn đang bay tới: bot càng khôn càng phản xạ nhanh
        if f.dodge_cd <= 0 and not f.anchored:
            shot = self._incoming(f)
            if shot and random.random() < f.smart * dt * 14:
                sx, sy = -shot["vy"], shot["vx"]
                if (f.x + sx * 0.001 - FIELD.centerx) * sx + (f.y + sy * 0.001 - FIELD.centery) * sy > 0:
                    sx, sy = -sx, -sy  # né về phía giữa sân cho khỏi kẹt góc
                self.dodge(f, sx, sy)
                return
        # 2. Chọn chiêu theo tình huống
        f.think -= dt
        if f.think <= 0:
            f.think = random.uniform(0.25, 0.6) * (1.4 - 0.5 * f.smart)
            if random.random() < 0.3:
                f.strafe = -f.strafe
            ready = [s for s in f.skills if f.cds.get(s, 0) <= 0 and self._skill_makes_sense(f, s, dist)]
            if ready:
                scored = sorted(((self._score_skill(f, s, p, dist), s) for s in ready), reverse=True)
                best, sid = scored[0]
                if best > 0.3 and random.random() < f.aggro + 0.2 * f.smart:
                    f.pending = sid
                    f.windup = progression.BOT_SKILLS.get(sid, {}).get("windup", 0.42)
                    f.aim = (p.x + p.vx * 0.2 * f.smart, p.y + p.vy * 0.2 * f.smart)
                    f.moving = False
                    return
            # né lùi khi người chơi đang vung đòn sát bên
            if p.attack_t > 0 and dist < REACH * 1.1 and f.dodge_cd <= 0 and random.random() < f.smart * 0.7:
                self.dodge(f, -dx, -dy)
                return
        # 3. Di chuyển theo lối đánh, tránh chông và vòng tên
        prefer = PREFER.get(f.style, REACH * 0.8)
        hp = f.hp / f.max_hp
        opening = p.attack_cd > 0.2 or p.dodge_cd > DODGE_CD - 0.4
        if hp < 0.25 and f.smart > 0.4 and "hoi_khi" in f.skills and f.cds.get("hoi_khi", 0) <= 0:
            prefer = 320  # giữ xa để kịp hồi khí
        elif opening and f.style != "ranged":
            prefer = REACH * 0.55  # bắt sơ hở: áp sát đánh ngay
        if dist > prefer + (12 if f.style != "ranged" else 40):  # đánh gần thì vòng lượn phải nằm trong tầm chém
            mx, my = dx / dist, dy / dist
        elif dist < prefer - 40:
            mx, my = -dx / dist, -dy / dist
        else:
            mx, my = -dy / dist * f.strafe * 0.7, dx / dist * f.strafe * 0.7
        ax, ay = self._danger_push(f)
        mx, my = mx + ax * 1.6, my + ay * 1.6
        if dist < min(self._reach(f), 440) and f.attack_cd <= 0 and random.random() < (f.aggro + (0.6 if opening else 0)) * dt * 7:
            self.attack(f)
        self._walk(f, mx, my, dt)

    @staticmethod
    def _skill_makes_sense(f, sid, dist):
        if sid == "hoi_khi":
            return f.hp < f.max_hp * 0.55
        if sid == "xoay_kiem":
            return dist < 170
        if sid == "the_thu":
            return dist < 300
        return True

    # ----- vòng lặp -----
    def _walk(self, f, dx, dy, dt):
        if not (dx or dy):
            f.moving = False
            return
        speed = f.speed * (0.55 if f.slow_t > 0 else 1.0)
        length = max(1.0, math.hypot(dx, dy))
        k = speed * dt * (1.0 if length <= 1.0 else 1.0 / length)
        f.x += dx * k
        f.y += dy * k
        self._clamp(f)
        f.moving = True
        f.facing = self._dir_name(dx, dy)

    def handle(self, event):
        # Bàn phím dành cho việc đánh: phím mũi tên không được chuyển con trỏ sang nút Rút lui rồi phím cách bấm nhầm
        if event.type != pygame.KEYDOWN and self.group.handle(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._quit()
            elif self.result:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._finish()
            elif event.key == pygame.K_SPACE:
                self.attack(self.player)
            elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                keys = pygame.key.get_pressed()
                self.dodge(self.player, (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]), (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]))
            elif event.key == pygame.K_q:
                self.drink()
            elif event.key == pygame.K_e:
                self.eat()
            elif pygame.K_1 <= event.key <= pygame.K_4:
                i = event.key - pygame.K_1
                if i < len(self.slots):
                    self.cast(self.player, self.slots[i])
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and not self.result:
            self.mouse_down, self.move_button, self.mouse = True, 3, event.pos  # giữ chuột phải: đi theo con trỏ
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.result:
            if BTN_ATTACK.collidepoint(event.pos):
                self.attack(self.player)
            elif BTN_DODGE.collidepoint(event.pos):
                self.dodge(self.player)
            elif BTN_POTION.collidepoint(event.pos):
                self.drink()
            elif BTN_EAT.collidepoint(event.pos):
                self.eat()
            else:
                for i, r in enumerate(self.slot_rects):
                    if r.collidepoint(event.pos) and i < len(self.slots):
                        self.cast(self.player, self.slots[i])
                        return
                self.mouse = event.pos
                if getattr(event, "touch", False):  # chạm màn hình điện thoại: giữ để đi tới, đánh bằng các nút
                    self.mouse_down, self.move_button = True, 1
                else:  # chuột trái trên sân: chém
                    self.attack_held = True
                    self.attack(self.player)
        elif event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 3):
            if event.button == 1:
                self.attack_held = False
            if event.button == self.move_button:
                self.mouse_down = False

    def update(self, dt):
        self.t += dt
        if self.background:  # map bên dưới vẫn cần báo cho người cùng map biết mình đang đánh
            self.background(dt)
        self.fx.update(dt)
        for pop in self.pops:
            pop[2] -= 44 * dt
            pop[3] -= dt
        self.pops = [p for p in self.pops if p[3] > 0]
        if self.result:
            return
        if self.intro > 0:
            self.intro -= dt
            return
        self.left -= dt
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        if not (dx or dy) and self.mouse_down:
            mx, my = self.mouse[0] - self.player.x, self.mouse[1] - self.player.y
            if math.hypot(mx, my) > 14:
                d = math.hypot(mx, my)
                dx, dy = mx / d, my / d
        for f in self.fighters:
            self._tick(f, dt)
        p = self.player
        if not p.dead and p.dodge_t <= 0:
            self._walk(p, dx, dy, dt)
        if self.attack_held:
            if pygame.mouse.get_pressed()[0]:
                self.attack(p)  # còn hồi đòn thì attack tự bỏ qua
            else:  # nhả chuột ở ngoài cửa sổ nên không nhận được MOUSEBUTTONUP
                self.attack_held = False
        for f in self.fighters:
            f.vx, f.vy = (f.x - f.px) / max(dt, 1e-3), (f.y - f.py) / max(dt, 1e-3)
            f.px, f.py = f.x, f.y
        for f in self.foes:
            self._bot(f, dt)
        for f in self.fighters:
            self._step_combo(f, dt)
            self._step_charge(f, dt)
            self._step_volley(f, dt)
        self._step_fires(dt)
        self._step_shots(dt)
        self._step_traps(dt)
        self._step_zones(dt)
        self._step_waves(dt)
        self._check_end()

    def _tick(self, f, dt):
        for key in list(f.cds):
            f.cds[key] = max(0.0, f.cds[key] - dt)
        f.attack_cd = max(0.0, f.attack_cd - dt)
        f.attack_t = max(0.0, f.attack_t - dt)
        f.dodge_cd = max(0.0, f.dodge_cd - dt)
        f.hurt_t = max(0.0, f.hurt_t - dt)
        f.shield_t = max(0.0, f.shield_t - dt)
        f.slow_t = max(0.0, f.slow_t - dt)
        f.hidden_t = max(0.0, f.hidden_t - dt)
        f.ride_t = max(0.0, f.ride_t - dt)
        if f.rage_t > 0:
            f.rage_t -= dt
            if f.rage_t <= 0:
                f.power, f.speed = f.base
        f.frame += dt * 8
        if f.dodge_t > 0:
            f.dodge_t -= dt
            f.x += f.dash[0] * dt
            f.y += f.dash[1] * dt
            self._clamp(f)
        if f.burn_t > 0 and not f.dead:
            f.burn_t -= dt
            f.hp -= BURN_DPS * dt
            if random.random() < dt * 14:
                self.fx.fire(f.x, f.y - 30, 1, 12)
            if f.hp <= 0:
                f.hp = 0.0
                f.dead = True

    def _step_shots(self, dt):
        for s in list(self.shots):
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            s["life"] -= dt
            hit = None
            for f in self.fighters:
                if f.team != s["team"] and not f.dead and (f.x - s["x"]) ** 2 + (f.y - 30 - s["y"]) ** 2 < (BODY + 10) ** 2:
                    hit = f
                    break
            if hit:
                self._hurt(hit, s["dmg"], s["src"], 18)
                if s["burn"] and hit.dodge_t <= 0:
                    hit.burn_t = BURN_TIME
                if s.get("hit") == "spark":  # mũi tên cắm vào: tia lửa nhỏ thay vì nổ
                    self.fx.burst(s["x"], s["y"], 8, [(255, 240, 200), (230, 200, 140)], 200, 0.3, 3, 200, kind="spark")
                else:
                    self.fx.play("fx/explosion.png", 9, s["x"], s["y"], 24, False, 2)
                self.shots.remove(s)
            elif s["life"] <= 0 or not FIELD.inflate(160, 160).collidepoint(s["x"], s["y"]):
                self.shots.remove(s)

    def _step_traps(self, dt):
        for tr in list(self.traps):
            tr["t"] += dt
            if tr["t"] < 0.4:
                continue
            for f in self.fighters:
                if f.team != tr["team"] and not f.dead and (f.x - tr["x"]) ** 2 + (f.y - tr["y"]) ** 2 < 36 ** 2:
                    self._hurt(f, tr["dmg"], tr["src"])
                    f.slow_t = SLOW_TIME
                    self._pop("Dính chông!", f.x, f.y - 100, (255, 200, 120))
                    self.traps.remove(tr)
                    break

    def _check_end(self):
        if self.player.dead:
            self._end(False)
        elif all(f.dead for f in self.foes):
            self._end(True)
        elif self.left <= 0:
            mine = self.player.hp / self.player.max_hp
            theirs = sum(f.hp for f in self.foes) / max(1.0, sum(f.max_hp for f in self.foes))
            self._end(mine >= theirs)

    def _end(self, win: bool):
        self.result = {"win": win}
        self.mouse_down = self.attack_held = False
        self.app.audio.play("thang" if win else "sai")
        self.group.clear()
        cx = W // 2
        self.group.add(ui.Button((cx - 150, 470, 300, 56), "Tiếp tục", self._finish, "gold"))

    def _finish(self):
        self.app.scenes.pop(self.result)

    # ----- vẽ -----
    def draw(self, screen):
        # Chỉ vẽ qua lớp đệm khi màn hình đang rung, bình thường vẽ thẳng cho nhẹ trên WebAssembly
        shaking = self.fx.shake_power > 0
        s = self.world if shaking else screen
        s.blit(self.bg, (0, 0))
        trap = sprites.icon("ui/caltrop.png", 3)
        for tr in self.traps:
            s.blit(trap, trap.get_rect(center=(tr["x"], tr["y"])))
        self._draw_warnings(s)
        for f in sorted(self.fighters, key=lambda g: g.y):
            self._draw_fighter(s, f)
        for shot in self.shots:
            img = shot["frames"][int(self.t * 12) % len(shot["frames"])]
            s.blit(img, img.get_rect(center=(shot["x"], shot["y"])))
        self.fx.draw(s)
        for text, x, y, _t, col in self.pops:
            fonts.text(s, text, fonts.font("black", 22), col, (x, y), "center", shadow=(24, 16, 14))
        if shaking:
            screen.blit(s, self.fx.offset())
        self._draw_hud(screen)
        self.group.draw(screen)

    def _draw_weapon(self, s, f):
        """Vũ khí trên tay: cầm khi đi, vung theo loại khi đánh, có vệt chém."""
        scale = max(3, round(f.cast.size / 16))
        if f.attack_t > 0:
            st = weapons.style(f.weapon)
            k = 1.0 - f.attack_t / st["time"]
            aim = -math.degrees(f.shot_angle) if st["move"] == "shoot" else None
            angle, push = weapons.swing(f.weapon, f.facing, k, aim)
            hx, hy = weapons.hand_at(f.facing, (f.x, f.y), scale, True)
            hy -= getattr(f.cast, "lift", 0) * scale  # người cưỡi ngựa cầm vũ khí cao hơn
            r = math.radians(angle)
            hx, hy = hx + math.cos(r) * push * f.cast.size, hy - math.sin(r) * push * f.cast.size
            img = weapons.image(f.weapon, scale)
            weapons.trail(s, f.weapon, f.facing, k, (hx, hy), img.get_height() if img else 40)
            weapons.blit(s, f.weapon, scale, (hx, hy), angle)
        else:
            bob = scale if f.moving and int(f.frame) % 2 else 0
            angle, _behind = weapons.held(f.facing)
            bob -= getattr(f.cast, "lift", 0) * scale
            weapons.blit(s, f.weapon, scale, weapons.hand_at(f.facing, (f.x, f.y), scale, False, bob), angle)

    def _draw_warnings(self, s):
        """Vòng mưa tên đỏ dần, sóng chấn địa, đường lao của chiêu Xung phong: báo trước để người chơi kịp né."""
        for z in self.fires:
            rect = pygame.Rect(0, 0, 140, 72)
            rect.center = (z["x"], z["y"])
            ui.alpha_rect(s, rect, (230, 110, 40, int(60 + 50 * min(1.0, z["t"]))), 36)
        for z in self.zones:
            k = min(1.0, z["t"] / RAIN_DELAY)
            ring = pygame.Rect(0, 0, RAIN_R * 2, RAIN_R)
            ring.center = (z["x"], z["y"])
            ui.alpha_rect(s, ring.inflate(-RAIN_R * (1 - k), -RAIN_R * (1 - k) / 2), (200, 40, 30, int(60 + 80 * k)), RAIN_R)
            pygame.draw.ellipse(s, (240, 90, 60), ring, 2)
        for w in self.waves:
            rect = pygame.Rect(0, 0, w["r"] * 2, w["r"])
            rect.center = (w["x"], w["y"])
            pygame.draw.ellipse(s, (226, 196, 140), rect, 5)
            pygame.draw.ellipse(s, (120, 90, 60), rect.inflate(-10, -5), 2)
        for f in self.foes:
            if f.windup > 0 and f.pending == "xung_phong":
                pygame.draw.line(s, (240, 90, 60), (f.x, f.y - 10), f.aim, 4)
            elif f.windup > 0 and f.pending == "chan_dia":
                rect = pygame.Rect(0, 0, WAVE_MAX * 2, WAVE_MAX)
                rect.center = (f.x, f.y)
                pygame.draw.ellipse(s, (240, 120, 80), rect, 1)

    def _draw_fighter(self, s, f):
        if f.dead:
            img = f.cast.dead
            s.blit(img, img.get_rect(midbottom=(f.x, f.y)))
            return
        if f.windup > 0:
            alert = sprites.icon("ui/emote_alert.png", 3)
            s.blit(alert, alert.get_rect(midbottom=(f.x, f.y - 66)))
        if f.hidden_t > 0:
            return  # đang ẩn trong khói
        if f.ride_t > 0:  # đang cưỡi chiến mã lao tới
            frames = chienma.views()["left" if f.facing == "left" else "right"]
            horse = frames[int(self.t * 12) % 2]
            s.blit(horse, horse.get_rect(midbottom=(f.x, f.y + 6)))
            img = f.cast.walk[f.facing][0]
            s.blit(img, img.get_rect(midbottom=(f.x, f.y - horse.get_height() * 0.45)))
            return
        img = f.cast.attack[f.facing] if f.attack_t > 0 else f.cast.walk[f.facing][int(f.frame) % 4 if f.moving else 0]
        if f.hurt_t > 0 and int(self.t * 40) % 2 == 0:
            return  # nhấp nháy khi trúng đòn
        pygame.draw.ellipse(s, (30, 24, 20), (f.x - 22, f.y - 8, 44, 14))
        rect = img.get_rect(midbottom=(f.x, f.y))
        if f.dodge_t > 0:
            ghost = img.copy()
            ghost.set_alpha(110)
            s.blit(ghost, rect.move(-f.dash[0] * 0.05, -f.dash[1] * 0.05))
        behind = f.weapon and f.attack_t <= 0 and weapons.held(f.facing)[1]
        if behind:
            self._draw_weapon(s, f)
        s.blit(img, rect)
        if f.weapon and not behind:
            self._draw_weapon(s, f)
        if f.shield_t > 0:
            sh = sprites.strip("fx/shield.png", 6, 4)[int(self.t * 12) % 6]
            s.blit(sh, sh.get_rect(center=(f.x, f.y - 30)))
        if f.team == 1:
            ui.progress_bar(s, (f.x - 34, f.y - 78, 68, 7), f.hp / f.max_hp, (214, 70, 60))

    def _draw_hud(self, screen):
        p = self.player
        ui.lacquer_panel(screen, (14, 10, 470, 76), 240)
        fonts.text(screen, "Bạn", fonts.font("bold", 17), theme.GOLD_LIGHT, (34, 22))
        ui.progress_bar(screen, (34, 50, 430, 16), p.hp / p.max_hp, (86, 190, 110))
        fonts.text(screen, f"{round(p.hp)}/{round(p.max_hp)}", fonts.font("semi", 13), theme.PAPER, (464, 24), "topright")
        foes = self.foes
        total_hp = sum(f.hp for f in foes)
        total_max = sum(f.max_hp for f in foes)
        ui.lacquer_panel(screen, (W - 134 - 430, 10, 430, 76), 240)
        name = foes[0].name if len(foes) == 1 else f"{self.title}: còn {sum(not f.dead for f in foes)} đối thủ"
        fonts.text(screen, name, fonts.font("bold", 17), theme.GOLD_LIGHT, (W - 134 - 410, 22))
        ui.progress_bar(screen, (W - 134 - 410, 50, 390, 16), total_hp / max(1.0, total_max), (214, 70, 60))
        fonts.text(screen, str(max(0, math.ceil(self.left))), fonts.font("black", 34), theme.WHITE, (W // 2 - 70, 26), "midtop", shadow=(24, 16, 14))
        self._draw_controls(screen)
        if self.intro > 0:
            label = "ĐẤU!" if self.intro < 0.6 else str(math.ceil(self.intro - 0.6))
            fonts.text(screen, label, fonts.font("black", 92), theme.GOLD_LIGHT, (W // 2, 310), "center", shadow=(60, 20, 14))
            fonts.text(screen, "WASD để đi · chuột trái chém · Shift né · 1, 2, 3, 4 tung kỹ năng · Q uống thuốc", fonts.font("semi", 18), theme.WHITE, (W // 2, 390), "center", shadow=(24, 16, 14))
        if self.result:
            self._draw_result(screen)

    def _draw_controls(self, screen):
        for i, r in enumerate(self.slot_rects):
            ui.lacquer_panel(screen, r, 236)
            fonts.text(screen, str(i + 1), fonts.font("bold", 14), theme.GOLD, (r.x + 12, r.y + 8))
            if i >= len(self.slots):
                fonts.text(screen, "Trống", fonts.font("ui", 12), theme.PAPER_3, r.center, "center")
                continue
            sid = self.slots[i]
            icon = sprites.icon(f"ui/sk_{sid}.png", 2)
            screen.blit(icon, icon.get_rect(center=(r.centerx, r.y + 32)))
            fonts.text(screen, progression.SKILLS[sid]["name"], fonts.font("semi", 11), theme.PAPER, (r.centerx, r.bottom - 15), "center")
            left = self.player.cds.get(sid, 0)
            if left > 0:
                ui.alpha_rect(screen, r.inflate(-8, -8), (10, 8, 8, 170))
                fonts.text(screen, f"{left:.1f}", fonts.font("bold", 18), theme.WHITE, r.center, "center")
        ui.lacquer_panel(screen, BTN_ATTACK, 240)
        fonts.text(screen, "CHÉM", fonts.font("black", 22), theme.GOLD_LIGHT, BTN_ATTACK.center, "center")
        fonts.text(screen, "chuột trái", fonts.font("ui", 12), theme.PAPER_3, (BTN_ATTACK.centerx, BTN_ATTACK.bottom - 22), "center")
        ui.lacquer_panel(screen, BTN_DODGE, 240)
        fonts.text(screen, "NÉ (Shift)", fonts.font("bold", 15), theme.PAPER, BTN_DODGE.center, "center")
        ui.lacquer_panel(screen, BTN_POTION, 240)
        pot = sprites.icon(rpg.item_icon("thuoc_nam"), 2)
        screen.blit(pot, pot.get_rect(center=(BTN_POTION.centerx, BTN_POTION.y + 28)))
        fonts.text(screen, f"Q · còn {self.state.potions}", fonts.font("semi", 12), theme.PAPER, (BTN_POTION.centerx, BTN_POTION.bottom - 14), "center")
        if not self.state.potions:
            ui.alpha_rect(screen, BTN_POTION.inflate(-8, -8), (10, 8, 8, 150))
        ui.lacquer_panel(screen, BTN_EAT, 240)
        fish = sprites.icon(rpg.item_icon("ca_nuong"), 2)
        screen.blit(fish, fish.get_rect(center=(BTN_EAT.centerx, BTN_EAT.y + 28)))
        fonts.text(screen, f"E · còn {self.state.grilled}", fonts.font("semi", 12), theme.PAPER, (BTN_EAT.centerx, BTN_EAT.bottom - 14), "center")
        if not self.state.grilled:
            ui.alpha_rect(screen, BTN_EAT.inflate(-8, -8), (10, 8, 8, 150))
        if self.player.dodge_cd > 0:
            ui.alpha_rect(screen, BTN_DODGE.inflate(-8, -8), (10, 8, 8, 170))

    def _draw_result(self, screen):
        ui.veil(screen, (10, 6, 4, 150))
        rect = pygame.Rect(W // 2 - 280, 190, 560, 360)
        ui.paper_panel(screen, rect)
        win = self.result["win"]
        fonts.text(screen, "CHIẾN THẮNG" if win else "THUA TRẬN", fonts.font("black", 40), theme.LACQUER_RED if win else theme.INK_SOFT, (rect.centerx, rect.y + 44), "center")
        img = self.player.cast.attack["down"] if win else self.player.cast.dead
        screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + 130)))
        msg = f"Bạn đã thắng: {self.title}." if win else ("Đánh quái để lên cấp, dùng tiềm năng tăng chỉ số, mua đồ ở lò rèn, "
                                                             "học sử để có điểm kỹ năng rồi quay lại nhé.")
        fonts.paragraph(screen, msg, fonts.font("serif", 18), theme.INK_SOFT, rect.x + 40, rect.y + 186, rect.w - 80, gap=3)


