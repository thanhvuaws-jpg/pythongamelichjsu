"""Quyền đi lại của quản trị viên trong game và điểm được tặng. Người chơi thường không được có các quyền này."""

# isort: skip_file
from __future__ import annotations

import json

import pygame
import pytest
from test_playthrough import Bot, press_key  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import platform_io
from core.sprites import TILE
from core.state import BONUS_KEY, ROLE_KEY
from core.tilemap import WATER
from scenes.roadmap import RoadmapScene
from scenes.world import WorldScene


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    b = Bot()
    b.state.reset()
    yield b


def world(bot, level="man1", admin=True):
    bot.state.is_admin = admin
    ws = WorldScene(bot, level, "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    return ws


def water_tile(ws):
    return next((x, y) for y in range(ws.map.h) for x in range(ws.map.w) if ws.map.get(x, y) == WATER)


def test_player_has_no_admin_powers(bot):
    ws = world(bot, admin=False)
    press_key(bot, pygame.K_v)
    assert not ws.noclip, "Phím V không có tác dụng với người chơi thường"
    x, y = ws.x, ws.y
    rect = ws._minimap_rect()
    bot.click((rect.x + 10, rect.y + 10))
    assert ws.mode == "walk"
    assert abs(ws.x - x) < TILE * 2 and abs(ws.y - y) < TILE * 2, "Bấm bản đồ nhỏ không được dịch chuyển"
    assert not ws._portal_open(), "Chưa xong màn thì cổng còn đóng"


def test_admin_walks_through_walls_and_water(bot):
    ws = world(bot)
    tx, ty = water_tile(ws)
    px, py = (tx + 0.5) * TILE, (ty + 0.5) * TILE
    assert ws._hit(px, py), "Bình thường không đi xuống nước được"
    press_key(bot, pygame.K_v)
    assert ws.noclip and not ws._hit(px, py)
    assert ws._hit(-10, py), "Vẫn không được ra khỏi bản đồ"
    normal = bot.state.speed_mult() * 5.2 * TILE
    assert ws._speed() > normal
    ws.x, ws.y = px, py
    press_key(bot, pygame.K_v)
    assert not ws.noclip
    assert not ws._hit(ws.x, ws.y), "Tắt xuyên tường khi đang đứng trên nước thì phải được đưa lên chỗ đứng được"


def test_admin_click_moves_straight_when_noclip(bot):
    ws = world(bot)
    press_key(bot, pygame.K_v)
    bot.click((900, 300))
    assert ws.steer is not None and not ws.path


def test_admin_teleports_by_clicking_minimap(bot):
    ws = world(bot)
    zone = ws.world.zones["r_bai_coc"]
    rect = ws._minimap_rect()
    bot.click((rect.x + zone.cx * 2, rect.y + zone.cy * 2))
    assert abs(ws.x / TILE - zone.cx) < 2 and abs(ws.y / TILE - zone.cy) < 2
    assert not ws._hit(ws.x, ws.y), "Chưa bật xuyên tường thì phải đáp xuống chỗ đứng được"


def test_minimap_jump_to_a_blocked_tile_lands_nearby(bot):
    ws = world(bot)
    tx, ty = water_tile(ws)
    rect = ws._minimap_rect()
    ws._admin_jump((rect.x + tx * 2, rect.y + ty * 2))
    assert not ws._hit(ws.x, ws.y)


def test_admin_can_open_any_portal_except_the_ending(bot):
    assert world(bot, "man1")._portal_open()
    assert world(bot, "man2")._portal_open()
    assert not world(bot, "man3")._portal_open(), "Cổng cuối kết thúc game nên vẫn phải chơi xong"


def test_admin_roadmap_can_travel_anywhere_even_other_levels(bot):
    ws = world(bot)
    press_key(bot, pygame.K_j)
    sc = bot.scenes.top
    assert isinstance(sc, RoadmapScene)
    locked = next(i for i, n in enumerate(sc.nodes) if n["level"] == "man1" and n["relic"] and sc._status(n) == "locked")
    assert sc._can_travel(sc.nodes[locked])
    sc.sel = locked
    press_key(bot, pygame.K_RETURN)
    assert bot.scenes.top is ws, "Đi tới di tích chưa mở cùng màn"
    press_key(bot, pygame.K_j)
    sc = bot.scenes.top
    target = next(i for i, n in enumerate(sc.nodes) if n["level"] == "man3" and n["relic"])
    relic = sc.nodes[target]["relic"]
    sc.sel = target
    bot.tick(2)
    press_key(bot, pygame.K_RETURN)
    nxt = bot.scenes.top
    assert isinstance(nxt, WorldScene) and nxt.level_id == "man3", "Phải sang được màn khác"
    zone = nxt.world.zones[relic["id"]]
    assert abs(nxt.x - (zone.cx + 0.5) * TILE) < 1
    bot.tick(5)
    assert len(bot.scenes.stack) == 1, "Đổi màn không được để lại scene cũ"


def test_teleporting_does_not_finish_quests(bot):
    st = bot.state
    ws = world(bot)
    before = len(st.stamps)
    late = st.levels["man1"]["relics"][-1]
    ws._travel(late["id"])
    bot.tick(5)
    assert len(st.stamps) == before
    assert not st.relic_done(late["id"]), "Dịch chuyển chỉ là đi lại, không tự xong nhiệm vụ"


def test_bonus_from_server_adds_points_and_reports(bot, monkeypatch):
    st = bot.state
    store = {BONUS_KEY: json.dumps({"points": 500, "skill_points": 7}), ROLE_KEY: "player"}
    monkeypatch.setattr(platform_io, "read_key", store.get)
    ws = world(bot, admin=False)
    earned = st.skill_points_earned()
    assert st.refresh_external() == 500
    assert st.total_points == st.progress.points + 500
    assert st.skill_points_earned() == earned + 7
    assert st.refresh_external() == 0, "Đọc lại không báo tặng lần nữa"
    store[BONUS_KEY] = json.dumps({"points": 800, "skill_points": 7})
    ws.bonus_t = 0.0
    bot.toasts.items.clear()
    bot.tick(2)
    assert st.bonus_points == 800
    assert any("300" in item["msg"] for item in bot.toasts.items)


def test_role_comes_from_storage_and_bad_bonus_is_ignored(bot, monkeypatch):
    st = bot.state
    store = {ROLE_KEY: "admin", BONUS_KEY: "không phải json"}
    monkeypatch.setattr(platform_io, "read_key", store.get)
    assert st.refresh_external() == 0
    assert st.is_admin
    store[ROLE_KEY] = "player"
    st.refresh_external()
    assert not st.is_admin


def test_bonus_is_not_written_into_the_save(bot):
    st = bot.state
    st.bonus_points, st.bonus_skill_points, st.is_admin = 99, 9, True
    saved = st.to_dict()
    assert "bonus_points" not in saved and "is_admin" not in saved
    assert saved["points"] == st.progress.points
