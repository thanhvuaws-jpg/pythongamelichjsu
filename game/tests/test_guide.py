"""Kiểm thử trailer hướng dẫn và bảng Lộ trình: người mới phải luôn biết cần làm gì."""

# isort: skip_file
from __future__ import annotations

import pygame
import pytest
from test_playthrough import Bot, play_story, press_key  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import platform_io
from scenes.roadmap import RoadmapScene
from scenes.story import StoryScene
from scenes.title import TitleScene
from scenes.trailer import BEATS, TrailerScene
from scenes.world import PauseScene, WorldScene


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    b = Bot()
    b.state.reset()
    yield b


def finish_relic(st, relic_id):
    for quest in st.engine(st.level_of[relic_id]).quests:
        if quest["id"] == relic_id:
            for obj in quest["objectives"]:
                st.progress.completed_objectives.add(obj["id"])
    st.stamps.add(relic_id)


# ----- trailer -----
def test_every_beat_of_the_trailer_runs_and_ends_on_a_prompt(bot):
    sc = TrailerScene(bot)
    bot.scenes.reset(sc)
    total = sum(b[2] for b in BEATS)
    assert 120 <= total <= 210, "Trailer hướng dẫn dài gần ba phút, đủ nói hết cách chơi"
    for _ in range(int(total * 30) + 60):
        bot.tick()
    assert sc.last, "Trailer phải tự chạy tới đoạn cuối"
    assert bot.scenes.top is sc, "Đoạn cuối chờ người chơi bấm, không tự đóng"


def test_trailer_can_be_stepped_and_skipped(bot):
    title = TitleScene(bot)
    bot.scenes.reset(title)
    sc = TrailerScene(bot)
    bot.scenes.push(sc)
    bot.tick(2)
    press_key(bot, pygame.K_SPACE)
    assert sc.i == 1
    press_key(bot, pygame.K_LEFT)
    assert sc.i == 0
    for i in range(len(BEATS)):
        sc._goto(i)
        bot.tick(6)
    bot.press(sc.group, "Bỏ qua")
    assert bot.scenes.top is title


def test_all_beats_draw_at_many_moments(bot):
    sc = TrailerScene(bot)
    bot.scenes.reset(sc)
    for i, beat in enumerate(BEATS):
        sc._goto(i)
        for step in range(8):
            sc.t = beat[2] * step / 8
            sc.draw(bot.screen)


def test_new_game_shows_trailer_once_then_enters_map(bot):
    st = bot.state
    title = TitleScene(bot)
    bot.scenes.reset(title)
    bot.tick(2)
    bot.press(title.group, "Bắt đầu hành trình")
    assert isinstance(bot.scenes.top, StoryScene)
    play_story(bot)
    assert isinstance(bot.scenes.top, TrailerScene), "Sau lời mở đầu phải tới trailer"
    assert st.tutorial_seen
    press_key(bot, pygame.K_ESCAPE)
    assert isinstance(bot.scenes.top, WorldScene)
    # Lần sau vào thẳng map
    bot.scenes.reset(TitleScene(bot))
    bot.tick(2)
    bot.press(bot.scenes.top.group, "Bắt đầu hành trình")
    assert isinstance(bot.scenes.top, WorldScene)


def test_old_saves_with_progress_are_not_interrupted(bot):
    st = bot.state
    st.intro_done = True
    st.stamps.add("r_duong_lam")
    title = TitleScene(bot)
    bot.scenes.reset(title)
    bot.tick(2)
    title._start()
    assert isinstance(bot.scenes.top, WorldScene)


def test_trailer_can_be_rewatched_from_menus(bot):
    title = TitleScene(bot)
    bot.scenes.reset(title)
    bot.tick(2)
    bot.press(title.group, "Xem hướng dẫn")
    assert isinstance(bot.scenes.top, TrailerScene)
    press_key(bot, pygame.K_ESCAPE)
    assert bot.scenes.top is title
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    press_key(bot, pygame.K_ESCAPE)
    pause = bot.scenes.top
    assert isinstance(pause, PauseScene)
    bot.press(pause.group, "Xem hướng dẫn")
    assert isinstance(bot.scenes.top, TrailerScene)
    press_key(bot, pygame.K_ESCAPE)
    assert bot.scenes.top is pause


def test_tutorial_flag_is_saved(bot):
    st = bot.state
    st.tutorial_seen = True
    saved = st.to_dict()
    st.reset()
    assert not st.tutorial_seen
    st.from_dict(saved)
    assert st.tutorial_seen


# ----- lộ trình -----
def open_roadmap(bot, level="man1"):
    ws = WorldScene(bot, level, "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    press_key(bot, pygame.K_j)
    sc = bot.scenes.top
    assert isinstance(sc, RoadmapScene)
    bot.tick(2)
    return ws, sc


def test_roadmap_opens_with_key_button_and_tracker_click(bot):
    ws, sc = open_roadmap(bot)
    press_key(bot, pygame.K_j)
    assert bot.scenes.top is ws
    bot.press(ws.group, "Mở menu")
    bot.press(ws.group, "Lộ trình")
    assert isinstance(bot.scenes.top, RoadmapScene)
    press_key(bot, pygame.K_ESCAPE)
    assert not ws.menu_open, "Chọn xong một mục thì menu tự thu lại"
    bot.click((200, 60))
    assert isinstance(bot.scenes.top, RoadmapScene), "Bấm vào khung việc cần làm cũng mở lộ trình"


def test_roadmap_points_at_the_first_relic_for_a_new_player(bot):
    _ws, sc = open_roadmap(bot)
    node = sc.nodes[sc.sel]
    assert node["level"] == "man1"
    assert sc._status(node) == "now"
    assert node["relic"]["id"] == bot.state.next_relic("man1")["id"]
    assert "Đường Lâm" in sc.doing or sc.doing


def test_roadmap_statuses_follow_progress(bot):
    st = bot.state
    first = st.levels["man1"]["relics"][0]
    finish_relic(st, first["id"])
    st._engines.clear()
    _ws, sc = open_roadmap(bot)
    by_id = {n["relic"]["id"]: n for n in sc.nodes if n["relic"]}
    assert sc._status(by_id[first["id"]]) == "done"
    assert sc._status(sc.nodes[sc.sel]) == "now"
    assert sc.nodes[sc.sel]["relic"]["id"] != first["id"], "Đã xong thì chỉ sang di tích tiếp theo"
    later = next(n for n in sc.nodes if n["level"] == "man3")
    assert sc._status(later) == "locked", "Chặng sau chưa mở"
    end = next(n for n in sc.nodes if n["level"] == "man1" and n["relic"] is None)
    assert sc._status(end) == "locked", "Chưa đủ dấu thì chưa dựng dòng thời gian"


def test_roadmap_timeline_node_when_all_relics_done(bot):
    st = bot.state
    for relic in st.levels["man1"]["relics"]:
        finish_relic(st, relic["id"])
    st._engines.clear()
    _ws, sc = open_roadmap(bot)
    node = sc.nodes[sc.sel]
    assert node["relic"] is None and sc._status(node) == "now"
    bot.tick(2)
    st.progress.timeline_done.add("man1")
    assert sc._status(node) == "done"
    bot.tick(2)


def test_roadmap_travel_goes_to_the_selected_relic(bot):
    ws, sc = open_roadmap(bot)
    node = sc.nodes[sc.sel]
    bot.click(sc.go.rect.center)
    assert bot.scenes.top is ws
    zone = ws.world.zones[node["relic"]["id"]]
    assert abs(ws.x - (zone.cx + 0.5) * 64) < 1


def test_roadmap_cannot_travel_to_locked_or_other_level_relic(bot):
    ws, sc = open_roadmap(bot)
    locked = next(i for i, n in enumerate(sc.nodes) if n["level"] == "man2")
    sc.sel = locked
    assert not sc._can_travel(sc.nodes[locked])
    press_key(bot, pygame.K_RETURN)
    assert bot.scenes.top is sc
    bot.tick(2)
    end = next(i for i, n in enumerate(sc.nodes) if n["relic"] is None)
    sc.sel = end
    assert not sc._can_travel(sc.nodes[end])
    bot.tick(2)


def test_roadmap_keyboard_and_mouse_selection(bot):
    _ws, sc = open_roadmap(bot)
    start = sc.sel
    press_key(bot, pygame.K_RIGHT)
    assert sc.sel == start + 1
    press_key(bot, pygame.K_LEFT)
    assert sc.sel == start
    press_key(bot, pygame.K_DOWN)
    assert sc.nodes[sc.sel]["row"] == 1
    press_key(bot, pygame.K_UP)
    assert sc.nodes[sc.sel]["row"] == 0
    target = sc.nodes[3]
    bot.click((target["x"], target["y"]))
    assert sc.sel == 3


def test_roadmap_lists_optional_things_for_this_level_only(bot):
    _ws, sc = open_roadmap(bot, "man3")
    rows = " ".join(sc._more_rows())
    assert "Dấu hỏi trên map: 0/4" in rows
    assert "Tư liệu đã ghép (phím T): 0/3" in rows
    assert "Giao tranh" not in rows, "Màn 3 không có giao tranh"
    assert "Thắng ở võ đài" in rows


def test_top_menu_is_one_button_until_opened(bot):
    """Góc trên chỉ có nút ba gạch; bấm mới xổ danh sách, bấm ra ngoài thì thu lại mà không đi tới chỗ vừa bấm."""
    from scenes.bestiary import BestiaryScene

    bot.state.reset()
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    assert [b.label for b in ws.group.buttons] == ["Mở menu"]
    bot.press(ws.group, "Mở menu")
    labels = [b.label for b in ws.group.buttons]
    for want in ("Lộ trình", "Kỹ năng", "Tư liệu", "Sổ tay", "Bản đồ", "Túi đồ", "Sổ bóng giặc", "Bạn chơi", "Hộ chiếu", "Ôn tập", "Tạm dừng"):
        assert want in labels, want
    assert all(b.rect.right <= 1280 and b.rect.bottom < ws._minimap_rect().y for b in ws.menu_items), "Danh sách nằm gọn, không đè bản đồ nhỏ"
    bot.tick()  # vẽ được khi đang mở
    x, y = ws.x, ws.y
    bot.click((640, 600))
    assert not ws.menu_open and not ws.path and (ws.x, ws.y) == (x, y), "Bấm ra ngoài chỉ thu menu lại"
    bot.press(ws.group, "Mở menu")
    press_key(bot, pygame.K_ESCAPE)
    assert not ws.menu_open and bot.scenes.top is ws, "Esc thu menu trước, chưa mở bảng tạm dừng"
    bot.press(ws.group, "Mở menu")
    bot.press(ws.group, "Sổ bóng giặc")
    assert isinstance(bot.scenes.top, BestiaryScene) and not ws.menu_open
