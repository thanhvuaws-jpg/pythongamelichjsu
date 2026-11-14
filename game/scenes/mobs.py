"""Quái trên map, kẻ canh mật thư, trùm cuối màn và người thách đấu.

- Quanh mỗi di tích có một toán "bóng giặc": quân xâm lược đúng thời của vùng đó (Nam Hán, Tống, Nguyên, Minh), riêng
  thời 1945 – 1954 chỉ có đồn bốt, lô cốt. Bấm F (hoặc E, hoặc bấm chuột) khi đứng gần để đánh ngay trên map.
- Mật thư cuối của mỗi di tích có kẻ cầm đầu canh giữ; mật thư cuối của cả màn có trùm. Hạ được mới nhặt được.
- Thỉnh thoảng một võ sinh đi tới thách đấu: Y nhận lời, N từ chối (hoặc cứ đi xa là coi như bỏ chạy).

Mọi việc nối tiếp sau trận đánh đi qua `Explore._push`, nên WorldScene không phải biết thêm gì.
"""

from __future__ import annotations

import math
import random

import pygame
from core import fonts, mobart, rpg, sprites, theme, ui, weapons
from core.sprites import TILE
from core.tilemap import WATER

from scenes.actors import Actor
from scenes.fight import STATIC_CASTS, FightScene

REACH = TILE * 1.6
WATER_REACH = 1.9
WANDER = 2
CAMP_MIN, CAMP_MAX = 6, 11  # khoảng cách (ô) từ tâm di tích tới chỗ đóng quân
LABEL_RANGE = TILE * 7
DUEL_FIRST = (60.0, 100.0)
DUEL_EVERY = (100.0, 170.0)
DUEL_MIN_LEVEL = 2
DUEL_ASK_RANGE = TILE * 1.4
DUEL_FLEE_RANGE = TILE * 5
DUEL_SPEED = TILE * 2.6
FIGHT_TIME = 60
MAP_OBJECT_SCALE = 3


def _reachable(world) -> set[tuple[int, int]]:
    """Mọi ô đi bộ tới được từ chỗ xuất phát, tính một lần cho mỗi map."""
    cached = getattr(world, "_reach", None)
    if cached is not None:
        return cached
    m = world.map
    start = tuple(world.spawn)
    seen = {start}
    queue = [start]
    for cur in queue:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (cur[0] + dx, cur[1] + dy)
            if nxt not in seen and not m.blocked(*nxt):
                seen.add(nxt)
                queue.append(nxt)
    world._reach = seen
    return seen


def mob_key(m) -> str:
    """Tên riêng của một con quái, giống nhau trên mọi máy và ở máy chủ (quái đứng cùng chỗ vì bản đồ dựng giống nhau)."""
    return f"{m.id}@{int(m.home[0] // TILE)},{int(m.home[1] // TILE)}"


class Mob:
    """Một quái trên map. kind: mob (lính thường), guard (kẻ canh mật thư), boss (trùm cuối màn)."""

    def __init__(self, mob_id: str, data: dict, tile: tuple[int, int], kind: str = "mob", key: str | None = None):
        self.id, self.data, self.kind, self.key = mob_id, data, kind, key
        self.x = tile[0] * TILE + TILE / 2
        self.y = tile[1] * TILE + TILE - 8
        self.home = (self.x, self.y)
        self.object = bool(data.get("object"))
        char = data["char"]
        if char in STATIC_CASTS:
            self.cast = STATIC_CASTS[char](MAP_OBJECT_SCALE)
        elif mobart.has(char):
            self.cast = mobart.cast(char, MAP_OBJECT_SCALE if self.object else 4)
        else:
            self.cast = sprites.cast(char)
        self.facing = random.choice(("down", "left", "right"))
        self.frame = 0.0
        self.goal: tuple[float, float] | None = None
        self.wait = random.uniform(0.5, 4)
        self.dead_t = 0.0
        self.scroll: Actor | None = None  # mật thư mà kẻ này đang canh

    @property
    def level(self) -> int:
        return self.data["level"]

    @property
    def alive(self) -> bool:
        return self.dead_t <= 0


class Mobs:
    def __init__(self, ws):
        self.ws = ws
        self.app = ws.app
        self.state = ws.state
        self.mobs: list[Mob] = []
        self.duel: dict | None = None
        self.duel_t = random.uniform(*DUEL_FIRST)
        self.warned: Mob | None = None
        self._spawn()

    # ----- dựng -----
    def _spawn(self):
        ws = self.ws
        reach = _reachable(ws.world)
        taken = {(int(a.x // TILE), int(a.y // TILE)) for a in ws.actors}
        busy = {(x + dx, y + dy) for x, y in taken for dx in range(-2, 3) for dy in range(-2, 3)}

        def open_tile(t):
            return t in reach and t not in busy and all((t[0] + dx, t[1] + dy) in reach for dx in (-1, 0, 1) for dy in (-1, 0, 1))

        field = getattr(ws, "field", None)
        if field:
            self._spawn_field(field, open_tile, busy)
            return
        mandatory = [r for r in ws.relics if not r.get("optional")]
        final = mandatory[-1]["id"] if mandatory else None
        for relic in ws.relics:
            rid = relic["id"]
            kinds = rpg.ZONE_MOBS.get(rid)
            if not kinds:
                continue
            zone = ws.world.zones[rid]
            rng = random.Random(rid)
            ring = [(zone.cx + dx, zone.cy + dy) for dx in range(-CAMP_MAX, CAMP_MAX + 1) for dy in range(-CAMP_MAX, CAMP_MAX + 1)
                    if CAMP_MIN ** 2 <= dx * dx + dy * dy <= CAMP_MAX ** 2]
            ring = sorted(t for t in ring if open_tile(t))
            rng.shuffle(ring)
            if ring:
                cx, cy = ring[0]
                spots = [t for t in ((cx + dx, cy + dy) for dx in range(-3, 4) for dy in range(-2, 3)) if open_tile(t)]
                rng.shuffle(spots)
                camp: list[tuple[int, int]] = []
                for t in spots:  # đứng cách nhau ít nhất hai ô cho khỏi chồng lên nhau
                    if len(camp) < rpg.CAMP_SIZE and all(max(abs(t[0] - c[0]), abs(t[1] - c[1])) >= 2 for c in camp):
                        camp.append(t)
                for i, tile in enumerate(camp):
                    mid = kinds[i % len(kinds)]
                    self.mobs.append(Mob(mid, rpg.MOBS[mid], tile))
                    busy.add(tile)
            self._spawn_guard(relic, rid == final, kinds[0], reach)

    def _spawn_field(self, field, open_tile, busy):
        """Vùng luyện: mỗi trại một toán quái, trại chính có thêm kẻ mạnh nhất vùng."""
        world = self.ws.world
        rng = random.Random(field["id"])
        for zid, kinds in field["camps"].items():
            zone = world.zones[zid]
            spots = [(zone.cx + dx, zone.cy + dy) for dx in range(-5, 6) for dy in range(-4, 5) if 4 <= dx * dx + dy * dy <= 30]
            spots = sorted(t for t in spots if open_tile(t))
            rng.shuffle(spots)
            shore = self._shore(zone, rng)
            camp: list[tuple[int, int]] = []
            for mid in kinds:
                pool = shore if rpg.MOBS[mid].get("water") else spots
                tile = next((t for t in pool if t not in camp and all(max(abs(t[0] - c[0]), abs(t[1] - c[1])) >= 2 for c in camp)), None)
                if tile is not None:
                    camp.append(tile)
                    self.mobs.append(Mob(mid, rpg.MOBS[mid], tile))
                    busy.add(tile)
            if zid == field.get("elite_zone"):
                elite = rpg.ELITES[field["id"]]
                pool = shore if elite.get("water") else spots
                spot = next((t for t in pool if t not in camp and all(max(abs(t[0] - c[0]), abs(t[1] - c[1])) >= 3 for c in camp)),
                            (zone.cx, zone.cy))
                self.mobs.append(Mob(field["id"], elite, spot, "elite", field["id"]))

    def _shore(self, zone, rng) -> list[tuple[int, int]]:
        """Ô nước cách bờ đúng một ô quanh trại: thuyền, tàu neo hẳn trên mặt nước (hình không đè lên bờ), người chơi
        đứng ở mép bờ vẫn với tới."""
        m = self.ws.map
        reach = _reachable(self.ws.world)
        out = []
        for dy in range(-9, 10):
            for dx in range(-11, 12):
                t = (zone.cx + dx, zone.cy + dy)
                if m.get(*t) != WATER:
                    continue
                near = [(t[0] + ax, t[1] + ay) for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                if any(n in reach for n in near):
                    continue  # sát bờ quá: hình thuyền sẽ đè lên đất
                if any((t[0] + 2 * ax, t[1] + 2 * ay) in reach and m.get(t[0] + ax, t[1] + ay) == WATER
                       for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    out.append(t)
        out.sort()
        rng.shuffle(out)
        return out

    def _spawn_guard(self, relic, final: bool, mob_id: str, reach):
        """Kẻ canh mật thư cuối cùng của di tích; mật thư cuối của màn thì là trùm."""
        ws = self.ws
        objs = [o for o in ws._objectives(relic) if o["kind"] == "collect"]
        if not objs:
            return
        last = objs[-1]["id"]
        scroll = next((a for a in ws.actors if a.kind == "scroll" and a.objective["id"] == last), None)
        if scroll is None:
            return
        sx, sy = int(scroll.x // TILE), int(scroll.y // TILE)
        spot = next(((sx + dx, sy + dy) for dx, dy in ((1, 0), (-1, 0), (1, 1), (-1, 1), (0, 1), (2, 0), (-2, 0)) if (sx + dx, sy + dy) in reach),
                    (sx + 1, sy))
        if final:
            data, kind = rpg.BOSSES[ws.level_id], "boss"
        else:
            data, kind = rpg.guard_of(mob_id), "guard"
        guard = Mob(mob_id, data, spot, kind, relic["id"])
        guard.scroll = scroll
        self.mobs.append(guard)

    # ----- tra cứu -----
    def visible(self, m: Mob) -> bool:
        if not m.alive:
            return False
        if m.kind in ("mob", "elite"):
            return True
        return m.key not in self.state.bosses_beaten and self.ws._is_current(m.scroll)

    def guard_of(self, scroll: Actor) -> Mob | None:
        """Kẻ đang chặn mật thư này, nếu có."""
        return next((m for m in self.mobs if m.scroll is not None and m.scroll is scroll and m.key not in self.state.bosses_beaten), None)

    def nearest(self) -> Mob | None:
        ws = self.ws
        best, best_d = None, None
        for m in self.mobs:
            d = (m.x - ws.x) ** 2 + (m.y - ws.y) ** 2
            reach = REACH * (WATER_REACH if m.data.get("water") else 1.0)  # thuyền neo ngoài một ô: với xa hơn
            if d < reach * reach and self.visible(m) and (best_d is None or d < best_d):
                best, best_d = m, d
        return best

    def at(self, wx: float, wy: float) -> Mob | None:
        return next((m for m in self.mobs if self.visible(m) and (m.x - wx) ** 2 + (m.y - TILE / 2 - wy) ** 2 < TILE ** 2), None)

    # ----- đánh -----
    def _backdrop(self) -> pygame.Surface:
        ws = self.ws
        """Nền trận đánh: chỉ lấy đất, cây, nhà ở chỗ đang đứng (bỏ người và quái) cho người đánh nổi lên."""
        snap = pygame.Surface((theme.WIDTH, theme.HEIGHT))
        cx, cy = int(ws.cam_x), int(ws.cam_y)
        ws.map.draw(snap, cx, cy)
        items = [(p.sort, p.img, p.x, p.y) for p in ws.world.visible_props(cx, cy, theme.WIDTH, theme.HEIGHT)]
        for _sort, img, x, y in sorted(items, key=lambda it: it[0]):
            snap.blit(img, (x - cx, y - cy))
        shade = pygame.Surface((theme.WIDTH, theme.HEIGHT), pygame.SRCALPHA)
        shade.fill((24, 16, 10, 90))
        snap.blit(shade, (0, 0))
        return snap

    def engage(self, m: Mob):
        ws, st = self.ws, self.state
        if not self.visible(m):
            return
        ws.path.clear()
        ws.auto = None
        ws._land()
        boss = m.kind != "mob"
        ease = st.boss_ease(m.key) if boss else 0.0
        spec = rpg.fight_spec(m.data, m.kind == "boss", ease)
        title = m.data["name"]
        self.app.audio.play("kiem")
        scene = FightScene(self.app, [spec], title, "vo_dai", time_limit=FIGHT_TIME if not boss else 90, backdrop=self._backdrop())
        ws.mp.begin_fight(scene, m.data["name"], m.x, m.y)
        ws.explore._push(scene, lambda r: self._fought(m, r))

    def _fought(self, m: Mob, result):
        st, ws = self.state, self.ws
        ws.mp.end_fight()
        if not isinstance(result, dict) or result.get("quit"):
            # rút lui: lùi ra một bước cho khỏi chạm quái lần nữa
            ws.y += TILE * 0.8 if not ws._hit(ws.x, ws.y + TILE * 0.8) else 0
            return
        if result.get("win"):
            if m.kind == "elite":
                log = st.field_log.setdefault(m.key, {})
                log["elite"] = log.get("elite", 0) + 1
                st.gain(m.data["exp"], m.data["tiem"], m.data["quan"])
                st.potions += 1
                st.save()
                m.dead_t = rpg.ELITE_RESPAWN
                self.app.toast(f"Hạ {m.data['name']}! +{m.data['exp']} kinh nghiệm, +{m.data['tiem']} tiềm năng, +{m.data['quan']} quan, 1 thuốc nam",
                               theme.GOLD_LIGHT, 4.5)
            elif m.kind == "mob":
                if m.id not in st.bestiary and m.id in rpg.MOB_FACTS:  # lần đầu hạ loại quái này: thêm một dòng sử
                    st.bestiary.add(m.id)
                    self.app.toast(f"Sử ghi: {rpg.MOB_FACTS[m.id][0]}", theme.PAPER, 7.0)
                exp, tiem, quan, drop = st.win_mob(m.data)
                ws.mp.kill(m.data["name"], exp, tiem)  # đồng đội đứng gần được chia phần
                ws.mp.mob_down(mob_key(m))
                m.dead_t = rpg.RESPAWN
                extra = ", rơi 1 thuốc nam" if drop else ""
                self.app.toast(f"Hạ {m.data['name']}: +{exp} kinh nghiệm, +{tiem} tiềm năng, +{quan} quan{extra}", theme.GOLD_LIGHT, 3.5)
            else:
                st.bosses_beaten.add(m.key)
                quan = m.data["quan"] if isinstance(m.data["quan"], int) else m.data["quan"][1]
                st.gain(m.data["exp"], m.data["tiem"], quan)
                st.save()
                m.dead_t = 1e9
                self.app.toast(f"Đã hạ {m.data['name']}! +{m.data['exp']} kinh nghiệm, +{m.data['tiem']} tiềm năng, +{quan} quan", theme.GOLD_LIGHT, 4.5)
                self.app.toast("Mật thư không còn ai canh. Nhặt lấy đi!", theme.JADE_LIGHT, 4.0)
            return
        # thua: ngất đi, được đưa về chỗ già làng; trùm thì lần sau yếu đi một chút
        if m.kind != "mob":
            st.boss_tries[m.key] = st.boss_tries.get(m.key, 0) + 1
            st.save()
            who = "Kẻ mạnh nhất vùng" if m.kind == "elite" else "Kẻ canh mật thư"
            self.app.toast(f"{who} còn mạnh quá. Lên cấp, mua đồ, học thêm kỹ năng rồi quay lại; hắn cũng đã mỏi mệt dần.", theme.PAPER, 5.0)
        else:
            self.app.toast("Bạn bị đánh ngất, dân làng đưa về chỗ già làng nghỉ ngơi.", theme.PAPER, 4.0)
        mx, my = ws.mentor.x, ws.mentor.y + TILE
        if not ws._hit(mx, my):
            ws.x, ws.y = mx, my
            ws._snap_camera()

    # ----- thách đấu -----
    def _bots(self) -> list[dict]:
        bots = self.state.extras["arena"]
        n = 1 + self.state.level // 3
        return bots[: max(1, min(len(bots), n))]

    def _start_duel(self):
        ws, st = self.ws, self.state
        reach = _reachable(ws.world)
        px, py = int(ws.x // TILE), int(ws.y // TILE)
        for _ in range(30):
            ang = random.uniform(0, math.tau)
            tile = (px + round(math.cos(ang) * 8), py + round(math.sin(ang) * 6))
            if tile in reach:
                break
        else:
            return
        bot = random.choice(self._bots())
        spec = rpg.challenger_spec(bot, st.level)
        who = Actor("duel", tile, bot["name"], "", sprites.cast(bot["char"]))
        self.duel = {"bot": bot, "spec": spec, "actor": who, "state": "come", "path": [], "repath": 0.0, "t": 0.0}

    def answer(self, accept: bool):
        d = self.duel
        if not d or d["state"] != "ask":
            return
        if accept:
            self.duel = None
            self.duel_t = random.uniform(*DUEL_EVERY)
            self.ws._land()
            scene = FightScene(self.app, [d["spec"]], f"Thách đấu: {d['bot']['name']}", "vo_dai", time_limit=FIGHT_TIME, backdrop=self._backdrop())
            self.ws.explore._push(scene, lambda r: self._duel_done(d, r))
        else:
            self._leave("Hừ, lần sau gặp lại!")

    def _leave(self, line: str):
        d = self.duel
        d["state"] = "leave"
        d["t"] = 0.0
        self.ws._say(d["actor"], line, 2.5)
        self.duel_t = random.uniform(*DUEL_EVERY)

    def _duel_done(self, d, result):
        st = self.state
        if isinstance(result, dict) and result.get("win"):
            exp, tiem, quan = rpg.challenger_reward(d["spec"]["mob_level"])
            st.duels_won += 1
            st.gain(exp, tiem, quan)
            st.save()
            self.app.toast(f"Thắng {d['bot']['name']}: +{exp} kinh nghiệm, +{tiem} tiềm năng, +{quan} quan", theme.GOLD_LIGHT, 4.0)
        elif isinstance(result, dict) and not result.get("quit"):
            self.app.toast(f"{d['bot']['name']} thắng trận này. Tu luyện thêm rồi đấu lại!", theme.PAPER, 3.5)

    def _update_duel(self, dt):
        ws = self.ws
        d = self.duel
        if d is None:
            if ws.mode == "boat" or ws.warp or self.state.level < DUEL_MIN_LEVEL:
                return
            self.duel_t -= dt
            if self.duel_t <= 0:
                self._start_duel()
            return
        a = d["actor"]
        d["t"] += dt
        dist = math.hypot(ws.x - a.x, ws.y - a.y)
        if d["state"] == "come":
            d["repath"] -= dt
            if d["repath"] <= 0:
                d["repath"] = 1.2
                d["path"] = ws.map.find_path((int(a.x // TILE), int((a.y - 4) // TILE)), (int(ws.x // TILE), int((ws.y - 4) // TILE)))
            if dist < DUEL_ASK_RANGE:
                d["state"] = "ask"
                d["t"] = 0.0
                a.facing = ws._dir_to(a.x, a.y, ws.x, ws.y)
                ws._say(a, f"Này! Nghe nói bạn đang theo Cụ Đồ học sử. Đấu với ta một trận chứ? ({d['bot']['desc']})", 6.0)
                self.app.audio.play("kiem")
            elif d["path"]:
                self._step(a, d["path"], dt, DUEL_SPEED)
            elif d["t"] > 25:
                self.duel = None  # không tới được thì thôi
                self.duel_t = random.uniform(*DUEL_EVERY)
        elif d["state"] == "ask":
            a.frame = 0.0
            a.facing = ws._dir_to(a.x, a.y, ws.x, ws.y)
            if dist > DUEL_FLEE_RANGE:
                self._leave("Chạy nhanh thế! Lần sau đừng hòng.")
        else:  # leave: đi ra xa rồi biến mất
            a.y += DUEL_SPEED * dt * 0.8
            a.facing = "down"
            a.frame += dt * 8
            if d["t"] > 2.6:
                self.duel = None

    @staticmethod
    def _step(a, path, dt, speed):
        tx, ty = path[0]
        gx, gy = (tx + 0.5) * TILE, (ty + 1) * TILE - 8
        dx, dy = gx - a.x, gy - a.y
        dist = math.hypot(dx, dy)
        if dist < 6:
            path.pop(0)
            return
        k = min(1.0, speed * dt / dist)
        a.x += dx * k
        a.y += dy * k
        a.facing = ("right" if dx > 0 else "left") if abs(dx) > abs(dy) else ("down" if dy > 0 else "up")
        a.frame += dt * 8

    # ----- cập nhật, vẽ -----
    def remote_kill(self, key) -> bool:
        """Người khác trên map vừa hạ con quái này: con quái cũng ngã trên máy mình, rồi mọc lại như thường."""
        for m in self.mobs:
            if m.kind == "mob" and m.alive and mob_key(m) == key:
                m.dead_t = rpg.RESPAWN
                return True
        return False

    def update(self, dt):
        ws = self.ws
        for m in self.mobs:
            if m.dead_t > 0:
                m.dead_t -= dt
                if m.dead_t <= 0:
                    m.x, m.y = m.home
                continue
            if m.object or m.kind != "mob":
                if (m.x - ws.x) ** 2 + (m.y - ws.y) ** 2 < (REACH * 2) ** 2 and not m.object:
                    m.facing = ws._dir_to(m.x, m.y, ws.x, ws.y)
                continue
            if m.goal is None:
                m.frame = 0.0
                m.wait -= dt
                if m.wait <= 0:
                    m.wait = random.uniform(2, 6)
                    gx, gy = m.home[0] + random.randint(-WANDER, WANDER) * TILE, m.home[1] + random.randint(-1, 1) * TILE
                    if not ws.map.blocked(int(gx // TILE), int((gy - 4) // TILE)):
                        m.goal = (gx, gy)
            else:
                dx, dy = m.goal[0] - m.x, m.goal[1] - m.y
                dist = math.hypot(dx, dy)
                if dist < 4:
                    m.goal = None
                else:
                    m.x += dx / dist * TILE * 0.9 * dt
                    m.y += dy / dist * TILE * 0.9 * dt
                    m.facing = ws._dir_to(0, 0, dx, dy)
                    m.frame += dt * 6
        self._update_duel(dt)

    def items(self, cx, cy) -> list[tuple]:
        out = []
        for m in self.mobs:
            if not self.visible(m) or not (-TILE * 2 < m.x - cx < theme.WIDTH + TILE * 2 and -TILE < m.y - cy < theme.HEIGHT + TILE * 3):
                continue
            img = m.cast.walk[m.facing][int(m.frame) % 4]
            out.append((m.y, 2, img, m.x - img.get_width() / 2, m.y - img.get_height() + 8))
            held = weapons.held_sprite(m.data.get("weapon"), m.facing, 4)
            if held:
                w, dx, dy, behind = held
                lift = getattr(m.cast, "lift", 0) * 4
                out.append((m.y, 1.5 if behind else 2.5, w, m.x + dx, m.y + 8 + dy - lift))
        if self.duel:
            a = self.duel["actor"]
            img = a.cast.walk[a.facing][int(a.frame) % 4]
            out.append((a.y, 2, img, a.x - TILE / 2, a.y - TILE + 8))
        return out

    def draw_labels(self, screen, cx, cy):
        ws, st = self.ws, self.state
        t = ws.t
        drawn: list[pygame.Rect] = []
        for m in sorted(self.mobs, key=lambda q: (q.kind == "mob", (q.x - ws.x) ** 2 + (q.y - ws.y) ** 2)):
            if not self.visible(m):
                continue
            near = (m.x - ws.x) ** 2 + (m.y - ws.y) ** 2 < LABEL_RANGE ** 2
            sx, sy = m.x - cx, m.y - cy
            if not (-60 < sx < theme.WIDTH + 60 and -60 < sy < theme.HEIGHT + 60):
                continue
            top = sy - m.cast.walk["down"][0].get_height() + 4
            if m.kind != "mob":
                glow = int(90 + 60 * math.sin(t * 5))
                ui.alpha_rect(screen, pygame.Rect(sx - 34, sy - 10, 68, 20), (220, 40, 30, glow), 10)
                tag = {"boss": "TRÙM", "elite": "KẺ MẠNH NHẤT VÙNG"}.get(m.kind, "CANH MẬT THƯ")
                fonts.text(screen, tag, fonts.font("black", 13), (255, 120, 90), (sx, top - 22), "midbottom", shadow=(24, 16, 14))
            if near or m.kind != "mob":
                f = fonts.font("bold", 13)
                text = f"{m.data['name']} · cấp {m.level}"
                box = pygame.Rect(0, 0, f.size(text)[0], 16)
                box.midbottom = (sx, top - 4)
                if box.collidelist(drawn) >= 0:
                    continue  # tên quái đứng gần nhau thì chỉ ghi tên con gần người chơi nhất
                drawn.append(box)
                fonts.text(screen, text, f, rpg.difficulty_color(st.level, m.level), (sx, top - 4), "midbottom", shadow=(24, 16, 14))
        if self.duel and self.duel["state"] == "ask":
            a = self.duel["actor"]
            ui.tag(screen, "Y: nhận lời thách đấu   ·   N: từ chối", (a.x - cx, a.y + 8 - cy), theme.LACQUER_RED, theme.GOLD_LIGHT, 14, "midtop")
        near = self.nearest()
        if near and not ws.nearest():
            label = {"mob": "F  Đánh", "elite": "F  Thách đấu kẻ mạnh nhất vùng"}.get(near.kind, "F  Hạ kẻ canh mật thư")
            ui.tag(screen, label, (near.x - cx, near.y + 6 - cy), theme.LACQUER_RED, theme.GOLD_LIGHT, 13, "midtop")

    def tracker(self) -> str | None:
        for m in self.mobs:
            if m.kind in ("guard", "boss") and self.visible(m):
                return f"Mật thư đang bị {m.data['name']} canh. Hạ hắn rồi mới nhặt được."
        return None
