"""Kiểm thử câu cá: người câu cá đứng sát nước, mua cần câu, thả câu, kéo cá, nướng cá, ăn cá nướng giữa trận."""

# isort: skip_file
from __future__ import annotations

import json
from pathlib import Path

import pygame
import pytest
from test_playthrough import Bot, play_story, press_key  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import platform_io, rpg
from core.sprites import TILE
from core.tilemap import WATER
from scenes import fishing
from scenes.fight import FightScene
from scenes.mobs import _reachable
from scenes.world import WorldScene

DUMMY = {"name": "Bù nhìn", "char": "Villager3", "hp": 500, "power": 0.0, "speed": 0, "aggro": 0.0}


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    return Bot()


def _world(bot, level="man1"):
    bot.state.reset()
    ws = WorldScene(bot, level, "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    return ws


@pytest.mark.parametrize("level", ["man1", "man2", "man3"])
def test_fisher_stands_at_the_water_with_a_fire(bot, level):
    ws = _world(bot, level)
    fisher = next(a for a in ws.actors if a.kind == "fisher")
    tile = (int(fisher.x // TILE), int(fisher.y // TILE))
    assert tile in _reachable(ws.world)
    assert any(ws.map.get(tile[0] + dx, tile[1] + dy) == WATER for dx, dy in fishing.DIRS.values()), "Người câu cá đứng sát mép nước"
    fire = next(a for a in ws.actors if a.kind == "bep")
    assert abs(fire.x - fisher.x) <= TILE * 1.5 and abs(fire.y - fisher.y) <= TILE * 1.5
    assert ws.fishing.swimmers, "Có cá bơi dưới nước gần chỗ câu"


def test_fisher_lines_cite_known_sources():
    cites = json.loads((Path(__file__).resolve().parent.parent / "content" / "sources.json").read_text(encoding="utf-8"))["citations"]
    for spec in fishing.FISHERS.values():
        assert spec["lines"]
        for line in spec["lines"]:
            assert line.get("cite"), line["text"]
            assert all(c in cites for c in line["cite"]), line["cite"]


def test_buy_rod_fish_cook_and_eat(bot):
    ws = _world(bot)
    st = bot.state
    st.quan = 100
    fisher = next(a for a in ws.actors if a.kind == "fisher")
    fire = next(a for a in ws.actors if a.kind == "bep")
    # chưa có cần thì bấm C chỉ được nhắc
    press_key(bot, pygame.K_c)
    assert not ws.fishing.active
    # nói chuyện: nghe kể, rồi được mời mua; nói lần nữa thì mua
    ws.x, ws.y = fisher.x, fisher.y
    ws.interact(fisher)
    play_story(bot)
    assert bot.scenes.top is ws and not st.has_rod() and ws.fishing.offer_t > 0
    ws.interact(fisher)
    assert st.has_rod() and st.quan == 100 - rpg.ITEMS[rpg.ROD]["price"]
    # đứng chỗ người câu cá (sát nước) mà thả câu
    press_key(bot, pygame.K_c)
    assert ws.fishing.mode == "wait" and ws.fishing.bob
    bx, by = ws.fishing.bob
    assert ws.map.get(int(bx // TILE), int(by // TILE)) == WATER, "Phao rơi xuống nước"
    # giật sớm thì cá chạy
    press_key(bot, pygame.K_c)
    assert not ws.fishing.active and st.fish_count() == 0
    # chờ phao chìm rồi kéo lên
    ws.fishing.rng.random = lambda: 0.99  # không vớt phải rong
    press_key(bot, pygame.K_c)
    ws.fishing.t = 0.01
    bot.tick(2)
    assert ws.fishing.mode == "bite"
    press_key(bot, pygame.K_c)
    assert st.fish_count() == 1 and not ws.fishing.active
    # để phao chìm quá lâu thì cá nhả mồi
    press_key(bot, pygame.K_c)
    ws.fishing.t = 0.01
    bot.tick(2)
    ws.fishing.t = 0.01
    bot.tick(2)
    assert not ws.fishing.active and st.fish_count() == 1
    # nướng ở bếp lửa
    ws.interact(fire)
    assert st.fish_count() == 0 and st.grilled == 1
    # ăn giữa trận
    fight = FightScene(bot, [dict(DUMMY)], "Thử")
    bot.scenes.push(fight)
    bot.tick(int(30 * 3.5))
    fight.player.hp = fight.player.max_hp * 0.3
    press_key(bot, pygame.K_e)
    assert st.grilled == 0 and fight.player.hp == pytest.approx(fight.player.max_hp * (0.3 + rpg.GRILL_HEAL))


def test_walking_away_reels_in_and_shop_does_not_sell_fish(bot):
    ws = _world(bot)
    st = bot.state
    st.inventory.append(rpg.ROD)
    st.gear["cong_cu"] = rpg.ROD
    fisher = next(a for a in ws.actors if a.kind == "fisher")
    ws.x, ws.y = fisher.x, fisher.y
    press_key(bot, pygame.K_c)
    assert ws.fishing.active
    ws.moving = True
    ws.fishing.update(0.1)
    assert not ws.fishing.active, "Đi chỗ khác thì thu cần"
    assert st.buy("ca_nuong") and st.buy("ca_tuoi"), "Cá tươi, cá nướng không bán"
    for _ in range(rpg.MAX_FISH + 3):
        st.catch("ca_ro")
    assert st.fish_count() == rpg.MAX_FISH
    assert st.cook() == rpg.MAX_GRILL and st.grilled == rpg.MAX_GRILL and st.fish_count() == rpg.MAX_FISH - rpg.MAX_GRILL


def test_fish_survive_save_and_load(bot):
    st = bot.state
    st.reset()
    st.inventory.append(rpg.ROD)
    st.gear["cong_cu"] = rpg.ROD
    st.catch("ca_chep")
    st.catch("ca_tram")
    st.cook()
    st.catch("ca_ro")
    data = st.to_dict()
    st.reset()
    st.from_dict(json.loads(json.dumps(data)))
    assert st.has_rod() and st.grilled == 2 and st.fish == {"ca_ro": 1}
