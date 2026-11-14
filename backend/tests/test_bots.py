"""Kiểm thử người chơi máy chạy trên máy chủ.

Đi đúng ô, tự cày quái và lên cấp, làm nhiệm vụ, không cướp quái của người chơi, hiện như người
chơi khác, quản trị viên thêm và xoá được.
"""

import random
import uuid

import httpx
import pytest
from sqlalchemy import select

from app.db import SessionLocal, engine, ping_db
from app.main import app
from app.models import BotPlayer, Role, User
from app.world import bots as botmod
from app.world import router as world_router
from app.world.bots import BotWorld
from app.world.hub import Hub, MemoryStore

PASSWORD = "mat-khau-dai-du-roi"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Inbox:
    def __init__(self):
        self.msgs: list[dict] = []

    async def __call__(self, msg):
        self.msgs.append(msg)

    def of(self, kind):
        return [m for m in self.msgs if m.get("t") == kind]


def _world(clock):
    return BotWorld(rng=random.Random(7), clock=clock)


def _run(world, clock, seconds, players=None, dt=0.2):
    events = []
    for _ in range(int(seconds / dt)):
        clock.now += dt
        events += world.update(dt, players)
    return events


def test_maps_were_exported_for_every_map():
    world = _world(Clock())
    assert {"man1", "man2", "man3", "f_dong_khe", "f_le_hoa"} <= set(world.maps)
    nav = world.maps["man1"]
    assert nav.cells and all(nav.ok(*c) for c in nav.cells[:50])
    assert nav.points["quest"] and nav.points["shop"] and nav.mobs


def test_training_bot_hunts_levels_up_and_stays_on_walkable_tiles():
    clock = Clock()
    world = _world(clock)
    bot = world.add("b1", "Minh Khang", "man1", "train", level=5)
    nav = world.maps["man1"]
    kills, fought = [], False
    for _ in range(int(240 / 0.2)):
        clock.now += 0.2
        events = world.update(0.2)
        kills += [e for e in events if e[0] == "kill"]
        fought = fought or bot.fight is not None
        assert nav.ok(*bot.tile(world.tile)), "Không đi xuyên tường, không xuống nước"
    assert fought and len(kills) >= botmod.KILLS_PER_LEVEL, "Tự đi đánh quái"
    assert bot.level > 5 and bot.dirty, "Hạ đủ quái thì lên cấp"
    assert all(k[2] in {m["key"] for m in nav.mobs} for k in kills)


def test_quest_bot_visits_places_and_never_fights():
    clock = Clock()
    world = _world(clock)
    bot = world.add("b2", "Gia Hân", "man2", "quest")
    places = set()
    for _ in range(int(120 / 0.2)):
        clock.now += 0.2
        events = world.update(0.2)
        assert not [e for e in events if e[0] == "kill"] and bot.fight is None
        if isinstance(bot.target, tuple) and not bot.path:
            places.add(bot.target)
    assert places, "Đi tới chỗ làm nhiệm vụ, lò rèn, chỗ câu cá"


def test_bots_leave_mobs_near_players_alone():
    clock = Clock()
    world = _world(clock)
    nav = world.maps["man1"]
    players = [nav.center((m["tx"], m["ty"])) for m in nav.mobs]  # có người đứng cạnh mọi con quái
    world.add("b3", "Bảo An", "man1", "train")
    events = _run(world, clock, 60, {"man1": players})
    assert not [e for e in events if e[0] == "kill"]


async def test_bots_show_up_as_players_and_talk_and_kill_for_the_map():
    clock = Clock()
    hub = Hub(MemoryStore(), clock, bots=_world(clock))
    bot = hub.bots.add("bot-1", "Quang Huy", "man1", "train", 8)
    me, far = Inbox(), Inbox()
    await hub.connect("u0", "An", me)
    await hub.connect("u1", "Bình", far)
    clock.now += 1
    await hub.handle("u0", {"t": "pos", "map": "man1", "x": 10, "y": 10})
    await hub.handle("u1", {"t": "pos", "map": "man2", "x": 10, "y": 10})
    seen = me.of("peers")[-1]["list"]
    assert [p["name"] for p in seen] == ["Quang Huy"] and seen[0]["lv"] == 8 and seen[0]["gear"]
    assert not far.of("peers")[-1]["list"], "Map khác không thấy"
    for _ in range(int(180 / 0.2)):
        clock.now += 0.2
        hub.people["u0"].seen = clock.now
        await hub.tick(0.2)
    assert me.of("mob_down") and me.of("say"), "Bot hạ quái, nói câu: người cùng map đều thấy"
    assert not far.of("mob_down")
    assert all(0 <= m["k"] < 12 and m["k"] != 8 for m in me.of("say")), (
        "Chỉ nói câu có sẵn, không rủ thách đấu"
    )
    await hub.handle("u0", {"t": "invite", "kind": "party", "to": "bot-1"})
    assert "đang bận" in me.of("notice")[-1]["text"]
    assert bot.level >= 8


async def test_player_kill_reaches_the_map_and_bots_skip_that_mob():
    clock = Clock()
    hub = Hub(MemoryStore(), clock, bots=_world(clock))
    a, b = Inbox(), Inbox()
    await hub.connect("u0", "An", a)
    await hub.connect("u1", "Bình", b)
    for uid in ("u0", "u1"):
        clock.now += 1
        await hub.handle(uid, {"t": "pos", "map": "man1", "x": 10, "y": 10})
    key = hub.bots.maps["man1"].mobs[0]["key"]
    await hub.handle("u0", {"t": "mob_kill", "mob": key})
    assert b.of("mob_down")[-1]["mob"] == key and not a.of("mob_down")
    assert hub.bots.dead["man1"][key] > clock.now


async def _account(c, email, role=None):
    r = await c.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "display_name": email.split("@")[0],
            "birth_year": 1990,
            "accept_policy": True,
        },
    )
    assert r.status_code == 201, r.text
    if role:
        async with SessionLocal() as s:
            row = await s.scalar(select(User).where(User.email == email))
            row.role = role
            await s.commit()
    r = await c.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_admin_adds_lists_and_removes_bots(monkeypatch):
    try:
        await ping_db()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Không có PostgreSQL: {type(exc).__name__}")
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "skip_email_verification", True)
    monkeypatch.setattr(world_router, "hub", Hub(MemoryStore(), bots=BotWorld()))
    tag = uuid.uuid4().hex[:8]
    admin_email, player_email = f"qtbot{tag}@test.vn", f"choibot{tag}@test.vn"
    made: list[str] = []
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        admin = await _account(c, admin_email, Role.admin)
        player = await _account(c, player_email)
        assert (await c.get("/api/v1/world/bots", headers=player)).status_code == 403
        r = await c.post(
            "/api/v1/world/bots",
            json={"map_id": "man1", "activity": "train", "count": 3, "level": 6},
            headers=admin,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        mine = [b for b in body["bots"] if b["map_id"] == "man1"]
        made = [b["id"] for b in mine]
        assert len(mine) == 3 and all(b["level"] == 6 and b["activity"] == "train" for b in mine)
        assert len({b["name"] for b in mine}) == 3 and body["maps"] and body["activities"]
        bad = await c.post(
            "/api/v1/world/bots", json={"map_id": "khong_co", "count": 1}, headers=admin
        )
        assert bad.status_code == 422
        r = await c.delete(f"/api/v1/world/bots/{mine[0]['id']}", headers=admin)
        assert len(r.json()["bots"]) == 2
        async with SessionLocal() as s:
            ids = [uuid.UUID(i) for i in made]
            rows = (await s.scalars(select(BotPlayer).where(BotPlayer.id.in_(ids)))).all()
            assert len(rows) == 2, "Bot lưu trong cơ sở dữ liệu, khởi động lại không mất"
        for bot_id in made[1:]:
            await c.delete(f"/api/v1/world/bots/{bot_id}", headers=admin)
    async with SessionLocal() as s:
        for row in await s.scalars(select(User).where(User.email.in_((admin_email, player_email)))):
            await s.delete(row)
        await s.commit()
    await engine.dispose()
