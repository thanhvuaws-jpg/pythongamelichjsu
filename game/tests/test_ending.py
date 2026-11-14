"""Đoạn kết sau cổng cuối Màn 3: tự chạy hết các đoạn, mỗi đoạn có nguồn, bỏ qua được, xem lại được từ màn hình tựa đề."""

# isort: skip_file
from __future__ import annotations

import pygame
import pytest
from test_playthrough import DT, Bot, press_key  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import platform_io
from scenes.ending import BEATS, EndingScene
from scenes.story import StoryScene
from scenes.title import PANEL, TitleScene


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    b = Bot()
    b.state.reset()
    yield b


def test_every_beat_cites_a_known_source(bot):
    cites = bot.state.sources["citations"]
    for title, _text, _secs, method, _bg, sources in BEATS:
        assert hasattr(EndingScene, method), method
        if title and not title.startswith("Hành trình"):
            assert sources, f"Đoạn '{title}' phải ghi nguồn"
        for c in sources or ():
            assert c in cites, c
    years = " ".join(t + " " + x for t, x, *_ in BEATS)
    assert "1954" in years and "30/4/1975" in years, "Phải nói rõ năm 1954 hoà bình, năm 1975 mới thống nhất"


def test_all_beats_draw_at_many_moments(bot):
    sc = EndingScene(bot)
    bot.scenes.reset(sc)
    for i, beat in enumerate(BEATS):
        sc._goto(i)
        for step in range(8):
            sc.t = beat[2] * step / 8
            sc.time += 0.37
            sc.draw(bot.screen)


def test_plays_through_on_its_own_then_waits(bot):
    outro = StoryScene(bot, bot.state.sources["outro"])
    sc = EndingScene(bot, then=outro)
    bot.scenes.reset(sc)
    total = sum(b[2] for b in BEATS)
    bot.tick(int(total / DT) + 30)
    assert sc.last and bot.scenes.top is sc, "Đoạn cuối chờ người chơi bấm, không tự đóng"
    press_key(bot, pygame.K_SPACE)
    assert bot.scenes.top is outro, "Xong đoạn kết thì tới lời dặn của Cụ Đồ Sử"


def test_can_step_back_and_skip(bot):
    outro = StoryScene(bot, bot.state.sources["outro"])
    sc = EndingScene(bot, then=outro)
    bot.scenes.reset(sc)
    press_key(bot, pygame.K_SPACE)
    press_key(bot, pygame.K_RIGHT)
    assert sc.i == 2
    press_key(bot, pygame.K_LEFT)
    assert sc.i == 1
    press_key(bot, pygame.K_ESCAPE)
    assert bot.scenes.top is outro


def test_title_offers_replay_only_after_finishing(bot):
    title = TitleScene(bot)
    bot.scenes.reset(title)
    assert "Xem lại đoạn kết" not in [b.label for b in title.group.buttons]
    bot.state.finished = True
    title = TitleScene(bot)
    bot.scenes.reset(title)
    labels = [b.label for b in title.group.buttons]
    assert "Xem lại đoạn kết" in labels
    assert all(PANEL.contains(b.rect) for b in title.group.buttons), "Bảy nút vẫn nằm gọn trong khung menu"
    bot.press(title.group, "Xem lại đoạn kết")
    sc = bot.scenes.top
    assert isinstance(sc, EndingScene)
    sc._goto(len(BEATS) - 1)
    bot.tick()
    press_key(bot, pygame.K_SPACE)
    assert bot.scenes.top is title, "Xem lại xong thì về màn hình tựa đề"
