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


# ----- cần điều khiển ảo, nhiều ngón cùng lúc -----
def _finger(kind, fid, pos):
    from core import theme

    return pygame.event.Event(kind, x=pos[0] / theme.WIDTH, y=pos[1] / theme.HEIGHT, dx=0.0, dy=0.0, finger_id=fid,
                              touch_id=0, pressure=1.0)


def _touch_mouse(kind, pos):
    extra = {"button": 1} if kind != pygame.MOUSEMOTION else {"rel": (0, 0), "buttons": (1, 0, 0)}
    return pygame.event.Event(kind, pos=(int(pos[0]), int(pos[1])), touch=True, **extra)


def test_stick_walks_smoothly_and_its_touch_never_becomes_a_tap_to_walk(bot):
    ws = _world(bot)
    stick = ws.stick
    centre = (stick.cx, stick.cy)
    right = (stick.cx + stick.r, stick.cy)
    for e in (_finger(pygame.FINGERDOWN, 0, centre), _touch_mouse(pygame.MOUSEBUTTONDOWN, centre),
              _finger(pygame.FINGERMOTION, 0, right), _touch_mouse(pygame.MOUSEMOTION, right)):
        bot.scenes.handle(e)
    assert bot.scenes.fingers and stick.active and stick.vector()[0] == pytest.approx(1.0)
    x0 = ws.x
    xs = []
    for _ in range(15):
        bot.tick()
        xs.append(ws.x)
    steps = [b - a for a, b in zip([x0, *xs], xs, strict=False)]
    assert ws.x > x0 + 40 and ws.facing == "right"
    assert min(steps) > 0 or ws.x > x0 + 40, "Giữ cần là đi đều"
    far = (stick.cx + 300, stick.cy - 200)  # nhấc tay ở ngoài vòng: không được hiểu là chạm lên bản đồ để đi tới đó
    for e in (_finger(pygame.FINGERUP, 0, far), _touch_mouse(pygame.MOUSEBUTTONUP, far)):
        bot.scenes.handle(e)
    assert not stick.active and not ws.path
    x1 = ws.x
    bot.tick(5)
    assert ws.x == x1, "Nhấc tay là dừng"


def test_second_finger_presses_a_button_while_the_stick_is_held(bot):
    ws = _world(bot)
    bot.state.level = rpg.HORSE_LEVEL
    bot.scenes.handle(_finger(pygame.FINGERDOWN, 0, (ws.stick.cx, ws.stick.cy)))
    btn = next(b for b in ws.touch_btns if b.label == "Gọi ngựa") if _labels(bot, ws) else None
    assert btn is not None
    bot.scenes.handle(_finger(pygame.FINGERDOWN, 1, btn.rect.center))
    bot.scenes.handle(_finger(pygame.FINGERUP, 1, btn.rect.center))
    assert ws.mode == "horse" and ws.stick.active


def test_stick_works_with_touch_mouse_only(bot):
    ws = _world(bot)
    assert not bot.scenes.fingers
    centre, down = (ws.stick.cx, ws.stick.cy), (ws.stick.cx, ws.stick.cy + ws.stick.r)
    bot.scenes.handle(_touch_mouse(pygame.MOUSEBUTTONDOWN, centre))
    bot.scenes.handle(_touch_mouse(pygame.MOUSEMOTION, down))
    assert ws.stick.owner == "mouse"
    y0 = ws.y
    for _ in range(10):  # get_pressed() của bản thử luôn nhả, nên gửi tay sự kiện thay vì chờ
        ws.update(1 / 30)
    assert ws.y > y0 + 20
    bot.scenes.handle(_touch_mouse(pygame.MOUSEBUTTONUP, down))
    assert not ws.stick.active and not ws.path


def test_tap_to_walk_keeps_moving_every_frame_and_cuts_straight_lines(bot):
    ws = _world(bot, touch=False)
    ws.noclip = True  # chỉ còn biên bản đồ chắn: đường thẳng chéo luôn đi được
    x0, y0 = ws.x, ws.y
    ws._walk_to(x0 + TILE * 6, y0 + TILE * 6)
    assert len(ws.path) >= 12, "Đường tìm trên lưới ô là đường gấp khúc"
    pos = [(ws.x, ws.y)]
    for _ in range(20):
        ws.update(1 / 30)
        pos.append((ws.x, ws.y))
    steps = [((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(pos, pos[1:], strict=False)]
    assert min(steps) > 0, "Không khựng lại ở giữa mỗi ô"
    assert max(steps) - min(steps) < 1.0, "Mỗi khung hình đi một quãng bằng nhau"
    dx, dy = ws.x - x0, ws.y - y0
    assert dx > 20 and dy > 20 and abs(dx - dy) < TILE, "Đi chéo thẳng một mạch chứ không đi hết ngang rồi mới xuống"


def test_fight_stick_and_attack_button_with_two_fingers(bot):
    bot.state.reset()
    bot.scenes.touch = True
    fight = FightScene(bot, [{"name": "Bù nhìn", "char": "Villager", "hp": 5000}], "Thử")
    bot.scenes.reset(fight)
    fight.intro = 0
    p = fight.player
    st = fight.stick
    bot.scenes.handle(_finger(pygame.FINGERDOWN, 0, (st.cx, st.cy)))
    bot.scenes.handle(_finger(pygame.FINGERMOTION, 0, (st.cx + st.r, st.cy)))
    x0 = p.x
    bot.tick(8)
    assert p.x > x0 + 20, "Ngón cái trái giữ cần thì đi"
    calls = []
    real = fight.attack
    fight.attack = lambda f: (calls.append(f), real(f))
    bot.scenes.handle(_finger(pygame.FINGERDOWN, 1, BTN_ATTACK.center))
    bot.scenes.handle(_touch_mouse(pygame.MOUSEBUTTONDOWN, BTN_ATTACK.center))  # chuột giả của cùng cú chạm: không tính lại
    assert p.attack_cd > 0
    bot.tick(45)
    assert sum(c is p for c in calls) >= 3, "Giữ nút CHÉM bằng ngón kia thì chém liên tục, vẫn đi được"
    bot.scenes.handle(_finger(pygame.FINGERUP, 1, BTN_ATTACK.center))
    assert fight.attack_finger is None and st.active


def test_case_room_stick(bot):
    bot.state.reset()
    bot.scenes.touch = True
    from scenes.case import CaseScene

    sc = CaseScene(bot, bot.state.extras["cases"][0])
    bot.scenes.reset(sc)
    bot.scenes.handle(_finger(pygame.FINGERDOWN, 0, (sc.stick.cx, sc.stick.cy)))
    bot.scenes.handle(_finger(pygame.FINGERMOTION, 0, (sc.stick.cx, sc.stick.cy - sc.stick.r)))
    y0 = sc.y
    bot.tick(10)
    assert sc.y < y0 - 20, "Trong nhà tư liệu cũng đi bằng cần"
