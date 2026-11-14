"""Kiểm thử chơi nhiều người: bộ điều phối, WebSocket, lưu đồng minh, tổ đội, thách đấu."""

import uuid

import pytest
from starlette.testclient import TestClient

from app.world import router as world_router
from app.world.hub import PARTY_MAX, PVP_GRACE, PVP_TIME, Hub, MemoryStore, clean_combat


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Inbox:
    """Kết nối giả: gom tin máy chủ gửi về."""

    def __init__(self):
        self.msgs: list[dict] = []

    async def __call__(self, msg):
        self.msgs.append(msg)

    def of(self, kind):
        return [m for m in self.msgs if m.get("t") == kind]

    def last(self, kind):
        found = self.of(kind)
        return found[-1] if found else None


async def _world(n=3):
    clock = Clock()
    hub = Hub(MemoryStore(), clock)
    boxes = {}
    for i in range(n):
        uid = f"u{i}"
        boxes[uid] = Inbox()
        await hub.connect(uid, f"Người {i}", boxes[uid])
    return hub, clock, boxes


async def _pos(hub, clock, uid, map_id="man1", x=100, y=100, **extra):
    clock.now += 1
    await hub.handle(
        uid, {"t": "pos", "map": map_id, "x": x, "y": y, "f": "left", "lv": 5, **extra}
    )


async def test_players_see_each_other_on_the_same_map():
    hub, clock, b = await _world()
    assert b["u0"].last("hello")["you"] == "u0"
    await _pos(hub, clock, "u1", x=300, gear={"vu_khi": "giao_dai", "la": "x"})
    await _pos(hub, clock, "u2", map_id="man2")
    await _pos(hub, clock, "u0")
    peers = b["u0"].last("peers")["list"]
    assert [p["id"] for p in peers] == ["u1"], "Chỉ thấy người cùng map"
    assert peers[0]["x"] == 300 and peers[0]["gear"] == {"vu_khi": "giao_dai"}, "Bỏ ô đồ lạ"
    clock.now += 60
    await _pos(hub, clock, "u0")
    assert b["u0"].last("peers")["list"] == [], "Lâu không gửi vị trí thì coi như rời map"
    assert hub.online() == {"man1": 2, "man2": 1}


async def test_bad_values_are_clamped():
    hub, clock, b = await _world(2)
    await _pos(hub, clock, "u1", x=1e12, y=float("nan"), lv=500, f="bay")
    await _pos(hub, clock, "u0")
    p = b["u0"].last("peers")["list"][0]
    assert p["x"] == 20000 and p["y"] == 0 and p["lv"] == 99 and p["f"] == "down"
    c = clean_combat({"hp": 1e9, "dmg": -5, "skills": {"a": 9, "b": 1, "c": 1, "d": 1, "e": 1}})
    assert c["hp"] == 4000 and c["dmg"] == 0.5 and len(c["skills"]) == 4 and c["skills"]["a"] == 3


async def test_preset_phrases_only_reach_the_same_map():
    hub, clock, b = await _world()
    await _pos(hub, clock, "u0")
    await _pos(hub, clock, "u1")
    await _pos(hub, clock, "u2", map_id="man3")
    await hub.handle("u0", {"t": "say", "k": 2})
    await hub.handle("u0", {"t": "say", "k": "lời tự do"})
    await hub.handle("u0", {"t": "say", "k": 99})
    assert len(b["u1"].of("say")) == 1 and b["u1"].last("say")["k"] == 2
    assert b["u2"].of("say") == [], "Không nghe được người ở map khác"


async def test_alliance_flow_is_saved():
    hub, clock, b = await _world()
    await hub.handle("u0", {"t": "invite", "kind": "ally", "to": "u1"})
    assert b["u1"].last("invite") == {
        "t": "invite",
        "kind": "ally",
        "from": "u0",
        "name": "Người 0",
        "lv": 1,
    }
    await hub.handle("u1", {"t": "answer", "kind": "ally", "from": "u0", "ok": True})
    assert frozenset(("u0", "u1")) in hub.store.alliances
    assert b["u0"].last("allies")["list"][0]["id"] == "u1"
    await hub.handle("u0", {"t": "invite", "kind": "ally", "to": "u1"})
    assert "đã là đồng minh" in b["u0"].last("notice")["text"]
    await hub.handle("u0", {"t": "ally_remove", "id": "u1"})
    assert not hub.store.alliances and b["u1"].last("allies")["list"] == []


async def test_invite_expires_and_refusal_is_reported():
    hub, clock, b = await _world()
    await hub.handle("u0", {"t": "invite", "kind": "ally", "to": "u1"})
    clock.now += 120
    await hub.handle("u1", {"t": "answer", "kind": "ally", "from": "u0", "ok": True})
    assert "hết hạn" in b["u1"].last("notice")["text"] and not hub.store.alliances
    await hub.handle("u0", {"t": "invite", "kind": "ally", "to": "u2"})
    await hub.handle("u2", {"t": "answer", "kind": "ally", "from": "u0", "ok": False})
    assert "từ chối" in b["u0"].last("notice")["text"]
    await hub.handle("u2", {"t": "answer", "kind": "ally", "from": "u9", "ok": True})
    assert "hết hạn" in b["u2"].last("notice")["text"], "Không trả lời được lời mời không có thật"


async def test_party_forms_shares_kills_and_disbands():
    hub, clock, b = await _world(PARTY_MAX + 2)
    await hub.handle("u0", {"t": "invite", "kind": "party", "to": "u1"})
    await hub.handle("u1", {"t": "answer", "kind": "party", "from": "u0", "ok": True})
    party = b["u1"].last("party")["party"]
    assert party["leader"] == "u0" and {m["id"] for m in party["members"]} == {"u0", "u1"}
    await hub.handle("u1", {"t": "invite", "kind": "party", "to": "u2"})
    assert "đội trưởng" in b["u1"].last("notice")["text"]
    for i in range(2, PARTY_MAX):
        await hub.handle("u0", {"t": "invite", "kind": "party", "to": f"u{i}"})
        await hub.handle(f"u{i}", {"t": "answer", "kind": "party", "from": "u0", "ok": True})
    await hub.handle("u0", {"t": "invite", "kind": "party", "to": f"u{PARTY_MAX}"})
    assert "đủ" in b["u0"].last("notice")["text"]
    # cùng đánh quái: đồng đội đứng gần được chia, đứng xa hoặc khác map thì không
    await _pos(hub, clock, "u0", x=100)
    await _pos(hub, clock, "u1", x=300)
    await _pos(hub, clock, "u2", x=5000)
    await _pos(hub, clock, "u3", map_id="man2")
    await hub.handle("u0", {"t": "kill", "mob": "Lính Tống", "exp": 40, "tiem": 10})
    assert b["u1"].last("share") == {
        "t": "share",
        "from": "Người 0",
        "mob": "Lính Tống",
        "exp": 20,
        "tiem": 5,
    }
    assert b["u2"].of("share") == [] and b["u3"].of("share") == []
    await _pos(hub, clock, "u0", x=100)
    peers = {p["id"]: p for p in b["u0"].last("peers")["list"]}
    assert peers["u1"]["party"] is True and peers["u2"]["party"] is True
    # rời đội: còn một người thì giải tán
    for uid in ("u3", "u2", "u1"):
        await hub.handle(uid, {"t": "party_leave"})
    assert b["u0"].last("party")["party"] is None and not hub.store.members


async def _duel(hub, clock, a, b):
    """a mời b thách đấu, b nhận lời: trả về mã phòng."""
    await hub.handle(a, {"t": "invite", "kind": "duel", "to": b})
    await hub.handle(b, {"t": "answer", "kind": "duel", "from": a, "ok": True})
    return hub.in_duel[a]


async def test_duel_puts_both_real_players_in_one_arena():
    hub, clock, b = await _world()
    await _pos(hub, clock, "u0", combat={"hp": 300, "dmg": 2, "skills": {"phong_lao": 2}})
    await _pos(hub, clock, "u1", map_id="man2")
    await hub.handle("u0", {"t": "invite", "kind": "duel", "to": "u1"})
    assert "cùng một map" in b["u0"].last("notice")["text"]
    await _pos(hub, clock, "u1", gear={"vu_khi": "kiem_thep"})
    room = await _duel(hub, clock, "u0", "u1")
    s0, s1 = b["u0"].last("pvp_start"), b["u1"].last("pvp_start")
    assert s0["room"] == s1["room"] == room
    assert (s0["side"], s1["side"]) == (0, 1), "Người mời đứng bên trái"
    assert s0["vs"]["id"] == "u1" and s0["vs"]["gear"] == {"vu_khi": "kiem_thep"}
    assert s1["vs"]["id"] == "u0" and s1["vs"]["combat"]["skills"] == {"phong_lao": 2}
    assert s0["time"] == PVP_TIME
    # trạng thái và động tác của một bên chuyển sang bên kia, giá trị lạ bị chặn
    state = {"x": 5000, "y": 300, "f": "bay", "hp": 999, "mhp": 300, "dg": 1}
    events = [{"k": "cast", "sid": "phong_lao"}, {"k": "hack"}, {"k": "atk", "a": 99}]
    await hub.handle("u0", {"t": "pvp", "room": room, "s": state, "ev": events})
    got = b["u1"].last("pvp")
    assert got["s"]["x"] == 2000 and got["s"]["f"] == "down" and got["s"]["hp"] == 300
    assert got["s"]["dg"] is True
    assert [e["k"] for e in got["ev"]] == ["cast", "atk"] and got["ev"][1]["a"] == 7
    await hub.handle("u0", {"t": "pvp", "room": room, "s": state})
    assert len(b["u1"].of("pvp")) == 1, "Gửi dồn dập quá nhanh thì bỏ bớt"
    # đòn trúng: máy bị đánh tự trừ máu, máy chủ chỉ chặn số liệu quá đáng
    await hub.handle("u1", {"t": "pvp_hit", "room": room, "dmg": 1e9, "knock": 500, "burn": 1})
    hit = b["u0"].last("pvp_hit")
    assert hit["dmg"] == 400 and hit["knock"] == 120 and hit["burn"] is True
    # người ngoài không chen vào phòng, không mời được người đang đấu
    await hub.handle("u2", {"t": "pvp_hit", "room": room, "dmg": 50})
    assert len(b["u0"].of("pvp_hit")) == 1
    await _pos(hub, clock, "u2")
    await hub.handle("u2", {"t": "invite", "kind": "duel", "to": "u0"})
    assert "trận thách đấu khác" in b["u2"].last("notice")["text"]
    # một bên gục: bên kia thắng, ghi kết quả cho cả hai
    await hub.handle("u1", {"t": "pvp_dead", "room": room})
    o0, o1 = b["u0"].last("pvp_over"), b["u1"].last("pvp_over")
    assert o0["win"] is True and o1["win"] is False and o0["why"] == o1["why"] == "ko"
    assert hub.store.duels == [("u0", "u1", True, "man1"), ("u1", "u0", False, "man1")]
    assert hub.in_duel == {} and hub.duels == {}
    clock.now += 1
    await hub.handle("u0", {"t": "pvp", "room": room, "s": state})
    assert len(b["u1"].of("pvp")) == 1, "Trận đã xong thì không chuyển tin nữa"


async def test_duel_ends_on_quit_leave_and_time():
    hub, clock, b = await _world(4)
    for uid in ("u0", "u1", "u2", "u3"):
        await _pos(hub, clock, uid)
    room = await _duel(hub, clock, "u0", "u1")
    await hub.handle("u0", {"t": "pvp_quit", "room": room})
    assert b["u1"].last("pvp_over")["win"] is True and b["u1"].last("pvp_over")["why"] == "quit"
    room = await _duel(hub, clock, "u0", "u1")
    await hub.disconnect("u1")
    assert b["u0"].last("pvp_over") == {
        "t": "pvp_over", "room": room, "win": True, "draw": False, "why": "left"
    }
    # hết giờ: ai còn nhiều máu hơn thì thắng
    room = await _duel(hub, clock, "u0", "u2")
    await hub.handle("u0", {"t": "pvp", "room": room, "s": {"hp": 30, "mhp": 100}})
    await hub.handle("u2", {"t": "pvp", "room": room, "s": {"hp": 80, "mhp": 200}})
    clock.now += PVP_TIME
    await hub.tick(0.2)
    assert room in hub.duels, "Còn thời gian dự phòng cho đếm ngược và mạng chậm"
    clock.now += PVP_GRACE
    await hub.tick(0.2)
    assert b["u2"].last("pvp_over")["win"] is True and b["u0"].last("pvp_over")["why"] == "time"
    # không ai gửi máu: hoà, cả hai đều không thắng
    await _duel(hub, clock, "u2", "u3")
    clock.now += PVP_TIME + PVP_GRACE
    await hub.tick(0.2)
    assert b["u3"].last("pvp_over")["draw"] is True and b["u3"].last("pvp_over")["win"] is False
    assert hub.store.duels[-2:] == [("u2", "u3", False, "man1"), ("u3", "u2", False, "man1")]


async def test_new_tab_during_a_duel_gives_the_win_to_the_other_side():
    hub, clock, b = await _world(2)
    await _pos(hub, clock, "u0")
    await _pos(hub, clock, "u1")
    await _duel(hub, clock, "u0", "u1")
    await hub.connect("u1", "Người 1", Inbox())
    assert b["u0"].last("pvp_over")["win"] is True and hub.in_duel == {}


async def test_entering_or_leaving_a_map_is_pushed_to_everyone_there():
    hub, clock, b = await _world()
    await _pos(hub, clock, "u0")
    await _pos(hub, clock, "u2", map_id="man2")
    before = len(b["u0"].of("peers"))
    await _pos(hub, clock, "u1")
    assert len(b["u0"].of("peers")) == before + 1, "Không phải chờ u0 gửi vị trí mới thấy người mới"
    assert [p["id"] for p in b["u0"].last("peers")["list"]] == ["u1"]
    await _pos(hub, clock, "u1", map_id="man2")
    assert b["u0"].last("peers")["list"] == [], "Người vừa đi sang map khác biến mất ngay"
    assert [p["id"] for p in b["u2"].last("peers")["list"]] == ["u1"]
    await hub.disconnect("u1")
    assert b["u2"].last("peers")["list"] == [], "Người rời game biến mất ngay"


async def test_a_new_tab_replaces_the_old_one():
    hub, clock, b = await _world(1)
    old = b["u0"]
    new = Inbox()
    await hub.connect("u0", "Người 0", new)
    assert "nơi khác" in old.last("notice")["text"]
    await hub.disconnect("u0", old)
    assert "u0" in hub.people, "Tab cũ đóng không được đá tab mới ra"
    await hub.disconnect("u0", new)
    assert "u0" not in hub.people


# ----- WebSocket thật, bộ điều phối dùng bản lưu trong bộ nhớ -----
class FakeUser:
    def __init__(self, uid, name):
        self.id, self.display_name = uid, name


def test_websocket_protocol(monkeypatch):
    from app.main import app

    hub = Hub(MemoryStore())
    users = {"tok-a": FakeUser(uuid.uuid4(), "An"), "tok-b": FakeUser(uuid.uuid4(), "Bình")}

    async def fake_user(token):
        return users.get(token)

    monkeypatch.setattr(world_router, "hub", hub)
    monkeypatch.setattr(world_router, "_user_from_token", fake_user)
    with TestClient(app) as c:
        with c.websocket_connect("/api/v1/world/ws") as bad:
            bad.send_json({"t": "auth", "token": "sai"})
            assert bad.receive_json() == {"t": "error", "code": "auth"}
        with (
            c.websocket_connect("/api/v1/world/ws") as a,
            c.websocket_connect("/api/v1/world/ws") as b,
        ):
            a.send_json({"t": "auth", "token": "tok-a"})
            b.send_json({"t": "auth", "token": "tok-b"})
            assert a.receive_json()["t"] == "hello" and b.receive_json()["t"] == "hello"
            for ws in (a, b):
                assert ws.receive_json()["t"] == "allies"
                assert ws.receive_json()["t"] == "party"
            b.send_json({"t": "pos", "map": "man1", "x": 50, "y": 60})
            assert b.receive_json()["t"] == "peers"
            a.send_text("không phải json")
            a.send_json({"t": "pos", "map": "man1", "x": 10, "y": 20})
            peers = a.receive_json()
            assert peers["t"] == "peers" and peers["list"][0]["name"] == "Bình"
            assert c.get("/api/v1/world/online").json() == {"man1": 2}


# ----- lưu vào PostgreSQL -----
async def test_db_store_round_trip():
    from app.db import SessionLocal, ping_db
    from app.models import User
    from app.world.router import DbStore

    try:
        await ping_db()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Không có PostgreSQL: {type(exc).__name__}")
    tag = uuid.uuid4().hex[:8]
    async with SessionLocal() as s:
        users = [
            User(
                email=f"mp{i}{tag}@test.vn",
                display_name=f"mp{i}{tag}",
                birth_year=1990,
                password_hash="x",
            )
            for i in range(3)
        ]
        s.add_all(users)
        await s.commit()
        ids = [str(u.id) for u in users]
    store = DbStore()
    try:
        await store.add_alliance(ids[1], ids[0])
        await store.add_alliance(ids[0], ids[1])  # trùng thì bỏ qua
        assert await store.allies(ids[0]) == {ids[1]} and await store.allies(ids[1]) == {ids[0]}
        await store.remove_alliance(ids[0], ids[1])
        assert await store.allies(ids[0]) == set()
        pid = await store.create_party(ids[0], ids[1])
        await store.join_party(pid, ids[2])
        found = await store.party_of(ids[2])
        assert found[0] == pid and found[1] == ids[0] and set(found[2]) == set(ids)
        await store.leave_party(ids[0])
        assert (await store.party_of(ids[1]))[1] == ids[1], (
            "Đội trưởng rời đi thì người khác lên thay"
        )
        for u in ids[1:]:
            await store.leave_party(u)
        assert await store.party_of(ids[1]) is None
        await store.record_duel(ids[0], ids[1], True, "man1")
        await store.record_duel(ids[0], "khong-phai-uuid", True, "man1")
    finally:
        async with SessionLocal() as s:
            for u in ids:
                obj = await s.get(User, uuid.UUID(u))
                await s.delete(obj)
            await s.commit()
