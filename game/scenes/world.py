"""Màn chơi chính: điều khiển nhân vật đi trong map, nói chuyện với NPC, nhặt mảnh ghép, qua cổng dịch chuyển.

Mỗi di tích là một khu vực trên map. Các bước của di tích (đã có trong nội dung) được đặt thành vật thể có thể
đi tới: nghe chuyện ở người giữ ký ức, kiểm tra ở bia đá hoặc dân làng, mảnh ghép phát sáng trên đất, cờ trận.
"""

from __future__ import annotations

import math
import random

import pygame
from core import art, chienma, fleet, fonts, outfit, rpg, sprites, theme, ui, weapons
from core.scene import Scene
from core.sprites import TILE
from core.tilemap import BRIDGE, WATER
from core.weather import Weather
from core.worldgen import CATALOG, build_world

from scenes.actors import Actor, boat_views, horse_views, make_critters
from scenes.archive import ArchiveScene
from scenes.atlas import AtlasScene
from scenes.battle import make_battle
from scenes.bestiary import BestiaryScene
from scenes.ending import EndingScene
from scenes.explore import Explore, world_extras
from scenes.fishing import Fishing
from scenes.honor import HonorScene, board_sprite
from scenes.mobs import Mobs, _reachable
from scenes.multiplayer import Multiplayer
from scenes.notebook import NotebookScene
from scenes.playercard import PlayerCard
from scenes.profile import ProfileScene
from scenes.question import FragmentScene, QuestionScene
from scenes.review import ReviewScene
from scenes.roadmap import RoadmapScene
from scenes.shop import ShopScene
from scenes.skills import SkillsScene
from scenes.social import SocialScene
from scenes.story import StoryScene
from scenes.timeline import TimelineScene
from scenes.trailer import TrailerScene

W, H = theme.WIDTH, theme.HEIGHT
SPEED = TILE * 5.2
HORSE_SPEED = 1.65
BOAT_SPEED = 1.15
STEP_TIME = 0.32
RIDER_LIFT = 24
RIDER_LIFT_FRONT = 38
BOAT_WIDTH = 150
BOAT_LIFT = 14  # tâm thuyền cao hơn ô đang đứng một chút cho người ngồi giữa khoang
BOAT_STAND = 14
ADMIN_SPEED = 2.2
BONUS_CHECK = 2.0
HIT_W, HIT_H = int(TILE * 0.28), int(TILE * 0.18)
REACH = TILE * 1.75
PICKUP = TILE * 0.95
ZONE_RADIUS = 9 * TILE
PLAYER = "SamuraiBlue"
HELP_TIME = 25
MUSIC = {"man1": "road", "man2": "temple", "man3": "sad"}
KEEPERS = {"cu_do": "Master", "cu_tu": "Monk", "ba_cu": "OldWoman", "lai_do": "OldMan3", "cuu_binh": "OldMan"}
QUESTIONERS = ("Villager3", "Villager4", "Woman", "Villager")
NEXT_DIR = {(1, 0): "right", (-1, 0): "left", (0, 1): "down", (0, -1): "up"}
HUD_TRACKER = pygame.Rect(12, 10, 440, 104)
HUD_RPG = pygame.Rect(12, H - 104, 410, 92)
HINT_X = 724  # giữa khoảng trống từ khung cấp độ tới bản đồ nhỏ
SMITH_CHAR = "Villager"
MENTOR_NAME = "Cụ Đồ Sử"
MENU_TOGGLE, MENU_W, MENU_ROW = 52, 200, 40
HONOR_LEVEL = "man1"  # nút ba gạch, bề rộng và chiều cao mỗi dòng của danh sách xổ xuống
_worlds: dict[str, object] = {}


class MenuToggle(ui.Button):
    """Nút ba gạch: vẽ ba vạch ngang thay cho chữ; khi menu đang mở thì vẽ dấu X."""

    def _render(self, active: bool, press: int) -> pygame.Surface:
        label, self.label = self.label, ""
        try:
            out = super()._render(active, press)
        finally:
            self.label = label
        cx, cy = self.rect.w // 2, self.rect.h // 2 + press - 1
        color = theme.GOLD_LIGHT if active else theme.PAPER
        if label.startswith("Đóng"):
            for d in (-1, 1):
                pygame.draw.line(out, color, (cx - 9, cy - 9 * d), (cx + 9, cy + 9 * d), 4)
        else:
            for dy in (-8, 0, 8):
                pygame.draw.rect(out, color, (cx - 12, cy + dy - 2, 24, 4), border_radius=2)
        return out


def get_world(state, level_id: str):
    """Dựng map một lần cho mỗi màn rồi giữ lại, chỉ các mảng ảnh nền được giải phóng khi rời map."""
    if level_id not in _worlds:
        spec = dict(state.worlds[level_id], extra=world_extras(state, level_id))
        _worlds[level_id] = build_world(level_id, spec, state.levels[level_id]["relics"])
        _worlds[level_id].map.warm()
    return _worlds[level_id]


class WorldScene(Scene):
    def __init__(self, app, level_id: str, entry: str = "saved"):
        super().__init__(app)
        st = self.state
        self.level_id = level_id
        st.current_level = level_id
        self.bundle = st.levels[level_id]
        self.level = self.bundle["level"]
        self.world = get_world(st, level_id)
        self.map = self.world.map
        self.engine = st.engine(level_id)
        self.relics = self.bundle["relics"]
        self._quest_steps = {q["id"]: q["objectives"] for q in self.engine.quests}
        self.places = {p["id"]: p for p in self.bundle["places"]}
        self._init_runtime(entry)

    def _init_runtime(self, entry: str):
        """Phần dùng chung cho map chính và vùng luyện: nhân vật, camera, thời tiết, quái, nút bấm."""
        st = self.state
        self.t = 0.0
        self.player_cast = outfit.hero_cast(st.gear)
        self.facing = "down"
        self.frame = 0.0
        self.moving = False
        self.path: list[tuple[int, int]] = []
        self.auto: Actor | None = None
        self.pending = None
        self.zone_in: str | None = None
        self.banner: dict | None = None
        self.bubble: dict | None = None
        self.stamp_t = -1.0
        self.stamp_img = None
        self.warp: dict | None = None
        self.portal_warned = False
        self.mode = "walk"  # walk, horse, boat
        self.noclip = False  # quản trị viên đi xuyên tường, xuyên nước
        self.bonus_t = BONUS_CHECK
        self.horse_actor: Actor | None = None
        self.land_pos: list[float] | None = None
        self.steer: tuple[float, float] | None = None
        self.step_t = 0.0
        self.sp_seen = st.skill_points_earned()
        self.weather = Weather()
        self._weather_zone = "?"
        self.boat_imgs = boat_views(fleet.boat_sprite(BOAT_WIDTH))
        self.horse_imgs = self.plain_horse = horse_views()
        self.explore = self._make_explore()
        self.actors: list[Actor] = []
        self._spawn_actors()
        self.mobs = Mobs(self)
        self.mp = Multiplayer(self)  # người chơi khác trên cùng map
        self.fishing = Fishing(self)  # câu cá, nướng cá
        self.fishing.spawn()
        self.critters = make_critters(self.map, self._life())
        self._place_player(entry)
        self.cam_x, self.cam_y = 0.0, 0.0
        self._snap_camera()
        self._build_menu()
        self._check_zone()
        self._show_level_title()

    def _make_explore(self):
        return Explore(self)

    def _life(self) -> list:
        return self.state.worlds[self.level_id].get("life", [])

    # ---------- dựng nhân vật, vật thể ----------
    def _spawn_gates(self):
        """Biển chỉ đường sang vùng luyện, đặt ở ô đi bộ tới được gần chỗ đã định."""
        reach = _reachable(self.world)
        taken = {(int(a.x // TILE), int(a.y // TILE)) for a in self.actors}
        sign = sprites.region(*CATALOG["sign"][:3])
        for f in self.state.fields.values():
            if f["parent"] != self.level_id:
                continue
            gx, gy = f["gate"]
            free = [t for t in reach if t not in taken and abs(t[0] - gx) <= 12 and abs(t[1] - gy) <= 12] or list(reach)
            tile = min(free, key=lambda t: ((t[0] - gx) ** 2 + (t[1] - gy) ** 2, t))
            taken.add(tile)
            self.actors.append(Actor("fieldgate", tile, f["gate_name"], f"Đi tới {f['name']}", img=sign, data=f))

    def _enter_field(self, a: Actor):
        st = self.state
        f = a.data
        if not st.relic_done(f["requires"]):
            title = st.index["relics"][f["requires"]]["title"]
            self._say(a, f"Đường tới {f['name']} còn chưa mở. Học xong di tích “{title}” rồi hẵng đi.")
            return
        self.path.clear()
        self._land()
        self._save_pos()
        self.warp = {"t": 0.0, "level": None, "entry": "field", "field": f["id"]}
        self.app.audio.play("nhan")

    def _spawn_actors(self):
        world = self.world
        for relic in self.relics:
            zone = world.zones[relic["id"]]
            keeper = Actor("keeper", (zone.cx, zone.cy), relic.get("keeper_name", ""), "Nói chuyện", sprites.cast(KEEPERS.get(relic.get("keeper"), "Monk")), relic=relic)
            self.actors.append(keeper)
            spots = iter(zone.spots)
            count = 0
            for obj in self._objectives(relic):
                if obj["kind"] in ("go_to", "dialogue"):
                    continue  # đi tới thì tự tính khi bước vào khu vực, nghe chuyện thì ở người giữ ký ức
                spot = next(spots)
                if obj["kind"] == "answer":
                    count += 1
                    if count % 2:
                        self.actors.append(Actor("quiz", spot, "Bia đá", "Đọc bia đá", img=sprites.region(*CATALOG["stele"][:3]), relic=relic, objective=obj))
                    else:
                        name = QUESTIONERS[(count // 2) % len(QUESTIONERS)]
                        self.actors.append(Actor("quiz", spot, "Người trong vùng", "Trả lời câu đố", sprites.cast(name), relic=relic, objective=obj))
                elif obj["kind"] == "collect":
                    self.actors.append(Actor("scroll", spot, "Mảnh ghép", "Nhặt mảnh ghép", img=sprites.icon("ui/scroll.png"), relic=relic, objective=obj))
                else:
                    self.actors.append(Actor("war", spot, "Cờ trận", "Vào trận", img=sprites.strip("fx/flag_red.png", 4)[0], relic=relic, objective=obj))
        self.mentor = Actor("mentor", world.mentor, MENTOR_NAME, "Nói chuyện", sprites.cast("Master"))
        self.actors.append(self.mentor)
        smith = Actor("smith", self._smith_tile(), "Thợ rèn", "Mua đồ", sprites.cast(SMITH_CHAR))
        self.actors.append(smith)
        if self.level_id == HONOR_LEVEL:  # Bảng vàng dựng ở map đầu, gần chỗ xuất phát cho ai cũng thấy
            tile = self._honor_tile((int(smith.x // TILE), int(smith.y // TILE)))
            self.actors.append(Actor("honor", tile, "Bảng vàng", "Xem bảng vàng", img=board_sprite()))
        arch = sprites.region(*CATALOG["arch"][:3], 3, 3)
        self.portal = Actor("portal", world.portal, "Cổng dịch chuyển", "", img=arch)
        self.actors.append(self.portal)
        self.back_portal = None
        back = self.state.worlds[self.level_id].get("back")
        if back:
            self.back_portal = Actor("back", back, "Cổng quay về", "", img=arch)
            self.actors.append(self.back_portal)
        for npc in world.npcs:
            self.actors.append(Actor("npc", npc["at"], "Người đi đường", "Bắt chuyện", sprites.cast(npc["char"]), lines=npc["lines"]))
        self.explore.spawn()
        self._spawn_gates()

    def _smith_tile(self) -> tuple[int, int]:
        """Lò rèn đứng gần chỗ xuất phát, lệch sang một bên cho khỏi chắn đường."""
        sx, sy = self.world.spawn
        avoid = {tuple(self.world.mentor), tuple(self.world.portal), (sx, sy)}
        for dx, dy in ((3, 0), (-3, 0), (3, 1), (-3, 1), (2, 2), (-2, 2), (4, -1), (-4, -1), (0, 3), (5, 0), (-5, 0)):
            t = (sx + dx, sy + dy)
            if t not in avoid and not self.map.blocked(*t) and not self.map.blocked(t[0], t[1] + 1):
                return t
        return (sx + 1, sy + 1)

    def _honor_tile(self, smith: tuple[int, int]) -> tuple[int, int]:
        """Bảng rộng hai ô: tìm chỗ trống hai ô liền nhau gần chỗ xuất phát, không đè lò rèn, Cụ Đồ Sử, cổng."""
        sx, sy = self.world.spawn
        avoid = {tuple(self.world.mentor), tuple(self.world.portal), (sx, sy), smith}
        for dx, dy in ((-4, -2), (4, -2), (-5, 2), (5, 2), (-3, -3), (3, -3), (-6, 0), (6, 0), (0, -4), (0, 4), (-7, -2), (7, -2)):
            t = (sx + dx, sy + dy)
            cells = [(t[0] + i, t[1] + j) for i in (-1, 0, 1) for j in (0, 1)]
            if not any(c in avoid or self.map.blocked(*c) for c in cells):
                return t
        return (sx - 2, sy + 2)

    def _place_player(self, entry: str):
        saved = self.state.player_pos.get(self.level_id)
        if entry == "saved" and isinstance(saved, list) and len(saved) == 2:
            self.x, self.y = float(saved[0]), float(saved[1])
            if not self._hit(self.x, self.y):
                return
        if entry == "from_next":
            tile = (self.world.portal[0], self.world.portal[1] + 2)
        elif entry == "travel":
            tile = self.world.spawn
        else:
            tile = self.world.spawn
        self.x, self.y = tile[0] * TILE + TILE / 2, tile[1] * TILE + TILE - 8

    def on_enter(self):
        self.app.audio.music(MUSIC.get(self.level_id, "road"))
        self._apply_weather(True)

    def _apply_weather(self, force=False):
        """Mỗi khu có thể có thời tiết riêng; ra khỏi khu thì trở về thời tiết chung của màn."""
        if self.zone_in == self._weather_zone and not force:
            return
        self._weather_zone = self.zone_in
        spec = self.state.worlds[self.level_id]
        kind = spec["zones"].get(self.zone_in, {}).get("weather", spec.get("weather"))
        self.weather.set(kind)
        self.app.audio.ambient("rain" if kind == "rain" else spec.get("sound"))

    def _report_points(self):
        """Báo khi vừa có thêm điểm kỹ năng, để người chơi biết việc học sử đang làm mình mạnh lên."""
        earned = self.state.skill_points_earned()
        if earned > self.sp_seen:
            self.app.toast(f"+{earned - self.sp_seen} điểm kỹ năng. Mở trang Kỹ năng (phím K) để dùng", theme.GOLD_LIGHT, 3.5)
            self.app.audio.play("nang")
        self.sp_seen = earned

    # ---------- nhiệm vụ ----------
    def _objectives(self, relic):
        return self._quest_steps[relic["id"]]

    def _next_obj(self, relic):
        done = self.state.progress.completed_objectives
        return next((o for o in self._objectives(relic) if o["id"] not in done), None)

    def _unlocked(self, relic) -> bool:
        return relic["place"] in self.engine.unlocked_places()

    def _portal_open(self) -> bool:
        st = self.state
        if self.level_id in st.progress.completed_levels:
            return True
        # Quản trị viên qua lại giữa các màn tự do; cổng ở màn cuối vẫn phải chơi xong mới mở vì nó kết thúc game
        return st.is_admin and st.order.index(self.level_id) + 1 < len(st.order)

    def _current(self) -> tuple[str, tuple[float, float] | None]:
        """Việc cần làm tiếp theo và vị trí của nó, cho khung nhiệm vụ và mũi tên chỉ đường."""
        st = self.state
        if st.reports:
            return f"Về báo cáo với {MENTOR_NAME} (già làng) để nhận thưởng", (self.mentor.x, self.mentor.y)
        relic = st.next_relic(self.level_id)
        if relic:
            obj = self._next_obj(relic)
            zone = self.world.zones[relic["id"]]
            name = self.places[relic["place"]]["name"]
            if obj is None or obj["kind"] == "go_to":
                return f"Đi tới {name}", (zone.cx * TILE, zone.cy * TILE)
            actor = next((a for a in self.actors if a.objective is not None and a.objective["id"] == obj["id"]), None)
            if obj["kind"] == "dialogue":
                keeper = next(a for a in self.actors if a.kind == "keeper" and a.relic is relic)
                return f"Nghe {relic.get('keeper_name', '')} kể chuyện", (keeper.x, keeper.y)
            if obj["kind"] == "answer":
                return f"Cửa kiểm tra: {actor.name.lower()} ở {name}", (actor.x, actor.y)
            if obj["kind"] == "collect":
                guard = self.mobs.guard_of(actor)
                if guard is not None:
                    return f"Hạ {guard.data['name']} đang canh mật thư", (guard.x, guard.y)
                return "Nhặt mảnh ghép tư liệu đang phát sáng", (actor.x, actor.y)
            title = st.index["battles"][obj["target_id"]]["title"]
            return f"Đến cờ trận: {title}", (actor.x, actor.y)
        if self.level_id not in st.progress.timeline_done:
            return "Về gặp Cụ Đồ Sử để dựng lại dòng thời gian", (self.mentor.x, self.mentor.y)
        idx = st.order.index(self.level_id)
        if idx + 1 < len(st.order):
            return "Bước vào cổng dịch chuyển để sang giai đoạn mới", (self.portal.x, self.portal.y)
        return "Bước vào cổng để khép lại cuốn sử", (self.portal.x, self.portal.y)

    def _check_zone(self):
        """Đánh dấu đã đến khu vực và hiện tên địa danh khi vừa bước vào."""
        inside = None
        for relic in self.relics:
            zone = self.world.zones[relic["id"]]
            dx, dy = self.x - (zone.cx + 0.5) * TILE, self.y - (zone.cy + 0.5) * TILE
            if dx * dx + dy * dy <= ZONE_RADIUS * ZONE_RADIUS:
                inside = relic
                break
        if inside is None:
            self.zone_in = None
            self._apply_weather()
            return
        if self._unlocked(inside):
            first = self._objectives(inside)[0]
            if first["id"] not in self.state.progress.completed_objectives:
                self._apply(self.engine.on_arrive(inside["place"]))
                self.state.save()
        if self.zone_in != inside["id"]:
            self.zone_in = inside["id"]
            place = self.places[inside["place"]]
            sub = place.get("modern_name", "")
            if not self._unlocked(inside):
                sub = "Chưa mở: hãy hoàn thành di tích trước đó"
            self.banner = {"title": inside["title"], "sub": sub, "t": 0.0}
        self._apply_weather()

    def _show_level_title(self):
        self.banner = {"title": self.level["title"], "sub": self.level["period_label"], "t": 0.0}

    def _apply(self, effects):
        for msg in self.state.effect_messages(effects, self.bundle):
            self.app.toast(msg)

    # ---------- tương tác ----------
    def _visible(self, a: Actor) -> bool:
        if a.objective is None or a.kind == "quiz":
            return self.explore.visible(a)
        done = a.objective["id"] in self.state.progress.completed_objectives
        if a.kind == "scroll":
            return not done and self._is_current(a)
        return done or self._is_current(a)

    def _is_current(self, a: Actor) -> bool:
        if a.objective is None or not self._unlocked(a.relic):
            return False
        nxt = self._next_obj(a.relic)
        return nxt is not None and nxt["id"] == a.objective["id"]

    def _say(self, actor: Actor, text: str, seconds: float = 4.5):
        self.bubble = {"actor": actor, "text": text, "t": seconds}

    def nearest(self) -> Actor | None:
        best, best_d = None, REACH * REACH
        for a in self.actors:
            d = (a.x - self.x) ** 2 + (a.y - self.y) ** 2
            if d < best_d and a.kind not in ("portal", "back") and self._visible(a):
                best, best_d = a, d
        return best

    def interact(self, a: Actor):
        self.path.clear()
        self.auto = None
        if a.cast:
            a.facing = self._dir_to(a.x, a.y, self.x, self.y)
            self.facing = self._dir_to(self.x, self.y, a.x, a.y)
        self.app.audio.play("click")
        if self.explore.interact(a) or self.fishing.interact(a):
            return
        if a.kind == "keeper":
            self._talk_keeper(a)
        elif a.kind == "npc":
            self._say(a, random.choice(a.lines))
        elif a.kind == "mentor":
            self._talk_mentor(a)
        elif a.kind == "smith":
            self.app.scenes.push(ShopScene(self.app, True, a.name))
        elif a.kind == "fieldgate":
            self._enter_field(a)
        elif a.kind == "honor":
            self.app.scenes.push(HonorScene(self.app))
        elif a.kind == "scroll" and self._guarded(a):
            return
        elif self._is_current(a):
            self._run(a.relic, a.objective)
        elif a.objective["id"] in self.state.progress.completed_objectives:
            self._say(a, "Việc ở đây đã xong rồi.")
        else:
            self._say(a, f"Hãy nghe {a.relic.get('keeper_name', 'người giữ ký ức')} kể trước đã.")

    def _talk_keeper(self, a: Actor):
        relic = a.relic
        if not self._unlocked(relic):
            need = [self.state.index["relics"][m["quest_done"]]["title"] for m in self.engine.place_missing(relic["place"]) if "quest_done" in m]
            self._say(a, "Cháu nên đi " + (need[0] if need else "nơi khác") + " trước, rồi hãy quay lại đây.")
            return
        nxt = self._next_obj(relic)
        if nxt is None:
            if relic.get("extra_talk"):
                talk = {"speaker": a.name, "portrait": relic.get("keeper", "tu_lieu"), "prompt": relic.get("extra_prompt", "Cháu quay lại à?")}
                self.pending = None
                self.app.scenes.push(StoryScene(self.app, talk, topics_only=self._topics(relic)))
            else:
                self._say(a, relic.get("keeper_done") or "Đi tiếp đi cháu.")
        elif nxt["kind"] == "dialogue":
            self._run(relic, nxt)
        else:
            hint = {"answer": "Câu hỏi đang chờ cháu ở gần đây, tìm dấu hỏi nhé.", "collect": "Có tờ tư liệu đang phát sáng quanh đây, nhặt đi cháu.", "battle": "Cờ trận đã dựng, đến đó khi cháu sẵn sàng."}
            self._say(a, relic.get("keeper_line") if nxt["kind"] == "go_to" else hint[nxt["kind"]])

    def _topics(self, relic):
        """Chủ đề có `replay` thì lấy nguyên đoạn hồi ức đã nghe để kể lại."""
        idx = self.state.index["dialogues"]
        return [dict(tp, lines=idx[tp["replay"]]["nodes"]) if tp.get("replay") else tp for tp in relic["extra_talk"]]

    def _guarded(self, scroll: Actor) -> bool:
        """Mật thư còn kẻ canh thì chưa nhặt được; nhắc một lần mỗi khi lại gần."""
        guard = self.mobs.guard_of(scroll)
        if guard is None:
            return False
        if self.mobs.warned is not guard:
            self.mobs.warned = guard
            self._say(scroll, f"{guard.data['name']} đang canh mật thư này. Bấm F để đánh!", 3.5)
        return True

    def _report(self, a: Actor):
        """Về báo cáo già làng: nhắc lại câu hỏi lớn của từng di tích, trao thưởng, chỉ việc tiếp theo."""
        st = self.state
        done = st.report()
        nodes = []
        for relic in done[-3:]:
            nodes.append({"speaker": a.name, "portrait": "cu_do", "fiction": True, "text": (
                f"Cháu về từ {relic['title']} rồi à. Câu hỏi lớn ở đó là: {relic['central_question']} "
                "Điều cháu tìm ra đã chép vào Sổ tay (phím N), lúc nào cũng mở ra đọc lại được.")})
        n = len(done)
        more = f" (cả {n - 3} di tích trước đó nữa)" if n > 3 else ""
        nxt = self._current()[0]
        nodes.append({"speaker": a.name, "portrait": "cu_do", "fiction": True, "text": (
            f"Làng ghi công cháu{more}: +{rpg.RELIC_EXP * n} kinh nghiệm, +{rpg.RELIC_TIEM * n} tiềm năng, +{rpg.RELIC_QUAN * n} quan. "
            f"Việc tiếp theo: {nxt[0].lower() + nxt[1:]}.")})
        self.app.audio.play("nang")
        self.explore._push(StoryScene(self.app, {"id": "extra", "bg": "lang_co", "nodes": nodes}), lambda _r: self._talk_mentor(a, False))

    def _talk_mentor(self, a: Actor, report: bool = True):
        st = self.state
        if report and st.reports:
            self._report(a)
        elif self.level_id in st.progress.timeline_done:
            self._say(a, "Dòng thời gian đã liền mạch. Cổng dịch chuyển mở rồi, đi đi cháu!")
        elif st.timeline_ready(self.level_id):
            self.pending = None
            self.app.scenes.push(TimelineScene(self.app, self.level_id))
        else:
            left = [r["title"] for r in st.mandatory_relics(self.level_id) if not st.relic_done(r["id"])]
            self._say(a, f"Còn {len(left)} di tích chưa xong. Gần nhất là: {left[0]}.")

    def _run(self, relic, obj):
        self.pending = (relic, obj)
        kind, target = obj["kind"], obj["target_id"]
        idx = self.state.index
        scenes = self.app.scenes
        if kind == "dialogue":
            scenes.push(StoryScene(self.app, idx["dialogues"][target]))
        elif kind == "answer":
            scenes.push(QuestionScene(self.app, idx["questions"][target]))
        elif kind == "collect":
            scenes.push(FragmentScene(self.app, idx["fragments"][target]))
        elif kind == "battle":
            self.app.audio.music("fight")
            scenes.push(make_battle(self.app, idx["battles"][target]))

    def on_resume(self, result=None):
        self.player_cast = outfit.hero_cast(self.state.gear)  # vừa thay đồ ở lò rèn hay túi đồ thì ngoại hình đổi ngay
        self.app.audio.music(MUSIC.get(self.level_id, "road"))
        self._apply_weather(True)
        self._after_explore(result)
        if isinstance(result, dict) and result.get("travel"):
            level = result.get("level", self.level_id)
            if level != self.level_id:  # chỉ quản trị viên mới được chọn di tích ở màn khác
                self._land()
                self._save_pos()
                self.map.forget()
                nxt = WorldScene(self.app, level, "spawn")
                self.app.scenes.replace(nxt)
                nxt._travel(result["travel"])
                return
            self._travel(result["travel"])
            return
        pending, self.pending = self.pending, None
        if pending and result:
            relic, obj = pending
            st = self.state
            kind, target = obj["kind"], obj["target_id"]
            if kind == "dialogue":
                effects = self.engine.on_dialogue_done(target)
            elif kind == "answer":
                effects = self.engine.on_question_correct(target)
            elif kind == "collect":
                effects = st.collect_fragment(target)
            else:
                effects = self.engine.on_battle_done(target)
            self._apply(effects)
            if self._next_obj(relic) is None and relic["id"] not in st.stamps:
                for msg in st.finish_relic(relic):
                    self.app.toast(msg, theme.GOLD_LIGHT, 4.0)
                for f in st.fields.values():
                    if f["requires"] == relic["id"]:
                        self.app.toast(f"Mở đường tới vùng luyện mới: {f['name']} (tìm biển chỉ đường trên map)", theme.JADE_LIGHT, 5.0)
                self.stamp_img = art.stamp(relic.get("stamp", relic["title"]), 190)
                self.stamp_t = 0.0
                self.app.audio.play("dau")
                keeper = next(a for a in self.actors if a.kind == "keeper" and a.relic is relic)
                self._say(keeper, relic.get("keeper_done") or "Làm tốt lắm.", 6.0)
        self._report_points()
        self._save_pos()
        self._check_zone()

    def _after_explore(self, result):
        """Chạy việc nối tiếp của phần khám phá nếu có."""
        cont, self.explore.next = self.explore.next, None
        if cont:
            cont(result)

    def _travel(self, relic_id: str):
        """Đi nhanh tới một di tích đã mở từ bản đồ."""
        self._land()
        zone = self.world.zones[relic_id]
        self.x, self.y = (zone.cx + 0.5) * TILE, (zone.cy + 2) * TILE - 8
        self.path.clear()
        self._snap_camera()
        self._check_zone()

    def _save_pos(self):
        # Đang chèo thuyền thì lưu chỗ vừa rời bờ, vì tải lại game sẽ đứng trên đất
        x, y = self.land_pos if self.mode == "boat" and self.land_pos else (self.x, self.y)
        self.state.player_pos[self.level_id] = [round(x), round(y)]
        self.state.save()

    # ---------- nút giao diện ----------
    def _build_menu(self):
        """Góc trên bên phải chỉ có một nút ba gạch cho đỡ che màn hình; bấm vào mới xổ danh sách các mục, kèm phím tắt."""
        self.menu_open = False
        self.menu_btn = MenuToggle((W - 12 - MENU_TOGGLE, 10, MENU_TOGGLE, 44), "Mở menu", self._toggle_menu, "ghost")
        items = (("Lộ trình", self._roadmap, "J"), ("Kỹ năng", self._skills, "K"), ("Tư liệu", self._archive, "T"),
                 ("Sổ tay", self._notebook, "N"), ("Bản đồ", self._atlas, "M"), ("Túi đồ", self._bag, "B"),
                 ("Sổ bóng giặc", self._bestiary, "G"), ("Bạn chơi", self._social, "P"), ("Chat", self._chat, "L"),
                 ("Hộ chiếu", self._profile, ""),
                 ("Ôn tập", self._review, ""), ("Tạm dừng", self._pause, "Esc"))
        self.menu_items = []
        y = 10 + 44 + 10
        for label, fn, key in items:
            btn = ui.Button((W - 12 - MENU_W, y, MENU_W, MENU_ROW - 5), label, self._pick(fn), "ghost", size=14, data=key)
            self.menu_items.append(btn)
            if label == "Kỹ năng":
                self.skill_btn = btn
            y += MENU_ROW
        self.group = ui.ButtonGroup([self.menu_btn])

    def _menu_rect(self) -> pygame.Rect:
        first, last = self.menu_items[0].rect, self.menu_items[-1].rect
        return pygame.Rect(first.x - 8, first.y - 8, first.w + 16, last.bottom - first.y + 16)

    def _toggle_menu(self, open_: bool | None = None):
        self.menu_open = (not self.menu_open) if open_ is None else open_
        self.menu_btn.label = "Đóng menu" if self.menu_open else "Mở menu"
        for b in self.menu_items:
            b.hover = b.focus = b._press = False
        self.group.buttons = [self.menu_btn, *self.menu_items] if self.menu_open else [self.menu_btn]
        self.group.index = -1

    def _pick(self, fn):
        def run():
            self._toggle_menu(False)
            fn()
        return run

    def _bag(self):
        self.app.scenes.push(ShopScene(self.app, False))

    def _bestiary(self):
        self.app.scenes.push(BestiaryScene(self.app))

    def _social(self):
        self.app.scenes.push(SocialScene(self.app))

    def _chat(self):
        self.mp.open_chat()

    def _draw_menu(self, screen):
        if self.menu_open:
            ui.lacquer_panel(screen, self._menu_rect(), 242)
        self.group.draw(screen)
        if self.menu_open:
            f = fonts.font("ui", 12)
            for b in self.menu_items:
                if b.data:
                    fonts.text(screen, b.data, f, theme.PAPER_3, (b.rect.right - 12, b.rect.centery), "midright")
        self._draw_skill_badge(screen)

    def _notebook(self):
        self.app.scenes.push(NotebookScene(self.app))

    def _profile(self):
        self.app.scenes.push(ProfileScene(self.app))

    def _review(self):
        self.app.scenes.push(ReviewScene(self.app, self.level_id))

    def _atlas(self):
        self.app.scenes.push(AtlasScene(self.app, self.level_id))

    def _pause(self):
        self._save_pos()
        self.app.scenes.push(PauseScene(self.app))

    def _skills(self):
        self.app.scenes.push(SkillsScene(self.app))

    def _roadmap(self):
        self.app.scenes.push(RoadmapScene(self.app, self.level_id, self._current()[0]))

    def _archive(self):
        self.app.scenes.push(ArchiveScene(self.app, self.level_id))

    # ---------- cưỡi ngựa, chèo thuyền ----------
    def mount(self, a: Actor):
        self.mode = "horse"
        self.horse_actor = a
        self.path.clear()
        self.auto = None
        self.app.audio.play("kiem")

    def _dismount(self):
        a = self.horse_actor
        if a is not None:
            a.x, a.y = self.x, self.y
            a.home = (a.x, a.y)
        self.horse_actor = None
        self.horse_imgs = self.plain_horse
        self.mode = "walk"

    def _summon_horse(self):
        """Phím H: gọi chiến mã từ cấp 3, gọi lần nữa thì cho ngựa về."""
        if self.mode == "horse":
            self._dismount()
            return
        if self.mode != "walk":
            return
        if self.state.level < rpg.HORSE_LEVEL:
            self.app.toast(f"Đạt cấp {rpg.HORSE_LEVEL} mới triệu hồi được chiến mã", theme.PAPER, 2.5)
            return
        self.mode = "horse"
        self.horse_actor = None
        self.horse_imgs = chienma.views()
        self.path.clear()
        self.auto = None
        self.app.audio.play("kiem")
        self.app.toast("Chiến mã đã tới! Bấm H lần nữa để cho ngựa về", theme.GOLD_LIGHT, 2.5)

    def board(self, a: Actor):
        """Xuống thuyền ở ô nước gần bến nhất."""
        tile = self._nearest_tile(a.x, a.y, 4, lambda x, y: self.map.get(x, y) == WATER)
        if tile is None:
            self._say(a, "Nước cạn quá, thuyền không xuống được.")
            return
        self.land_pos = [self.x, self.y]
        self.mode = "boat"
        self.path.clear()
        self.auto = None
        self.x, self.y = (tile[0] + 0.5) * TILE, (tile[1] + 0.5) * TILE
        self.app.audio.play("nuoc")

    def _disembark(self):
        tile = self._nearest_tile(self.x, self.y, 2, lambda x, y: not self.map.blocked(x, y))
        if tile is None:
            self.app.toast("Chèo sát bờ hoặc cầu tàu rồi mới lên được", theme.PAPER, 2.5)
            return
        self.x, self.y = (tile[0] + 0.5) * TILE, tile[1] * TILE + TILE - 8
        self.mode = "walk"
        self.steer = None
        self.app.audio.play("nuoc")

    def _land(self):
        """Rời ngựa, rời thuyền ngay lập tức khi đổi chỗ hay đổi màn."""
        if self.mode == "boat" and self.land_pos:
            self.x, self.y = self.land_pos
        elif self.mode == "horse":
            self._dismount()
        self.mode = "walk"
        self.steer = None

    @staticmethod
    def _nearest_tile(px, py, radius, test):
        cx, cy = int(px // TILE), int(py // TILE)
        best, best_d = None, 1e9
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                d = ((x + 0.5) * TILE - px) ** 2 + ((y + 0.5) * TILE - py) ** 2
                if d < best_d and test(x, y):
                    best, best_d = (x, y), d
        return best

    # ---------- quyền quản trị ----------
    def _toggle_noclip(self):
        self.noclip = not self.noclip
        self.steer = None
        self.path.clear()
        self.app.toast("Đi xuyên tường: " + ("bật" if self.noclip else "tắt"), theme.GOLD_LIGHT, 2.0)
        if not self.noclip and self._hit(self.x, self.y):
            # Vừa tắt mà đang đứng trong tường thì đưa ra ô trống gần nhất để không bị kẹt
            tile = self._nearest_tile(self.x, self.y, 12, lambda x, y: not self.map.blocked(x, y))
            if tile:
                self.x, self.y = (tile[0] + 0.5) * TILE, (tile[1] + 1) * TILE - 8

    def _minimap_rect(self) -> pygame.Rect:
        return self.world.build_minimap().get_rect(bottomright=(W - 16, H - 16))

    def _admin_jump(self, pos):
        """Bấm vào bản đồ nhỏ để dịch chuyển tức thì tới chỗ đó."""
        rect = self._minimap_rect()
        tx, ty = (pos[0] - rect.x) // 2, (pos[1] - rect.y) // 2
        if not self.noclip and self.map.blocked(tx, ty):
            tile = self._nearest_tile((tx + 0.5) * TILE, (ty + 0.5) * TILE, 12, lambda x, y: not self.map.blocked(x, y))
            if tile is None:
                return
            tx, ty = tile
        self._land()
        self.path.clear()
        self.auto = None
        self.x, self.y = (tx + 0.5) * TILE, (ty + 1) * TILE - 8
        self._snap_camera()
        self.app.audio.play("nhan")
        self._check_zone()

    def _check_bonus(self):
        """Điểm được tặng tới trong lúc đang chơi thì báo ngay."""
        gained = self.state.refresh_external()
        if gained > 0:
            self.app.toast(f"Quản trị viên vừa tặng bạn {gained} điểm", theme.GOLD_LIGHT, 3.5)
        self._report_points()

    def _speed(self) -> float:
        k = self.state.speed_mult() * self.explore.speed_mult()
        if self.noclip:
            k *= ADMIN_SPEED
        if self.mode == "horse":
            k *= HORSE_SPEED
        elif self.mode == "boat":
            k *= BOAT_SPEED
        return SPEED * k

    # ---------- di chuyển ----------
    @staticmethod
    def _dir_to(x0, y0, x1, y1) -> str:
        dx, dy = x1 - x0, y1 - y0
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        return "down" if dy > 0 else "up"

    def _hit(self, x, y) -> bool:
        if self.noclip:
            return not (0 <= x < self.world.px_w and 0 <= y < self.world.px_h)
        if self.mode == "boat":  # thuyền chỉ đi trên nước, được chui qua gầm cầu
            get = self.map.get
            return any(get(int(px // TILE), int(py // TILE)) not in (WATER, BRIDGE) for px, py in ((x - HIT_W, y - HIT_H), (x + HIT_W, y - HIT_H), (x - HIT_W, y + 2), (x + HIT_W, y + 2)))
        blocked = self.map.blocked
        for px, py in ((x - HIT_W, y - HIT_H), (x + HIT_W, y - HIT_H), (x - HIT_W, y + 2), (x + HIT_W, y + 2)):
            if blocked(int(px // TILE), int(py // TILE)):
                return True
        return False

    def _move(self, dx, dy, dt):
        length = math.hypot(dx, dy)
        if not length:
            return False
        step = self._speed() * dt / length
        nx, ny = self.x + dx * step, self.y + dy * step
        moved = False
        if not self._hit(nx, self.y):
            self.x = nx
            moved = True
        if not self._hit(self.x, ny):
            self.y = ny
            moved = True
        if abs(dx) > abs(dy):
            self.facing = "right" if dx > 0 else "left"
        else:
            self.facing = "down" if dy > 0 else "up"
        return moved

    def _walk_to(self, wx, wy):
        start = (int(self.x // TILE), int((self.y - 4) // TILE))
        self.path = self.map.find_path(start, (int(wx // TILE), int(wy // TILE)))

    def handle(self, event):
        if self.warp:
            return
        # Bàn phím dành cho việc đi lại: phím mũi tên không được chuyển con trỏ sang nút rồi phím cách bấm nhầm nút đó
        if event.type != pygame.KEYDOWN and self.group.handle(event):
            return
        if self.menu_open:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._toggle_menu(False)
                return
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                if event.type == pygame.MOUSEBUTTONUP and not self._menu_rect().collidepoint(event.pos):
                    self._toggle_menu(False)  # bấm ra ngoài: chỉ đóng menu, không đi tới chỗ vừa bấm
                return
        if self.mp.handle(event):  # thẻ lời mời ở góc trên phải: Đồng ý, Từ chối
            return
        if event.type == pygame.KEYDOWN:
            duel = self.mobs.duel
            if duel and duel["state"] == "ask" and event.key in (pygame.K_y, pygame.K_n):
                self.mobs.answer(event.key == pygame.K_y)
                return
            if event.key == pygame.K_c or (self.fishing.mode == "bite" and event.key in (pygame.K_e, pygame.K_SPACE)):
                self.fishing.press()
            elif event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
                near = self.nearest()
                mob = self.mobs.nearest()
                if near:
                    self.interact(near)
                elif mob:
                    self.mobs.engage(mob)
                elif self.mode == "boat":
                    self._disembark()
            elif event.key == pygame.K_f:
                mob = self.mobs.nearest()
                if mob:
                    self.mobs.engage(mob)
            elif event.key == pygame.K_h:
                self._summon_horse()
            elif event.key == pygame.K_b:
                self._bag()
            elif event.key == pygame.K_g:
                self._bestiary()
            elif event.key == pygame.K_p:
                self._social()
            elif event.key == pygame.K_r:
                self._toggle_horse()
            elif event.key == pygame.K_k:
                self._skills()
            elif event.key == pygame.K_j:
                self._roadmap()
            elif event.key == pygame.K_t:
                self._archive()
            elif event.key == pygame.K_v and self.state.is_admin:
                self._toggle_noclip()
            elif event.key == pygame.K_m:
                self._atlas()
            elif event.key == pygame.K_n:
                self._notebook()
            elif event.key == pygame.K_l:
                self.mp.open_chat()
            elif event.key == pygame.K_ESCAPE:
                self._pause()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if HUD_TRACKER.collidepoint(event.pos):
                self._roadmap()
                return
            if self.state.is_admin and self._minimap_rect().collidepoint(event.pos):
                self._admin_jump(event.pos)
                return
            wx, wy = event.pos[0] + self.cam_x, event.pos[1] + self.cam_y
            other = self.mp.avatar_at(wx, wy)
            if other is not None:  # bấm vào người chơi khác: bảng trạng thái của họ, mời tổ đội, đồng minh, thách đấu
                self.path.clear()
                self.auto = None
                self.app.scenes.push(PlayerCard(self.app, self.mp, other.id))
                return
            clicked = None
            for a in self.actors:
                if a.kind not in ("portal", "back") and self._visible(a) and (a.x - wx) ** 2 + (a.y - TILE / 2 - wy) ** 2 < TILE ** 2:
                    clicked = a
                    break
            mob = None if clicked else self.mobs.at(wx, wy)
            if clicked and (clicked.x - self.x) ** 2 + (clicked.y - self.y) ** 2 < REACH ** 2:
                self.interact(clicked)
            elif clicked:
                self.auto = clicked
                self._walk_to(clicked.x, clicked.y + TILE)
            elif mob and (mob.x - self.x) ** 2 + (mob.y - self.y) ** 2 < (REACH * 1.2) ** 2:
                self.mobs.engage(mob)
            elif mob:
                self.auto = None
                self._walk_to(mob.x, mob.y + TILE)
            elif self.mode == "boat" or self.noclip:
                self.steer = (wx, wy)
            else:
                self.auto = None
                self._walk_to(wx, wy)

    def _toggle_horse(self):
        if self.mode == "horse":
            self._dismount()
        elif self.mode == "walk":
            near = next((a for a in self.actors if a.kind == "horse" and (a.x - self.x) ** 2 + (a.y - self.y) ** 2 < REACH ** 2), None)
            if near:
                self.mount(near)

    def update(self, dt):
        self.t += dt
        if self.warp:
            self._update_warp(dt)
            return
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        self.moving = False
        if dx or dy:
            self.path.clear()
            self.auto = None
            self.steer = None
            self.moving = self._move(dx, dy, dt)
        elif self.steer:
            sx, sy = self.steer[0] - self.x, self.steer[1] - self.y
            if abs(sx) < 8 and abs(sy) < 8:
                self.steer = None
            else:
                self.moving = self._move(sx, sy, dt)
                if not self.moving:
                    self.steer = None
        elif self.path:
            self.moving = self._follow_path(dt)
        if self.auto and (self.auto.x - self.x) ** 2 + (self.auto.y - self.y) ** 2 < (REACH * 0.8) ** 2:
            actor, self.auto = self.auto, None
            self.interact(actor)
            return
        self.frame = self.frame + dt * 8 if self.moving else 0.0
        self.step_t -= dt
        if self.moving and self.step_t <= 0 and self.mode != "boat":
            self.step_t = STEP_TIME / (HORSE_SPEED if self.mode == "horse" else 1.0)
            self.app.audio.play("buoc")
        self._update_npcs(dt)
        for c in self.critters:
            c.update(dt, self.map, self.x, self.y)
        self.weather.update(dt)
        self.explore.update(dt)
        self.mobs.update(dt)
        self.mp.update(dt)
        self.fishing.update(dt)
        self._drain_events()
        self.bonus_t -= dt
        if self.bonus_t <= 0:
            self.bonus_t = BONUS_CHECK
            self._check_bonus()
        self._check_zone()
        self._check_pickup()
        self._check_portals()
        self._update_timers(dt)
        self._follow_camera(dt)
        self.map.prefetch(self.cam_x, self.cam_y, W, H)

    def _drain_events(self):
        """Lên cấp, nhận tinh hoa...: hiện thành dòng thông báo."""
        ev = self.state.events
        if ev:
            for msg in ev:
                self.app.toast(msg, theme.GOLD_LIGHT, 3.5)
            if any(m.startswith("Lên cấp") for m in ev):
                self.app.audio.play("nang")
            ev.clear()

    def _follow_path(self, dt) -> bool:
        tx, ty = self.path[0]
        gx, gy = (tx + 0.5) * TILE, (ty + 1) * TILE - 8
        dx, dy = gx - self.x, gy - self.y
        if abs(dx) < TILE / 6 and abs(dy) < TILE / 6:
            self.path.pop(0)
            return True
        if not self._move(dx, dy, dt):
            self.path.clear()
            return False
        return True

    def _update_npcs(self, dt):
        for a in self.actors:
            if a.kind not in ("npc",):
                if a.cast and (a.x - self.x) ** 2 + (a.y - self.y) ** 2 < (REACH * 2) ** 2:
                    a.facing = self._dir_to(a.x, a.y, self.x, self.y)
                continue
            if a.goal is None:
                a.frame = 0.0
                a.wait -= dt
                if a.wait <= 0:
                    a.wait = random.uniform(1.5, 5)
                    gx, gy = a.home[0] + random.randint(-2, 2) * TILE, a.home[1] + random.randint(-1, 1) * TILE
                    if not self.map.blocked(int(gx // TILE), int(gy // TILE)):
                        a.goal = (gx, gy)
            else:
                dx, dy = a.goal[0] - a.x, a.goal[1] - a.y
                dist = math.hypot(dx, dy)
                if dist < 4:
                    a.goal = None
                else:
                    a.x += dx / dist * TILE * 1.2 * dt
                    a.y += dy / dist * TILE * 1.2 * dt
                    a.facing = self._dir_to(0, 0, dx, dy)
                    a.frame += dt * 6

    def _check_pickup(self):
        for a in self.actors:
            if a.kind == "scroll" and (a.x - self.x) ** 2 + (a.y - self.y) ** 2 < PICKUP ** 2 and self._visible(a):
                if self._guarded(a):
                    return
                self.path.clear()
                self.auto = None
                self._run(a.relic, a.objective)
                return

    def _check_portals(self):
        near = (self.portal.x - self.x) ** 2 + (self.portal.y - TILE / 4 - self.y) ** 2 < TILE ** 2
        if near and self._portal_open():
            idx = self.state.order.index(self.level_id)
            if idx + 1 < len(self.state.order):
                self._begin_warp(self.state.order[idx + 1], "spawn")
            else:
                self._begin_warp(None, "ending")
            return
        if near and not self.portal_warned:
            self.portal_warned = True
            self._say(self.mentor, "Cổng chưa mở đâu cháu. Phải dựng xong dòng thời gian đã.")
        elif not near:
            self.portal_warned = False
        if self.back_portal and (self.back_portal.x - self.x) ** 2 + (self.back_portal.y - TILE / 4 - self.y) ** 2 < (TILE * 0.8) ** 2:
            idx = self.state.order.index(self.level_id)
            self._begin_warp(self.state.order[idx - 1], "from_next")

    def _begin_warp(self, level, entry):
        self.path.clear()
        self._land()
        self.explore.carrying = False
        self._save_pos()
        self.warp = {"t": 0.0, "level": level, "entry": entry}
        self.app.audio.play("nhan")

    def _update_warp(self, dt):
        self.warp["t"] += dt
        self.frame += dt * 16
        if self.warp["t"] >= 1.1:
            w = self.warp
            self.warp = None
            self.map.forget()
            if w.get("field"):
                from scenes.field import FieldScene  # nhập muộn: field.py dựa trên module này

                self.app.scenes.replace(FieldScene(self.app, w["field"]))
                return
            if w["entry"] == "ending":  # đoạn kết có cờ, rồi tới lời dặn của Cụ Đồ Sử
                outro = StoryScene(self.app, self.state.sources["outro"])
                self.app.scenes.replace(EndingScene(self.app, then=outro))
                self.state.finished = True
                self.state.save()
                return
            self.app.scenes.replace(WorldScene(self.app, w["level"], w["entry"]))
            self.app.audio.music(MUSIC.get(w["level"], "road"))

    def _update_timers(self, dt):
        if self.banner:
            self.banner["t"] += dt
            if self.banner["t"] > 3.4:
                self.banner = None
        if self.bubble:
            self.bubble["t"] -= dt
            if self.bubble["t"] <= 0:
                self.bubble = None
        if self.stamp_t >= 0:
            self.stamp_t += dt
            if self.stamp_t > 3.0:
                self.stamp_t = -1.0

    def _snap_camera(self):
        self.cam_x = max(0, min(self.world.px_w - W, self.x - W / 2))
        self.cam_y = max(0, min(self.world.px_h - H, self.y - H / 2))

    def _follow_camera(self, dt):
        k = min(1.0, dt * 7)
        gx = max(0, min(self.world.px_w - W, self.x - W / 2))
        gy = max(0, min(self.world.px_h - H, self.y - H / 2))
        self.cam_x += (gx - self.cam_x) * k
        self.cam_y += (gy - self.cam_y) * k

    # ---------- vẽ ----------
    def draw(self, screen):
        cx, cy = int(self.cam_x), int(self.cam_y)
        self.map.draw(screen, cx, cy)
        self._draw_ripples(screen, cx, cy)
        self.fishing.draw_water(screen, cx, cy)
        self._draw_entities(screen, cx, cy)
        self.fishing.draw(screen, cx, cy)
        self._draw_markers(screen, cx, cy)
        self.weather.draw(screen)
        self._draw_bubble(screen, cx, cy)
        self._draw_hud(screen)
        if self.warp:
            k = min(1.0, self.warp["t"] / 1.1)
            ui.veil(screen, (255, 250, 230, int(255 * k * k)))

    def _draw_ripples(self, screen, cx, cy):
        frames = sprites.strip("fx/ripple.png", 4)
        idx = int(self.t * 3)
        for i, (tx, ty) in enumerate(self.world.ripples):
            x, y = tx * TILE - cx, ty * TILE - cy
            if -TILE < x < W and -TILE < y < H:
                screen.blit(frames[(idx + i) % 4], (x, y))

    def _draw_entities(self, screen, cx, cy):
        items = []
        for p in self.world.visible_props(cx, cy, W, H):
            items.append((p.sort, 0, p.img, p.x, p.y))
        n = int(self.t * 7)
        for an in self.world.anims:
            x, y = an.x - cx, an.y - cy
            if -80 < x < W + 80 and -80 < y < H + 80:
                items.append((an.sort, 1, an.frames[int(self.t * an.fps) % len(an.frames)], an.x, an.y))
        for a in self.actors:
            if not self._on_screen(a, cx, cy) or (a.img is None and a.cast is None) or not self._visible(a):
                continue
            items.append(self._actor_item(a, n))
        for c in self.critters:
            x, y = c.x - cx, c.y - cy
            if -80 < x < W + 80 and -80 < y < H + 80:
                img = c.image()
                items.append((c.y, 2, img, c.x - img.get_width() / 2, c.y - img.get_height() + 6))
        items.extend(self.mobs.items(cx, cy))
        items.extend(self.mp.items(cx, cy))
        items.extend(self.fishing.items(cx, cy))
        items.extend(self._player_items())
        items.sort(key=lambda it: (it[0], it[1]))
        for _sort, _k, img, x, y in items:
            screen.blit(img, (x - cx, y - cy))

    @staticmethod
    def _on_screen(a: Actor, cx: int, cy: int) -> bool:
        return -TILE * 2 < a.x - cx < W + TILE * 2 and -TILE < a.y - cy < H + TILE * 3

    def _actor_item(self, a: Actor, n: int):
        if a.cast:
            img = a.cast.walk[a.facing][int(a.frame) % 4]
            return (a.y, 2, img, a.x - TILE / 2, a.y - TILE + 8)
        if a.kind in ("portal", "back"):
            return (a.y, 2, a.img, a.x - TILE * 1.5, a.y - TILE * 3 + 16)
        if a.kind in ("war", "skirmish"):
            img = sprites.strip("fx/flag_red.png", 4)[n % 4]
            return (a.y, 2, img, a.x - TILE / 2, a.y - TILE)
        if a.kind in ("scroll", "gather", "depot"):
            bob = int(4 * math.sin(self.t * 4))
            return (a.y, 2, a.img, a.x - a.img.get_width() / 2, a.y - TILE + bob)
        if a.kind == "honor":
            return (a.y, 2, a.img, a.x - a.img.get_width() / 2, a.y - a.img.get_height() + 10)
        return (a.y, 2, a.img, a.x - TILE / 2, a.y - TILE + 8)

    def _weapon_item(self, person) -> list[tuple]:
        """Vũ khí trên tay người chơi, đặt theo chân của khung nhân vật vừa tính; quay lưng thì vũ khí khuất sau người."""
        held = weapons.held_sprite(self.state.gear.get("vu_khi"), self.facing, 4)
        if held is None or self.warp or self.fishing.active:  # đang cầm cần câu thì cất vũ khí
            return []
        img, dx, dy, behind = held
        bob = 4 if self.moving and int(self.frame) % 2 else 0
        foot_x, foot_y = person[3] + TILE / 2, person[4] + TILE
        return [(person[0], person[1] - 0.5 if behind else person[1] + 0.5, img, foot_x + dx, foot_y + dy + bob)]

    def _player_items(self) -> list[tuple]:
        """Người chơi, cùng con ngựa hoặc chiếc thuyền đang dùng, và vũ khí trên tay."""
        person = self._player_item()
        if self.mode == "boat":
            bob = int(2 * math.sin(self.t * 3))
            img = self.boat_imgs[self.facing]
            w, h = img.get_size()
            cy = self.y - BOAT_LIFT + bob
            standing = (self.y, 4, person[2], self.x - TILE / 2, cy - TILE + BOAT_STAND)
            return [(self.y, 3, img, self.x - w / 2, cy - h / 2), standing]
        if self.mode == "horse":
            frames = self.horse_imgs[self.facing]
            img = frames[int(self.frame) % 2 if self.moving else 0]
            w, h = img.get_size()
            mount = (self.y, 3, img, self.x - w / 2, self.y - h + 8)
            if self.facing == "down":  # ngựa đi về phía người xem: đầu ngựa che trước, người ngồi cao phía sau
                rider = (self.y, 2, person[2], person[3], person[4] - RIDER_LIFT_FRONT)
                return [rider, mount, *self._weapon_item(rider)]
            rider = (self.y, 4, person[2], person[3], person[4] - RIDER_LIFT)
            return [mount, rider, *self._weapon_item(rider)]
        return [person, *self._weapon_item(person)]

    def _player_item(self):
        if self.moving or self.warp:
            img = self.player_cast.walk[self.facing][int(self.frame) % 4]
        else:
            img = self.player_cast.walk[self.facing][0]
        if self.warp:
            order = ("down", "right", "up", "left")
            img = self.player_cast.walk[order[int(self.t * 14) % 4]][0]
        return (self.y, 3, img, self.x - TILE / 2, self.y - TILE + 8)

    def _draw_markers(self, screen, cx, cy):
        # vòng xoáy trong cổng
        frames = sprites.strip("fx/portal.png", 6)
        frame = frames[int(self.t * 10) % 6]
        if self._portal_open():
            screen.blit(frame, frame.get_rect(center=(self.portal.x - cx, self.portal.y - TILE - cy)))
        else:
            fonts.text(screen, "Chưa mở", fonts.font("semi", 13), theme.PAPER, (self.portal.x - cx, self.portal.y - TILE * 3 - 4 - cy), "midbottom", shadow=(20, 14, 12))
        if self.back_portal:
            screen.blit(frame, frame.get_rect(center=(self.back_portal.x - cx, self.back_portal.y - TILE - cy)))
        bob = 3 * math.sin(self.t * 5)
        for a in self.actors:
            if not self._on_screen(a, cx, cy):
                continue
            icon = None
            if a.kind == "keeper" and self._unlocked(a.relic):
                nxt = self._next_obj(a.relic)
                if nxt and nxt["kind"] == "dialogue":
                    icon = "ui/emote_alert.png"
            elif a.kind == "mentor":
                if self.state.timeline_ready(self.level_id) and self.level_id not in self.state.progress.timeline_done:
                    icon = "ui/emote_alert.png"
            elif a.kind == "quiz" and self._is_current(a):
                icon = "ui/emote_question.png"
            elif a.kind == "war" and self._is_current(a):
                icon = "ui/emote_alert.png"
            elif a.kind == "fieldgate":
                icon = "ui/emote_alert.png" if self.state.relic_done(a.data["requires"]) else "ui/emote_lock.png"
                fonts.text(screen, "VÙNG LUYỆN", fonts.font("bold", 14), theme.GOLD_LIGHT, (a.x - cx, a.y - TILE - 26 - cy), "midbottom", shadow=(24, 16, 14))
            elif self._visible(a):
                icon = self.explore.marker(a)
            if a.kind == "arena":
                fonts.text(screen, "VÕ ĐÀI", fonts.font("bold", 16), theme.GOLD_LIGHT, (a.x - cx, a.y - TILE - 10 - cy), "midbottom", shadow=(24, 16, 14))
            elif a.kind == "smith":
                fonts.text(screen, "LÒ RÈN", fonts.font("bold", 16), theme.GOLD_LIGHT, (a.x - cx, a.y - TILE - 10 - cy), "midbottom", shadow=(24, 16, 14))
            elif a.kind == "honor":
                fonts.text(screen, "TOP 20 NGƯỜI CHƠI", fonts.font("bold", 14), theme.GOLD_LIGHT, (a.x - cx, a.y - a.img.get_height() + 4 - cy),
                           "midbottom", shadow=(24, 16, 14))
            elif a.kind == "mentor" and self.state.reports:
                icon = "ui/emote_alert.png"
            if a.kind == "discovery" and a.data.get("water") and a.data["id"] not in self.state.discovered:
                sp = sprites.strip("fx/spirit.png", 5, 2)[int(self.t * 9) % 5]
                screen.blit(sp, sp.get_rect(center=(a.x - cx, a.y - 26 - cy)))
            if a.kind == "scroll" and self._visible(a):
                sp = sprites.strip("fx/spirit.png", 5, 2)[int(self.t * 9) % 5]
                screen.blit(sp, sp.get_rect(center=(a.x - cx, a.y - 26 - cy)))
            if icon:
                img = sprites.icon(icon)
                screen.blit(img, img.get_rect(midbottom=(a.x - cx, a.y - TILE - 2 + bob - cy)))
        near = self.nearest()
        if near and near.label and self._can_use(near):
            label = "Báo cáo" if near.kind == "mentor" and self.state.reports else near.label
            ui.tag(screen, f"E  {label}", (near.x - cx, near.y + 6 - cy), theme.LACQUER, theme.GOLD_LIGHT, 13, "midtop")
        self.mobs.draw_labels(screen, cx, cy)
        self.mp.draw_labels(screen, cx, cy)

    def _can_use(self, a: Actor) -> bool:
        return a.kind in ("keeper", "npc", "mentor", "smith", "fieldgate", "honor") or self.explore.can_use(a) or self._is_current(a)

    def _draw_bubble(self, screen, cx, cy):
        b = self.bubble
        if not b:
            return
        a = b["actor"]
        f = fonts.font("semi", 15)
        lines = fonts.wrap(b["text"], f, 340)
        lh = f.get_linesize()
        w = max(f.size(line)[0] for line in lines) + 24
        h = len(lines) * lh + 16
        rect = pygame.Rect(0, 0, w, h)
        rect.midbottom = (a.x - cx, a.y - TILE - 6 - cy)
        rect.clamp_ip(screen.get_rect().inflate(-12, -12))
        ui.paper_panel(screen, rect, shadow=False)
        y = rect.y + 8
        for line in lines:
            fonts.text(screen, line, f, theme.INK, (rect.x + 12, y))
            y += lh

    def _draw_hud(self, screen):
        msg, target = self._current()
        ui.lacquer_panel(screen, HUD_TRACKER, 236)
        x = HUD_TRACKER.x + 16
        w = HUD_TRACKER.w - 32
        fonts.text(screen, self.level["title"], fonts.font("serif", 18), theme.GOLD_LIGHT, (x, HUD_TRACKER.y + 10))
        fonts.text(screen, f"{self.level['period_label']}  ·  {self.state.total_points} điểm", fonts.font("ui", 13), theme.PAPER_3, (x, HUD_TRACKER.y + 34))
        ui.progress_bar(screen, (x, HUD_TRACKER.y + 54, w, 7), self._progress_ratio())
        fonts.paragraph(screen, msg, fonts.font("semi", 14), theme.PAPER, x, HUD_TRACKER.y + 66, w, gap=0)
        side = self.mobs.tracker() or self.explore.tracker()
        if side:
            ui.tag(screen, side, (HUD_TRACKER.x + 4, HUD_TRACKER.bottom + 6), theme.JADE, theme.WHITE, 14)
        if self.state.is_admin:
            state = "bật" if self.noclip else "tắt"
            label = f"Quản trị   V: xuyên tường ({state})   Bấm bản đồ nhỏ: dịch chuyển   J: tới mọi di tích"
            ui.tag(screen, label, (HUD_TRACKER.x + 4, HUD_TRACKER.bottom + (36 if side else 6)), theme.LACQUER_RED, theme.GOLD_LIGHT, 13)
        self._draw_minimap(screen)
        self._draw_rpg(screen)
        online = self.mp.hud_tag()
        if online:
            ui.tag(screen, online, (W - 16, self._minimap_rect().y - 16), theme.LACQUER_2, theme.GOLD_LIGHT, 13, "bottomright")
        hint = (HINT_X, H - 22)
        if self.mode == "boat":
            ui.tag(screen, "Đang chèo thuyền: WASD để chèo, tới sát bờ bấm E để lên", hint, theme.LACQUER, theme.PAPER, 14, "midbottom")
        elif self.mode == "horse":
            key = "R" if self.horse_actor is not None else "H"
            ui.tag(screen, f"Đang cưỡi ngựa: bấm {key} để xuống", hint, theme.LACQUER, theme.PAPER, 14, "midbottom")
        elif self.fishing.active:
            ui.tag(screen, "Đang câu cá: phao chìm, hiện dấu chấm than thì bấm C kéo lên · đi chỗ khác là thu cần", hint, theme.LACQUER,
                   theme.PAPER, 14, "midbottom")
        elif self.t < HELP_TIME and not self.state.stamps:
            ui.tag(screen, "WASD đi · E nói chuyện · F đánh quái · C câu cá · H chiến mã · L chat · nút ba gạch: các bảng khác", hint,
                   theme.LACQUER, theme.PAPER, 13, "midbottom")
        if target:
            self._draw_arrow(screen, target)
        if self.banner:
            self._draw_banner(screen)
        if self.stamp_t >= 0:
            k = min(1.0, self.stamp_t / 0.25)
            size = int(300 - 110 * k)
            img = pygame.transform.smoothscale(self.stamp_img, (size, size))
            screen.blit(img, img.get_rect(center=(W // 2, H // 2 - 60)))
        self.mp.draw_chat(screen, HUD_RPG.y)
        self.mp.draw_invites(screen)
        self._draw_menu(screen)

    def _progress_ratio(self) -> float:
        return self.state.level_ratio(self.level_id)

    def _draw_rpg(self, screen):
        """Khung cấp độ: cấp, cảnh giới, kinh nghiệm, sức mạnh, tiềm năng, tiền, tinh hoa, thuốc."""
        st = self.state
        r = HUD_RPG
        ui.lacquer_panel(screen, r, 236)
        x = r.x + 14
        fonts.text(screen, f"Cấp {st.level} · {st.realm_name()}", fonts.font("serif", 18), theme.GOLD_LIGHT, (x, r.y + 8))
        fonts.text(screen, f"Sức mạnh {st.power_rating()}", fonts.font("bold", 14), theme.RED_BRIGHT, (r.right - 14, r.y + 12), "topright")
        need = rpg.exp_need(st.level)
        capped = st.level >= st.level_cap()
        ui.progress_bar(screen, (x, r.y + 36, r.w - 28, 9), 1.0 if capped else st.exp / need, theme.JADE_LIGHT)
        label = "Đã tới giới hạn cảnh giới: cần đột phá (K)" if capped else f"Kinh nghiệm {st.exp}/{need}"
        fonts.text(screen, label, fonts.font("ui", 12), theme.PAPER_3, (x, r.y + 48))
        f = fonts.font("semi", 13)
        line = f"Tiềm năng {st.tiem_nang}   ·   {st.quan} quan   ·   Tinh hoa {st.essence()}   ·   Thuốc {st.potions}"
        fonts.text(screen, line, f, theme.PAPER, (x, r.y + 66))

    def _draw_skill_badge(self, screen):
        left = self.state.skill_points_left()
        if left > 0:
            r = self.skill_btn.rect if self.menu_open else self.menu_btn.rect  # menu đóng thì báo trên nút ba gạch
            pygame.draw.circle(screen, theme.RED_BRIGHT, (r.right - 4, r.y + 4), 11)
            pygame.draw.circle(screen, theme.WHITE, (r.right - 4, r.y + 4), 11, 2)
            fonts.text(screen, str(left), fonts.font("bold", 12), theme.WHITE, (r.right - 4, r.y + 4), "center")

    def _draw_minimap(self, screen):
        mm = self.world.build_minimap()
        rect = self._minimap_rect()
        ui.lacquer_panel(screen, rect.inflate(16, 16), 240)
        screen.blit(mm, rect)
        for relic in self.relics:
            zone = self.world.zones[relic["id"]]
            col = theme.JADE_LIGHT if self.state.relic_done(relic["id"]) else theme.RED_BRIGHT if self._unlocked(relic) else (150, 150, 140)
            pygame.draw.rect(screen, col, (rect.x + zone.cx * 2 - 2, rect.y + zone.cy * 2 - 2, 5, 5))
        px, py = self.world.portal
        pygame.draw.rect(screen, theme.BLUE if self._portal_open() else (90, 90, 100), (rect.x + px * 2 - 2, rect.y + py * 2 - 2, 5, 5))
        for ax, ay, col in self.explore.points():
            pygame.draw.rect(screen, col, (rect.x + ax / TILE * 2 - 1, rect.y + ay / TILE * 2 - 1, 3, 3))
        for a in self.actors:
            if a.kind == "fieldgate":
                pygame.draw.rect(screen, theme.GOLD, (rect.x + a.x / TILE * 2 - 2, rect.y + a.y / TILE * 2 - 2, 5, 5))
        if int(self.t * 3) % 2 == 0:
            pygame.draw.rect(screen, theme.WHITE, (rect.x + self.x / TILE * 2 - 2, rect.y + self.y / TILE * 2 - 2, 4, 4))
        else:
            pygame.draw.rect(screen, (20, 20, 20), (rect.x + self.x / TILE * 2 - 2, rect.y + self.y / TILE * 2 - 2, 4, 4))

    def _draw_arrow(self, screen, target):
        """Mũi tên ở mép màn hình chỉ tới việc cần làm khi nó ở ngoài khung nhìn."""
        sx, sy = target[0] - self.cam_x, target[1] - self.cam_y
        if 60 < sx < W - 60 and 130 < sy < H - 60:
            return
        cx, cy = W / 2, H / 2
        ang = math.atan2(sy - cy, sx - cx)
        r = min((W / 2 - 70) / max(abs(math.cos(ang)), 0.01), (H / 2 - 90) / max(abs(math.sin(ang)), 0.01))
        ax, ay = cx + math.cos(ang) * r, cy + math.sin(ang) * r
        bob = 6 * ui.pulse(self.t, 5)
        ax += math.cos(ang) * bob
        ay += math.sin(ang) * bob
        pts = [(ax + math.cos(ang) * 26, ay + math.sin(ang) * 26), (ax + math.cos(ang + 2.5) * 22, ay + math.sin(ang + 2.5) * 22), (ax + math.cos(ang - 2.5) * 22, ay + math.sin(ang - 2.5) * 22)]
        pygame.draw.polygon(screen, (24, 16, 14), [(x, y + 4) for x, y in pts])
        pygame.draw.polygon(screen, theme.RED_BRIGHT, pts)
        pygame.draw.polygon(screen, theme.WHITE, pts, 3)

    def _draw_banner(self, screen):
        b = self.banner
        t = b["t"]
        alpha = min(1.0, t / 0.4, (3.4 - t) / 0.5)
        if alpha <= 0.02:
            return
        lop = b.get("img")
        if lop is None:
            title = fonts.render(b["title"], fonts.font("serif", 30), theme.GOLD_LIGHT)
            sub = fonts.render(b["sub"], fonts.font("italic", 16), theme.PAPER)
            w = max(title.get_width(), sub.get_width()) + 70
            lop = pygame.Surface((w, 84), pygame.SRCALPHA)
            ui.lacquer_panel(lop, lop.get_rect(), 236)
            lop.blit(title, title.get_rect(midtop=(w // 2, 8)))
            lop.blit(sub, sub.get_rect(midtop=(w // 2, 50)))
            b["img"] = lop
        lop.set_alpha(int(255 * alpha))
        screen.blit(lop, (W // 2 - lop.get_width() // 2, 130))


PAUSE_CARD = pygame.Rect(W // 2 - 440, 96, 880, 540)
PAUSE_ICONS = {"Tiếp tục chơi": "ui/sword.png", "Xem hướng dẫn": "ui/emote_question.png", "Cài đặt": "ui/gem.png",
               "Về màn hình chính": "ui/book.png"}
PAUSE_KEYS = (
    ("WASD", "đi lại"), ("E", "nói chuyện, nhặt đồ"), ("F", "đánh quái"), ("H", "gọi chiến mã"), ("R", "cưỡi ngựa có sẵn"),
    ("B", "túi đồ"), ("G", "sổ bóng giặc"), ("P", "bạn chơi"), ("K", "tu luyện"), ("T", "tư liệu"), ("J", "lộ trình"),
    ("M", "bản đồ"), ("N", "sổ tay"), ("Esc", "tạm dừng"),
)


class PauseScene(Scene):
    """Tạm dừng: phím Esc hoặc nút Menu. Bên trái là các lựa chọn, bên phải là bảng phím."""

    opaque = False

    def __init__(self, app):
        super().__init__(app)
        self.group = ui.ButtonGroup()
        self.slide: dict[int, float] = {}
        self.t = 0.0
        x, y = PAUSE_CARD.x + 32, PAUSE_CARD.y + 120
        for label, fn, style in (
            ("Tiếp tục chơi", lambda: self.app.scenes.pop(), "gold"),
            ("Xem hướng dẫn", lambda: self.app.scenes.push(TrailerScene(self.app)), "primary"),
            ("Cài đặt", lambda: self.app.scenes.push(ProfileScene(self.app, 3)), "primary"),
            ("Về màn hình chính", self._quit, "ghost"),
        ):
            h = 70 if style == "gold" else 58
            self.group.add(ui.Button((x, y, 360, h), label, fn, style, True, 16))
            y += h + 12

    def _quit(self):
        self.state.save()
        self.app.go_title()

    def backdrop(self, screen):
        ui.veil(screen, (10, 6, 4, 170))

    def handle(self, event):
        self.group.handle(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.pop()

    def update(self, dt):
        self.t += dt
        ui.ease_slide(self.group.buttons, self.slide, dt)

    def draw(self, screen):
        st = self.state
        ui.lacquer_panel(screen, PAUSE_CARD, 240)
        fonts.text(screen, "TẠM DỪNG", fonts.font("serif", 36), theme.GOLD_LIGHT, (PAUSE_CARD.x + 32, PAUSE_CARD.y + 26))
        where = st.levels[st.current_level]["level"]["title"] if st.current_level in st.levels else ""
        fonts.text(screen, f"{where} · cấp {st.level} · {st.realm_name()} · {len(st.stamps)} di tích đã đóng dấu", fonts.font("ui", 15),
                   theme.PAPER_3, (PAUSE_CARD.x + 34, PAUSE_CARD.y + 76))
        ui.fancy_menu(screen, self.group.buttons, self.slide, PAUSE_ICONS)
        keys = pygame.Rect(PAUSE_CARD.x + 430, PAUSE_CARD.y + 120, 418, 390)
        ui.alpha_rect(screen, keys, (0, 0, 0, 70), 10)
        fonts.text(screen, "Phím tắt", fonts.font("bold", 17), theme.GOLD_LIGHT, (keys.x + 18, keys.y + 14))
        f_key, f_txt = fonts.font("bold", 14), fonts.font("ui", 14)
        for i, (key, what) in enumerate(PAUSE_KEYS):
            col, row = i % 2, i // 2
            x, y = keys.x + 18 + col * 200, keys.y + 52 + row * 46
            kw = max(34, f_key.size(key)[0] + 16)
            pygame.draw.rect(screen, theme.PAPER_2, (x, y, kw, 30), border_radius=6)
            pygame.draw.rect(screen, theme.GOLD_DARK, (x, y, kw, 30), 2, border_radius=6)
            fonts.text(screen, key, f_key, theme.INK, (x + kw / 2, y + 15), "center")
            fonts.text(screen, what, f_txt, theme.PAPER, (x + kw + 10, y + 15), "midleft")
