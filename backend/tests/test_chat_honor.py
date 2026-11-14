"""Kiểm thử chat trong game (lọc chữ, kênh, chống spam) và Bảng vàng (top điểm, top sức mạnh)."""

import uuid

import httpx
import pytest
from sqlalchemy import select

from app.db import SessionLocal, engine, ping_db
from app.game.router import HONOR_N, rank_power
from app.main import app
from app.models import User
from app.world import chat
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


async def _world(n=3):
    clock = Clock()
    hub = Hub(MemoryStore(), clock)
    boxes = {}
    for i in range(n):
        uid = f"u{i}"
        boxes[uid] = Inbox()
        await hub.connect(uid, f"Người {i}", boxes[uid])
    return hub, clock, boxes


async def _go(hub, clock, uid, map_id):
    clock.now += 1
    await hub.handle(uid, {"t": "pos", "map": map_id, "x": 100, "y": 100})


# ----- lọc chữ -----
def test_clean_trims_and_strips_control_characters():
    assert chat.clean("  Xin​   chào\n\tcác bạn  ") == "Xin chào các bạn"
    assert chat.clean("a" * 500) == "a" * chat.MAX_LEN
    assert chat.clean(None) == "" and chat.clean(123) == ""


def test_censor_hides_swear_words_but_not_ordinary_ones():
    assert chat.censor("đm thằng này") == "** thằng này"
    assert chat.censor("ĐM vcl luôn") == "** *** luôn"
    assert chat.censor("Dit me may") == "****** may"
    for ok in (
        "Xin chào các bạn",
        "cac ban oi",
        "đeo kính vào",
        "Cẩn thận quái mạnh",
        "Thắng rồi!!!",
        "cấp 12 rồi",
    ):
        assert chat.censor(ok) == ok, ok


# ----- kênh chat -----
async def test_map_chat_reaches_only_the_same_map():
    hub, clock, b = await _world()
    await _go(hub, clock, "u0", "man1")
    await _go(hub, clock, "u1", "man1")
    await _go(hub, clock, "u2", "man2")
    await hub.handle("u0", {"t": "chat", "ch": "map", "text": "  Cùng đánh quái không?  "})
    got = b["u1"].of("chat")
    assert (
        got
        and got[-1]["text"] == "Cùng đánh quái không?"
        and got[-1]["name"] == "Người 0"
        and got[-1]["ch"] == "map"
    )
    assert b["u0"].of("chat"), "Người gửi cũng thấy tin của mình"
    assert not b["u2"].of("chat"), "Map khác không nghe thấy"


async def test_world_chat_reaches_everyone_and_newcomers_see_recent_lines():
    hub, clock, b = await _world()
    await _go(hub, clock, "u0", "man1")
    await _go(hub, clock, "u2", "man3")
    await hub.handle(
        "u0", {"t": "chat", "ch": "world", "text": "Ai lập tổ đội đánh Đông Khê không? vcl"}
    )
    for uid in ("u0", "u1", "u2"):
        msg = b[uid].of("chat")[-1]
        assert msg["ch"] == "world" and msg["text"].endswith("không? ***"), uid
    late = Inbox()
    await hub.connect("u9", "Người mới", late)
    recent = late.of("chat_recent")
    assert recent and recent[0]["list"][-1]["from"] == "u0"


async def test_chat_is_rate_limited_and_bad_messages_are_dropped():
    hub, clock, b = await _world(2)
    await _go(hub, clock, "u0", "man1")
    await _go(hub, clock, "u1", "man1")
    await hub.handle("u0", {"t": "chat", "ch": "world", "text": "một"})
    await hub.handle("u0", {"t": "chat", "ch": "world", "text": "hai"})
    assert [m["text"] for m in b["u1"].of("chat")] == ["một"]
    assert "nhanh quá" in b["u0"].of("notice")[-1]["text"]
    clock.now += chat.GAP["world"]
    await hub.handle("u0", {"t": "chat", "ch": "world", "text": "hai"})
    for bad in (
        {"t": "chat", "ch": "riêng", "text": "x"},
        {"t": "chat", "ch": "map", "text": "   "},
        {"t": "chat", "ch": "map", "text": ["x"]},
    ):
        clock.now += 5
        await hub.handle("u0", bad)
    assert [m["text"] for m in b["u1"].of("chat")] == ["một", "hai"]


# ----- Bảng vàng -----
def test_rank_power_sorts_ties_and_ignores_junk():
    rows = [
        ("An", {"power": 900, "level": 10}),
        ("Bình", {"power": 1200, "level": 12}),
        ("Chi", {"power": 900, "level": 11}),
        ("Dũng", {"power": "lạ"}),
        ("Em", None),
        ("Giang", {"power": -5}),
        ("Hà", {"power": 10**9, "level": 40}),
    ]
    out = rank_power(rows)
    assert [r["name"] for r in out] == ["Hà", "Bình", "Chi", "An"]
    assert out[0]["value"] == 1_000_000, "Số quá lớn bị kẹp lại"
    assert [r["rank"] for r in out] == [1, 2, 3, 3], "Cùng sức mạnh thì cùng hạng"
    many = rank_power([(f"P{i}", {"power": i + 1}) for i in range(40)])
    assert len(many) == HONOR_N


async def test_honor_api_lists_points_and_power(monkeypatch):
    try:
        await ping_db()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Không có PostgreSQL: {type(exc).__name__}")
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "skip_email_verification", True)
    tag = uuid.uuid4().hex[:8]
    emails = [f"vang{i}{tag}@test.vn" for i in range(2)]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        heads = []
        for email in emails:
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
            r = await c.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
            heads.append({"Authorization": f"Bearer {r.json()['access_token']}"})
        assert (await c.get("/api/v1/game/honor")).status_code == 401, "Phải đăng nhập mới xem được"
        strong = {
            "solved": ["q_dl_1"],
            "attempts": {"q_dl_1": 1},
            "rpg": {"level": 40, "power": 999_000},
        }
        await c.put("/api/v1/game/save", json={"data": strong}, headers=heads[0])
        await c.put(
            "/api/v1/game/save",
            json={"data": {"rpg": {"level": 39, "power": 998_000}}},
            headers=heads[1],
        )
        r = await c.get("/api/v1/game/honor", headers=heads[1])
        assert r.status_code == 200
        body = r.json()
        names = [e["name"] for e in body["power"]]
        a, b = emails[0].split("@")[0], emails[1].split("@")[0]
        assert a in names and b in names and names.index(a) < names.index(b)
        assert len(body["points"]) <= HONOR_N and len(body["power"]) <= HONOR_N
        assert all(set(e) == {"rank", "name", "value", "level"} for e in body["power"]), (
            "Chỉ có tên hiển thị, không lộ email"
        )
    async with SessionLocal() as session:
        for row in await session.scalars(select(User).where(User.email.in_(emails))):
            await session.delete(row)
        await session.commit()
    await engine.dispose()


async def test_fight_state_reaches_people_on_the_same_map():
    hub, clock, b = await _world(2)
    await _go(hub, clock, "u1", "man1")
    clock.now += 1
    fight = {"name": "Lính Tống" * 9, "x": 320.4, "y": "lạ"}
    await hub.handle("u0", {"t": "pos", "map": "man1", "x": 100, "y": 100, "fight": fight})
    await _go(hub, clock, "u1", "man1")
    seen = next(p for p in b["u1"].of("peers")[-1]["list"] if p["id"] == "u0")
    assert seen["fight"] == {"name": ("Lính Tống" * 9)[:40], "x": 320, "y": 0}
    clock.now += 1
    await hub.handle("u0", {"t": "pos", "map": "man1", "x": 100, "y": 100})
    await _go(hub, clock, "u1", "man1")
    seen = next(p for p in b["u1"].of("peers")[-1]["list"] if p["id"] == "u0")
    assert seen["fight"] is None, "Không gửi kèm nữa là đã đánh xong"

