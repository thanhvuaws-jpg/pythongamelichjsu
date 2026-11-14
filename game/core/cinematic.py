"""Cảnh hồi ức diễn lại trận Bạch Đằng theo từng nhịp lời kể: nhử địch, triều rút, đâm cọc, tàn trận.

Khác với trận đánh, cảnh này tự diễn, người chơi chỉ đọc lời kể. Mỗi nhịp tự đặt lại vị trí nên bấm nhanh hay đọc chậm
đều đúng cảnh. Hình dựng màu nâu cũ, riêng cờ, lửa và máu giữ màu thật cho nổi lên.
"""

from __future__ import annotations

import math
import random

import pygame

from core import art, diorama, fleet, sprites, theme
from core.sprites import TILE
from core.worldgen import stake_sprite

W, H = theme.WIDTH, theme.HEIGHT
LANES = (215, 285, 355, 425)  # chừa phía dưới cho hộp lời kể
LANE_BOATS = (2, 3, 3, 2)
STAKES = ((0, 790), (0, 930), (1, 730), (1, 900), (2, 730), (2, 900), (3, 790), (3, 930))
ESCAPERS = ((0, 1), (3, 1))  # (luồng, thứ tự) những thuyền lọt qua được bãi cọc
BEATS = ("lure", "ebb", "crash", "after")
ENEMY_W, ALLY_W = 160, 120
BOW = 50
STUCK_TIME = 3.2
WRECK_ANGLE = -22
FLEE_SPEED = 150
SLOW_TIME = 0.8
SLOW_SCALE = 0.3
PANIC_AT = 1.3
WATER_TOP = 164
_base: pygame.Surface | None = None
_water: pygame.Surface | None = None


def _bank(b):
    for x, name in ((0, "gray_big"), (5, "gray_tall"), (8, "pines"), (12, "gray_big"), (17, "gray_tall"), (19, "pines")):
        b.put(name, x, -1, True)


def _backdrop() -> tuple[pygame.Surface, pygame.Surface]:
    """Bờ sông và bãi bùn đứng yên, mặt nước trượt lên xuống theo con nước; đều đã chuyển màu nâu cũ."""
    global _base, _water
    if _base is None:
        base = pygame.Surface((W, H))
        mud = sprites.region("floor", 0, 5)
        for y in range(TILE, TILE * 4, TILE):
            for x in range(0, W, TILE):
                base.blit(mud, (x, y))
        base.fill((150, 120, 100), special_flags=pygame.BLEND_RGB_MULT)
        base.blit(diorama.render("tide_memory", 20, 2, _bank), (0, 0))
        _base = diorama.to_old(base)
        _base.blit(art.vignette(), (0, 0))
        water = pygame.Surface((W, H))
        tile = sprites.region("water", 1, 7)
        for y in range(0, H, TILE):
            for x in range(0, W, TILE):
                water.blit(tile, (x, y))
        shade = pygame.Surface((W, H))
        shade.fill((70, 90, 110))
        shade.set_alpha(120)
        water.blit(shade, (0, 0))
        _water = diorama.to_old(water)
        _water.blit(art.vignette(), (0, -WATER_TOP))  # ghép sẵn viền tối: vẽ lại mỗi khung hình rất tốn trên web
    return _base, _water


def turtle_sprite(scale: int = 5) -> pygame.Surface:
    """Rùa Vàng nhìn nghiêng, ngẩng đầu sang trái; gói asset không có rùa nên vẽ ở độ phân giải thấp rồi phóng to cho cùng độ nét."""
    outline, gold, light, dark, skin, shade = (24, 16, 14), (232, 186, 70), (250, 226, 136), (168, 116, 36), (214, 186, 96), (150, 124, 56)
    low = pygame.Surface((44, 30), pygame.SRCALPHA)
    pygame.draw.polygon(low, outline, [(34, 19), (43, 26), (40, 29), (31, 24)])  # chân sau
    pygame.draw.polygon(low, shade, [(35, 20), (41, 26), (39, 28), (32, 23)])
    pygame.draw.polygon(low, outline, [(5, 15), (13, 11), (17, 19), (9, 22)])  # cổ
    pygame.draw.polygon(low, skin, [(7, 15), (13, 12), (16, 18), (10, 20)])
    pygame.draw.ellipse(low, outline, (0, 5, 13, 12))  # đầu
    pygame.draw.ellipse(low, skin, (1, 6, 11, 10))
    low.set_at((4, 9), outline)
    low.set_at((5, 9), outline)
    pygame.draw.line(low, shade, (1, 13), (6, 13))
    pygame.draw.ellipse(low, outline, (10, 3, 30, 26))  # mai rùa
    pygame.draw.ellipse(low, gold, (11, 4, 28, 24))
    pygame.draw.arc(low, light, (13, 6, 22, 16), 1.2, 3.0, 2)
    for x0, x1, y0 in ((17, 21, 9), (24, 29, 7), (31, 35, 10), (20, 25, 15), (28, 33, 16)):
        pygame.draw.polygon(low, dark, [(x0, y0 + 2), (x0 + 2, y0), (x1 - 2, y0), (x1, y0 + 2), (x1 - 2, y0 + 4), (x0 + 2, y0 + 4)], 1)
    pygame.draw.polygon(low, outline, [(11, 19), (19, 21), (15, 29), (7, 27)])  # chân trước
    pygame.draw.polygon(low, skin, [(12, 20), (18, 22), (14, 27), (9, 26)])
    return pygame.transform.scale(low, (44 * scale, 30 * scale))


class TurtleMemory:
    """Truyền thuyết Hồ Gươm, đúng theo lời kể: gươm thần, rồi Rùa Vàng nổi lên đòi gươm và lặn xuống.

    Nền màu nâu cũ, riêng rùa và gươm giữ màu thật cho ra vẻ huyền thoại. Mặt nước che phần thân dưới của rùa.
    """

    BEATS = ("sword", "turtle")
    TURTLE_X, BOAT_X, LAKE_Y = 430, 860, 372
    RISE_TIME, FLY_START, FLY_TIME, SINK_START, SINK_TIME = 1.6, 2.0, 1.2, 6.5, 1.8
    SWORD_HOME_Y = 300

    def __init__(self, fx):
        self.fx = fx
        self.t = 0.0
        self.beat = "sword"
        self.turtle = turtle_sprite()
        self.sword = sprites.icon("ui/sword.png", 5)
        self.sword_flat = pygame.transform.rotate(self.sword, 90)
        self.boat = diorama.to_old(fleet.boat_sprite(190))
        self.rower = sprites.cast("LinhDaiViet", old=True).walk["left"][0]
        self.next_fx = 0.0

    def set_beat(self, beat):
        if beat != self.beat:
            self.beat = beat
            self.t = 0.0

    def _sword_pos(self) -> tuple[float, float]:
        if self.beat == "sword":
            return 640, self.SWORD_HOME_Y - min(1.0, self.t / 1.5) * 70 + 6 * math.sin(self.t * 2.4)
        k = min(1.0, max(0.0, (self.t - self.FLY_START) / self.FLY_TIME))
        x = self.BOAT_X + (self.TURTLE_X - 30 - self.BOAT_X) * k
        y = self.LAKE_Y - 110 - math.sin(k * math.pi) * 90 + k * 34
        return x, y + self._turtle_depth() * self.turtle.get_height() * 0.72  # ngậm rồi thì lặn theo rùa

    def _turtle_depth(self) -> float:
        """0 là nổi hẳn, 1 là chìm hẳn dưới mặt nước."""
        if self.beat != "turtle":
            return 1.0
        if self.t < self.RISE_TIME:
            return 1 - self.t / self.RISE_TIME
        if self.t > self.SINK_START:
            return min(1.0, (self.t - self.SINK_START) / self.SINK_TIME)
        return 0.0

    def update(self, dt):
        self.t += dt
        self.next_fx -= dt
        if self.next_fx > 0:
            return
        self.next_fx = 0.12
        depth = self._turtle_depth()
        if self.beat == "sword" or self.t < self.FLY_START + self.FLY_TIME:
            x, y = self._sword_pos()
            self.fx.burst(x, y, 2, [(255, 236, 170), (250, 250, 230)], 60, 0.5, 3, 20, kind="spark")
        if self.beat == "turtle" and 0.0 < depth < 1.0:
            self.fx.splash(self.TURTLE_X + 40, self.LAKE_Y, 5)

    def draw(self, s, offset=(0, 0)):
        s.blit(diorama.old("ho_guom"), offset)
        ox, oy = offset
        bob = 4 * math.sin(self.t * 1.6)
        s.blit(self.boat, self.boat.get_rect(midbottom=(self.BOAT_X + ox, self.LAKE_Y + 20 + bob + oy)))
        s.blit(self.rower, self.rower.get_rect(midbottom=(self.BOAT_X - 10 + ox, self.LAKE_Y - 10 + bob + oy)))
        depth = self._turtle_depth()
        w, h = self.turtle.get_size()
        top = self.LAKE_Y - h * 0.72 * (1 - depth) + oy
        visible = int(self.LAKE_Y + oy - top + 6)
        if visible > 0 and depth < 1.0:
            part = self.turtle.subsurface((0, 0, w, min(h, visible)))
            s.blit(part, (self.TURTLE_X - w * 0.3 + ox, top + 2 * math.sin(self.t * 2.2)))
            pygame.draw.ellipse(s, (232, 214, 170), (self.TURTLE_X - w * 0.34 + ox, self.LAKE_Y - 3 + oy, w * 1.04, 12), 2)
        if self.beat == "sword":
            x, y = self._sword_pos()
            s.blit(self.sword, self.sword.get_rect(center=(x + ox, y + oy)))
        elif self.t < self.FLY_START + self.FLY_TIME or depth < 0.6:
            x, y = self._sword_pos()
            img = self.sword if self.t < self.FLY_START else self.sword_flat
            s.blit(img, img.get_rect(center=(x + ox, y + oy)))


class TideMemory:
    def __init__(self, fx, audio, dark_sails: bool = False):
        self.fx = fx
        self.audio = audio
        self.t = 0.0
        self.total = 0.0
        self.beat = ""
        self.tide = 1.0
        self.flow = 0.0
        self.slow = 0.0
        self.first_hit = True
        self.volley = 0.0
        self.jump_t = 0.0
        self.jumpers: list[dict] = []
        self.base, self.water = _backdrop()
        sail = (150, 62, 50) if dark_sails else (206, 190, 150)
        hull = fleet.boat_sprite(ENEMY_W, (150, 136, 150), sail=sail)
        self.enemy_right = sprites.sepia(hull)
        self.enemy_left = pygame.transform.flip(self.enemy_right, True, False)
        self.ally = sprites.sepia(fleet.boat_sprite(ALLY_W))
        fleet.add_flag(self.ally, (196, 40, 34))
        self.ally_back = pygame.transform.flip(self.ally, True, False)
        foe = ("LinhNguyen", "TuongNguyen") if dark_sails else ("LinhTong", "TuongTong")
        self.c_enemy = (sprites.cast(foe[0], 3, old=True), sprites.cast(foe[0], 3, old=True))
        self.c_ally = (sprites.cast("LinhDaiViet", 3, old=True), sprites.cast("LinhDaiViet2", 3, old=True))
        self.arrow = sprites.sepia(sprites.icon("fx/arrow.png", 3))
        self.stake = sprites.sepia(stake_sprite())
        self.flames = sprites.strip("fx/flame.png", 8, 2)
        self.smoke = sprites.strip("fx/smoke.png", 6, 3)
        self.shoals = {i: sprites.sepia(fleet.shoal(i)) for i in range(4)}
        self.alert = sprites.icon("ui/emote_alert.png", 3)
        self._rot: dict[tuple, pygame.Surface] = {}
        self.boats = self._make_boats()
        self.allies = self._make_allies()

    # ----- dựng đội hình -----
    def _crew(self, casts, offsets):
        return [{"cast": casts[i % 2], "off": off, "alive": True, "atk": 0.0} for i, off in enumerate(offsets)]

    def _make_boats(self):
        boats = []
        for lane, count in enumerate(LANE_BOATS):
            for j in range(count):
                boats.append({
                    "lane": lane, "j": j, "x": 0.0, "bait": 300 + j * 150 + (lane % 2) * 60, "state": "run", "doom": None,
                    "t": 0.0, "cd": 0.0, "crew": self._crew(self.c_enemy, (-44, 0, 44)),
                })
        return boats

    def _make_allies(self):
        return [{"lane": i, "x": 0.0, "crew": self._crew(self.c_ally, (-24, 24))} for i in range(4)]

    def _reset_crew(self):
        for side in (self.boats, self.allies):
            for item in side:
                for c in item["crew"]:
                    c["alive"], c["atk"] = True, 0.0

    def set_beat(self, beat: str):
        """Chuyển nhịp: đặt lại đúng thế trận của nhịp đó, không phụ thuộc người chơi đọc nhanh hay chậm."""
        self.beat, self.t = beat, 0.0
        self.jumpers.clear()
        if beat == "lure":
            self.tide = 1.0
            self._reset_crew()
            for b in self.boats:
                b.update(x=1420.0 + b["j"] * 150 + b["lane"] * 24, state="run", doom=None, t=0.0)
            for i, a in enumerate(self.allies):
                a["x"] = 1000.0 + (i % 2) * 90
        elif beat == "ebb":
            self.tide = min(self.tide, 0.8)
            self._reset_crew()
            for b in self.boats:
                b.update(x=float(b["bait"]), state="run", doom=None, t=0.0)
            self._place_allies_left()
        elif beat == "crash":
            self.tide = 0.3
            self._assign_stakes()
            for b in self.boats:
                b.update(x=float(b["bait"]), state="run", t=0.0)
            self._place_allies_left()
        elif beat == "after":
            self.tide = 0.14
            self._assign_stakes()
            for b in self.boats:
                b["state"] = "wreck" if b["doom"] is not None else "gone"
                b["x"] = (b["doom"] - BOW) if b["doom"] is not None else W + 200
                for c in b["crew"]:
                    c["alive"] = False
            for i, a in enumerate(self.allies):
                a["x"] = 420.0 + (i % 2) * 90

    def _place_allies_left(self):
        for i, a in enumerate(self.allies):
            a["x"] = 90.0 + (i % 2) * 70

    def _assign_stakes(self):
        for lane in range(len(LANES)):
            boats = sorted((b for b in self.boats if b["lane"] == lane), key=lambda b: -b["bait"])
            cols = [x for ln, x in STAKES if ln == lane]
            for b in boats:
                if (lane, b["j"]) in ESCAPERS:
                    b["doom"] = None
                else:
                    b["doom"] = cols[min(b["j"], len(cols) - 1)] if (lane, b["j"]) else None

    # ----- diễn -----
    def _ebb(self) -> float:
        return max(0.0, min(1.0, (0.74 - self.tide) / 0.6))

    def update(self, dt: float):
        if self.slow > 0:
            self.slow -= dt
            dt *= SLOW_SCALE
        self.t += dt
        self.total += dt
        for side in (self.boats, self.allies):
            for item in side:
                for c in item["crew"]:
                    c["atk"] = max(0.0, c["atk"] - dt)
        {"lure": self._lure, "ebb": self._ebb_beat, "crash": self._crash, "after": self._after}.get(self.beat, lambda _d: None)(dt)
        self._jumpers(dt)

    def _shoot(self, from_ally: bool):
        pool = [(a, c) for a in self.allies for c in a["crew"] if c["alive"]] if from_ally else [(b, c) for b in self.boats if b["state"] == "run" for c in b["crew"] if c["alive"]]
        foes = [b for b in self.boats if b["state"] in ("run", "stuck")] if from_ally else self.allies
        if not pool or not foes:
            return
        src, c = random.choice(pool)
        dst = random.choice(foes)
        c["atk"] = 0.3
        img = self.arrow if from_ally else pygame.transform.flip(self.arrow, True, False)
        self.fx.shoot(img, src["x"] + c["off"], LANES[src["lane"]] - 44, dst["x"] + random.randint(-40, 40), LANES[dst["lane"]] - 24, 680, 30)

    def _archery(self, dt, enemy_too=True):
        self.volley -= dt
        if self.volley <= 0:
            self.volley = random.uniform(0.28, 0.5)
            self._shoot(True)
            if enemy_too:
                self._shoot(False)

    def _lure(self, dt):
        self.tide = 1.0
        self.flow -= 50 * dt
        for b in self.boats:
            b["x"] = max(b["bait"], b["x"] - 135 * dt)
        for i, a in enumerate(self.allies):
            a["x"] = max(90.0 + (i % 2) * 70, a["x"] - 190 * dt)
        self._archery(dt)

    def _ebb_beat(self, dt):
        self.tide = max(0.24, self.tide - 0.17 * dt)
        self.flow += 110 * dt
        self._archery(dt, enemy_too=self.t < PANIC_AT)

    def _crash(self, dt):
        self.tide = max(0.1, self.tide - 0.1 * dt)
        self.flow += 140 * dt
        for b in self.boats:
            self._boat_step(b, dt)
        for a in self.allies:
            near = [b["x"] for b in self.boats if b["lane"] == a["lane"] and b["state"] in ("stuck", "wreck")]
            goal = min(near) - 190 if near else 480.0
            if a["x"] < goal:
                a["x"] += 170 * dt
        self._archery(dt, enemy_too=False)
        self.jump_t -= dt
        if self.jump_t <= 0:
            self.jump_t = random.uniform(0.9, 1.5)
            self._send_boarder()

    def _boat_step(self, b, dt):
        y = LANES[b["lane"]]
        if b["state"] == "run":
            b["x"] += FLEE_SPEED * dt
            if b["doom"] is not None and b["x"] >= b["doom"] - BOW:
                self._impact(b)
            elif b["x"] > W + 200:
                b["state"] = "gone"
        elif b["state"] == "stuck":
            b["t"] += dt
            b["cd"] -= dt
            if random.random() < dt * 14:
                self.fx.fire(b["x"] + random.uniform(-50, 60), y - 28, 1, 16)
            if b["cd"] <= 0:
                b["cd"] = random.uniform(0.5, 0.9)
                victim = next((c for c in b["crew"] if c["alive"]), None)
                if victim and b["t"] > 0.7:
                    self._kill(b, victim, True)
            if b["t"] > STUCK_TIME:
                b["state"] = "wreck"
                self.fx.debris(b["x"], y - 16, 6)
                self.fx.splash(b["x"], y, 8)

    def _kill(self, b, c, slash=False):
        c["alive"] = False
        x, y = b["x"] + c["off"], LANES[b["lane"]] - 34
        self.fx.blood(x, y, 16)
        self.fx.fall(x, y)
        if slash:
            self.fx.play("fx/curved.png", 4, x, y, 14, random.random() < 0.5, 3)
            self.audio.play("chem")

    def _impact(self, b):
        """Thuyền đâm vào cọc: mảnh gỗ văng, nước bắn, người ngã, cú đầu tiên chậm lại một nhịp."""
        y = LANES[b["lane"]]
        b["state"], b["t"], b["cd"] = "stuck", 0.0, 0.0
        bow = b["x"] + BOW
        self.fx.splinters(bow, y - 10, 14)
        self.fx.debris(bow, y - 16, 12)
        self.fx.splash(bow, y, 16)
        self.fx.shake(8)
        self.audio.play("va")
        victim = next((c for c in b["crew"] if c["alive"]), None)
        if victim:
            self._kill(b, victim)
        if self.first_hit:
            self.first_hit = False
            self.slow = SLOW_TIME

    def _send_boarder(self):
        stuck = [b for b in self.boats if b["state"] == "stuck" and any(c["alive"] for c in b["crew"])]
        if not stuck:
            return
        b = random.choice(stuck)
        a = min(self.allies, key=lambda s: abs(s["lane"] - b["lane"]) * 100 + abs(s["x"] - b["x"]))
        for c in a["crew"]:
            c["atk"] = 0.35
        self.audio.play("kiem")
        self.jumpers.append({"cast": self.c_ally[random.randint(0, 1)], "x0": a["x"], "y0": LANES[a["lane"]] - 8, "boat": b, "off": random.choice((-30, 0, 30)), "t": 0.0, "phase": "jump"})

    def _jumpers(self, dt):
        for j in self.jumpers:
            j["t"] += dt
            if j["phase"] == "jump" and j["t"] >= 0.5:
                j["phase"], j["t"] = "fight", 0.0
                b = j["boat"]
                y = LANES[b["lane"]] - 34
                self.fx.play("fx/cutx.png", 4, b["x"] + j["off"], y, 14, False, 3)
                self.fx.shake(4)
                self.audio.play("chem")
                for c in b["crew"]:
                    if c["alive"]:
                        self._kill(b, c)
            elif j["phase"] == "fight" and j["t"] >= 0.6:
                j["phase"], j["t"] = "back", 0.0
            elif j["phase"] == "back" and j["t"] >= 0.5:
                j["phase"] = "done"
        self.jumpers = [j for j in self.jumpers if j["phase"] != "done"]

    def _after(self, dt):
        self.flow += 30 * dt
        if random.random() < dt * 5:
            wrecks = [b for b in self.boats if b["state"] == "wreck"]
            if wrecks:
                b = random.choice(wrecks)
                self.fx.smoke(b["x"], LANES[b["lane"]] - 30, 1, 30)

    # ----- vẽ -----
    def _rotated(self, img, deg):
        key = (id(img), int(deg))
        out = self._rot.get(key)
        if out is None:
            out = pygame.transform.rotate(img, int(deg))
            self._rot[key] = out
        return out

    def _draw_stake(self, s, x, y, ox, oy):
        k = self._ebb()
        if k <= 0.02:
            return
        shoal = self.shoals[min(3, int(k * 4))]
        s.blit(shoal, shoal.get_rect(center=(x + ox, y + 2 + oy)))
        h = int(self.stake.get_height() * k)
        s.blit(self.stake, (x - self.stake.get_width() / 2 + ox, y + 4 - h + oy), (0, 0, self.stake.get_width(), h))

    def _draw_crew(self, s, crew, x, feet, facing, moving):
        for i, c in enumerate(crew):
            cast = c["cast"]
            if not c["alive"]:
                img = cast.dead
            elif c["atk"] > 0:
                img = cast.attack[facing]
            else:
                img = cast.walk[facing][int(self.total * 7 + i) % 4 if moving else 0]
            s.blit(img, (x + c["off"] - cast.size / 2, feet - cast.size))

    def _draw_enemy(self, s, b, ox, oy):
        y = LANES[b["lane"]]
        facing_right = self.beat in ("crash", "after") or (self.beat == "ebb" and self.t >= PANIC_AT)
        img = self.enemy_right if facing_right else self.enemy_left
        bob = math.sin(self.total * 2.4 + b["bait"] * 0.02) * 2
        drop = 0.0
        if b["state"] == "stuck":
            img = self._rotated(img, -4 - min(1.0, b["t"]) * 8)
        elif b["state"] == "wreck":
            img = self._rotated(img, WRECK_ANGLE)
            drop = 16
            bob = 0.0
        s.blit(img, img.get_rect(midbottom=(b["x"] + ox, y + 8 + bob + drop + oy)))
        if b["state"] != "wreck":
            self._draw_crew(s, b["crew"], b["x"] + ox, y - 14 + bob + oy, "right" if facing_right else "left", b["state"] == "run")
        if b["state"] in ("stuck", "wreck"):
            n = int(self.total * 12)
            for off in (-48, 8, 50) if b["state"] == "stuck" else (-30, 26):
                flame = self.flames[(n + off) % 8]
                s.blit(flame, flame.get_rect(midbottom=(b["x"] + off + ox, y - 6 + drop + oy)))

    def draw(self, s, offset=(0, 0)):
        ox, oy = offset
        s.blit(self.base, (ox, oy))
        top = int(WATER_TOP + 20 - 40 * self.tide)
        s.blit(self.water, (ox, top + oy))
        pygame.draw.rect(s, (246, 234, 208), (0, top + oy, W, 4))
        for i in range(16):  # sóng trôi theo chiều con nước: vào sông khi triều lên, ra biển khi triều rút
            yy = top + 22 + i * 21
            xx = (i * 137 + self.flow * (0.7 + i * 0.03)) % (W + 80) - 40
            pygame.draw.rect(s, (246, 228, 192), (xx + ox, yy + oy, 40, 3))
        for lane in range(len(LANES)):
            y = LANES[lane]
            for ln, x in STAKES:
                if ln == lane:
                    self._draw_stake(s, x, y, ox, oy)
            for a in self.allies:
                if a["lane"] == lane:
                    fleeing = self.beat == "lure"
                    img = self.ally_back if fleeing else self.ally
                    s.blit(img, img.get_rect(midbottom=(a["x"] + ox, y + 8 + oy)))
                    self._draw_crew(s, a["crew"], a["x"] + ox, y - 8 + oy, "left" if fleeing else "right", fleeing)
            for b in self.boats:
                if b["lane"] == lane and b["state"] != "gone":
                    self._draw_enemy(s, b, ox, oy)
            for b in self.boats:  # cọc vẽ đè lên thân thuyền để thấy cọc đâm xuyên qua
                if b["lane"] == lane and b["state"] in ("stuck", "wreck") and b["doom"] is not None:
                    self._draw_stake(s, b["doom"], y, ox, oy)
        self._draw_jumpers(s, ox, oy)
        if self.beat == "ebb" and self.t >= PANIC_AT and int(self.total * 6) % 2 == 0:
            for b in self.boats:
                s.blit(self.alert, self.alert.get_rect(midbottom=(b["x"] + ox, LANES[b["lane"]] - 62 + oy)))

    def _draw_jumpers(self, s, ox, oy):
        for j in self.jumpers:
            b = j["boat"]
            tx, ty = b["x"] + j["off"], LANES[b["lane"]] - 14
            k = min(1.0, j["t"] / 0.5)
            cast = j["cast"]
            if j["phase"] == "jump":
                x, y = j["x0"] + (tx - j["x0"]) * k, j["y0"] + (ty - j["y0"]) * k - 90 * math.sin(k * math.pi)
                img = cast.walk["right"][1]
            elif j["phase"] == "fight":
                x, y = tx, ty
                img = cast.attack["right"] if int(j["t"] * 14) % 2 else cast.walk["right"][0]
            else:
                x, y = tx + (j["x0"] - tx) * k, ty + (j["y0"] - ty) * k - 80 * math.sin(k * math.pi)
                img = cast.walk["left"][1]
            s.blit(img, img.get_rect(midbottom=(x + ox, y + oy)))
