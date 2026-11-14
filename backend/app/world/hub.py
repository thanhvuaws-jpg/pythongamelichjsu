"""Bộ điều phối thế giới chung: ai ở map nào, đứng đâu, mặc gì; mời tổ đội, đồng minh, thách đấu.

Vị trí chỉ giữ trong bộ nhớ của tiến trình máy chủ. Đồng minh, tổ đội, kết quả thách đấu đi qua
`store` để lưu vào cơ sở dữ liệu (bản thật dùng PostgreSQL, kiểm thử dùng bản trong bộ nhớ). Lời nói
nhanh là các câu có sẵn gửi theo số thứ tự; chat gõ tự do có hai kênh (map, thế giới), mọi tin đều
được làm sạch, che từ tục và giới hạn tốc độ ở `app.world.chat`.

Người chơi máy do máy chủ tự cho chạy (`app.world.bots`): có mặt trong danh sách người cùng map như
mọi người chơi khác. Ai hạ một con quái (người hay bot) thì người cùng map cũng thấy con đó ngã.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.world import chat
from app.world.bots import RESPAWN, BotWorld

Send = Callable[[dict], Awaitable[None]]
DIRS = {"down", "up", "left", "right"}
MODES = {"walk", "horse", "boat"}
SLOTS = {"vu_khi", "giap", "mu", "giay", "gang"}
PHRASES = 12  # số câu nói có sẵn ở phía game
PARTY_MAX = 4
INVITE_TTL = 60.0
PEERS_EVERY = 0.2  # gửi danh sách người cùng map tối đa năm lần mỗi giây
STALE = 15.0  # quá lâu không gửi vị trí thì coi như đã rời map
SHARE_RANGE = 900.0  # đồng đội đứng trong tầm này mới được chia kinh nghiệm
SHARE_RATE = 0.5
POS_MIN_GAP = 0.04  # bỏ bớt khi một máy gửi dồn dập quá 25 lần mỗi giây
# Thách đấu: hai người vào cùng một võ đài, mỗi máy điều khiển nhân vật của mình,
# máy chủ chuyển tin qua lại
PVP_TIME = 90.0  # thời gian một trận (giây), không kể đếm ngược
PVP_GRACE = 8.0  # chờ thêm cho đếm ngược và mạng chậm rồi mới phân xử theo máu
PVP_GAP = 0.03  # chuyển tối đa khoảng 33 tin trạng thái mỗi giây cho mỗi người
PVP_MAX_HIT = 400.0  # một đòn trúng không thể quá mức này
# Máy người ra đòn tự báo đòn trúng, nên máy chủ giới hạn sát thương theo "ngân sách" của
# mỗi người, tính theo hệ số sức đánh lúc vào trận: sửa máy mình để gửi dồn đòn cũng không
# hạ đối thủ ngay được.
PVP_HIT_MAX = 50.0  # một đòn tối đa (nhân hệ số sức đánh)
PVP_DPS = 60.0  # ngân sách hồi lại mỗi giây (nhân hệ số sức đánh)
PVP_BURST = 150.0  # ngân sách dồn được tối đa (nhân hệ số sức đánh)
PVP_HIT_COST = 5.0  # mỗi tin đòn tốn ít nhất chừng này, kể cả tin chỉ hất lùi, gây bỏng, làm chậm
PVP_EVENTS = {"atk", "cast", "dodge"}


class Store(Protocol):
    async def allies(self, uid: str) -> set[str]: ...
    async def add_alliance(self, a: str, b: str) -> None: ...
    async def remove_alliance(self, a: str, b: str) -> None: ...
    async def party_of(self, uid: str) -> tuple[str, str, list[str]] | None: ...
    async def create_party(self, leader: str, member: str) -> str: ...
    async def join_party(self, pid: str, uid: str) -> None: ...
    async def leave_party(self, uid: str) -> None: ...
    async def record_duel(
        self, reporter: str, opponent: str, win: bool, map_id: str, draw: bool = False
    ) -> None: ...


@dataclass
class Presence:
    uid: str
    name: str
    send: Send
    map: str | None = None
    x: float = 0.0
    y: float = 0.0
    f: str = "down"
    m: bool = False
    mode: str = "walk"
    gear: dict[str, str] = field(default_factory=dict)
    lv: int = 1
    realm: str = ""
    pow: int = 0
    combat: dict[str, Any] = field(default_factory=dict)
    seen: float = 0.0
    peers_at: float = 0.0
    pos_at: float = 0.0
    chat_at: dict[str, float] = field(default_factory=dict)
    fight: dict[str, Any] | None = None  # đang đánh ai, ở đâu: người cùng map vẽ cảnh vung vũ khí
    pvp_at: float = 0.0  # lần chuyển tin trạng thái thách đấu gần nhất


@dataclass
class Duel:
    """Một trận thách đấu đang diễn ra giữa hai người thật."""

    id: str
    a: str  # người mời, đứng bên trái
    b: str  # người nhận lời, đứng bên phải
    map: str
    until: float  # quá giờ này mà chưa ai gục thì phân xử theo máu
    hp: dict[str, float] = field(default_factory=dict)  # tỉ lệ máu mới nhất của mỗi bên
    power: dict[str, float] = field(default_factory=dict)  # hệ số sức đánh lúc vào trận
    budget: dict[str, float] = field(default_factory=dict)  # sát thương còn được gửi
    budget_at: dict[str, float] = field(default_factory=dict)

    def other(self, uid: str) -> str:
        return self.b if uid == self.a else self.a


def _num(v, lo, hi, default=0.0) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, x)) if x == x else default  # bỏ NaN


def _str(v, limit: int) -> str:
    return v[:limit] if isinstance(v, str) else ""


def clean_gear(gear) -> dict[str, str]:
    if not isinstance(gear, dict):
        return {}
    return {k: v[:24] for k, v in gear.items() if k in SLOTS and isinstance(v, str)}


def clean_fight(f) -> dict[str, Any] | None:
    """Đang đánh quái nào, quái đứng đâu; thiếu hoặc lạ thì coi như không đánh."""
    if not isinstance(f, dict) or not isinstance(f.get("name"), str):
        return None
    return {
        "name": f["name"][:40],
        "x": round(_num(f.get("x"), 0, 20000)),
        "y": round(_num(f.get("y"), 0, 20000)),
    }


def clean_combat(c) -> dict[str, Any]:
    """Chỉ số chiến đấu người chơi tự gửi lên để đối thủ thấy đúng máu, kỹ năng khi thách đấu.

    Chặn trong giới hạn hợp lý."""
    if not isinstance(c, dict):
        return {}
    skills = c.get("skills") if isinstance(c.get("skills"), dict) else {}
    return {
        "hp": _num(c.get("hp"), 50, 4000, 100),
        "dmg": _num(c.get("dmg"), 0.5, 8, 1),
        "spd": _num(c.get("spd"), 0.5, 2.5, 1),
        "cd": _num(c.get("cd"), 0.4, 1, 1),
        "skills": {
            k[:24]: int(_num(v, 1, 3, 1)) for k, v in list(skills.items())[:4] if isinstance(k, str)
        },
    }


class Hub:
    def __init__(
        self,
        store: Store,
        clock: Callable[[], float] = time.monotonic,
        bots: BotWorld | None = None,
    ):
        self.store = store
        self.clock = clock
        self.bots = bots  # người chơi máy; None thì thế giới chỉ có người thật
        self.people: dict[str, Presence] = {}
        self.invites: dict[
            tuple[str, str, str], float
        ] = {}  # (loại, người mời, người được mời) -> hết hạn
        self.allies: dict[str, set[str]] = {}
        self.party: dict[str, str] = {}  # uid -> mã tổ đội
        self.parties: dict[str, dict] = {}  # mã tổ đội -> {"leader", "members": list}
        # tin thế giới gần nhất, gửi cho người mới vào
        self.recent: deque[dict] = deque(maxlen=chat.RECENT)
        self.duels: dict[str, Duel] = {}  # mã trận -> trận thách đấu đang diễn ra
        self.in_duel: dict[str, str] = {}  # uid -> mã trận
        self._duel_n = 0

    # ----- kết nối -----
    async def connect(self, uid: str, name: str, send: Send) -> None:
        old = self.people.get(uid)
        if old is not None:  # mở game ở tab khác: tab cũ thôi nhận tin
            await self._safe(
                old.send,
                {"t": "notice", "text": "Bạn vừa vào game ở nơi khác, kết nối này đã đóng."},
            )
        rid = self.in_duel.get(uid)
        if rid in self.duels:  # tab mới không biết trận đang đánh ở tab cũ: coi như rời trận
            await self._duel_over(self.duels[rid], self.duels[rid].other(uid), "left")
        self.people[uid] = Presence(uid, name, send, seen=self.clock())
        self.allies[uid] = await self.store.allies(uid)
        found = await self.store.party_of(uid)
        if found:
            pid, leader, members = found
            self.parties[pid] = {"leader": leader, "members": members}
            for m in members:
                self.party[m] = pid
        await send({"t": "hello", "you": uid, "name": name})
        if self.recent:
            await send({"t": "chat_recent", "list": list(self.recent)})
        await self._send_allies(uid)
        await self._send_party(uid)

    async def disconnect(self, uid: str, send: Send | None = None) -> None:
        p = self.people.get(uid)
        if p is None or (send is not None and p.send is not send):
            return  # tab cũ đóng sau khi tab mới đã vào: giữ tab mới
        del self.people[uid]
        self.invites = {k: v for k, v in self.invites.items() if uid not in (k[1], k[2])}
        rid = self.in_duel.get(uid)
        if rid in self.duels:  # rời game giữa trận: đối thủ thắng
            await self._duel_over(self.duels[rid], self.duels[rid].other(uid), "left")
        await self._refresh_map(p.map)  # người cùng map thấy mình biến mất ngay

    def online(self) -> dict[str, int]:
        """Số người đang ở mỗi map, cho trang quản trị."""
        out: dict[str, int] = {}
        for p in self.people.values():
            if p.map:
                out[p.map] = out.get(p.map, 0) + 1
        return out

    # ----- xử lý tin nhắn -----
    async def handle(self, uid: str, msg: dict) -> None:
        p = self.people.get(uid)
        if p is None or not isinstance(msg, dict):
            return
        p.seen = self.clock()
        kind = msg.get("t")
        handler = {
            "pos": self._pos,
            "say": self._say,
            "chat": self._chat,
            "invite": self._invite,
            "answer": self._answer,
            "party_leave": self._party_leave,
            "ally_remove": self._ally_remove,
            "kill": self._kill,
            "mob_kill": self._mob_kill,
            "pvp": self._pvp,
            "pvp_hit": self._pvp_hit,
            "pvp_dead": self._pvp_dead,
            "pvp_quit": self._pvp_dead,
        }.get(kind)
        if handler:
            await handler(p, msg)

    async def _pos(self, p: Presence, msg: dict) -> None:
        now = self.clock()
        if now - p.pos_at < POS_MIN_GAP:
            return
        p.pos_at = now
        old_map = p.map
        p.map = _str(msg.get("map"), 32) or None
        p.x, p.y = _num(msg.get("x"), 0, 20000), _num(msg.get("y"), 0, 20000)
        p.f = msg.get("f") if msg.get("f") in DIRS else "down"
        p.m = bool(msg.get("m"))
        p.mode = msg.get("mode") if msg.get("mode") in MODES else "walk"
        if "gear" in msg:
            p.gear = clean_gear(msg.get("gear"))
        p.lv = int(_num(msg.get("lv"), 1, 99, 1))
        p.realm = _str(msg.get("realm"), 20)
        p.pow = int(_num(msg.get("pow"), 0, 10**6))
        if "combat" in msg:
            p.combat = clean_combat(msg.get("combat"))
        p.fight = clean_fight(msg.get("fight"))
        if p.map != old_map:
            # vừa vào map (hay đổi map): người ở đó thấy mình ngay, người ở map cũ thấy mình đi
            await self._refresh_map(p.map)
            if old_map:
                await self._refresh_map(old_map)
        elif now - p.peers_at >= PEERS_EVERY:
            p.peers_at = now
            await p.send({"t": "peers", "map": p.map, "list": self.peers(p)})

    async def _refresh_map(self, map_id: str | None) -> None:
        """Gửi ngay danh sách người cùng map cho mọi người ở map đó (có người vào, ra, rời game)."""
        if not map_id:
            return
        now = self.clock()
        for q in list(self.people.values()):
            if q.map == map_id:
                q.peers_at = now
                await self._safe(q.send, {"t": "peers", "map": q.map, "list": self.peers(q)})

    def peers(self, p: Presence) -> list[dict]:
        now = self.clock()
        mine = self.party.get(p.uid)
        out = []
        for q in self.people.values():
            if q.uid == p.uid or q.map != p.map or p.map is None or now - q.seen > STALE:
                continue
            out.append(
                {
                    "id": q.uid,
                    "name": q.name,
                    "x": round(q.x),
                    "y": round(q.y),
                    "f": q.f,
                    "m": q.m,
                    "mode": q.mode,
                    "gear": q.gear,
                    "lv": q.lv,
                    "realm": q.realm,
                    "pow": q.pow,
                    "fight": q.fight,
                    "party": mine is not None and self.party.get(q.uid) == mine,
                    "ally": q.uid in self.allies.get(p.uid, set()),
                }
            )
        if self.bots is not None and p.map:
            out.extend(self.bots.peers_for(p.map))
        return out

    async def _say(self, p: Presence, msg: dict) -> None:
        k = msg.get("k")
        if not isinstance(k, int) or not 0 <= k < PHRASES or p.map is None:
            return
        for q in list(self.people.values()):
            if q.map == p.map:
                await self._safe(q.send, {"t": "say", "from": p.uid, "name": p.name, "k": k})

    async def _mob_kill(self, p: Presence, msg: dict) -> None:
        """Người chơi vừa hạ một con quái: người cùng map thấy nó ngã, bot không nhắm vào nó nữa."""
        key = _str(msg.get("mob"), 64)
        if not key or not p.map:
            return
        if self.bots is not None:
            self.bots.dead.setdefault(p.map, {})[key] = self.clock() + RESPAWN
        await self._to_map(p.map, {"t": "mob_down", "mob": key}, skip=p.uid)

    async def _to_map(self, map_id: str, msg: dict, skip: str | None = None) -> None:
        for q in list(self.people.values()):
            if q.map == map_id and q.uid != skip:
                await self._safe(q.send, msg)

    # ----- người chơi máy -----
    async def tick(self, dt: float) -> None:
        """Một nhịp của máy chủ: phân xử các trận thách đấu đã hết giờ, cho người chơi máy đi;
        báo người cùng map khi bot hạ quái hay nói một câu."""
        now = self.clock()
        for d in [d for d in self.duels.values() if now >= d.until]:
            ha, hb = d.hp.get(d.a, 1.0), d.hp.get(d.b, 1.0)
            await self._duel_over(d, d.a if ha > hb else d.b if hb > ha else None, "time")
        if self.bots is None or not self.bots.bots:
            return
        now = self.clock()
        players: dict[str, list[tuple[float, float]]] = {}
        for q in self.people.values():
            if q.map and now - q.seen <= STALE:
                players.setdefault(q.map, []).append((q.x, q.y))
        for event in self.bots.update(dt, players):
            if event[0] == "kill":
                await self._to_map(event[1], {"t": "mob_down", "mob": event[2]})
            elif event[0] == "say":
                bot, k = event[2], event[3]
                await self._to_map(event[1], {"t": "say", "from": bot.id, "name": bot.name, "k": k})

    async def _chat(self, p: Presence, msg: dict) -> None:
        """Chat gõ tự do: kênh map tới người cùng map, kênh thế giới tới mọi người đang online."""
        ch = msg.get("ch")
        if ch not in chat.CHANNELS:
            return
        text = chat.censor(chat.clean(msg.get("text")))
        if not text or (ch == "map" and p.map is None):
            return
        now = self.clock()
        if now - p.chat_at.get(ch, -1e9) < chat.GAP[ch]:
            await p.send({"t": "notice", "text": "Bạn gửi nhanh quá, chờ vài giây rồi chat tiếp."})
            return
        p.chat_at[ch] = now
        out = {"t": "chat", "ch": ch, "from": p.uid, "name": p.name, "text": text, "map": p.map}
        if ch == "world":
            self.recent.append(out)
            targets = list(self.people.values())
        else:
            targets = [q for q in self.people.values() if q.map == p.map]
        for q in targets:
            await self._safe(q.send, out)

    # ----- lời mời -----
    async def _invite(self, p: Presence, msg: dict) -> None:
        kind, to = msg.get("kind"), msg.get("to")
        target = self.people.get(to) if isinstance(to, str) else None
        bot = self.bots.bots.get(to) if self.bots is not None and isinstance(to, str) else None
        if bot is not None and kind in ("party", "ally", "duel"):
            await p.send({"t": "notice", "text": f"{bot.name} đang bận, chưa nhận lời được."})
            return
        if kind not in ("party", "ally", "duel") or target is None or target.uid == p.uid:
            return
        why = self._cannot(kind, p, target)
        if why:
            await p.send({"t": "notice", "text": why})
            return
        self.invites[(kind, p.uid, target.uid)] = self.clock() + INVITE_TTL
        await target.send({"t": "invite", "kind": kind, "from": p.uid, "name": p.name, "lv": p.lv})
        await p.send({"t": "notice", "text": f"Đã gửi lời mời tới {target.name}."})

    def _cannot(self, kind: str, p: Presence, target: Presence) -> str | None:
        if kind == "ally" and target.uid in self.allies.get(p.uid, set()):
            return f"{target.name} đã là đồng minh của bạn."
        if kind == "party":
            if target.uid in self.party:
                return f"{target.name} đang ở trong một tổ đội khác."
            pid = self.party.get(p.uid)
            if pid and self.parties[pid]["leader"] != p.uid:
                return "Chỉ đội trưởng mới mời thêm người được."
            if pid and len(self.parties[pid]["members"]) >= PARTY_MAX:
                return f"Tổ đội đã đủ {PARTY_MAX} người."
        if kind == "duel" and (target.map != p.map or p.map is None):
            return "Hai người phải đứng cùng một map mới thách đấu được."
        if kind == "duel" and (p.uid in self.in_duel or target.uid in self.in_duel):
            return "Một trong hai người đang ở trong một trận thách đấu khác."
        return None

    async def _answer(self, p: Presence, msg: dict) -> None:
        kind, frm = msg.get("kind"), msg.get("from")
        key = (kind, frm, p.uid)
        until = self.invites.pop(key, None)
        if until is None or until < self.clock():
            await p.send({"t": "notice", "text": "Lời mời đã hết hạn."})
            return
        inviter = self.people.get(frm)
        if inviter is None:
            await p.send({"t": "notice", "text": "Người mời đã rời game."})
            return
        if not msg.get("ok"):
            await self._safe(inviter.send, {"t": "notice", "text": f"{p.name} đã từ chối."})
            return
        why = self._cannot(kind, inviter, p)
        if why:
            await p.send({"t": "notice", "text": why})
            return
        if kind == "ally":
            await self.store.add_alliance(inviter.uid, p.uid)
            self.allies.setdefault(inviter.uid, set()).add(p.uid)
            self.allies.setdefault(p.uid, set()).add(inviter.uid)
            for a, b in ((inviter, p), (p, inviter)):
                await self._safe(
                    a.send, {"t": "notice", "text": f"Bạn và {b.name} đã kết đồng minh."}
                )
                await self._send_allies(a.uid)
        elif kind == "party":
            pid = self.party.get(inviter.uid)
            if pid is None:
                pid = await self.store.create_party(inviter.uid, p.uid)
                self.parties[pid] = {"leader": inviter.uid, "members": [inviter.uid, p.uid]}
                self.party[inviter.uid] = pid
            else:
                await self.store.join_party(pid, p.uid)
                self.parties[pid]["members"].append(p.uid)
            self.party[p.uid] = pid
            for m in self.parties[pid]["members"]:
                await self._send_party(m)
        elif kind == "duel":
            await self._start_duel(inviter, p)

    # ----- tổ đội, đồng minh -----
    async def _party_leave(self, p: Presence, _msg: dict) -> None:
        pid = self.party.pop(p.uid, None)
        if pid is None:
            return
        await self.store.leave_party(p.uid)
        info = self.parties.get(pid, {"members": [], "leader": None})
        info["members"] = [m for m in info["members"] if m != p.uid]
        await p.send({"t": "party", "party": None})
        if len(info["members"]) < 2:  # còn một người thì giải tán
            for m in info["members"]:
                self.party.pop(m, None)
                await self.store.leave_party(m)
                await self._send_party(m)
            self.parties.pop(pid, None)
            return
        if info["leader"] == p.uid:
            info["leader"] = info["members"][0]
        for m in info["members"]:
            await self._send_party(m)

    async def _ally_remove(self, p: Presence, msg: dict) -> None:
        other = msg.get("id")
        if not isinstance(other, str) or other not in self.allies.get(p.uid, set()):
            return
        await self.store.remove_alliance(p.uid, other)
        self.allies[p.uid].discard(other)
        self.allies.get(other, set()).discard(p.uid)
        await self._send_allies(p.uid)
        if other in self.people:
            await self._send_allies(other)

    async def _kill(self, p: Presence, msg: dict) -> None:
        """Hạ được quái: đồng đội cùng map đứng gần được chia một nửa kinh nghiệm và tiềm năng."""
        pid = self.party.get(p.uid)
        if pid is None or p.map is None:
            return
        exp = int(_num(msg.get("exp"), 0, 2000) * SHARE_RATE)
        tiem = int(_num(msg.get("tiem"), 0, 800) * SHARE_RATE)
        mob = _str(msg.get("mob"), 40)
        for uid in self.parties.get(pid, {}).get("members", []):
            q = self.people.get(uid)
            if q is None or q.uid == p.uid or q.map != p.map:
                continue
            if (q.x - p.x) ** 2 + (q.y - p.y) ** 2 > SHARE_RANGE**2:
                continue
            await self._safe(
                q.send, {"t": "share", "from": p.name, "mob": mob, "exp": exp, "tiem": tiem}
            )

    # ----- thách đấu: hai người thật đánh nhau trong cùng một võ đài -----
    async def _start_duel(self, a: Presence, b: Presence) -> None:
        """Người mời (a) đứng bên trái, người nhận lời (b) bên phải. Mỗi máy điều khiển nhân vật
        của mình; máy chủ chỉ chuyển trạng thái, đòn trúng qua lại và phân xử khi có người gục,
        rút lui, rời game hoặc hết giờ."""
        self._duel_n += 1
        now = self.clock()
        d = Duel(f"d{self._duel_n}", a.uid, b.uid, a.map or "", now + PVP_TIME + PVP_GRACE)
        for q in (a, b):
            d.power[q.uid] = float((q.combat or {}).get("dmg", 1.0))
            d.budget[q.uid] = PVP_BURST * d.power[q.uid]
            d.budget_at[q.uid] = now
        self.duels[d.id] = d
        self.in_duel[a.uid] = self.in_duel[b.uid] = d.id
        for side, (me, vs) in enumerate(((a, b), (b, a))):
            snap = {
                "id": vs.uid,
                "name": vs.name,
                "gear": vs.gear,
                "lv": vs.lv,
                "realm": vs.realm,
                "combat": vs.combat or clean_combat({}),
            }
            start = {"t": "pvp_start", "room": d.id, "side": side, "time": PVP_TIME, "vs": snap}
            await self._safe(me.send, start)

    def _duel_of(self, p: Presence, msg: dict) -> Duel | None:
        d = self.duels.get(msg.get("room")) if isinstance(msg.get("room"), str) else None
        return d if d is not None and p.uid in (d.a, d.b) else None

    async def _pvp(self, p: Presence, msg: dict) -> None:
        """Trạng thái nhân vật của một bên (vị trí, hướng, máu, đang né, đang thủ) và các động
        tác vừa làm."""
        d = self._duel_of(p, msg)
        if d is None:
            return
        now = self.clock()
        if now - p.pvp_at < PVP_GAP:
            return
        p.pvp_at = now
        s = msg.get("s") if isinstance(msg.get("s"), dict) else {}
        mhp = _num(s.get("mhp"), 1, 5000, 100)
        hp = _num(s.get("hp"), 0, mhp, mhp)
        d.hp[p.uid] = hp / mhp
        state = {
            "x": round(_num(s.get("x"), 0, 2000)),
            "y": round(_num(s.get("y"), 0, 2000)),
            "f": s.get("f") if s.get("f") in DIRS else "down",
            "m": bool(s.get("m")),
            "hp": round(hp, 1),
            "mhp": round(mhp),
            "dg": bool(s.get("dg")),
            "sh": bool(s.get("sh")),
            "rd": bool(s.get("rd")),
        }
        events = []
        for e in msg.get("ev") if isinstance(msg.get("ev"), list) else []:
            if isinstance(e, dict) and e.get("k") in PVP_EVENTS and len(events) < 6:
                angle = round(_num(e.get("a"), -7, 7), 3)
                events.append({"k": e["k"], "sid": _str(e.get("sid"), 24), "a": angle})
        other = self.people.get(d.other(p.uid))
        if other is not None:
            await self._safe(other.send, {"t": "pvp", "room": d.id, "s": state, "ev": events})

    async def _pvp_hit(self, p: Presence, msg: dict) -> None:
        """Máy người ra đòn thấy đòn trúng đối thủ: chuyển sang máy đối thủ để tự trừ máu
        (né, thế thủ vẫn được tính)."""
        d = self._duel_of(p, msg)
        other = self.people.get(d.other(p.uid)) if d else None
        if other is None:
            return
        now, power = self.clock(), d.power.get(p.uid, 1.0)
        refill = (now - d.budget_at.get(p.uid, now)) * PVP_DPS * power
        budget = min(PVP_BURST * power, d.budget.get(p.uid, 0.0) + refill)
        d.budget_at[p.uid] = now
        if budget < PVP_HIT_COST:  # gửi dồn quá nhanh: bỏ tin này
            d.budget[p.uid] = budget
            return
        dmg = min(_num(msg.get("dmg"), 0, PVP_MAX_HIT), PVP_HIT_MAX * power, budget)
        d.budget[p.uid] = budget - max(dmg, PVP_HIT_COST)
        await self._safe(
            other.send,
            {
                "t": "pvp_hit",
                "room": d.id,
                "dmg": round(dmg, 1),
                "knock": round(_num(msg.get("knock"), 0, 120)),
                "sx": round(_num(msg.get("sx"), 0, 2000)),
                "sy": round(_num(msg.get("sy"), 0, 2000)),
                "burn": bool(msg.get("burn")),
                "slow": bool(msg.get("slow")),
            },
        )

    async def _pvp_dead(self, p: Presence, msg: dict) -> None:
        """Một bên báo mình đã gục hoặc rút lui: bên kia thắng."""
        d = self._duel_of(p, msg)
        if d is not None:
            await self._duel_over(d, d.other(p.uid), "quit" if msg.get("t") == "pvp_quit" else "ko")

    async def _duel_over(self, d: Duel, winner: str | None, why: str) -> None:
        if self.duels.pop(d.id, None) is None:
            return
        for uid in (d.a, d.b):
            if self.in_duel.get(uid) == d.id:
                del self.in_duel[uid]
        for uid in (d.a, d.b):
            await self.store.record_duel(uid, d.other(uid), uid == winner, d.map, winner is None)
            q = self.people.get(uid)
            if q is not None:
                over = {"t": "pvp_over", "room": d.id, "win": uid == winner, "draw": winner is None}
                await self._safe(q.send, {**over, "why": why})

    # ----- gửi trạng thái -----
    async def _send_allies(self, uid: str) -> None:
        p = self.people.get(uid)
        if p is None:
            return
        out = []
        for a in sorted(self.allies.get(uid, set())):
            q = self.people.get(a)
            out.append(
                {
                    "id": a,
                    "name": q.name if q else "",
                    "online": q is not None,
                    "map": q.map if q else None,
                }
            )
        await self._safe(p.send, {"t": "allies", "list": out})

    async def _send_party(self, uid: str) -> None:
        p = self.people.get(uid)
        if p is None:
            return
        pid = self.party.get(uid)
        if pid is None:
            await self._safe(p.send, {"t": "party", "party": None})
            return
        info = self.parties[pid]
        members = [
            {
                "id": m,
                "name": self.people[m].name if m in self.people else "",
                "online": m in self.people,
            }
            for m in info["members"]
        ]
        await self._safe(
            p.send,
            {"t": "party", "party": {"id": pid, "leader": info["leader"], "members": members}},
        )

    @staticmethod
    async def _safe(send: Send, msg: dict) -> None:
        try:
            await send(msg)
        except Exception:  # noqa: BLE001  một kết nối hỏng không được làm hỏng tin gửi cho người khác
            return


class MemoryStore:
    """Lưu tạm trong bộ nhớ, dùng cho kiểm thử."""

    def __init__(self):
        self.alliances: set[frozenset[str]] = set()
        self.members: dict[str, str] = {}
        self.leaders: dict[str, str] = {}
        self.duels: list[tuple[str, str, bool, str]] = []
        self._n = 0

    async def allies(self, uid):
        return {next(iter(pair - {uid})) for pair in self.alliances if uid in pair}

    async def add_alliance(self, a, b):
        self.alliances.add(frozenset((a, b)))

    async def remove_alliance(self, a, b):
        self.alliances.discard(frozenset((a, b)))

    async def party_of(self, uid):
        pid = self.members.get(uid)
        if pid is None:
            return None
        return pid, self.leaders[pid], [u for u, p in self.members.items() if p == pid]

    async def create_party(self, leader, member):
        self._n += 1
        pid = f"p{self._n}"
        self.leaders[pid] = leader
        self.members[leader] = pid
        self.members[member] = pid
        return pid

    async def join_party(self, pid, uid):
        self.members[uid] = pid

    async def leave_party(self, uid):
        self.members.pop(uid, None)

    async def record_duel(self, reporter, opponent, win, map_id, draw=False):
        self.duels.append((reporter, opponent, "draw" if draw else win, map_id))
