"""Kiểm thử Bảng vàng ở map đầu: tấm bảng đứng gần chỗ xuất phát, mở ra hai bảng 20 tên; bản lưu ghi sức mạnh cho máy chủ."""

# isort: skip_file
from __future__ import annotations

import json

import pygame
import pytest
from test_playthrough import Bot  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import platform_io
from core.sprites import TILE
from scenes import honor
from scenes.honor import HonorScene
from scenes.mobs import _reachable
from scenes.world import WorldScene


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    return Bot()


def _board(bot, level="man1"):
    bot.state.reset()
    ws = WorldScene(bot, level, "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    return ws, next((a for a in ws.actors if a.kind == "honor"), None)


def test_board_stands_near_spawn_on_the_first_map_only(bot):
    ws, board = _board(bot)
    assert board is not None
    tile = (int(board.x // TILE), int(board.y // TILE))
    sx, sy = ws.world.spawn
    assert abs(tile[0] - sx) <= 8 and abs(tile[1] - sy) <= 5, "Đứng gần chỗ xuất phát cho ai cũng thấy"
    assert tile in _reachable(ws.world)
    assert _board(bot, "man2")[1] is None and _board(bot, "man3")[1] is None


def test_board_opens_the_top_twenty(bot, monkeypatch):
    rows = [{"rank": i + 1, "name": f"Người {i + 1}", "value": 900 - i, "level": 30 - i} for i in range(25)]
    store = {honor.HONOR_KEY: json.dumps({"points": rows, "power": rows[:3] + [{"bad": 1}, "lạ"]})}
    monkeypatch.setattr(platform_io, "read_key", store.get)
    ws, board = _board(bot)
    ws.x, ws.y = board.x, board.y + TILE * 0.5
    bot.tick()
    assert ws.nearest() is board
    ws.interact(board)
    sc = bot.scenes.top
    assert isinstance(sc, HonorScene)
    assert len(sc.data["points"]) == honor.TOP and len(sc.data["power"]) == 3, "Tối đa 20 tên, bỏ dòng hỏng"
    bot.tick(3)
    sc.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
    assert bot.scenes.top is ws


def test_board_without_server_data_still_opens(bot, monkeypatch):
    monkeypatch.setattr(platform_io, "read_key", lambda key: "{hỏng")
    assert honor.load() == {"points": [], "power": []}
    bot.scenes.reset(HonorScene(bot))
    bot.tick(2)


def test_save_carries_power_for_the_server(bot):
    st = bot.state
    st.reset()
    assert st.to_dict()["rpg"]["power"] == st.power_rating() > 0
