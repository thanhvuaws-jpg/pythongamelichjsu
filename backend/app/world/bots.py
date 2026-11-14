"""Người chơi máy chạy trên máy chủ: tự cày quái, làm nhiệm vụ, sắm đồ, câu cá cho map có người.

Bot không gắn với người chơi nào: quản trị viên thêm, bớt ở trang quản trị; máy chủ cho bot đi
suốt, kể cả khi không ai online. Người chơi thấy bot như mọi người chơi khác trong danh sách người
cùng map (tên, cấp, đồ, đang đánh ai).

Máy chủ không dựng được map nên đọc `botmaps.json` (do tools/export_botmaps.py xuất từ đúng bản đồ
của game): ô đi được, chỗ làm nhiệm vụ, lò rèn, chỗ câu cá, các con quái thường. Bot hạ con quái nào
thì máy chủ báo người cùng map để con đó cũng ngã trên máy họ. Bot không đụng quái đang ở gần người
chơi thật.
"""

from __future__ import annotations

import base64
import json
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).with_name("botmaps.json")
SPEED = 4.4  # ô mỗi giây, gần bằng người chơi đi bộ
FIGHT = (3.0, 6.0)
STAY = {
    "quest": (4.0, 8.0),
    "mentor": (3.0, 6.0),
    "shop": (3.0, 5.0),
    "fish": (6.0, 12.0),
    "wander": (1.5, 4.0),
}
REST = (1.0, 3.0)
KILLS_PER_LEVEL = 3
LEVEL_CAP = 40
RESPAWN = 30.0
SAFE_TILES = 7  # quái gần người chơi thật hơn chừng này ô thì bot để dành
TALK_EVERY = (25.0, 60.0)
MAX_BOTS = 60
ACTIVITIES = {"mix": "Lúc cày quái, lúc làm nhiệm vụ", "train": "Cày quái", "quest": "Làm nhiệm vụ"}
PLANS = {
    "train": (("hunt", 0.85), ("wander", 0.1), ("shop", 0.05)),
    "quest": (("quest", 0.55), ("mentor", 0.15), ("shop", 0.1), ("fish", 0.1), ("wander", 0.1)),
    "mix": (("hunt", 0.5), ("quest", 0.25), ("shop", 0.08), ("fish", 0.1), ("wander", 0.07)),
}
# Số thứ tự câu nói nhanh ở phía game (core/net.py PHRASES); bot không dùng câu "Thách đấu không?"
SAY = {
    "hunt": (1, 10, 5),
    "quest": (6, 7, 11),
    "mentor": (6, 11),
    "shop": (2, 5),
    "fish": (4, 9),
    "wander": (0, 3, 9),
    "idle": (0, 9),
}
DOING = {
    "hunt": "đang đi tìm quái",
    "quest": "đang làm nhiệm vụ",
    "mentor": "đang về báo cáo già làng",
    "shop": "ghé lò rèn",
    "fish": "đang câu cá",
    "wander": "đang đi dạo",
    "idle": "đang nghỉ",
}
NAMES = (
    "Minh Khang",
    "Gia Hân",
    "Bảo An",
    "Tuệ Lâm",
    "Đức Minh",
    "Khánh Vy",
    "Quang Huy",
    "Thảo Nhi",
    "Nhật Minh",
    "Hoài An",
    "Phúc Lâm",
    "Ngọc Diệp",
    "Trọng Nhân",
    "An Nhiên",
    "Hải Nam",
    "Mỹ Linh",
    "Tấn Phát",
    "Bích Ngọc",
    "Văn Đông",
    "Kim Ngân",
    "Thanh Tùng",
    "Lan Anh",
    "Hoàng Long",
    "Thu Trang",
    "Đăng Khoa",
    "Yến Nhi",
    "Bảo Châu",
    "Quốc Bảo",
    "Hà My",
    "Tiến Đạt",
    "Minh Thư",
    "Gia Huy",
    "Ngọc Hân",
    "Trung Hiếu",
    "Phương Linh",
    "Duy Anh",
    "Khánh Linh",
    "Hữu Phước",
    "Cẩm Tú",
    "Việt Hoàng",
)
STEPS = (
    (-1, 0),
    (1, 0),
    (0, 1),
    (0, -1),
    (-1, 1),
    (1, 1),
    (-2, 0),
    (2, 0),
    (0, 2),
    (-2, 1),
    (2, 1),
)


class NavMap:
    """Một map như máy chủ thấy: ô nào đi được, các chỗ có việc làm, các con quái thường."""

    def __init__(self, map_id: str, spec: dict, tile: int):
        self.id, self.name, self.tile = map_id, spec["name"], tile
        self.w, self.h = spec["w"], spec["h"]
        self.bits = base64.b64decode(spec["walk"])
        self.points = {k: [tuple(p) for p in v] for k, v in spec["points"].items()}
        self.mobs = spec["mobs"]
        self.spawn = tuple(spec["spawn"])
        self.cells = [(x, y) for y in range(self.h) for x in range(self.w) if self.ok(x, y)]

    def ok(self, x: int, y: int) -> bool:
        if not (0 <= x < self.w and 0 <= y < self.h):
            return False
        i = y * self.w + x
        return bool(self.bits[i // 8] >> (i % 8) & 1)

    def center(self, t: tuple[int, int]) -> tuple[float, float]:
        """Chỗ đứng của một ô, đúng cách game đặt nhân vật lên ô."""
        return t[0] * self.tile + self.tile / 2, t[1] * self.tile + self.tile - 8

    def near(self, tx: int, ty: int, taken: set) -> tuple[int, int] | None:
        for dx, dy in STEPS:
            t = (tx + dx, ty + dy)
            if self.ok(*t) and t not in taken:
                return t
        return None

    def path(
        self, start: tuple[int, int], goal: tuple[int, int], limit: int = 6000
    ) -> list[tuple[int, int]] | None:
        """Tìm đường bốn hướng; không tới được thì trả None."""
        if start == goal:
            return []
        prev = {start: None}
        queue = deque([start])
        while queue and len(prev) < limit:
            cur = queue.popleft()
            if cur == goal:
                out = []
                while cur != start:
                    out.append(cur)
                    cur = prev[cur]
                return out[::-1]
            x, y = cur
            for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if nxt not in prev and self.ok(*nxt):
                    prev[nxt] = cur
                    queue.append(nxt)
        return None


@dataclass
class BotSim:
    id: str
    name: str
    map_id: str
    activity: str
    level: int
    x: float = 0.0
    y: float = 0.0
    facing: str = "down"
    gear: dict[str, str] = field(default_factory=dict)
    path: list[tuple[int, int]] = field(default_factory=list)
    task: str = "idle"
    wait: float = 1.0
    target: Any = None  # con quái (dict) hoặc ô có việc làm
    fight: dict[str, Any] | None = None
    kills: int = 0
    talk: float = 30.0
    dirty: bool = False  # cấp đã đổi, chưa lưu vào cơ sở dữ liệu

    def tile(self, size: int) -> tuple[int, int]:
        return int(self.x // size), int((self.y - 4) // size)


class BotWorld:
    def __init__(
        self, data: dict | None = None, rng: random.Random | None = None, clock=time.monotonic
    ):
        data = data if data is not None else json.loads(DATA_FILE.read_text(encoding="utf-8"))
        self.tile = data["tile"]
        self.realms = data["realms"]
        self.items = data["items"]
        self.maps = {k: NavMap(k, v, self.tile) for k, v in data["maps"].items()}
        self.bots: dict[str, BotSim] = {}
        self.dead: dict[str, dict[str, float]] = {}  # map -> tên riêng con quái -> lúc mọc lại
        self.rng = rng or random.Random()
        self.clock = clock

    # ----- thêm, bớt -----
    def free_name(self) -> str:
        used = {b.name for b in self.bots.values()}
        free = [n for n in NAMES if n not in used]
        if free:
            return self.rng.choice(free)
        return f"{self.rng.choice(NAMES)} {len(used) + 1}"

    def add(
        self, bot_id: str, name: str, map_id: str, activity: str = "mix", level: int = 1
    ) -> BotSim:
        nav = self.maps[map_id]
        level = max(1, min(LEVEL_CAP, int(level)))
        bot = BotSim(
            bot_id, name[:40], map_id, activity if activity in ACTIVITIES else "mix", level
        )
        spots = [p for kind in ("quest", "mentor", "shop") for p in nav.points.get(kind, [])] or [
            nav.spawn
        ]
        sx, sy = self.rng.choice(spots)
        near = [c for c in nav.cells if abs(c[0] - sx) <= 6 and abs(c[1] - sy) <= 5] or nav.cells
        bot.x, bot.y = nav.center(self.rng.choice(near))
        bot.gear = self.gear_for(level)
        bot.wait = self.rng.uniform(*REST)
        bot.talk = self.rng.uniform(*TALK_EVERY)
        self.bots[bot_id] = bot
        return bot

    def remove(self, bot_id: str) -> bool:
        return self.bots.pop(bot_id, None) is not None

    def gear_for(self, level: int) -> dict[str, str]:
        gear = {}
        for slot, items in self.items.items():
            fit = [iid for lv, iid in items if lv <= level]
            if fit:
                gear[slot] = self.rng.choice(fit[-2:])
        return gear

    def realm(self, level: int) -> str:
        return next((name for cap, name in self.realms if level <= cap), self.realms[-1][1])

    @staticmethod
    def power(bot: BotSim) -> int:
        """Sức mạnh ước chừng theo cấp và đồ, gần với con số của người chơi cùng cấp."""
        return 380 + bot.level * 46 + len(bot.gear) * 25

    # ----- người chơi thấy gì -----
    def peer(self, bot: BotSim) -> dict[str, Any]:
        return {
            "id": bot.id,
            "name": bot.name,
            "x": round(bot.x),
            "y": round(bot.y),
            "f": bot.facing,
            "m": bool(bot.path),
            "mode": "walk",
            "gear": bot.gear,
            "lv": bot.level,
            "realm": self.realm(bot.level),
            "pow": self.power(bot),
            "party": False,
            "ally": False,
            "fight": bot.fight,
        }

    def peers_for(self, map_id: str | None) -> list[dict[str, Any]]:
        return [self.peer(b) for b in self.bots.values() if b.map_id == map_id]

    def doing(self, bot: BotSim) -> str:
        if bot.fight:
            return f"đang đánh {bot.fight['name']}"
        return DOING.get(bot.task, "đang đi")

    # ----- chọn việc -----
    def _taken(self, bot: BotSim) -> set[tuple[int, int]]:
        out = set()
        for o in self.bots.values():
            if o is bot or o.map_id != bot.map_id:
                continue
            for tx, ty in (o.tile(self.tile), *(o.path[-1:])):
                out.update((tx + dx, ty + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        return out

    def _go(self, bot: BotSim, nav: NavMap, goal: tuple[int, int]) -> bool:
        path = nav.path(bot.tile(self.tile), goal)
        if path is None:
            return False
        bot.path = path
        return True

    def _start(self, bot: BotSim, task: str, players: list[tuple[float, float]]) -> bool:
        nav = self.maps[bot.map_id]
        taken = self._taken(bot)
        if task == "hunt":
            now, dead = self.clock(), self.dead.get(bot.map_id, {})
            busy = {o.target["key"] for o in self.bots.values() if isinstance(o.target, dict)}
            pool = []
            for m in nav.mobs:
                if dead.get(m["key"], 0) > now or m["key"] in busy:
                    continue
                mx, my = nav.center((m["tx"], m["ty"]))
                if any(math.hypot(mx - px, my - py) < SAFE_TILES * self.tile for px, py in players):
                    continue
                pool.append((math.hypot(mx - bot.x, my - bot.y), m))
            for _d, m in sorted(pool, key=lambda p: p[0])[:3]:
                goal = nav.near(m["tx"], m["ty"], taken)
                if goal and self._go(bot, nav, goal):
                    bot.target, bot.wait = m, self.rng.uniform(*FIGHT)
                    return True
            return False
        if task == "wander":
            tx, ty = bot.tile(self.tile)
            spots = [
                c
                for c in nav.cells
                if 3 <= abs(c[0] - tx) + abs(c[1] - ty) <= 10 and c not in taken
            ]
            if not spots or not self._go(bot, nav, self.rng.choice(spots)):
                return False
            bot.target, bot.wait = None, self.rng.uniform(*STAY["wander"])
            return True
        points = list(nav.points.get(task, []))
        self.rng.shuffle(points)
        for p in points[:3]:
            goal = nav.near(p[0], p[1], taken)
            if goal and self._go(bot, nav, goal):
                bot.target, bot.wait = p, self.rng.uniform(*STAY[task])
                return True
        return False

    def _choose(self, bot: BotSim, players):
        tasks, weights = zip(*PLANS[bot.activity], strict=True)
        for task in [*self.rng.choices(tasks, weights, k=3), "wander"]:
            if self._start(bot, task, players):
                bot.task = task
                return
        bot.wait = self.rng.uniform(*REST)

    def _target_xy(self, bot: BotSim) -> tuple[float, float] | None:
        nav = self.maps[bot.map_id]
        if isinstance(bot.target, dict):
            return nav.center((bot.target["tx"], bot.target["ty"]))
        if isinstance(bot.target, tuple):
            return nav.center(bot.target)
        return None

    @staticmethod
    def _face(dx: float, dy: float) -> str:
        return (
            ("right" if dx > 0 else "left") if abs(dx) > abs(dy) else ("down" if dy > 0 else "up")
        )

    def _finish(self, bot: BotSim, events: list):
        if bot.task == "hunt" and isinstance(bot.target, dict):
            key = bot.target["key"]
            self.dead.setdefault(bot.map_id, {})[key] = self.clock() + RESPAWN
            events.append(("kill", bot.map_id, key))
            bot.kills += 1
            if bot.kills % KILLS_PER_LEVEL == 0 and bot.level < LEVEL_CAP:
                bot.level += 1
                bot.gear = self.gear_for(bot.level)
                bot.dirty = True
        bot.task, bot.target, bot.fight, bot.path = "idle", None, None, []
        bot.wait = self.rng.uniform(*REST)

    # ----- mỗi nhịp -----
    def update(
        self, dt: float, players: dict[str, list[tuple[float, float]]] | None = None
    ) -> list[tuple]:
        """Cho mọi bot đi một nhịp.

        Trả các việc cần báo người cùng map: ("kill", map, quái), ("say", map, bot, câu).
        """
        players = players or {}
        events: list[tuple] = []
        now = self.clock()
        for m, keys in self.dead.items():
            self.dead[m] = {k: t for k, t in keys.items() if t > now}
        for bot in list(self.bots.values()):
            nav = self.maps.get(bot.map_id)
            if nav is None:
                continue
            bot.talk -= dt
            if bot.talk <= 0:
                bot.talk = self.rng.uniform(*TALK_EVERY)
                events.append(
                    ("say", bot.map_id, bot, self.rng.choice(SAY.get(bot.task, SAY["idle"])))
                )
            if bot.path:
                self._walk(bot, nav, dt)
                continue
            goal = self._target_xy(bot)
            if goal is not None:
                bot.facing = self._face(goal[0] - bot.x, goal[1] - bot.y)
                if bot.task == "hunt":
                    bot.fight = {
                        "name": bot.target["name"],
                        "x": round(goal[0]),
                        "y": round(goal[1]),
                    }
            bot.wait -= dt
            if bot.wait <= 0:
                if bot.task == "idle":
                    self._choose(bot, players.get(bot.map_id, []))
                else:
                    self._finish(bot, events)
        return events

    def _walk(self, bot: BotSim, nav: NavMap, dt: float):
        gx, gy = nav.center(bot.path[0])
        dx, dy = gx - bot.x, gy - bot.y
        dist = math.hypot(dx, dy)
        move = SPEED * self.tile * dt
        if dist <= move:
            bot.x, bot.y = gx, gy
            bot.path.pop(0)
        else:
            bot.x += dx / dist * move
            bot.y += dy / dist * move
        bot.facing = self._face(dx, dy)
