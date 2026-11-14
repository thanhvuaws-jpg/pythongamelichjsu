"""Người chơi máy chạy trên máy chủ, nhìn từ phía game: hiện như người chơi khác (không có chữ gì khác người thật), hạ quái
thì con quái đó ngã trên máy mình, mình hạ quái thì người khác cũng thấy; bản đồ máy chủ dùng khớp với bản đồ của game."""

# isort: skip_file
from __future__ import annotations

import importlib.util
import json
import random
import sys
from pathlib import Path

import pygame
import pytest
from test_multiplayer import HubPipe, Ticking  # nạp trước: thêm đường dẫn game và backend vào sys.path
from test_playthrough import Bot, press_key, win_fight
from core import net, platform_io
from core.sprites import TILE
from scenes.mobs import mob_key
from scenes.world import WorldScene

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.world.bots import DATA_FILE, BotWorld  # noqa: E402
from app.world.hub import Hub, MemoryStore  # noqa: E402


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    b = Bot()
    yield b
    net.use(net.Net(None))


def _online(bot, hub):
    me = net.Net(HubPipe(hub, "a", "An"))
    net.use(me)
    bot.state.reset()
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick(12)  # vài lần gửi vị trí, nhận danh sách người cùng map
    return me, ws


def test_server_bots_look_like_any_other_player(bot):
    hub = Hub(MemoryStore(), Ticking(), bots=BotWorld(rng=random.Random(3)))
    hub.bots.add("bot-1", "Minh Khang", "man1", "train", 9)
    me, ws = _online(bot, hub)
    av = ws.mp.avatars.get("bot-1")
    assert av is not None and av.data["name"] == "Minh Khang" and av.data["lv"] == 9
    bot.tick(3)  # vẽ tên như mọi người chơi khác


def test_bot_kills_reach_my_screen_and_my_kills_reach_the_server(bot):
    hub = Hub(MemoryStore(), Ticking(), bots=BotWorld(rng=random.Random(3)))
    me, ws = _online(bot, hub)
    mob = next(m for m in ws.mobs.mobs if m.kind == "mob" and not m.data.get("water"))
    other = net.Net(HubPipe(hub, "b", "Bình"))
    other.send({"t": "pos", "map": "man1", "x": 50, "y": 50})
    other.send({"t": "mob_kill", "mob": mob_key(mob)})
    bot.tick(3)
    assert not mob.alive, "Người khác (hay bot) hạ quái thì quái ngã trên máy mình"
    ws.mobs.update(999)
    target = next(m for m in ws.mobs.mobs if m.kind == "mob" and m.alive and not m.data.get("water"))
    ws.x, ws.y = target.x, target.y + TILE * 0.5
    bot.tick()
    press_key(bot, pygame.K_f)
    win_fight(bot, bot.scenes.top)
    other.poll()
    assert hub.bots.dead["man1"].get(mob_key(target)), "Mình hạ quái thì máy chủ biết, bot không nhắm con đó nữa"


def test_botmaps_are_up_to_date():
    """Bản đồ cho bot phải khớp bản đồ game đang dựng; lệch thì chạy lại tools/export_botmaps.py."""
    spec = importlib.util.spec_from_file_location("export_botmaps", ROOT / "tools" / "export_botmaps.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    fresh = tool.build()
    saved = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    assert json.loads(json.dumps(fresh)) == saved, "Bản đồ đã đổi: chạy tools/export_botmaps.py"

