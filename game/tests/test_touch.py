"""Chơi bằng cảm ứng (điện thoại): những việc trước chỉ làm được bằng phím nay có nút chạm, trận đánh chạm sân để đi."""

# isort: skip_file
from __future__ import annotations

import random

import pygame
import pytest
from test_playthrough import Bot  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import platform_io, rpg
from core.sprites import TILE
from scenes import fishing
from scenes.fight import BTN_ATTACK, FIELD, FightScene
from scenes.world import WorldScene


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    return Bot()


def _world(bot, touch=True):
    bot.state.reset()
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.scenes.touch = touch
    bot.tick(2)
    return ws


def _labels(bot, ws):
    bot.tick()
    return [b.label for b in ws.touch_btns]


def _tap(bot, ws, label):
    btn = next(b for b in ws.touch_btns if b.label == label)
    bot.click(btn.rect.center)


def test_mouse_and_keyboard_players_see_no_touch_buttons(bot):
    ws = _world(bot, touch=False)
    bot.tick(3)
    assert not platform_io.is_touch_device(), "Chạy trên máy tính thì không coi là điện thoại"
    assert ws.touch_btns == []


def test_first_touch_switches_to_touch_mode(bot):
    ws = _world(bot, touch=False)
    bot.scenes.handle(pygame.event.Event(pygame.FINGERDOWN, x=0.5, y=0.5, dx=0.0, dy=0.0, finger_id=0, touch_id=0, pressure=1.0))
    assert bot.scenes.touch
    assert _labels(bot, ws) is not None


def test_horse_and_boat_without_a_keyboard(bot):
    ws = _world(bot)
    bot.state.level = rpg.HORSE_LEVEL
    assert "Gọi ngựa" in _labels(bot, ws)
    _tap(bot, ws, "Gọi ngựa")
    assert ws.mode == "horse"
    assert "Xuống ngựa" in _labels(bot, ws)
    _tap(bot, ws, "Xuống ngựa")
    assert ws.mode == "walk"
    fisher = next(a for a in ws.actors if a.kind == "fisher")
    ws.board(fisher)
    assert ws.mode == "boat" and _labels(bot, ws) == ["Lên bờ"], "Lên thuyền rồi phải có nút lên bờ"
    _tap(bot, ws, "Lên bờ")
    assert ws.mode == "walk" and not ws.path, "Bấm nút không làm nhân vật đi tới chỗ nút"


def test_fishing_by_touch(bot, monkeypatch):
    monkeypatch.setattr(fishing, "JUNK", 0.0)
    ws = _world(bot)
    st = bot.state
    st.inventory.append(rpg.ROD)
    st.gear["cong_cu"] = rpg.ROD
    fisher = next(a for a in ws.actors if a.kind == "fisher")
    ws.x, ws.y = fisher.x, fisher.y
    labels = _labels(bot, ws)
    assert labels[0] == fisher.label and "Thả câu" in labels, "Nút to cho việc ở ngay cạnh, cùng nút thả câu"
    facing = ws.facing
    bot.tick(3)
    assert ws.facing == facing, "Xem có câu được không thì không được xoay người"
    _tap(bot, ws, "Thả câu")
    assert ws.fishing.mode == "wait" and _labels(bot, ws) == ["Thu cần"]
    ws.fishing.t = 0.01
    assert _labels(bot, ws) == ["Kéo cần!"]
    _tap(bot, ws, "Kéo cần!")
    assert not ws.fishing.active and st.fish_count() == 1


def test_road_challenger_answered_by_touch(bot):
    ws = _world(bot)
    bot.state.level = 4
    random.seed(3)
    ws.mobs.duel_t = 0.01
    bot.tick(2)
    d = ws.mobs.duel
    d["actor"].x, d["actor"].y = ws.x + 20, ws.y
    bot.tick()
    assert d["state"] == "ask" and _labels(bot, ws) == ["Nhận lời", "Từ chối"]
    _tap(bot, ws, "Từ chối")
    assert d["state"] == "leave"


def test_big_button_talks_to_whoever_is_next_to_you(bot, monkeypatch):
    ws = _world(bot)
    mentor = next(a for a in ws.actors if a.kind == "mentor")
    ws.x, ws.y = mentor.x, mentor.y + TILE * 0.6
    talked = []
    monkeypatch.setattr(ws, "interact", talked.append)
    label = _labels(bot, ws)[0]
    assert label == mentor.label
    _tap(bot, ws, label)
    assert talked == [mentor], "Bấm nút là nói chuyện với người đứng cạnh, như phím E"


def test_fight_on_touch_moves_on_the_field_and_attacks_with_the_button(bot):
    bot.state.reset()
    bot.scenes.touch = True
    fight = FightScene(bot, [{"name": "Bù nhìn", "char": "Villager", "hp": 500}], "Thử")
    bot.scenes.reset(fight)
    fight.intro = 0
    p = fight.player
    bot.scenes.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(FIELD.right - 30, int(p.y)), button=1))
    assert fight.mouse_down and p.attack_cd == 0, "Chạm sân là đi tới, không chém"
    x = p.x
    bot.tick(10)
    assert p.x > x
    bot.scenes.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(FIELD.right - 30, int(p.y)), button=1))
    assert not fight.mouse_down
    bot.click(BTN_ATTACK.center)
    assert p.attack_cd > 0, "Nút CHÉM"
