"""Trận đánh tương tác: Bạch Đằng (cọc và thuỷ triều), Chi Lăng (phục binh), Điện Biên Phủ (vây lấn).

Trận nào cũng kết thúc đúng lịch sử. Người chơi không thể "thua" mà chỉ nhận 1 đến 3 sao theo cách chỉ huy,
có thể đánh lại để lấy thêm sao. Diễn biến trong trận là mô phỏng đã đơn giản hoá, có ghi rõ trên màn hình.
"""

from __future__ import annotations

import math
import random

import pygame
from core import art, diorama, fleet, fonts, fx, sprites, theme, ui
from core.scene import Scene
from core.tilemap import PATH, RICE, WATER
from core.worldgen import stake_sprite

W, H = theme.WIDTH, theme.HEIGHT
NOTE = "Mô phỏng giáo dục: vị trí, nhịp trận và kỹ năng đã được cách điệu, kết cục trận đánh theo sử liệu."
_cache: dict[str, pygame.Surface] = {}


def _once(name, builder):
    if name not in _cache:
        _cache[name] = builder(random.Random(name))
    return _cache[name]


class BattleBase(Scene):
    howto = ""

    def __init__(self, app, battle: dict):
        super().__init__(app)
        self.b = battle
        self.fx = fx.Fx(self.state.settings["violence"])
        self.world = pygame.Surface((W, H))
        self.t = 0.0
        self.stage = "intro"
        self.stage_t = 0.0
        self.group = ui.ButtonGroup()
        self.retreat = ui.Button((W - 130, 12, 116, 36), "Rút lui", self._leave, "ghost", size=14)
        self.stars = 0
        self.report: list[str] = []
        self.setup()
        self.group.add(ui.Button((W // 2 - 280, 584, 270, 52), "Rút lui", self._leave, "ghost", size=17))
        self.group.add(ui.Button((W // 2 + 10, 584, 270, 52), "Vào trận", self._start, "gold"))

    # ----- khung chung -----
    def setup(self): ...

    def begin(self): ...

    def on_event(self, event): ...

    def step(self, dt): ...

    def draw_world(self, s): ...

    def draw_hud(self, screen): ...

    def _start(self):
        self.app.audio.play("trong")
        self.begin()

    def _leave(self):
        self.app.audio.play("click")
        self.app.scenes.pop(False)

    def goto(self, stage: str):
        self.stage = stage
        self.stage_t = 0.0
        self.group.clear()

    def finish(self, stars: int, report: list[str]):
        self.goto("result")
        self.stars = stars
        self.report = report
        st = self.state
        bid = self.b["id"]
        old = st.battle_stars.get(bid, 0)
        if stars > old:
            st.battle_stars[bid] = stars
            st.progress.points += 10 * (stars - old)
            self.report.append(f"Thưởng thêm: +{10 * (stars - old)} điểm kiến thức")
        for msg in st.check_badges():
            self.app.toast(msg, theme.GOLD_LIGHT, 4.0)
        st.save()
        self.app.audio.play("thang")
        cx = W // 2
        self.group.add(ui.Button((cx - 280, 610, 270, 50), "Đánh lại để lấy thêm sao", self._again, "ghost", size=17))
        self.group.add(ui.Button((cx + 10, 610, 270, 50), "Tiếp tục", lambda: self.app.scenes.pop(True), "gold"))

    def _again(self):
        self.app.scenes.replace(make_battle(self.app, self.b))

    def handle(self, event):
        if self.stage not in ("intro", "result") and self.retreat.handle(event):
            return
        if self.group.handle(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.stage != "result":
            self._leave()
            return
        if self.stage not in ("intro", "result"):
            self.on_event(event)

    def update(self, dt):
        self.t += dt
        self.stage_t += dt
        self.fx.update(dt)
        if self.stage != "intro":
            self.step(dt)

    def draw(self, screen):
        self.draw_world(self.world)
        self.fx.draw(self.world)
        screen.blit(self.world, self.fx.offset())
        if self.stage == "intro":
            self._draw_intro(screen)
        elif self.stage == "result":
            self._draw_result(screen)
        else:
            self.draw_hud(screen)
            self.retreat.draw(screen)
        self.group.draw(screen)

    def hud_text(self, screen, title, text, col=theme.PAPER):
        """Khung hướng dẫn ở góc trên bên trái, dùng chung cho mọi giai đoạn."""
        rect = pygame.Rect(14, 12, 800, 92)
        ui.lacquer_panel(screen, rect, 236)
        fonts.text(screen, title, fonts.font("serif", 20), theme.GOLD_LIGHT, (rect.x + 18, rect.y + 10))
        fonts.paragraph(screen, text, fonts.font("semi", 15), col, rect.x + 18, rect.y + 38, rect.w - 36, gap=1)

    def _draw_intro(self, screen):
        ui.veil(screen, (14, 8, 6, 170))
        rect = pygame.Rect(170, 40, 940, 610)
        ui.paper_panel(screen, rect)
        x, w = rect.x + 40, rect.w - 80
        ui.tag(screen, f"TRẬN ĐÁNH · {self.b.get('year', '')}", (x, rect.y + 22))
        y = fonts.paragraph(screen, self.b["title"], fonts.font("serif", 32), theme.INK, x, rect.y + 54, w)
        y = fonts.paragraph(screen, f"Ta: {self.b.get('ally', '')}   ·   Địch: {self.b.get('enemy', '')}", fonts.font("bold", 16), theme.LACQUER_RED, x, y + 4, w)
        y = fonts.paragraph(screen, self.b.get("intro", ""), fonts.font("serif", 19), theme.INK_SOFT, x, y + 10, w, gap=4)
        y = fonts.paragraph(screen, "Cách chơi: " + self.howto, fonts.font("semi", 16), theme.INK, x, y + 12, w, gap=3)
        fonts.paragraph(screen, NOTE, fonts.font("italic", 14), theme.INK_FAINT, x, rect.bottom - 86, w, gap=1)

    def _draw_result(self, screen):
        ui.veil(screen, (14, 8, 6, 180))
        rect = pygame.Rect(170, 30, 940, 650)
        ui.paper_panel(screen, rect)
        x, w = rect.x + 40, rect.w - 80
        fonts.text(screen, "CHIẾN THẮNG", fonts.font("black", 34), theme.LACQUER_RED, (rect.centerx, rect.y + 20), "midtop")
        fonts.text(screen, self.b["title"], fonts.font("serif", 20), theme.INK, (rect.centerx, rect.y + 66), "midtop")
        for i in range(3):
            cx = rect.centerx + (i - 1) * 74
            art._star(screen, cx + 2, rect.y + 132, 31, theme.GOLD_DARK)
            art._star(screen, cx, rect.y + 130, 30, theme.GOLD if i < self.stars else theme.PAPER_3)
        y = rect.y + 172
        for line in self.report:
            y = fonts.paragraph(screen, "• " + line, fonts.font("semi", 16), theme.INK, x, y, w, gap=2)
        y = fonts.paragraph(screen, self.b.get("victory", ""), fonts.font("serif", 18), theme.INK_SOFT, x, y + 8, w, gap=4)
        y = fonts.paragraph(screen, "Số sao phản ánh cách chỉ huy trong mô phỏng; kết cục trận đánh theo sử liệu.", fonts.font("italic", 14), theme.INK_FAINT, x, y + 6, w)
        cite = self.state.citation_text(self.b.get("citations"))
        if cite:
            fonts.paragraph(screen, "Nguồn: " + cite, fonts.font("italic", 13), theme.INK_FAINT, x, y + 2, w, gap=1)


# =====================================================================
# Bạch Đằng: cắm cọc, nhử địch, triều rút lộ cọc, thuyền địch đâm vào cọc mà vỡ
# =====================================================================
LANES = (405, 470, 535, 600)
COLS = tuple(720 + i * 54 for i in range(6))
LANE_BOATS = (2, 4, 4, 2)
BUDGET = 6
MIN_STAKES = 4
STAKE_CAP = 2
TIDE_FALL = 0.055
EBB_RATE = 0.2
WINDOW = (0.45, 0.62)
GAUGE = pygame.Rect(830, 62, 296, 24)
PANIC_TIME = 1.0
FLEE_SPEED = 165
BOW = 50  # thuyền lao tới khi cọc đã đâm sâu vào thân, không chỉ chạm mũi
STUCK_TIME = 2.2
SINK_TIME = 1.1
BURN_TIME = 1.5
SLOW_TIME = 0.7
SLOW_SCALE = 0.3
ENEMY_W, ALLY_W = 160, 120
SKILLS = (
    {"id": "lua", "name": "Tên lửa", "key": pygame.K_1, "cd": 3.0, "icon": "ui/skill_fire.png"},
    {"id": "lao", "name": "Phóng lao", "key": pygame.K_2, "cd": 2.0, "icon": "ui/skill_spear.png"},
    {"id": "xung", "name": "Xung phong", "key": pygame.K_3, "cd": 4.5, "icon": "ui/skill_cut.png"},
)
SKILL_Y = 632
MAX_POPS = 3


def _tide_bank(b):
    """Bờ sông bên kia: núi đá, rừng, nhà ven sông."""
    for x, name in ((0, "gray_big"), (5, "gray_tall"), (8, "pines"), (12, "gray_big"), (17, "gray_tall"), (19, "pines")):
        b.put(name, x, 0, True)
    for x, name in ((1, "tree"), (4, "bamboo"), (7, "hut"), (11, "tree"), (15, "bamboo"), (16, "tree"), (18, "hut2")):
        b.put(name, x, 3, True)


def _tide_bg(_rng):
    return diorama.render("tide", 20, 6, _tide_bank)


def _river(_rng):
    """Mặt sông lát bằng tile nước, tối hơn một chút cho hợp cảnh trận."""
    s = pygame.Surface((W, 480))
    tile = sprites.region("water", 1, 7)
    for y in range(0, 480, sprites.TILE):
        for x in range(0, W, sprites.TILE):
            s.blit(tile, (x, y))
    shade = pygame.Surface((W, 480))
    shade.fill((30, 70, 90))
    shade.set_alpha(70)
    s.blit(shade, (0, 0))
    return s


def _mud(_rng):
    s = pygame.Surface((W, 90))
    tile = sprites.region("floor", 0, 5)
    for x in range(0, W, sprites.TILE):
        for y in range(0, 90, sprites.TILE):
            s.blit(tile, (x, y))
    s.fill((150, 120, 100), special_flags=pygame.BLEND_RGB_MULT)
    return s


class TideBattle(BattleBase):
    howto = (
        "Triều xuống thì cắm cọc vào các luồng sông, luồng đông thuyền địch cần nhiều cọc hơn. Triều lên che kín cọc thì "
        "cho thuyền nhẹ giả thua, nhử địch vượt qua bãi cọc. Bấm PHẢN CÔNG khi kim mức nước vào vạch vàng: triều rút, "
        "cọc lộ ra, thuyền địch quay đầu sẽ đâm vào cọc. Dùng kỹ năng 1, 2, 3 để chặn những thuyền còn thoát."
    )

    def setup(self):
        self.tide = 0.1
        self.flow = 0.0
        self.stakes: set[tuple[int, int]] = set()
        self.hover = None
        self.boats: list[dict] = []
        self.allies: list[dict] = []
        self.jumpers: list[dict] = []
        self.pops: list[list] = []
        self.ready = False
        self.impaled = 0
        self.burned = 0
        self.timing = ""
        self.factor = 1.0
        self.volley_t = 0.0
        self.end_t = 0.0
        self.panic = 0.0
        self.slow = 0.0
        self.first_hit = True
        self.cds = {sk["id"]: 0.0 for sk in SKILLS}
        self.skill_btns: dict[str, ui.Button] = {}
        self.bg = _once("tide", _tide_bg)
        self.river = _once("river", _river)
        self.mud = _once("mud", _mud)
        self.shallow = pygame.Surface((W, 480))
        self.shallow.fill((206, 176, 120))
        sail = (150, 62, 50) if self.b.get("year", 0) > 1000 else (206, 190, 150)
        self.enemy_img = pygame.transform.flip(fleet.boat_sprite(ENEMY_W, (150, 136, 150), sail=sail), True, False)
        self.enemy_back = pygame.transform.flip(self.enemy_img, True, False)
        self.ally_img = fleet.boat_sprite(ALLY_W, flag=(196, 40, 34))
        foe = "LinhNguyen" if self.b.get("year", 0) > 1000 else "LinhTong"  # năm 1288 quân Nguyên, năm 938 quân Nam Hán
        self.c_enemy = (sprites.cast(foe, 3), sprites.cast(foe, 3))
        self.c_ally = (sprites.cast("LinhDaiViet", 3), sprites.cast("LinhDaiViet2", 3))
        self.arrow = sprites.icon("fx/arrow.png", 3)
        self.lance = pygame.transform.rotate(sprites.icon("fx/lance.png", 3), -90)
        self.fireball = sprites.strip("fx/fireball.png", 4, 3)
        self.flames = sprites.strip("fx/flame.png", 8, 2)
        self._rot: dict[tuple, pygame.Surface] = {}

    @property
    def broken(self) -> int:
        return self.impaled + self.burned

    def begin(self):
        self.goto("plant")
        self._plant_button()

    def update(self, dt):
        # Chậm lại một nhịp lúc thuyền đầu tiên đâm vào cọc
        if self.slow > 0:
            self.slow -= dt
            dt *= SLOW_SCALE
        super().update(dt)

    # ----- giai đoạn 1: cắm cọc -----
    def _plant_button(self):
        self.group.clear()
        n = len(self.stakes)
        label = f"Xong, chờ triều lên ({n}/{BUDGET} hàng cọc)" if n >= MIN_STAKES else f"Cắm ít nhất {MIN_STAKES} hàng cọc ({n}/{BUDGET})"
        self.group.add(ui.Button((W - 400, 648, 380, 58), label, self._to_flood, "gold", n >= MIN_STAKES, 17))

    @staticmethod
    def _cell(lane, col):
        return pygame.Rect(COLS[col] - 25, LANES[lane] - 27, 50, 54)

    def _cell_at(self, pos):
        for lane in range(4):
            for col in range(6):
                if self._cell(lane, col).collidepoint(pos):
                    return lane, col
        return None

    def on_event(self, event):
        if self.stage == "strike" and event.type == pygame.KEYDOWN:
            for sk in SKILLS:
                if event.key == sk["key"]:
                    self._cast(sk)
            return
        if self.stage != "plant":
            return
        if event.type == pygame.MOUSEMOTION:
            self.hover = self._cell_at(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            cell = self._cell_at(event.pos)
            if cell is None:
                return
            if cell in self.stakes:
                self.stakes.remove(cell)
            elif len(self.stakes) < BUDGET:
                self.stakes.add(cell)
                self.fx.splash(COLS[cell[1]], LANES[cell[0]], 8)
                self.app.audio.play("va")
            self._plant_button()

    def _crew(self, casts, offsets):
        return [{"cast": casts[i % 2], "off": off, "alive": True, "atk": 0.0} for i, off in enumerate(offsets)]

    def _to_flood(self):
        self.goto("flood")
        self.ready = False
        for lane, count in enumerate(LANE_BOATS):
            for j in range(count):
                self.boats.append({
                    "lane": lane, "x": 1460.0 + j * 120 + lane * 16, "form": 1090 + j * 110 + (lane % 2) * 55,
                    "bait": 250 + j * 100 + (lane % 2) * 50, "state": "run", "doom": None, "t": 0.0, "cd": 0.0, "burn": None,
                    "crew": self._crew(self.c_enemy, (-44, 0, 44)),
                })
        for i in range(5):
            self.allies.append({
                "lane": i % 4, "x": -80.0 - i * 60, "form": 820 + (i % 2) * 110, "bait": 70 + (i % 2) * 70,
                "crew": self._crew(self.c_ally, (-24, 24)),
            })

    # ----- giai đoạn 2, 3: nhử rồi phản công -----
    def _to_lure(self):
        self.goto("lure")
        self.app.audio.play("trong")
        self.group.add(ui.Button((W - 400, 648, 380, 58), "PHẢN CÔNG!", self._strike, "primary", size=24))

    def _strike(self):
        if self.tide > WINDOW[1]:
            self.factor = 0.7
            self.timing = "Phản công hơi sớm: nước còn cao, cọc chưa nhô lên, nhiều thuyền lọt qua."
        elif self.tide >= WINDOW[0]:
            self.factor = 1.0
            self.timing = "Phản công đúng lúc: triều rút mạnh, cọc nhô lên ngay dưới mạn thuyền."
        else:
            self.factor = 0.45
            self.timing = "Phản công muộn: địch đã thấy nước rút và quay đầu trước."
        doomed = []
        for lane in range(4):
            boats = sorted((b for b in self.boats if b["lane"] == lane), key=lambda b: -b["x"])
            taken = set()
            for col in sorted(c for ln, c in self.stakes if ln == lane):
                n = 0
                for b in boats:
                    if id(b) in taken or b["x"] >= COLS[col]:
                        continue
                    b["doom"] = COLS[col]
                    taken.add(id(b))
                    doomed.append(b)
                    n += 1
                    if n == STAKE_CAP:
                        break
        random.shuffle(doomed)
        keep = round(len(doomed) * self.factor)
        for b in doomed[keep:]:
            b["doom"] = None
        self.impaled = keep
        self.goto("strike")
        self.panic = PANIC_TIME
        self.app.audio.play("trong")
        self.fx.shake(6)
        self._skill_bar()

    def _skill_bar(self):
        self.skill_btns = {}
        x = 300
        for i, sk in enumerate(SKILLS):
            btn = ui.Button((x + i * 226, SKILL_Y, 216, 74), "", lambda s=sk: self._cast(s), "primary")
            self.skill_btns[sk["id"]] = btn
            self.group.add(btn)

    # ----- kỹ năng -----
    def _pop(self, text, x, y, color=theme.GOLD_LIGHT):
        if len(self.pops) < MAX_POPS:  # nhiều thuyền va cùng lúc thì không để chữ chồng lên nhau
            self.pops.append([text, x, y, 1.1, color])

    def _shooters(self):
        return [(a, c) for a in self.allies for c in a["crew"] if c["alive"]]

    def _escaping(self):
        """Thuyền sắp thoát (không vướng cọc, chưa cháy) được ưu tiên, gần thoát nhất trước."""
        run = [b for b in self.boats if b["state"] == "run" and b["burn"] is None]
        return sorted(run, key=lambda b: (b["doom"] is not None, -b["x"]))

    def _cast(self, sk):
        sid = sk["id"]
        if self.stage != "strike" or self.cds[sid] > 0:
            return
        done = {"lua": self._cast_fire, "lao": self._cast_spear, "xung": self._cast_charge}[sid]()
        if done:
            self.cds[sid] = sk["cd"] * self.state.cd_mult()
        else:
            self._pop("Không còn mục tiêu", W / 2, 300)

    def _muzzle(self, b):
        """Vị trí bắn ra từ thuyền ta gần mục tiêu nhất, đồng thời cho lính trên đó vào tư thế đánh."""
        ally = min(self.allies, key=lambda a: abs(LANES[a["lane"]] - LANES[b["lane"]]) + abs(a["x"] - b["x"]) * 0.2)
        for c in ally["crew"]:
            c["atk"] = 0.35
        return ally["x"] + 30, LANES[ally["lane"]] - 40

    def _lead(self, b, x0, y0, speed):
        """Bắn đón đầu vì thuyền địch vẫn đang chạy."""
        y1 = LANES[b["lane"]] - 30
        moving = FLEE_SPEED if b["state"] == "run" and self.panic <= 0 else 0
        flight = math.hypot(b["x"] - x0, y1 - y0) / speed
        return b["x"] + moving * flight, y1

    def _cast_fire(self):
        targets = self._escaping()
        if not targets:
            return False
        b = targets[0]
        x0, y0 = self._muzzle(b)
        self.app.audio.play("lua")
        for i in range(3):
            x1, y1 = self._lead(b, x0, y0, 760)
            self.fx.shoot(self.fireball, x0, y0, x1 + (i - 1) * 26, y1, 760, 100 + i * 24, lambda bb=b: self._fire_hit(bb))
        return True

    def _fire_hit(self, b):
        if b["state"] not in ("run", "stuck"):
            return
        self.fx.play("fx/explosion.png", 9, b["x"], LANES[b["lane"]] - 30, 18, False, 2)
        self.fx.shake(3)
        self.app.audio.play("no")
        if b["state"] == "run" and b["burn"] is None:
            b["burn"] = BURN_TIME
            self._pop("Bốc cháy!", b["x"], LANES[b["lane"]] - 90, (255, 170, 80))

    def _cast_spear(self):
        targets = [b for b in self.boats if b["state"] in ("run", "stuck")]
        targets.sort(key=lambda b: (b["state"] != "run", b["doom"] is not None, -b["x"]))
        victims = [(b, c) for b in targets for c in b["crew"] if c["alive"]][:4]
        if not victims:
            return False
        self.app.audio.play("ban")
        for b, c in victims:
            x0, y0 = self._muzzle(b)
            x1, y1 = self._lead(b, x0, y0, 900)
            self.fx.shoot(self.lance, x0, y0, x1 + c["off"], y1, 900, 50, lambda bb=b, cc=c: self._spear_hit(bb, cc))
        return True

    def _kill(self, b, c):
        c["alive"] = False
        x, y = b["x"] + c["off"], LANES[b["lane"]] - 34
        self.fx.blood(x, y, 16)
        self.fx.fall(x, y)
        self.app.audio.play("chem")

    def _spear_hit(self, b, c):
        if b["state"] not in ("run", "stuck") or not c["alive"]:
            return
        self._kill(b, c)
        if b["state"] == "run" and b["burn"] is None and not any(m["alive"] for m in b["crew"]):
            b["burn"] = BURN_TIME  # không còn người chèo lái, thuyền trôi dạt và bị đốt
            self._pop("Bỏ thuyền!", b["x"], LANES[b["lane"]] - 90)

    def _cast_charge(self):
        stuck = [b for b in self.boats if b["state"] == "stuck"]
        run = self._escaping()
        target = stuck[0] if stuck else (run[0] if run else None)
        if target is None:
            return False
        x0, y0 = self._muzzle(target)
        self.app.audio.play("kiem")
        for i in (-1, 1):
            self.jumpers.append({
                "cast": self.c_ally[(i + 1) // 2], "x0": x0, "y0": y0 + 26, "boat": target, "off": i * 26,
                "t": 0.0, "phase": "jump",
            })
        return True

    def _board(self, b):
        """Lính ta vừa đáp xuống thuyền địch: chém hạ toàn bộ người trên thuyền."""
        y = LANES[b["lane"]] - 34
        self.fx.play("fx/cutx.png", 4, b["x"], y, 14, False, 3)
        self.fx.play("fx/curved.png", 4, b["x"] + 26, y - 6, 14, True, 3)
        self.fx.shake(5)
        self.app.audio.play("chem")
        for c in b["crew"]:
            if c["alive"]:
                self._kill(b, c)
        if b["state"] == "run" and b["burn"] is None:
            b["burn"] = BURN_TIME
            self._pop("Chiếm thuyền!", b["x"], y - 60)
        elif b["state"] == "stuck":
            b["t"] = max(b["t"], STUCK_TIME - 0.9)

    # ----- cập nhật -----
    def step(self, dt):
        for side in (self.boats, self.allies):
            for item in side:
                for c in item["crew"]:
                    c["atk"] = max(0.0, c["atk"] - dt)
        for pop in self.pops:
            pop[2] -= 34 * dt
            pop[3] -= dt
        self.pops = [p for p in self.pops if p[3] > 0]
        fn = {"flood": self._step_flood, "lure": self._step_lure, "strike": self._step_strike}.get(self.stage)
        if fn:
            fn(dt)

    def _auto_fire(self, dt, enemy_shoots=True):
        """Cung thủ hai bên tự bắn nhau cho trận thêm sống động."""
        self.volley_t -= dt
        if self.volley_t > 0:
            return
        self.volley_t = random.uniform(0.3, 0.55)
        foes = [b for b in self.boats if b["state"] in ("run", "stuck") and -40 < b["x"] < W + 40]
        pairs = self._shooters()
        if not foes or not pairs:
            return
        ally, c = random.choice(pairs)
        c["atk"] = 0.3
        t = random.choice(foes)
        self.fx.shoot(self.arrow, ally["x"] + c["off"], LANES[ally["lane"]] - 44, t["x"] + random.randint(-40, 40), LANES[t["lane"]] - 30, 700, 34, lambda x=t["x"], y=LANES[t["lane"]]: self.fx.burst(x, y - 30, 4, [(255, 236, 170)], 90, 0.25, 3, 100))
        if enemy_shoots:
            b = random.choice(foes)
            shooter = [m for m in b["crew"] if m["alive"]]
            if shooter:
                shooter[0]["atk"] = 0.3
                a = random.choice(self.allies)
                self.fx.shoot(pygame.transform.flip(self.arrow, True, False), b["x"], LANES[b["lane"]] - 44, a["x"] + random.randint(-50, 50), LANES[a["lane"]] - 14, 640, 30, lambda x=a["x"], y=LANES[a["lane"]]: self.fx.splash(x + random.randint(-60, 60), y + 6, 4))

    def _step_flood(self, dt):
        self.tide = min(1.0, self.tide + dt / 2.6)
        self.flow -= 60 * dt
        for b in self.boats:
            b["x"] = max(b["form"], b["x"] - 175 * dt)
        for a in self.allies:
            a["x"] = min(a["form"], a["x"] + 260 * dt)
        if not self.ready and self.tide >= 1.0 and all(b["x"] <= b["form"] + 2 for b in self.boats):
            self.ready = True
            self.group.add(ui.Button((W - 400, 648, 380, 58), "Khiêu chiến rồi giả thua", self._to_lure, "gold", size=20))
        if self.ready:
            self._auto_fire(dt)

    def _step_lure(self, dt):
        self.tide -= TIDE_FALL * dt
        self.flow += 40 * dt
        for b in self.boats:
            b["x"] = max(b["bait"], b["x"] - 138 * dt)
        for a in self.allies:
            a["x"] = max(a["bait"], a["x"] - 210 * dt)
        self._auto_fire(dt)
        if self.tide <= 0.2:
            self._strike()

    def _impact(self, b):
        """Khoảnh khắc thuyền đâm vào cọc: mảnh gỗ văng, nước bắn, người ngã, chậm lại một nhịp."""
        y = LANES[b["lane"]]
        b["state"], b["cd"], b["t"] = "stuck", 0.0, 0.0
        bow = b["x"] + BOW * 0.7
        self.fx.splinters(bow, y - 10, 16)
        self.fx.debris(bow, y - 16, 12)
        self.fx.splash(bow, y, 18)
        self.fx.shake(9)
        self.app.audio.play("va")
        self._pop("Đâm cọc!", b["x"], y - 96, (255, 214, 120))
        victim = next((c for c in b["crew"] if c["alive"]), None)
        if victim:
            self._kill(b, victim)
        if self.first_hit:
            self.first_hit = False
            self.slow = SLOW_TIME

    def _step_strike(self, dt):
        self.tide = max(0.08, self.tide - EBB_RATE * dt)
        self.flow += 150 * dt
        self.panic = max(0.0, self.panic - dt)
        for key in self.cds:
            self.cds[key] = max(0.0, self.cds[key] - dt)
        for sk in SKILLS:
            btn = self.skill_btns.get(sk["id"])
            if btn:
                btn.enabled = self.cds[sk["id"]] <= 0
        active = False
        for b in self.boats:
            if b["state"] != "gone":
                active = True
                self._step_boat(b, dt)
        self._step_allies(dt)
        self._step_jumpers(dt)
        self._auto_fire(dt, enemy_shoots=self.panic <= 0)
        if not active and not self.jumpers:
            self.end_t += dt
            if self.end_t > 1.0:
                total = sum(LANE_BOATS)
                ratio = self.broken / total
                stars = 3 if ratio >= 0.85 else 2 if ratio >= 0.55 else 1
                self.finish(stars, [
                    f"Thuyền địch bị phá trong mô phỏng: {self.broken}/{total} (vỡ trên cọc {self.impaled}, bị đốt hoặc chiếm {self.burned})",
                    self.timing,
                    f"Số hàng cọc đã cắm: {len(self.stakes)}/{BUDGET}",
                ])

    def _step_boat(self, b, dt):
        y = LANES[b["lane"]]
        if b["state"] == "run":
            if b["burn"] is not None:
                b["burn"] -= dt
                self.fx.fire(b["x"] + random.uniform(-50, 50), y - 28, 1, 20)
                if random.random() < dt * 5:
                    self.fx.smoke(b["x"], y - 50, 1, 30)
                b["x"] += FLEE_SPEED * 0.35 * dt
                if b["burn"] <= 0:
                    self.burned += 1
                    b["state"], b["t"] = "sink", 0.0
                    self.fx.debris(b["x"], y - 16, 10)
                return
            if self.panic > 0:
                return
            b["x"] += FLEE_SPEED * dt
            if b["doom"] is not None and b["x"] >= b["doom"] - BOW:
                self._impact(b)
            elif b["x"] > W + 120:
                b["state"] = "gone"
        elif b["state"] == "stuck":
            b["t"] += dt
            b["cd"] -= dt
            self.fx.fire(b["x"] + random.uniform(-30, 60), y - 26, 1, 16)
            if b["cd"] <= 0:
                b["cd"] = random.uniform(0.45, 0.8)
                self.fx.smoke(b["x"], y - 44, 1, 24)
                victim = next((c for c in b["crew"] if c["alive"]), None)
                if victim and b["t"] > 0.6:
                    self.fx.clash(b["x"] + victim["off"], y - 34)
                    self._kill(b, victim)
            if b["t"] > STUCK_TIME:
                b["state"], b["t"] = "sink", 0.0
                self.fx.debris(b["x"], y - 16, 8)
        elif b["state"] == "sink":
            b["t"] += dt
            if random.random() < dt * 8:
                self.fx.splash(b["x"] + random.uniform(-60, 60), y + 4, 4)
            if b["t"] > SINK_TIME:
                b["state"] = "gone"
                self.fx.splash(b["x"], y, 12)
                self.app.audio.play("nuoc")

    def _step_allies(self, dt):
        for a in self.allies:
            near = [b["x"] for b in self.boats if b["lane"] == a["lane"] and b["state"] in ("stuck", "sink")]
            goal = min(near) - 190 if near else min(COLS[0] - 150.0, a["x"] + 90)
            if a["x"] < goal:
                a["x"] += 210 * dt

    def _step_jumpers(self, dt):
        for j in self.jumpers:
            j["t"] += dt
            if j["phase"] == "jump" and j["t"] >= 0.5:
                j["phase"], j["t"] = "fight", 0.0
                if j["off"] < 0:
                    self._board(j["boat"])
            elif j["phase"] == "fight" and j["t"] >= 0.55:
                j["phase"], j["t"] = "back", 0.0
            elif j["phase"] == "back" and j["t"] >= 0.5:
                j["phase"] = "done"
        self.jumpers = [j for j in self.jumpers if j["phase"] != "done"]

    # ----- vẽ -----
    def _ebb(self) -> float:
        """0 khi nước che kín cọc, 1 khi cọc lộ hoàn toàn."""
        return max(0.0, min(1.0, (0.74 - self.tide) / 0.6))

    def _stake(self, s, x, y):
        k = self._ebb()
        if k <= 0.02:
            return
        shoal = fleet.shoal(min(3, int(k * 4)))
        s.blit(shoal, shoal.get_rect(center=(x, y + 2)))
        img = stake_sprite()
        h = int(img.get_height() * k)  # cọc nhô dần: chỉ vẽ phần ngọn tương ứng với mức triều
        s.blit(img, (x - img.get_width() / 2, y + 4 - h), (0, 0, img.get_width(), h))

    def _rotated(self, img, deg):
        key = (id(img), int(deg))
        out = self._rot.get(key)
        if out is None:
            out = pygame.transform.rotate(img, int(deg))
            self._rot[key] = out
        return out

    def _draw_crew(self, s, crew, x, feet, facing, moving):
        for i, c in enumerate(crew):
            cast = c["cast"]
            if not c["alive"]:
                img = cast.dead
            elif c["atk"] > 0:
                img = cast.attack[facing]
            else:
                img = cast.walk[facing][int(self.t * 7 + i) % 4 if moving else 0]
            s.blit(img, (x + c["off"] - cast.size / 2, feet - cast.size))

    def _draw_boat(self, s, b):
        y = LANES[b["lane"]]
        fleeing = self.stage == "strike"
        img = self.enemy_back if fleeing else self.enemy_img
        bob = math.sin(self.t * 2.4 + b["x"] * 0.02) * 2
        state = b["state"]
        drop = 0.0
        if state == "stuck":
            img = self._rotated(img, -4 - min(1.0, b["t"]) * 8)
        elif state == "sink":
            k = b["t"] / SINK_TIME
            img = self._rotated(img, -12 - k * 24).copy()
            img.set_alpha(max(0, int(255 * (1 - k))))
            drop = k * 34
        s.blit(img, img.get_rect(midbottom=(b["x"], y + 8 + bob + drop)))
        if state in ("run", "stuck"):
            self._draw_crew(s, b["crew"], b["x"], y - 14 + bob, "right" if fleeing else "left", state == "run")
        if state == "stuck" or b["burn"] is not None:
            n = int(self.t * 12)
            for off in (-48, 8, 50):
                flame = self.flames[(n + off) % 8]
                s.blit(flame, flame.get_rect(midbottom=(b["x"] + off, y - 8)))

    def draw_world(self, s):
        s.blit(self.bg, (0, 0))
        s.blit(self.mud, (0, 290))
        top = int(362 - 62 * self.tide)
        s.blit(self.river, (0, top))
        ebb = self._ebb()
        if ebb > 0:  # nước cạn dần: mặt sông nhạt đi, thấy đáy bùn
            self.shallow.set_alpha(int(70 * ebb))
            s.blit(self.shallow, (0, top))
        pygame.draw.rect(s, (236, 246, 246), (0, top, W, 4))
        for i in range(18):  # sóng trôi theo chiều con nước
            yy = top + 22 + i * 21
            xx = (i * 137 + self.flow * (0.7 + i * 0.03)) % (W + 80) - 40
            pygame.draw.rect(s, (168, 224, 236), (xx, yy, 40, 3))
        if self.stage == "plant":
            for lane in range(4):
                ui.tag(s, f"Luồng {lane + 1}: {LANE_BOATS[lane]} thuyền", (COLS[0] - 44, LANES[lane]), theme.LACQUER, theme.GOLD_LIGHT, 13, "midright")
                for col in range(6):
                    r = self._cell(lane, col)
                    hot = self.hover == (lane, col)
                    pygame.draw.rect(s, theme.GOLD_LIGHT if hot else (190, 224, 220), r, 3 if hot else 1)
        for lane in range(4):
            for ln, col in self.stakes:
                if ln == lane:
                    self._stake(s, COLS[col], LANES[lane])
            for a in self.allies:
                if a["lane"] == lane:
                    s.blit(self.ally_img, self.ally_img.get_rect(midbottom=(a["x"], LANES[lane] + 8)))
                    facing = "left" if self.stage == "lure" else "right"
                    self._draw_crew(s, a["crew"], a["x"], LANES[lane] - 8, facing, self.stage == "lure")
            for b in self.boats:
                if b["lane"] == lane and b["state"] != "gone":
                    self._draw_boat(s, b)
            # cọc vẽ đè lên thân thuyền để thấy cọc đâm xuyên qua
            for b in self.boats:
                if b["lane"] == lane and b["state"] in ("stuck", "sink") and b["doom"] is not None:
                    self._stake(s, b["doom"], LANES[lane])
        self._draw_jumpers(s)
        if self.stage == "strike" and self.panic > 0:
            icon = sprites.icon("ui/emote_alert.png", 3)
            for b in self.boats:
                if b["state"] == "run":
                    s.blit(icon, icon.get_rect(midbottom=(b["x"], LANES[b["lane"]] - 62)))
        for text, x, y, _t, col in self.pops:
            fonts.text(s, text, fonts.font("black", 20), col, (x, y), "center", shadow=(24, 16, 14))

    def _draw_jumpers(self, s):
        for j in self.jumpers:
            b = j["boat"]
            tx, ty = b["x"] + j["off"], LANES[b["lane"]] - 14
            k = min(1.0, j["t"] / 0.5)
            if j["phase"] == "jump":
                x, y = j["x0"] + (tx - j["x0"]) * k, j["y0"] + (ty - j["y0"]) * k - 90 * math.sin(k * math.pi)
                img = j["cast"].walk["right"][1]
            elif j["phase"] == "fight":
                x, y = tx, ty
                img = j["cast"].attack["right"] if int(j["t"] * 14) % 2 else j["cast"].walk["right"][0]
            else:
                x, y = tx + (j["x0"] - tx) * k, ty + (j["y0"] - ty) * k - 80 * math.sin(k * math.pi)
                img = j["cast"].walk["left"][1]
            s.blit(img, img.get_rect(midbottom=(x, y)))

    def draw(self, screen):
        super().draw(screen)
        if self.stage == "strike":
            self._draw_skill_labels(screen)

    def _draw_skill_labels(self, screen):
        for i, sk in enumerate(SKILLS):
            btn = self.skill_btns.get(sk["id"])
            if not btn:
                continue
            r = btn.rect
            icon = sprites.icon(sk["icon"], 2)
            screen.blit(icon, (r.x + 12, r.y + 12))
            fonts.text(screen, f"{i + 1}. {sk['name']}", fonts.font("semi", 16), theme.GOLD_LIGHT, (r.x + 68, r.y + 14))
            left = self.cds[sk["id"]]
            if left > 0:
                ui.alpha_rect(screen, (r.x + 3, r.y + 3, r.w - 6, r.h - 6), (10, 8, 8, 150))
                fonts.text(screen, f"{left:.1f}s", fonts.font("bold", 20), theme.WHITE, (r.x + 112, r.y + 34))
            else:
                fonts.text(screen, "Sẵn sàng", fonts.font("ui", 13), theme.PAPER, (r.x + 68, r.y + 38))

    def draw_hud(self, screen):
        title = self.b["title"]
        if self.stage == "plant":
            left = BUDGET - len(self.stakes)
            self.hud_text(screen, title, f"Triều đang xuống. Bấm vào ô để cắm cọc đầu bịt sắt (bấm lại để gỡ). Mỗi hàng cọc chặn được khoảng {STAKE_CAP} thuyền. Còn {left} hàng cọc.")
        elif self.stage == "flood":
            msg = "Thuyền địch đã vào cửa sông. Cho thuyền nhẹ khiêu chiến rồi giả thua để nhử chúng." if self.ready else "Triều lên, nước che kín bãi cọc. Đoàn thuyền địch tiến vào..."
            self.hud_text(screen, title, msg)
        elif self.stage == "lure":
            self.hud_text(screen, title, "Địch hăng hái đuổi theo qua bãi cọc. Nhìn thước triều: bấm PHẢN CÔNG khi kim trắng vào vạch vàng.", theme.GOLD_LIGHT)
        elif self.panic > 0:
            self.hud_text(screen, title, "Nước rút rồi! Cọc nhô khỏi mặt sông. Quân địch hoảng loạn, vội quay đầu chạy ra biển...", theme.GOLD_LIGHT)
        else:
            self.hud_text(screen, title, "Thuyền địch đâm vào cọc mà vỡ! Dùng kỹ năng (phím 1, 2, 3) để chặn những thuyền đang thoát.", theme.GOLD_LIGHT)
        if self.stage != "plant":
            self._gauge(screen)

    def _gauge(self, screen):
        g = GAUGE
        ui.lacquer_panel(screen, (g.x - 16, 12, g.w + 32, 92), 236)
        fonts.text(screen, "Thước triều (trái là cạn, phải là cao)", fonts.font("semi", 13), theme.PAPER, (g.centerx, 24), "midtop")
        pygame.draw.rect(screen, (40, 58, 62), g)
        w = int(g.w * self.tide)
        pygame.draw.rect(screen, (92, 150, 160), (g.x, g.y, w, g.h))
        a, b = g.x + int(g.w * WINDOW[0]), g.x + int(g.w * WINDOW[1])
        ui.alpha_rect(screen, (a, g.y, b - a, g.h), (*theme.GOLD_LIGHT, 180))
        x = g.x + w
        pygame.draw.line(screen, theme.WHITE, (x, g.y - 6), (x, g.bottom + 6), 3)
        pygame.draw.rect(screen, theme.GOLD_DARK, g, 2)


# =====================================================================
# Chi Lăng: chọn chỗ phục binh, nhử Liễu Thăng vào gò Mã Yên
# =====================================================================
SPOTS = (
    {"id": "ma_yen", "name": "Sườn núi cạnh gò Mã Yên", "x": 500, "y": 430, "value": 3, "note": "Núi đá sát đường, nhìn thẳng xuống chỗ hẹp nhất của thung lũng."},
    {"id": "rung", "name": "Rừng rậm ven đường", "x": 760, "y": 440, "value": 3, "note": "Che kín quân, ngay khúc đường đoàn quân địch phải kéo dài đội hình."},
    {"id": "lay", "name": "Ven bãi lầy", "x": 300, "y": 620, "value": 2, "note": "Ngựa nặng dễ sa lầy, chặn được đường chạy của tiền quân địch."},
    {"id": "doi", "name": "Đồi trống giữa thung", "x": 950, "y": 440, "value": 1, "note": "Quan sát tốt nhưng ít cây che, trinh sát địch dễ phát hiện."},
    {"id": "cua_ai", "name": "Ngay cửa ải phía bắc", "x": 1170, "y": 440, "value": 1, "note": "Đánh ở đây quá sớm: địch chưa vào sâu, dễ rút lui."},
    {"id": "xa", "name": "Bờ sông phía xa", "x": 90, "y": 620, "value": 0, "note": "Quá xa chiến trường, phục binh không kịp đổ ra."},
)
ZONE = (460, 660)
ROAD_Y = (508, 572)
BEST_VALUE = 8


def _valley_tiles(b):
    b.stroke([(0, 8), (20, 8)], PATH, 2)
    b.rect(4, 10, 8, 2, WATER)  # bãi lầy cạnh đường
    for x, name in ((0, "gray_big"), (5, "gray_tall"), (9, "gray_big"), (14, "gray_tall"), (17, "gray_big")):
        b.put(name, x, 0, True)
    for x, name in ((1, "bamboo"), (3, "pine"), (12, "pine"), (16, "bamboo"), (18, "pine")):
        b.put(name, x, 3, True)
    for x, name in ((0, "pine"), (13, "tree"), (15, "bamboo"), (17, "pine"), (2, "bamboo"), (19, "tree")):
        b.put(name, x, 10, True)
    b.put("gray_tall", 8, 4, True)  # gò Mã Yên


def _valley_bg(_rng):
    return diorama.render("valley", 20, 12, _valley_tiles)


class AmbushBattle(BattleBase):
    howto = (
        "Chọn 3 trong 6 chỗ phục binh: chỗ che được quân và sát khúc đường hẹp thì hiệu quả hơn. Trần Lựu giả thua nhử "
        "Liễu Thăng chạy vào thung lũng. Bấm PHỤC BINH khi cờ đỏ của Liễu Thăng đi vào vùng gò Mã Yên."
    )

    def setup(self):
        self.chosen: list[dict] = []
        self.hover = None
        self.enemy: list[dict] = []
        self.squad: list[dict] = []
        self.ally: list[dict] = []
        self.leader = None
        self.timing = ""
        self.factor = 1.0
        self.volley_t = 0.0
        self.kill_t = 0.0
        self.to_kill = 0
        self.fell = False
        self.bg = _once("valley", _valley_bg)
        self.c_enemy = sprites.cast("LinhMinh", 3)
        self.c_ally = sprites.cast("NghiaQuan", 3)
        self.c_lead = sprites.cast("TuongMinh", 4)
        self.c_tran = sprites.cast("TuongDaiViet", 4)

    def begin(self):
        self.goto("place")
        self._place_button()

    def _place_button(self):
        self.group.clear()
        n = len(self.chosen)
        label = "Cho Trần Lựu ra nhử địch" if n == 3 else f"Chọn đủ 3 chỗ phục binh ({n}/3)"
        self.group.add(ui.Button((W - 400, 636, 380, 58), label, self._to_lure, "gold", n == 3, 18))

    def _spot_at(self, pos):
        for sp in SPOTS:
            if (sp["x"] - pos[0]) ** 2 + (sp["y"] - pos[1]) ** 2 <= 34 ** 2:
                return sp
        return None

    def on_event(self, event):
        if self.stage != "place":
            return
        if event.type == pygame.MOUSEMOTION:
            self.hover = self._spot_at(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            sp = self._spot_at(event.pos)
            if not sp:
                return
            if sp in self.chosen:
                self.chosen.remove(sp)
            elif len(self.chosen) < 3:
                self.chosen.append(sp)
            self.app.audio.play("click")
            self._place_button()

    def _to_lure(self):
        self.goto("lure")
        rng = random.Random(1427)
        self.squad = [{"x": 1290.0 + i * 34, "y": rng.uniform(*ROAD_Y)} for i in range(5)]
        for i in range(30):
            self.enemy.append({"x": 1460.0 + i * 34, "y": rng.uniform(*ROAD_Y), "alive": True, "fx": rng.uniform(0, 6)})
        self.leader = {"x": 1400.0, "y": (ROAD_Y[0] + ROAD_Y[1]) / 2, "alive": True}
        self.group.add(ui.Button((W - 400, 636, 380, 58), "PHỤC BINH!", self._ambush, "primary", size=24))

    def _ambush(self):
        x = self.leader["x"]
        if x > ZONE[1]:
            self.factor, self.timing = 0.65, "Đánh hơi sớm: Liễu Thăng chưa vào sâu, đội hình địch chưa kéo dài."
        elif x >= ZONE[0]:
            self.factor, self.timing = 1.0, "Đánh đúng lúc: Liễu Thăng lọt vào khúc hẹp gần gò Mã Yên."
        else:
            self.factor, self.timing = 0.75, "Đánh hơi muộn: tiền quân địch đã qua được khúc hẹp."
        self.score = sum(sp["value"] for sp in self.chosen) / BEST_VALUE * self.factor
        self.to_kill = max(10, round(len(self.enemy) * min(1.0, self.score)))
        for sp in self.chosen:
            for _ in range(9):
                self.ally.append({
                    "x": sp["x"] + random.uniform(-44, 44), "y": sp["y"] + random.uniform(-16, 16),
                    "tx": random.uniform(max(40.0, x - 150), min(W - 40.0, x + 500)), "ty": random.uniform(*ROAD_Y),
                })
        self.goto("fight")
        self.app.audio.play("trong")
        self.fx.shake(8)

    def step(self, dt):
        if self.stage == "lure":
            for s in self.squad:
                s["x"] -= 150 * dt
            for e in self.enemy:
                e["x"] -= 112 * dt
            self.leader["x"] -= 112 * dt
            if self.leader["x"] < 250:
                self._ambush()
        elif self.stage == "fight":
            self._step_fight(dt)

    def _step_fight(self, dt):
        for s in self.squad:
            s["x"] += 40 * dt
        for a in self.ally:
            dx, dy = a["tx"] - a["x"], a["ty"] - a["y"]
            d = max(1.0, math.hypot(dx, dy))
            if d > 6:
                a["x"] += dx / d * 190 * dt
                a["y"] += dy / d * 190 * dt
        alive = [e for e in self.enemy if e["alive"]]
        self.volley_t -= dt
        if self.volley_t <= 0 and alive:
            self.volley_t = 0.5
            for sp in self.chosen:
                t = random.choice(alive)
                self.fx.volley(sp["x"], sp["y"] - 10, t["x"], t["y"], 6, 60, 620)
        self.kill_t -= dt
        killed = len(self.enemy) - len(alive)
        if self.kill_t <= 0 and alive and killed < self.to_kill:
            self.kill_t = 0.14
            e = random.choice(alive)
            e["alive"] = False
            self.fx.clash(e["x"], e["y"] - 10)
            self.app.audio.play("va")
        if not self.fell and self.stage_t > 1.8:
            self.fell = True
            self.leader["alive"] = False
            self.fx.blood(self.leader["x"], self.leader["y"] - 12, 26)
            self.fx.shake(10)
            self.app.toast("Liễu Thăng tử trận tại gò Mã Yên", theme.GOLD_LIGHT, 4.0)
        for e in alive:
            if killed >= self.to_kill:
                e["x"] += 200 * dt  # tàn quân chạy ngược lại phía bắc
        if self.stage_t > 7.0:
            stars = 3 if self.score >= 0.85 else 2 if self.score >= 0.55 else 1
            names = ", ".join(sp["name"] for sp in self.chosen)
            self.finish(stars, [f"Phục binh: {names}", self.timing, f"Hiệu quả phục kích: {min(100, round(self.score * 100))}%"])

    def _sprite(self, s, cast, x, y, facing, alive, seed=0):
        if alive:
            img = cast.walk[facing][int(self.t * 8 + seed) % 4]
        else:
            img = cast.dead
        s.blit(img, img.get_rect(midbottom=(x, y + 8)))

    def draw_world(self, s):
        s.blit(self.bg, (0, 0))
        fonts.text(s, "Gò Mã Yên", fonts.font("semi", 14), theme.PAPER, (545, 390), "midtop", shadow=(24, 20, 16))
        fonts.text(s, "Bãi lầy", fonts.font("italic", 14), theme.PAPER, (470, 655), "midtop", shadow=(24, 20, 16))
        if self.stage == "lure":
            ui.alpha_rect(s, (ZONE[0], ROAD_Y[0] - 14, ZONE[1] - ZONE[0], ROAD_Y[1] - ROAD_Y[0] + 28), (*theme.GOLD_LIGHT, 90))
        if self.stage == "place":
            self._draw_spots(s)
        items = [(a["y"], self.c_ally, a["x"], "down", True, i) for i, a in enumerate(self.ally)]
        items += [(q["y"], self.c_tran, q["x"], "left", True, i) for i, q in enumerate(self.squad)]
        items += [(e["y"], self.c_enemy, e["x"], "left", e["alive"], i) for i, e in enumerate(self.enemy)]
        if self.leader:
            items.append((self.leader["y"], self.c_lead, self.leader["x"], "left", self.leader["alive"], 0))
        items.sort(key=lambda it: it[0])
        for y, cast, x, facing, alive, seed in items:
            if -40 < x < W + 40:
                self._sprite(s, cast, x, y, facing, alive, seed)
        if self.leader and self.leader["alive"] and self.leader["x"] < W + 40:
            frames = sprites.strip("fx/flag_red.png", 4, 3)
            s.blit(frames[int(self.t * 8) % 4], (self.leader["x"] - 8, self.leader["y"] - 96))

    def _draw_spots(self, s):
        for sp in SPOTS:
            picked = sp in self.chosen
            hot = sp is self.hover
            pygame.draw.circle(s, theme.LACQUER_RED if picked else (60, 52, 40), (sp["x"], sp["y"]), 24)
            pygame.draw.circle(s, theme.GOLD_LIGHT if picked or hot else theme.PAPER_3, (sp["x"], sp["y"]), 24, 3)
            art._star(s, sp["x"], sp["y"], 13, theme.GOLD_LIGHT if picked else (150, 140, 120))
            ui.tag(s, sp["name"], (sp["x"], sp["y"] + 28), theme.LACQUER, theme.PAPER, 13, "midtop")

    def draw_hud(self, screen):
        title = self.b["title"]
        if self.stage == "place":
            note = self.hover["note"] if self.hover else "Rê chuột lên từng vị trí để xem ưu, nhược điểm rồi bấm để chọn (bấm lại để bỏ)."
            self.hud_text(screen, title, f"Chọn 3 chỗ phục binh. {note}")
        elif self.stage == "lure":
            self.hud_text(screen, title, "Trần Lựu giả thua chạy về phía thung lũng, Liễu Thăng cầm quân đuổi gấp. Bấm PHỤC BINH khi cờ đỏ vào vùng sáng.", theme.GOLD_LIGHT)
        else:
            self.hud_text(screen, title, "Phục binh bốn mặt đổ ra! Tên bắn như mưa, đội hình địch rối loạn giữa đường hẹp.", theme.GOLD_LIGHT)


# =====================================================================
# Điện Biên Phủ: đổi phương châm, kéo pháo, đánh lần lượt từng cứ điểm
# =====================================================================
NODES = {
    "him_lam": ("Him Lam", 610, 170, "13/3/1954: pháo ta mở màn chiến dịch. Phan Đình Giót lấy thân mình lấp lỗ châu mai, Him Lam bị tiêu diệt ngay trong đêm."),
    "doc_lap": ("Độc Lập", 420, 128, "Rạng sáng 15/3/1954: cứ điểm Độc Lập ở phía bắc bị đánh chiếm."),
    "ban_keo": ("Bản Kéo", 160, 190, "17/3/1954: quân địch ở Bản Kéo ra hàng. Phân khu Bắc của tập đoàn cứ điểm bị xoá sổ."),
    "e": ("Đồi E", 620, 290, "Từ 30/3/1954: đợt hai mở màn, đánh vào dãy cao điểm phía đông, chiếm được đồi E."),
    "d": ("Đồi D", 650, 376, "Đồi D thất thủ trong đêm đầu của đợt hai, quân ta áp sát khu trung tâm từ phía đông."),
    "c": ("Đồi C", 620, 462, "Đồi C giằng co giành đi giật lại nhiều ngày, đào hào lấn sát từng mét đất."),
    "a1": ("Đồi A1", 560, 540, "Đồi A1 là trận giằng co ác liệt nhất. Đêm 6/5/1954 khối bộc phá gần một tấn nổ dưới lòng đồi, rạng sáng 7/5 A1 thất thủ."),
    "muong_thanh": ("Mường Thanh", 392, 400, "Chiều 7/5/1954: quân ta tiến vào sở chỉ huy, bắt tướng De Castries. Sau 56 ngày đêm, chiến dịch toàn thắng."),
}
PHASES = (
    {"label": "Đợt 1 · 13–17/3/1954", "hint": "Đánh dứt điểm các cứ điểm phía bắc, mở cửa vào lòng chảo.", "targets": ("him_lam", "doc_lap", "ban_keo")},
    {"label": "Đợt 2 · từ 30/3/1954", "hint": "Đánh dãy đồi phía đông khu trung tâm, thắt chặt vòng vây.", "targets": ("e", "d", "c")},
    {"label": "Đợt 3 · đến 6/5/1954", "hint": "Giải quyết điểm tựa quan trọng cuối cùng ở phía đông.", "targets": ("a1",)},
    {"label": "Tổng công kích · 7/5/1954", "hint": "Tiến thẳng vào sở chỉ huy địch ở trung tâm.", "targets": ("muong_thanh",)},
)
BOARD = pygame.Rect(30, 112, 810, 590)
HAUL_STEPS = 8
HAUL_LEN = 980.0  # quãng đường kéo trên màn hình, dùng để tính bánh xe quay
SWEET = 0.16


def _board_tiles(b):
    b.blob(6, 5, 5, 4, RICE)
    b.stroke([(6, 0), (6, 3), (7, 6), (6, 10)], WATER, 2)
    b.rect(3, 3, 1, 5, PATH)
    for x, name in ((0, "pines"), (4, "gray_big"), (9, "pines")):
        b.put(name, x, 0, True)
    for y, name in ((3, "pine"), (5, "gray_tall"), (8, "pine")):
        b.put(name, 0, y, True)
        b.put(name, 11, y, True)
    for x in (2, 8):
        b.put("pine", x, 9, True)


def _valley_top(_rng):
    return diorama.render("board", 13, 10, _board_tiles)


def _haul_tiles(b):
    b.stroke([(0, 10), (3, 9), (7, 8), (11, 6), (15, 5), (20, 4)], PATH, 2)
    for x, name in ((0, "gray_big"), (5, "pines"), (10, "gray_big"), (15, "pines")):
        b.put(name, x, 0, True)
    for x, y, name in ((1, 4, "bamboo"), (5, 3, "pine"), (9, 3, "bamboo"), (2, 6, "pine"), (16, 1, "pine"), (0, 7, "pine"), (7, 5, "pine")):
        b.put(name, x, y, True)
    for x, y, name in ((10, 10, "gray_big"), (15, 8, "gray_tall"), (5, 10, "pine"), (18, 7, "pine"), (13, 8, "bamboo"), (2, 10, "bamboo")):
        b.put(name, x, y, True)


def _haul_bg(_rng):
    return diorama.render("haul", 20, 12, _haul_tiles)


class SiegeBattle(BattleBase):
    howto = (
        "Quyết định phương châm tác chiến, kéo pháo đúng nhịp qua sườn núi, rồi đánh từng cứ điểm theo đúng đợt của chiến dịch. "
        "Trận này chỉ có khói và tiếng nổ, thể hiện sự trân trọng với những người đã ngã xuống."
    )

    def setup(self):
        self.mistakes = 0
        self.misses = 0
        self.note = ""
        self.pull = 0
        self.mark = 0.0
        self.taken: list[str] = []
        self.phase = 0
        self.busy = 0.0
        self.pending = None
        self.log: list[str] = []
        self.end_t = None
        self.board = _once("valley_top", _valley_top)

    def begin(self):
        self.goto("choose")
        self.note = ""
        self.group.add(ui.Button((70, 420, 540, 76), "Đánh nhanh, giải quyết nhanh", self._rush, "primary", size=22))
        self.group.add(ui.Button((670, 420, 540, 76), "Đánh chắc, tiến chắc", self._steady, "gold", size=22))

    def _rush(self):
        self.mistakes += 1
        self.app.audio.play("sai")
        self.note = (
            "Hãy cân nhắc lại. Địch đã tăng cường phòng ngự, tập đoàn cứ điểm rất mạnh; đánh nhanh trong vài đêm khó bảo đảm chắc thắng. "
            "Chính vì thế, sau nhiều đêm suy nghĩ, ngày 26/1/1954 Đại tướng Võ Nguyên Giáp đã quyết định thay đổi phương châm."
        )

    def _steady(self):
        self.app.audio.play("dung")
        self.goto("haul")
        self.pull = 0
        self.shown = 0.0
        self.wheel = 0.0
        self.chants: list[list] = []
        self.arrive_t = None
        self.group.add(ui.Button((W // 2 - 190, 636, 380, 62), "HÒ... DÔ TA NÀO!", self._heave, "primary", size=24))

    def _heave(self):
        if self.arrive_t is not None or self.pull >= HAUL_STEPS:
            return
        k = (math.sin(self.stage_t * 2.6) + 1) / 2
        x, y = self._gun_pos(self.shown)
        if abs(k - 0.5) <= SWEET:
            self.pull += 1
            self.app.audio.play("trong")
            self.fx.burst(x, y + 10, 10, [(120, 100, 70), (92, 76, 54)], 110, 0.5, 4, 200)
            self.chants.append([x + 60, y - 120, 1.2, "Hò dô ta!"])
            if self.pull >= HAUL_STEPS:
                self.arrive_t = 1.6  # để khẩu pháo lăn hết tới nơi rồi mới sang trận đánh
        else:
            self.misses += 1
            self.pull = max(0, self.pull - 1)  # trượt nhịp: pháo trôi lùi một đoạn
            self.fx.shake(6)
            self.chants.append([x + 40, y - 110, 1.0, "Giữ lấy!"])
            self.app.audio.play("sai")

    def _gun_pos(self, pull=None):
        k = (self.pull if pull is None else pull) / HAUL_STEPS
        return 120 + k * 920, 640 - k * 330

    def _to_assault(self):
        self.goto("assault")
        self.note = ""
        self.phase = 0

    def on_event(self, event):
        if self.stage == "haul" and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self._heave()
        if self.stage != "assault" or self.busy > 0 or self.phase >= len(PHASES):
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for nid, (_name, x, y, _text) in NODES.items():
                sx, sy = BOARD.x + x, BOARD.y + y
                if (sx - event.pos[0]) ** 2 + (sy - event.pos[1]) ** 2 <= 30 ** 2 and nid not in self.taken:
                    self._attack(nid)
                    return

    def _attack(self, nid):
        ph = PHASES[self.phase]
        if nid not in ph["targets"]:
            self.mistakes += 1
            self.app.audio.play("sai")
            self.note = f"Chưa đến lúc đánh {NODES[nid][0]}. {ph['label']}: {ph['hint']}"
            return
        self.note = ""
        self.pending = nid
        self.busy = 1.5
        self.app.audio.play("no")

    def step(self, dt):
        if self.stage == "haul":
            self.mark = (math.sin(self.stage_t * 2.6) + 1) / 2
            before = self.shown
            self.shown += (self.pull - self.shown) * min(1.0, dt * 4)  # pháo lăn dần tới chỗ mới, không nhảy cóc
            dist = (self.shown - before) * HAUL_LEN / HAUL_STEPS
            self.wheel += dist / 9  # bánh lăn theo quãng đường, lùi thì quay ngược
            for c in self.chants:
                c[1] -= 30 * dt
                c[2] -= dt
            self.chants = [c for c in self.chants if c[2] > 0]
            if self.arrive_t is not None:
                self.arrive_t -= dt
                if self.arrive_t <= 0:
                    self.arrive_t = None
                    self._to_assault()
        elif self.stage == "assault":
            self._step_assault(dt)

    def _step_assault(self, dt):
        if self.busy > 0:
            self.busy -= dt
            nid = self.pending
            _, x, y, _ = NODES[nid]
            if random.random() < dt * 8:
                self.fx.explosion(BOARD.x + x + random.uniform(-36, 36), BOARD.y + y + random.uniform(-26, 26), 0.8)
                self.app.audio.play("no")
            if self.busy <= 0:
                self.taken.append(nid)
                self.log.append(NODES[nid][3])
                self.app.audio.play("dung")
                if all(t in self.taken for t in PHASES[self.phase]["targets"]):
                    self.phase += 1
                    if self.phase >= len(PHASES):
                        self.end_t = 3.2
        if self.end_t is not None:
            self.end_t -= dt
            if self.end_t <= 0:
                total = self.mistakes + self.misses // 3
                stars = 3 if total == 0 else 2 if total <= 2 else 1
                self.finish(stars, [
                    f"Chọn sai đợt hoặc phương châm: {self.mistakes} lần",
                    f"Nhịp kéo pháo trượt: {self.misses} lần",
                ])

    # ----- vẽ -----
    def draw_world(self, s):
        if self.stage in ("assault", "result"):
            self._world_assault(s)
        elif self.stage == "haul":
            self._world_haul(s)
        else:
            s.blit(diorama.scene("dien_bien"), (0, 0))

    def _world_haul(self, s):
        """Hai hàng bộ đội kéo dây hai bên đường dốc, hai người chèn bánh phía sau, khẩu pháo lăn theo nhịp."""
        s.blit(_once("haul", _haul_bg), (0, 0))
        pos = min(self.shown, HAUL_STEPS)
        x, y = self._gun_pos(pos)
        soldier = sprites.cast("BoDoi", 3)
        heaving = abs(self.pull - self.shown) > 0.05
        ahead = min(HAUL_STEPS + 0.6, pos + 3.0)  # đầu dây không vượt quá chỗ đặt pháo
        hx, hy = self._gun_pos(ahead)
        for side in (-1, 1):  # hai sợi dây
            pygame.draw.line(s, (232, 212, 160), (x + 20, y - 34 + side * 4), (hx, hy - 30 + side * 14), 3)
        crew = []
        for i in range(10):
            k = pos + 0.45 + (ahead - pos - 0.5) * (i // 2) / 4
            px, py = self._gun_pos(k)
            side = -1 if i % 2 == 0 else 1
            crew.append((py + side * 14, px, side))
        for py, px, _side in sorted(crew):
            frame = soldier.attack["right"] if heaving and int(self.t * 8) % 2 else soldier.walk["right"][int(self.t * 6 + px) % 4 if heaving else 0]
            s.blit(frame, frame.get_rect(midbottom=(px, py + 8)))
        gun = art.cannon_sprite(self.wheel)
        s.blit(gun, gun.get_rect(midbottom=(x, y + 6)))
        for i in (0, 1):  # người chèn bánh
            bx, by = self._gun_pos(max(0.0, pos - 0.55 - i * 0.12))
            frame = soldier.attack["right"] if heaving else soldier.walk["right"][0]
            s.blit(frame, frame.get_rect(midbottom=(bx - 10 * i, by + 10 + 14 * i)))
        for cx, cy, _life, text in self.chants:
            fonts.text(s, text, fonts.font("black", 22), theme.GOLD_LIGHT, (cx, cy), "center", shadow=(24, 16, 14))
        if self.arrive_t is not None:
            fonts.text(s, "Pháo đã vào trận địa!", fonts.font("black", 34), theme.GOLD_LIGHT, (W // 2, 120), "center", shadow=(24, 16, 14))

    def _world_assault(self, s):
        s.fill(theme.LACQUER)
        s.blit(self.board, BOARD, (0, 0, BOARD.w, BOARD.h))
        pygame.draw.rect(s, theme.GOLD_DARK, BOARD, 2)
        current = PHASES[self.phase]["targets"] if self.phase < len(PHASES) else ()
        for nid, (name, x, y, _) in NODES.items():
            sx, sy = BOARD.x + x, BOARD.y + y
            if nid in self.taken:
                flag = sprites.strip("fx/flag_red.png", 4)[int(self.t * 8) % 4]
                s.blit(flag, flag.get_rect(center=(sx, sy)))
                art._star(s, sx - 2, sy - 12, 5, theme.GOLD_LIGHT)
            else:
                if nid in current and self.busy <= 0:
                    pygame.draw.circle(s, theme.GOLD_LIGHT, (sx, sy), 29 + 3 * ui.pulse(self.t, 4), 3)
                bunker = sprites.region("camp", 10, 3, 2, 2, 2)
                s.blit(bunker, bunker.get_rect(center=(sx, sy)))
            ui.tag(s, name, (sx, sy + 24), theme.LACQUER, theme.PAPER, 13, "midtop")

    def draw_hud(self, screen):
        if self.stage == "choose":
            self._hud_choose(screen)
        elif self.stage == "haul":
            self._hud_haul(screen)
        else:
            self._hud_assault(screen)

    def _hud_choose(self, screen):
        rect = pygame.Rect(70, 70, 1140, 330)
        ui.lacquer_panel(screen, rect, 242)
        x, w = rect.x + 34, rect.w - 68
        fonts.text(screen, "Tháng 1/1954 · Quyết định khó khăn nhất", fonts.font("serif", 26), theme.GOLD_LIGHT, (x, rect.y + 20))
        y = fonts.paragraph(
            screen,
            "Pháo đã kéo vào trận địa theo phương án đánh trong ba đêm hai ngày. Nhưng địch đã tăng cường lực lượng, công sự mỗi ngày một vững. "
            "Bộ đội ta lần đầu đánh tập đoàn cứ điểm quy mô lớn. Nếu là người chỉ huy, bạn chọn phương châm nào?",
            fonts.font("serif", 19), theme.PAPER, x, rect.y + 64, w, gap=4,
        )
        if self.note:
            fonts.paragraph(screen, self.note, fonts.font("semi", 16), (240, 170, 130), x, y + 12, w, gap=3)

    def _hud_haul(self, screen):
        self.hud_text(
            screen, "Kéo pháo: đổi phương án, đưa pháo vào hầm mới",
            f"Bấm nút (hoặc phím cách) khi kim vào vạch vàng để kéo đúng nhịp. Tiến độ: {self.pull}/{HAUL_STEPS}. Tô Vĩnh Diện đã lấy thân mình chèn pháo để cứu khẩu pháo khi dây kéo đứt.",
        )
        bar = pygame.Rect(W // 2 - 300, 596, 600, 22)
        pygame.draw.rect(screen, theme.LACQUER, bar, border_radius=8)
        z = pygame.Rect(0, 0, int(bar.w * SWEET * 2), bar.h)
        z.center = bar.center
        pygame.draw.rect(screen, theme.GOLD, z, border_radius=6)
        pygame.draw.rect(screen, theme.GOLD_DARK, bar, 2, border_radius=8)
        mx = bar.x + bar.w * self.mark
        pygame.draw.polygon(screen, theme.WHITE, [(mx - 9, bar.y - 12), (mx + 9, bar.y - 12), (mx, bar.y + 4)])

    def _hud_assault(self, screen):
        self.hud_text(
            screen, self.b["title"],
            "Bấm vào cứ điểm thuộc đợt đang diễn ra. Vòng sáng là các mục tiêu của đợt này. Đây là sơ đồ minh hoạ, không theo đúng tỉ lệ.",
        )
        rect = pygame.Rect(856, 112, 394, 590)
        ui.lacquer_panel(screen, rect, 244)
        x, w = rect.x + 20, rect.w - 40
        y = rect.y + 14
        if self.phase < len(PHASES):
            ph = PHASES[self.phase]
            fonts.text(screen, ph["label"], fonts.font("bold", 19), theme.GOLD_LIGHT, (x, y))
            y = fonts.paragraph(screen, ph["hint"], fonts.font("semi", 15), theme.PAPER, x, y + 30, w, gap=2)
        else:
            fonts.text(screen, "Toàn thắng", fonts.font("bold", 21), theme.GOLD_LIGHT, (x, y))
            y += 34
        if self.note:
            y = fonts.paragraph(screen, self.note, fonts.font("semi", 15), (240, 170, 130), x, y + 6, w, gap=2)
        y += 10
        pygame.draw.line(screen, theme.GOLD_DARK, (x, y), (x + w, y))
        y += 10
        for text in reversed(self.log):
            if y > rect.bottom - 60:
                break
            y = fonts.paragraph(screen, text, fonts.font("ui", 14), theme.PAPER_3, x, y, w, gap=2) + 8


KINDS = {"tide": TideBattle, "ambush": AmbushBattle, "siege": SiegeBattle}


def make_battle(app, battle: dict) -> BattleBase:
    return KINDS[battle["kind"]](app, battle)
