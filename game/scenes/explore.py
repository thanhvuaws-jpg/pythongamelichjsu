"""Phần khám phá thêm trên map: điểm phát hiện, vụ điều tra, nhiệm vụ phụ, giao tranh, võ đài, ngựa, thuyền.

Tách khỏi world.py để phần nhiệm vụ chính đọc cho gọn. Các việc nối tiếp nhau (nghe chuyện, trả lời, nhận thưởng) được
xâu lại bằng `self.next`: khi scene vừa mở đóng lại thì WorldScene gọi hàm này.
"""

from __future__ import annotations

from core import fleet, sprites, theme
from core.worldgen import CATALOG, door_of

from scenes.actors import Actor
from scenes.archive import ArchiveScene
from scenes.arena import ArenaScene
from scenes.case import CaseScene
from scenes.fight import FightScene
from scenes.question import QuestionScene
from scenes.story import StoryScene

PICKUP_RANGE = 72
CARRY_SLOW = 0.7
KINDS = {"discovery", "case", "giver", "gather", "depot", "skirmish", "arena", "horse", "pier", "piece", "archive"}
MARK_FIND, MARK_CASE, MARK_SIDE = (240, 214, 90), (120, 196, 240), (150, 230, 150)
MARK_DOC = (250, 236, 200)


def world_extras(state, level_id: str) -> dict:
    """Những chỗ trên map cần chừa ra và nối đường cho phần khám phá."""
    ex = state.extras
    out = {"links": [], "open": [], "buildings": [], "burned": []}
    for d in ex["discoveries"]:
        if d["level"] != level_id or d.get("water"):
            continue
        out["links"].append(d["at"])
        if d.get("building"):
            out["buildings"].append((d["building"]["name"], *d["building"]["at"]))
        if d.get("burned"):
            out["burned"].append(d["at"])
    for c in ex["cases"]:
        if c["level"] == level_id:
            out["buildings"].append((c["building"]["name"], *c["building"]["at"]))
            out["links"].append(door_of(c["building"]))
    for s in ex["sides"]:
        if s["level"] == level_id:
            out["links"].append(s["giver"]["at"])
            out["links" if s.get("carry") else "open"].extend(s["spots"])
    for k in ex["skirmishes"]:
        if k["level"] == level_id:
            out["links"].append(k["at"])
    for d in ex.get("documents", []):
        if d["level"] == level_id:
            out["open"].extend(d["pieces"])
    annex = state.worlds[level_id].get("annex")
    if annex:
        out["links"].append(annex["keeper"])
    return out


class Explore:
    def __init__(self, ws):
        self.ws = ws
        self.app = ws.app
        self.state = ws.state
        self.next = None
        self.carrying = False

    # ----- dựng -----
    def spawn(self):
        ws, st = self.ws, self.state
        lid = ws.level_id
        spec = st.worlds[lid]
        add = ws.actors.append
        for d in st.extras["discoveries"]:
            if d["level"] == lid:
                cast = sprites.cast(d["char"]) if d.get("char") else None
                img = sprites.region(*CATALOG[d["prop"]][:3]) if d.get("prop") else None
                add(Actor("discovery", d["at"], d["name"], d["label"], cast, img, data=d))
        for c in st.extras["cases"]:
            if c["level"] == lid:
                add(Actor("case", door_of(c["building"]), c["name"], f"Vào: {c['name']}", data=c))
        for s in st.extras["sides"]:
            if s["level"] != lid:
                continue
            add(Actor("giver", s["giver"]["at"], s["giver"]["name"], "Nói chuyện", sprites.cast(s["giver"]["char"]), data=s))
            icon = sprites.icon(s["item"]["icon"])
            for i, spot in enumerate(s["spots"]):
                kind = "depot" if s.get("carry") else "gather"
                add(Actor(kind, spot, s["item"]["name"], f"Lấy {s['item']['name'].lower()}", img=icon, data=(s, i)))
        for k in st.extras["skirmishes"]:
            if k["level"] == lid:
                add(Actor("skirmish", k["at"], k["title"], "Giao chiến", img=sprites.strip("fx/flag_red.png", 4)[0], data=k))
        if spec.get("arena"):
            ax, ay = spec["arena"]
            add(Actor("arena", (ax, ay - 2), "Võ sư", "Vào võ đài", sprites.cast("FighterWhite")))
        if spec.get("horse"):
            add(Actor("horse", spec["horse"], "Con ngựa", "Cưỡi ngựa (R)", img=sprites.strip("animal/horse.png", 2)[0]))
        for tile in spec.get("piers", ()):
            add(Actor("pier", tile, "Bến thuyền", "Chèo thuyền", img=fleet.boat_sprite(84)))
        scroll = sprites.icon("ui/scroll.png")
        for d in st.documents(lid):
            for i, tile in enumerate(d["pieces"]):
                add(Actor("piece", tile, "Mảnh tư liệu", "Nhặt mảnh tư liệu", img=scroll, data=(d, i)))
        annex = spec.get("annex")
        if annex:
            add(Actor("archive", annex["keeper"], annex["keeper_name"], "Kho tư liệu", sprites.cast(annex["keeper_char"]), data=annex))

    # ----- tiến trình -----
    def active_side(self, s: dict) -> dict | None:
        return self.state.side_state.get(s["id"]) if s["id"] not in self.state.side_done else None

    def visible(self, a: Actor) -> bool:
        st = self.state
        if a.kind in ("gather", "depot"):
            s, i = a.data
            active = self.active_side(s)
            if active is None:
                return False
            return not self.carrying if a.kind == "depot" else i not in active["got"]
        if a.kind == "skirmish":
            return a.data["id"] not in st.skirmish_done and st.relic_done(a.data["requires"])
        if a.kind == "piece":
            d, i = a.data
            return i not in st.doc_got(d)
        if a.kind == "horse":
            return self.ws.mode != "horse"
        if a.kind == "pier":
            return self.ws.mode != "boat"
        return True

    def can_use(self, a: Actor) -> bool:
        return a.kind in KINDS

    def _push(self, scene, then):
        self.next = then
        self.app.scenes.push(scene)

    def interact(self, a: Actor) -> bool:
        kind = a.kind
        if kind not in KINDS:
            return False
        if kind == "discovery":
            self._discover(a)
        elif kind == "case":
            self._enter_case(a)
        elif kind == "giver":
            self._talk_giver(a)
        elif kind == "depot":
            self._take_load(a)
        elif kind == "gather":
            self._gather(a)
        elif kind == "skirmish":
            self._skirmish(a)
        elif kind == "arena":
            self.app.scenes.push(ArenaScene(self.app))
        elif kind == "horse":
            self.ws.mount(a)
        elif kind == "pier":
            self.ws.board(a)
        elif kind == "piece":
            self._pick(a)
        elif kind == "archive":
            self.app.scenes.push(ArchiveScene(self.app, self.ws.level_id))
        return True

    def _story(self, nodes, bg="lang_co", legend=False) -> StoryScene:
        return StoryScene(self.app, {"id": "extra", "bg": bg, "nodes": nodes, "legend": legend})

    # ----- điểm phát hiện -----
    def _discover(self, a):
        item = a.data
        if item["id"] in self.state.discovered:
            self.ws._say(a, item["done"])
            return
        self._push(self._story(item["lines"], item.get("bg", "lang_co"), item.get("legend", False)), lambda _r: self._ask_discovery(a))

    def _ask_discovery(self, a):
        self._push(QuestionScene(self.app, a.data["question"]), lambda _r: self._found(a))

    def _found(self, a):
        st = self.state
        st.discovered.add(a.data["id"])
        st.save()
        self.app.toast(f"Khám phá mới: {a.data['name']}", theme.GOLD_LIGHT, 3.5)
        self.ws._say(a, a.data["done"])

    # ----- vụ điều tra -----
    def _enter_case(self, a):
        st = self.state
        case = a.data
        need = case["requires"]
        if not st.relic_done(need):
            self.ws._say(a, f"Cửa còn đóng. Hãy xong di tích “{st.index['relics'][need]['title']}” rồi quay lại.")
            return
        self.app.scenes.push(CaseScene(self.app, case))

    # ----- nhiệm vụ phụ -----
    def _talk_giver(self, a):
        s, st = a.data, self.state
        sid = s["id"]
        if sid in st.side_done:
            self.ws._say(a, s["done"])
            return
        active = st.side_state.get(sid)
        if active is None:
            nodes = [{"speaker": a.name, "portrait": s["portrait"], "fiction": True, **n} for n in s["intro"]]
            self._push(self._story(nodes), lambda _r: self._start_side(s))
            return
        if s.get("carry") and self.carrying:
            self.carrying = False
            active["delivered"] = active.get("delivered", 0) + 1
            self.app.audio.play("dung")
            st.save()
        done = active.get("delivered", 0) if s.get("carry") else len(active["got"])
        if done >= s["count"]:
            self._push(QuestionScene(self.app, s["question"]), lambda _r: self._finish_side(a))
        else:
            self.ws._say(a, f"{s['waiting']} ({done}/{s['count']})")

    def _start_side(self, s):
        self.state.side_state[s["id"]] = {"got": [], "delivered": 0}
        self.state.save()
        self.app.toast(f"Nhiệm vụ phụ mới: {s['title']}", theme.JADE_LIGHT, 3.5)

    def _finish_side(self, a):
        s, st = a.data, self.state
        st.side_done.add(s["id"])
        st.save()
        self.app.toast(f"Xong nhiệm vụ phụ: {s['title']}", theme.GOLD_LIGHT, 3.5)
        self.ws._say(a, s["done"])

    def _gather(self, a):
        s, i = a.data
        active = self.active_side(s)
        if active is None or i in active["got"]:
            return
        active["got"].append(i)
        self.app.audio.play("nhan")
        self.state.save()
        self.app.toast(f"{s['item']['name']}: {len(active['got'])}/{s['count']}", theme.JADE_LIGHT, 2.0)

    def _take_load(self, a):
        s, _i = a.data
        if self.active_side(s) is not None and not self.carrying:
            self.carrying = True
            self.app.audio.play("nhan")
            self.ws._say(a, f"Đã gùi {s['item']['name'].lower()}. Mang lên cho {s['giver']['name'].lower()} nhé.", 3.0)

    # ----- tư liệu -----
    def _pick(self, a):
        d, i = a.data
        st = self.state
        if not st.take_piece(d, i):
            return
        self.app.audio.play("nhan")
        n, got = len(d["pieces"]), len(st.doc_got(d))
        line = d["question"]["items"][i]["text"]
        self.app.toast(f"Mảnh tư liệu {got}/{n}: “{line}”", theme.PAPER, 4.0)
        if got >= n:
            annex = st.worlds[d["level"]].get("annex", {})
            self.app.toast(f"Đủ mảnh “{d['title']}”. Mang tới {annex.get('name', 'Kho tư liệu')} (hoặc bấm T) để ghép lại.", theme.GOLD_LIGHT, 5.0)

    # ----- giao tranh -----
    def _skirmish(self, a):
        item = a.data
        self._push(self._story(item["lines"], item["scene"]), lambda _r: self._fight(a))

    def _fight(self, a):
        item = a.data
        self.app.audio.music("fight")
        self._push(FightScene(self.app, item["foes"], item["title"], item["scene"]), lambda r: self._fought(a, r))

    def _fought(self, a, result):
        item, st = a.data, self.state
        if isinstance(result, dict) and result.get("win"):
            st.skirmish_done.add(item["id"])
            st.save()
            self.app.toast(item["win"], theme.GOLD_LIGHT, 4.0)
        else:
            self.ws._say(a, "Giặc còn đó. Tăng thêm chỉ số rồi quay lại nhé.")

    # ----- trên map -----
    def speed_mult(self) -> float:
        return CARRY_SLOW if self.carrying else 1.0

    def update(self, _dt):
        ws = self.ws
        for a in ws.actors:
            if a.kind == "gather" and self.visible(a) and (a.x - ws.x) ** 2 + (a.y - ws.y) ** 2 < PICKUP_RANGE ** 2:
                self._gather(a)
            elif a.kind == "piece" and self.visible(a) and (a.x - ws.x) ** 2 + (a.y - ws.y) ** 2 < PICKUP_RANGE ** 2:
                self._pick(a)

    def tracker(self) -> str | None:
        """Dòng nhỏ dưới khung nhiệm vụ cho biết tiến độ nhiệm vụ phụ đang làm."""
        for s in self.state.extras["sides"]:
            if s["level"] != self.ws.level_id:
                continue
            active = self.active_side(s)
            if active is None:
                continue
            done = active.get("delivered", 0) if s.get("carry") else len(active["got"])
            load = ", đang gùi" if self.carrying else ""
            return f"{s['title']}: {done}/{s['count']}{load}"
        st = self.state
        for d in st.documents(self.ws.level_id):
            got = len(st.doc_got(d))
            if d["id"] not in st.doc_done and 0 < got:
                return f"Tư liệu {d['title']}: {got}/{len(d['pieces'])} mảnh" if got < len(d["pieces"]) else f"Tư liệu {d['title']}: đủ mảnh, bấm T để ghép"
        return None

    def points(self) -> list[tuple[float, float, tuple]]:
        """Chấm nhỏ trên bản đồ thu nhỏ cho những nơi chưa khám phá."""
        out = []
        st = self.state
        for a in self.ws.actors:
            if a.kind == "discovery" and a.data["id"] not in st.discovered:
                out.append((a.x, a.y, MARK_FIND))
            elif a.kind == "case" and a.data["id"] not in st.case_done and st.relic_done(a.data["requires"]):
                out.append((a.x, a.y, MARK_CASE))
            elif a.kind == "giver" and a.data["id"] not in st.side_done:
                out.append((a.x, a.y, MARK_SIDE))
            elif a.kind == "archive":
                out.append((a.x, a.y, MARK_DOC))
        return out

    def marker(self, a: Actor) -> str | None:
        st = self.state
        if a.kind == "discovery" and a.data["id"] not in st.discovered:
            return "ui/emote_question.png"
        if a.kind == "case" and a.data["id"] not in st.case_done:
            return "ui/emote_alert.png" if st.relic_done(a.data["requires"]) else "ui/emote_lock.png"
        if a.kind == "giver" and a.data["id"] not in st.side_done:
            return "ui/emote_alert.png" if a.data["id"] not in st.side_state else "ui/emote_talk.png"
        if a.kind == "skirmish":
            return "ui/emote_alert.png"
        if a.kind == "archive":
            return "ui/emote_alert.png" if any(st.doc_ready(d) for d in st.documents()) else "ui/emote_talk.png"
        return None

