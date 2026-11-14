"""Vùng luyện: map phụ gắn với một sự kiện có thật, đầy bóng giặc đúng thời để luyện tay.

Mỗi vùng có người kể chuyện (nhân vật hư cấu) kể lại sự kiện kèm trích dẫn nguồn và hỏi một câu; vài toán quái theo trại;
kẻ mạnh nhất vùng đánh xong một lúc lại xuất hiện. Cổng ở mép map đưa về map chính, đứng đúng chỗ vừa rời đi.
Dùng lại toàn bộ cách đi lại, đánh quái, cưỡi chiến mã, thách đấu của WorldScene; chỉ thay phần gắn với di tích.
"""

from __future__ import annotations

import random

from core import outfit, rpg, sprites, theme
from core.scene import Scene
from core.sprites import TILE
from core.worldgen import CATALOG, build_world

from scenes.actors import Actor
from scenes.archive import ArchiveScene
from scenes.atlas import AtlasScene
from scenes.question import QuestionScene
from scenes.review import ReviewScene
from scenes.roadmap import RoadmapScene
from scenes.story import StoryScene
from scenes.world import WorldScene

_fields: dict[str, object] = {}


def get_field(state, field_id: str):
    if field_id not in _fields:
        spec = dict(state.fields[field_id], extra={"links": [], "open": [], "buildings": [], "burned": []})
        zones = [{"id": z} for z in spec["zones"]]
        _fields[field_id] = build_world(field_id, spec, zones)
        _fields[field_id].map.warm()
    return _fields[field_id]


class FieldExplore:
    """Vùng luyện không có điểm khám phá, vụ điều tra: thay Explore bằng bản rỗng có cùng các hàm."""

    def __init__(self, ws):
        self.ws = ws
        self.app = ws.app
        self.next = None
        self.carrying = False

    def _push(self, scene, then):
        self.next = then
        self.app.scenes.push(scene)

    def spawn(self):
        pass

    def visible(self, _a) -> bool:
        return True

    def can_use(self, a) -> bool:
        return a.kind == "elder"

    def interact(self, _a) -> bool:
        return False

    def update(self, _dt):
        pass

    def tracker(self):
        n = self.ws.log().get("elite", 0)
        extra = f" · đã hạ kẻ mạnh nhất vùng {n} lần" if n else ""
        return f"Vùng luyện: quái hồi sinh, đánh bao nhiêu cũng được{extra}"

    def points(self):
        return []

    def speed_mult(self) -> float:
        return 1.0

    def marker(self, a):
        if a.kind == "elder" and not self.ws.log().get("talk"):
            return "ui/emote_alert.png"
        return None


class FieldScene(WorldScene):
    def __init__(self, app, field_id: str):
        Scene.__init__(self, app)
        st = self.state
        self.field = st.fields[field_id]
        self.field_id = self.level_id = field_id
        self.parent = self.field["parent"]
        self.level = {"title": self.field["title"], "period_label": self.field["sub"]}
        self.bundle = None
        self.engine = None
        self.relics: list[dict] = []
        self._quest_steps: dict = {}
        self.places: dict = {}
        self.world = get_field(st, field_id)
        self.map = self.world.map
        self._init_runtime("spawn")

    # ----- phần riêng của vùng luyện -----
    def log(self) -> dict:
        return self.state.field_log.setdefault(self.field_id, {})

    def _make_explore(self):
        return FieldExplore(self)

    def _life(self) -> list:
        return self.field.get("life", [])

    def _spawn_actors(self):
        world, f = self.world, self.field
        elder = f["elder"]
        self.mentor = Actor("elder", world.mentor, elder["name"], "Nghe kể chuyện", sprites.cast(elder["char"]))
        self.actors.append(self.mentor)
        arch = sprites.region(*CATALOG["arch"][:3], 3, 3)
        self.portal = Actor("portal", world.portal, "Đường về", "", img=arch)
        self.actors.append(self.portal)
        self.back_portal = None
        for npc in f.get("npcs", []):
            self.actors.append(Actor("npc", npc["at"], "Người lính", "Bắt chuyện", sprites.cast(npc["char"]), lines=npc["lines"]))

    def _place_player(self, entry: str):
        sx, sy = self.world.spawn
        self.x, self.y = sx * TILE + TILE / 2, sy * TILE + TILE - 8

    def on_enter(self):
        self.app.audio.music(self.field.get("music", "road"))
        self._apply_weather(True)

    def _apply_weather(self, force=False):
        if force or self._weather_zone != self.field_id:
            self._weather_zone = self.field_id
            self.weather.set(self.field.get("weather"))
            self.app.audio.ambient(self.field.get("sound"))

    def _check_zone(self):
        self._apply_weather()

    def _show_level_title(self):
        self.banner = {"title": self.field["title"], "sub": self.field["sub"], "t": 0.0}

    def _elite(self):
        return next((m for m in self.mobs.mobs if m.kind == "elite"), None)

    def _current(self):
        if not self.log().get("talk"):
            return f"Nghe {self.field['elder']['name']} kể chuyện {self.field['name']}", (self.mentor.x, self.mentor.y)
        elite = self._elite()
        if elite and elite.alive:
            return f"Hạ {elite.data['name']} (kẻ mạnh nhất vùng)", (elite.x, elite.y)
        return "Luyện tay với bóng giặc, xong thì về cổng ở mép tây", (self.portal.x, self.portal.y)

    def _progress_ratio(self) -> float:
        log = self.log()
        return 0.5 * bool(log.get("talk")) + 0.5 * bool(log.get("elite"))

    def _portal_open(self) -> bool:
        return True

    def _check_portals(self):
        if (self.portal.x - self.x) ** 2 + (self.portal.y - TILE / 4 - self.y) ** 2 < TILE ** 2:
            self._begin_warp(self.parent, "saved")

    def _can_use(self, a: Actor) -> bool:
        return a.kind in ("elder", "npc")

    def interact(self, a: Actor):
        self.path.clear()
        self.auto = None
        if a.cast:
            a.facing = self._dir_to(a.x, a.y, self.x, self.y)
            self.facing = self._dir_to(self.x, self.y, a.x, a.y)
        self.app.audio.play("click")
        if a.kind == "elder":
            self._talk_elder(a)
        elif a.kind == "npc":
            self._say(a, random.choice(a.lines))

    def _talk_elder(self, a: Actor):
        """Người kể chuyện: kể lại sự kiện kèm nguồn, rồi hỏi một câu; trả lời đúng lần đầu có thưởng."""
        elder = self.field["elder"]
        nodes = [{"speaker": elder["name"], "portrait": elder["portrait"], "fiction": True, **ln} for ln in elder["lines"]]
        story = StoryScene(self.app, {"id": "extra", "bg": "lang_co", "nodes": nodes})
        self.explore._push(story, lambda _r: self._ask(a))

    def _ask(self, a: Actor):
        self.explore._push(QuestionScene(self.app, self.field["elder"]["question"]), lambda r: self._asked(a, r))

    def _asked(self, a: Actor, result):
        st, log = self.state, self.log()
        first = not log.get("talk")
        log["talk"] = True
        qid = self.field["elder"]["question"]["id"]
        if first and result and qid in st.solved:
            exp, tiem, quan = rpg.FIELD_TALK_REWARD
            st.gain(exp, tiem, quan)
            self.app.toast(f"Hiểu thêm một trang sử: +{exp} kinh nghiệm, +{tiem} tiềm năng, +{quan} quan", theme.GOLD_LIGHT, 4.0)
        st.save()
        self._say(a, "Giờ thì đi luyện tay đi cháu. Nhớ chuyện thật là chuyện ta vừa kể.", 4.0)

    def on_resume(self, result=None):
        self.player_cast = outfit.hero_cast(self.state.gear)
        self.app.audio.music(self.field.get("music", "road"))
        self._apply_weather(True)
        self._after_explore(result)
        if isinstance(result, dict) and result.get("travel"):  # chọn di tích trên bản đồ: về map chính rồi đi tới đó
            self._land()
            self._save_pos()
            self.map.forget()
            nxt = WorldScene(self.app, result.get("level", self.parent), "spawn")
            self.app.scenes.replace(nxt)
            nxt._travel(result["travel"])
            return
        self._report_points()
        self._save_pos()

    # ----- các nút dùng chặng của map chính -----
    def _atlas(self):
        self.app.scenes.push(AtlasScene(self.app, self.parent))

    def _review(self):
        self.app.scenes.push(ReviewScene(self.app, self.parent))

    def _roadmap(self):
        self.app.scenes.push(RoadmapScene(self.app, self.parent, self._current()[0]))

    def _archive(self):
        self.app.scenes.push(ArchiveScene(self.app, self.parent))
