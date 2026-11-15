"""Câu cá, nướng cá.

- Mỗi màn có một người câu cá đứng ở mép sông, hồ gần chỗ xuất phát, cạnh một bếp lửa. Nói chuyện với người ấy để nghe vài
  chuyện sử gắn với sông nước, cái ăn (có nguồn) và mua cần câu tre (nói lần hai thì mua); đến bếp lửa để nướng cá.
- Mang cần câu, đứng sát mép nước bấm C thả câu. Phao chìm, hiện dấu chấm than thì bấm C kéo lên; bấm sớm quá cá chạy mất.
- Cá nướng ăn giữa trận đánh (phím E) để hồi máu. Vùng luyện không có người câu cá nhưng có nước thì vẫn câu được.
"""

from __future__ import annotations

import math
import random

import pygame
from core import rpg, sprites, theme
from core.sprites import TILE
from core.tilemap import WATER

from scenes.actors import Actor

WAIT = (2.0, 5.0)  # giây chờ cá cắn câu
BITE = 1.1  # phao chìm bao lâu thì cá nhả mồi
FLY = 0.55  # cá bay từ mặt nước lên tay
JUNK = 0.1  # đôi khi chỉ vớt được rong
REACH_TILES = 2
OFFER_TIME = 12.0  # nói chuyện lần hai trong khoảng này thì mua cần câu
SWIMMERS = 6
DIRS = {"down": (0, 1), "up": (0, -1), "left": (-1, 0), "right": (1, 0)}
HOW_TO = ("Có cần câu thì đứng sát mép nước, bấm C mà thả câu. Phao chìm, hiện dấu chấm than thì bấm C kéo lên. Câu được cá thì "
          "mang lại bếp lửa bên cạnh mà nướng; cá nướng ăn giữa trận bằng phím E.")

# Người câu cá mỗi màn. Lời kể có trích dẫn đều đã tra (xem docs/RA_SOAT_SU_LIEU.md, đợt năm); câu cuối là hướng dẫn chơi.
FISHERS = {
    "man1": {"name": "Ông lão câu cá", "char": "OldMan3", "portrait": "lai_do", "bg": "bach_dang", "lines": [
        {"text": "Sử cũ chép: tổ tiên nhà Trần là Trần Kinh, đến ở hương Tức Mặc, sống bằng nghề đánh cá. Mấy đời sau, con cháu "
                 "họ dựng nên nhà Trần.", "cite": ["c_tt_tran_goc"]},
        {"text": "Dân sông nước thuộc con nước lên xuống từng ngày. Năm 938 Ngô Quyền, năm 1288 Hưng Đạo Vương đều đánh giặc trên "
                 "sông Bạch Đằng bằng cách tính đúng con nước ấy.", "cite": ["c_tt_ngo", "c_tt_tran_nt"]},
    ]},
    "man2": {"name": "Bà cụ đánh cá", "char": "OldWoman", "portrait": "ba_cu", "bg": "ho_guom", "lines": [
        {"text": "Truyện Sự tích Hồ Gươm kể Lê Thận làm nghề đánh cá, ba lần thả lưới đều vớt được một thanh sắt, sau mới biết là "
                 "lưỡi gươm. Đó là truyền thuyết, không phải chính sử.", "cite": ["c_ho_guom"]},
        {"text": "Những năm đầu khởi nghĩa, nghĩa quân Lam Sơn nhiều lần thiếu ăn; Bình Ngô đại cáo còn nhắc những ngày “lương hết "
                 "mấy tuần”.", "cite": ["c_nv_bndc"]},
    ]},
    "man3": {"name": "Bác dân chài", "char": "OldMan", "portrait": "cuu_binh", "bg": "ba_dinh", "lines": [
        {"text": "Tuyên ngôn Độc lập viết: từ Quảng Trị đến Bắc Kỳ, hơn hai triệu đồng bào ta bị chết đói.", "cite": ["c_tuyen_ngon"]},
        {"text": "Ngày 3/9/1945, trong phiên họp đầu tiên của Chính phủ lâm thời, việc cấp bách được nêu đầu tiên là giải quyết "
                 "nạn đói.", "cite": ["c_cp_1945"]},
    ]},
}


def _reach(world):
    from scenes.mobs import _reachable

    return _reachable(world)


def shore_tiles(world, game_map) -> list[tuple[int, int]]:
    """Ô đất đi tới được, sát nước, mà quanh đó có cả một khoảng nước (sông, hồ chứ không phải vũng nhỏ)."""
    out = []
    for t in _reach(world):
        x, y = t
        if not any(game_map.get(x + dx, y + dy) == WATER for dx, dy in DIRS.values()):
            continue
        wet = sum(game_map.get(x + i, y + j) == WATER for i in range(-2, 3) for j in range(-2, 3))
        if wet >= 8:
            out.append(t)
    return sorted(out)


class Swimmer:
    """Con cá bơi lờ đờ dưới nước gần chỗ câu, chỉ để cảnh thêm sống động."""

    def __init__(self, tile, color, rng):
        self.x, self.y = (tile[0] + 0.5) * TILE, (tile[1] + 0.5) * TILE
        self.img = sprites.image(f"animal/fish_{color}.png").subsurface((0, 0, 16, 16))
        self.img = pygame.transform.scale(self.img, (TILE * 3 // 4, TILE * 3 // 4))
        self.img.set_alpha(150)
        self.vx = rng.choice((-1, 1)) * rng.uniform(18, 34)
        self.vy = rng.uniform(-8, 8)
        self.phase = rng.uniform(0, 6.3)

    def update(self, dt, game_map):
        nx, ny = self.x + self.vx * dt, self.y + self.vy * dt
        if game_map.get(int(nx // TILE), int(ny // TILE)) != WATER:
            self.vx, self.vy = -self.vx, -self.vy  # chạm bờ thì quay đầu
            return
        self.x, self.y = nx, ny

    def image(self):
        return self.img if self.vx < 0 else pygame.transform.flip(self.img, True, False)


class Fishing:
    def __init__(self, ws):
        self.ws = ws
        self.app = ws.app
        self.state = ws.state
        self.mode: str | None = None  # None, "wait", "bite"
        self.t = 0.0
        self.bob: tuple[float, float] | None = None
        self.fly: dict | None = None
        self.offer_t = 0.0
        self.rng = random.Random()
        self.swimmers: list[Swimmer] = []
        self.fire: Actor | None = None

    # ---------- người câu cá và bếp lửa ----------
    def spawn(self):
        spec = FISHERS.get(self.ws.level_id)
        if not spec:
            return
        ws = self.ws
        taken = {(int(a.x // TILE), int(a.y // TILE)) for a in ws.actors}
        spots = [t for t in shore_tiles(ws.world, ws.map) if t not in taken]
        if not spots:
            return
        sx, sy = ws.world.spawn
        tile = min(spots, key=lambda t: ((t[0] - sx) ** 2 + (t[1] - sy) ** 2, t))
        reach = _reach(ws.world)
        fire = next((n for n in ((tile[0] + dx, tile[1] + dy) for dx, dy in ((-1, 0), (1, 0), (0, 1), (0, -1), (-1, 1), (1, 1)))
                     if n in reach and n not in taken and ws.map.get(*n) != WATER), None)
        fisher = Actor("fisher", tile, spec["name"], "Nói chuyện", sprites.cast(spec["char"]), data=spec)
        ws.actors.append(fisher)
        if fire:  # bếp vẽ riêng (đống lửa rộng hai ô, có ngọn lửa động) nên actor không mang ảnh
            self.fire = Actor("bep", fire, "Bếp lửa", "Nướng cá")
            ws.actors.append(self.fire)
        rng = random.Random(f"{ws.level_id}-ca")
        water = [(tile[0] + i, tile[1] + j) for i in range(-6, 7) for j in range(-5, 6) if ws.map.get(tile[0] + i, tile[1] + j) == WATER]
        for _ in range(min(SWIMMERS, len(water))):
            self.swimmers.append(Swimmer(rng.choice(sorted(water)), rng.choice(("red", "white", "yellow")), rng))

    def interact(self, a: Actor) -> bool:
        if a.kind == "fisher":
            self._talk(a)
        elif a.kind == "bep":
            self._cook(a)
        else:
            return False
        return True

    def _talk(self, a: Actor):
        st = self.state
        if not st.has_rod() and self.offer_t > 0:
            self._buy(a)
            return
        from scenes.story import StoryScene

        spec = a.data
        nodes = [{"speaker": spec["name"], "portrait": spec["portrait"], "fiction": True, **ln} for ln in spec["lines"]]
        nodes.append({"speaker": spec["name"], "portrait": spec["portrait"], "fiction": True, "text": HOW_TO})
        story = StoryScene(self.app, {"id": "extra", "bg": spec["bg"], "nodes": nodes})
        self.ws.explore._push(story, lambda _r: self._after_talk(a))

    def _after_talk(self, a: Actor):
        st = self.state
        if st.has_rod():
            self.ws._say(a, "Cá tươi thì mang lại bếp lửa mà nướng. Đi câu đi cháu!")
            return
        price = rpg.ITEMS[rpg.ROD]["price"]
        self.offer_t = OFFER_TIME
        self.ws._say(a, f"Ta có cần câu tre, {price} quan một cái. Muốn mua thì nói chuyện với ta lần nữa.", OFFER_TIME)

    def _buy(self, a: Actor):
        self.offer_t = 0.0
        if rpg.ROD in self.state.inventory:  # có rồi mà cất trong túi
            self.state.equip(rpg.ROD)
            self.ws._say(a, "Cần câu cháu có rồi, lấy ra mà dùng. Bấm C ở mép nước để thả câu.")
            return
        why = self.state.buy(rpg.ROD)
        if why:
            self.app.audio.play("sai")
            self.ws._say(a, f"Chưa mua được: {why} Đánh quái, học sử là có quan.")
            return
        self.app.audio.play("dung")
        self.ws._say(a, "Cần của cháu đây. Đứng sát mép nước bấm C mà thả câu, phao chìm thì bấm C kéo lên.", 6.0)

    def _cook(self, a: Actor):
        st = self.state
        if not st.fish_count():
            self.ws._say(a, "Bếp đang đỏ lửa. Câu được cá thì mang lại đây mà nướng.")
            return
        if st.grilled >= rpg.MAX_GRILL:
            self.ws._say(a, f"Xâu cá nướng đã đủ {rpg.MAX_GRILL} con, ăn bớt đã rồi hãy nướng thêm.")
            return
        n = st.cook()
        self.app.audio.play("lua")
        self.app.toast(f"Nướng xong {n} con cá, thơm phức! Cá nướng: {st.grilled} (ăn giữa trận bằng phím E)", theme.GOLD_LIGHT, 4.0)

    # ---------- câu ----------
    @property
    def active(self) -> bool:
        return self.mode is not None

    def _water_ahead(self) -> tuple[int, int] | None:
        ws = self.ws
        px, py = int(ws.x // TILE), int(ws.y // TILE)
        order = [ws.facing] + [d for d in DIRS if d != ws.facing]
        for d in order:
            dx, dy = DIRS[d]
            for k in range(1, REACH_TILES + 1):
                t = (px + dx * k, py + dy * k)
                if ws.map.get(*t) == WATER:
                    ws.facing = d
                    return t
        return None

    def can_cast(self) -> bool:
        """Có cần câu, đang đi bộ, đứng sát nước: hiện nút Thả câu khi chơi bằng cảm ứng. Không đổi hướng nhìn như _water_ahead."""
        ws = self.ws
        if self.mode is not None or ws.mode != "walk" or not self.state.has_rod():
            return False
        px, py = int(ws.x // TILE), int(ws.y // TILE)
        return any(ws.map.get(px + dx * k, py + dy * k) == WATER for dx, dy in DIRS.values() for k in range(1, REACH_TILES + 1))

    def press(self):
        """Phím C (hay nút chạm): chưa câu thì thả câu, đang chờ thì giật sớm, phao chìm thì kéo cá lên."""
        if self.mode == "bite":
            self._land()
        elif self.mode == "wait":
            self._stop("Giật sớm quá, cá chưa cắn câu đã chạy mất.")
        else:
            self._cast()

    def _cast(self):
        ws, st = self.ws, self.state
        if not st.has_rod():
            self.app.toast("Chưa có cần câu. Hỏi người câu cá ở mép sông, hoặc mua ở lò rèn (mục Đồ nghề).", theme.PAPER, 3.5)
            return
        if ws.mode != "walk":
            self.app.toast("Xuống ngựa, lên bờ rồi hãy thả câu.", theme.PAPER, 3.0)
            return
        if st.fish_count() >= rpg.MAX_FISH:
            self.app.toast(f"Giỏ đã đầy {rpg.MAX_FISH} con cá. Mang đến bếp lửa của người câu cá mà nướng đã.", theme.PAPER, 3.5)
            return
        tile = self._water_ahead()
        if tile is None:
            self.app.toast("Đứng sát mép nước rồi hãy thả câu.", theme.PAPER, 3.0)
            return
        ws.path.clear()
        self.mode = "wait"
        self.t = self.rng.uniform(*WAIT)
        self.bob = ((tile[0] + 0.5) * TILE, (tile[1] + 0.55) * TILE)
        self.app.audio.play("nuoc")

    def _land(self):
        st = self.state
        bob = self.bob
        self.mode, self.bob = None, None
        if self.rng.random() < JUNK:
            self.app.audio.play("click")
            self.app.toast("Chỉ vớt được một cọng rong. Thử lại xem!", theme.PAPER, 2.5)
            return
        kinds = list(rpg.FISH)
        kind = self.rng.choices(kinds, [rpg.FISH[k][2] for k in kinds])[0]
        name, color, _w = rpg.FISH[kind]
        first = st.fish_count() == 0 and st.grilled == 0
        if not st.catch(kind):
            self.app.toast("Giỏ đầy rồi, đành thả cá về sông.", theme.PAPER, 3.0)
            return
        self.fly = {"t": 0.0, "from": bob, "img": sprites.image(f"animal/fish_{color}.png").subsurface((0, 0, 16, 16))}
        self.app.audio.play("nhan")
        self.app.toast(f"Câu được {name}! Giỏ có {st.fish_count()} con.", theme.JADE_LIGHT, 3.0)
        if first:
            self.app.toast("Mang cá đến bếp lửa của người câu cá để nướng, cá nướng ăn giữa trận (phím E) để hồi máu.",
                           theme.GOLD_LIGHT, 5.0)

    def _stop(self, msg: str | None = None):
        self.mode, self.bob = None, None
        if msg:
            self.app.audio.play("sai")
            self.app.toast(msg, theme.PAPER, 2.5)

    def update(self, dt):
        if self.offer_t > 0:
            self.offer_t = max(0.0, self.offer_t - dt)
        for s in self.swimmers:
            s.update(dt, self.ws.map)
        if self.fly:
            self.fly["t"] += dt
            if self.fly["t"] >= FLY:
                self.fly = None
        if self.mode is None:
            return
        if self.ws.moving or self.ws.mode != "walk" or self.ws.warp:
            self._stop()  # đi đi chỗ khác thì thu cần
            return
        self.t -= dt
        if self.t > 0:
            return
        if self.mode == "wait":
            self.mode, self.t = "bite", BITE
            self.app.audio.play("nuoc")
        else:
            self._stop("Cá ăn mồi rồi chạy mất. Phao chìm là phải bấm C ngay!")

    # ---------- vẽ ----------
    def items(self, cx, cy) -> list[tuple]:
        """Bếp lửa và ngọn lửa, xếp lớp theo chiều sâu cùng người và vật."""
        a = self.fire
        if a is None or not (-TILE * 3 < a.x - cx < theme.WIDTH + TILE * 3 and -TILE * 3 < a.y - cy < theme.HEIGHT + TILE * 3):
            return []
        img = _hearth()
        flame = _flames()[int(self.ws.t * 10) % 8]
        top = a.y - img.get_height() + 6
        base = (a.y, 1, img, a.x - img.get_width() / 2, top)
        fire = (a.y + 1, 1, flame, a.x - flame.get_width() / 2, top - flame.get_height() * 0.62)
        skewer = _skewer()
        fish = (a.y + 2, 1, skewer, a.x + img.get_width() / 2 - skewer.get_width() * 0.7, top - skewer.get_height() * 0.55)
        return [base, fire, fish]

    def _hand(self) -> tuple[float, float]:
        ws = self.ws
        dx, _dy = DIRS[ws.facing]
        return ws.x + (dx or 0.3) * TILE * 0.3, ws.y - TILE * 0.55

    def draw_water(self, screen, cx, cy):
        """Cá bơi dưới nước: vẽ ngay sau mặt nước, trước người và vật."""
        w, h = screen.get_size()
        for s in self.swimmers:
            x, y = s.x - cx, s.y - cy
            if -TILE < x < w + TILE and -TILE < y < h + TILE:
                img = s.image()
                bob = 2 * math.sin(self.ws.t * 3 + s.phase)
                screen.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2 + bob))

    def draw(self, screen, cx, cy):
        if self.bob:
            hx, hy = self._hand()
            bx, by = self.bob
            tip = {"left": (hx - TILE * 0.9, hy - TILE * 0.7), "right": (hx + TILE * 0.9, hy - TILE * 0.7),
                   "down": (hx + TILE * 0.5, hy + TILE * 0.3), "up": (hx + TILE * 0.5, hy - TILE * 0.9)}[self.ws.facing]
            pygame.draw.line(screen, (20, 27, 27), (hx - cx, hy - cy), (tip[0] - cx, tip[1] - cy), 5)
            pygame.draw.line(screen, (176, 170, 86), (hx - cx, hy - cy), (tip[0] - cx, tip[1] - cy), 3)
            sink = 6 if self.mode == "bite" and int(self.ws.t * 10) % 2 else 0
            bob_y = by + 2 * math.sin(self.ws.t * 4) + sink
            mid = ((tip[0] + bx) / 2 - cx, max(tip[1], bob_y) - cy + 10)  # dây câu chùng xuống
            pygame.draw.lines(screen, (236, 232, 220), False, [(tip[0] - cx, tip[1] - cy), mid, (bx - cx, bob_y - cy)], 1)
            pygame.draw.circle(screen, (20, 27, 27), (bx - cx, bob_y - cy), 6)
            pygame.draw.circle(screen, (214, 56, 44), (bx - cx, bob_y - cy), 5)
            pygame.draw.rect(screen, (250, 246, 236), (bx - cx - 5, bob_y - cy, 10, 3))
            if self.mode == "bite":
                emote = sprites.icon("ui/emote_alert.png", 3)
                screen.blit(emote, emote.get_rect(midbottom=(self.ws.x - cx, self.ws.y - TILE * 1.25 - cy)))
        if self.fly:
            k = min(1.0, self.fly["t"] / FLY)
            fx, fy = self.fly["from"]
            tx, ty = self.ws.x, self.ws.y - TILE * 0.6
            x = fx + (tx - fx) * k
            y = fy + (ty - fy) * k - math.sin(k * math.pi) * TILE * 1.2
            img = pygame.transform.rotate(pygame.transform.scale(self.fly["img"], (TILE * 3 // 4, TILE * 3 // 4)), k * 300)
            screen.blit(img, img.get_rect(center=(x - cx, y - cy)))


_cache: dict = {}


def _hearth() -> pygame.Surface:
    """Bếp lửa nhỏ bên mép nước: kiềng đá, hai que củi bắt chéo, than hồng."""
    if "hearth" not in _cache:
        low = pygame.Surface((22, 12), pygame.SRCALPHA)
        outline, stone, stone_l = (20, 27, 27), (120, 116, 108), (160, 156, 146)
        pygame.draw.ellipse(low, (60, 36, 24), (3, 5, 16, 6))  # nền tro
        for x in (5, 9, 13):
            low.set_at((x, 8), (236, 120, 40))  # than hồng
        for a, b in (((4, 3), (17, 9)), ((17, 3), (4, 9))):
            pygame.draw.line(low, outline, a, b, 3)
            pygame.draw.line(low, (126, 80, 44), a, b, 1)
        for x, y in ((0, 6), (4, 9), (9, 10), (14, 9), (18, 6)):
            pygame.draw.ellipse(low, outline, (x, y - 1, 5, 4))
            pygame.draw.ellipse(low, stone, (x + 1, y, 3, 2))
            low.set_at((x + 1, y), stone_l)
        _cache["hearth"] = pygame.transform.scale(low, (88, 48))
    return _cache["hearth"]


def _flames() -> list[pygame.Surface]:
    """Ngọn lửa nhỏ lại cho vừa một bếp nướng cá."""
    if "flames" not in _cache:
        _cache["flames"] = [pygame.transform.scale(f, (40, 48)) for f in sprites.strip("fx/flame.png", 8)]
    return _cache["flames"]


def _skewer() -> pygame.Surface:
    """Một xiên cá cắm nghiêng cạnh bếp."""
    if "skewer" not in _cache:
        _cache["skewer"] = pygame.transform.rotate(sprites.icon(rpg.item_icon("ca_nuong"), 2), -12)
    return _cache["skewer"]
