"""Kiểm thử ôn tập: có câu để ôn ngay sau khi chơi, đúng lịch 1-3-7-14-30 ngày, không cày điểm được."""

# isort: skip_file
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pygame
import pytest
from test_playthrough import Bot, play_question, press_key  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import platform_io
from core import state as state_mod
from scenes.question import QuestionScene
from scenes.review import ReviewScene
from scenes.timeline import LevelSummaryScene

T0 = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)


class Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now

    def days(self, n):
        self.now += timedelta(days=n)


@pytest.fixture()
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(state_mod, "_now", c)
    return c


@pytest.fixture()
def bot(clock):
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    b = Bot()
    b.state.reset()
    yield b


def questions(st, level="man1", n=20):
    return st.levels[level]["questions"][:n]


def answer(st, q, tries):
    """Trả lời trong lúc chơi: sai `tries - 1` lần rồi đúng."""
    for _ in range(tries - 1):
        st.record_answer(q, False)
    st.record_answer(q, True)


def run_session(bot, rv, wrong_ids=()):
    bot.press(rv.group, "Bắt đầu ôn tập")
    guard = 0
    while isinstance(bot.scenes.top, QuestionScene):
        guard += 1
        assert guard < 30
        sc = bot.scenes.top
        if sc.q["id"] in wrong_ids:
            bot.tick(2)
            sc.selected = set()
            sc.result = None
            # trả lời sai: ghi thẳng một đáp án sai rồi đóng
            bot.state.review_answer(sc.q, False)
            bot.scenes.pop(False)
        else:
            play_question(bot, sc.q)
    assert rv.finished


def test_nothing_answered_shows_empty_state(bot):
    rv = ReviewScene(bot)
    bot.scenes.reset(rv)
    bot.tick(2)
    assert rv.total == 0
    assert not any("Bắt đầu" in b.label for b in rv.group.buttons)


def test_can_review_right_after_playing_and_wrong_ones_come_first(bot):
    st = bot.state
    qs = questions(st)
    answer(st, qs[0], 1)
    answer(st, qs[1], 3)  # sai hai lần
    answer(st, qs[2], 1)
    answer(st, qs[3], 2)  # sai một lần
    plan = st.review_plan()
    assert plan["answered"] == 4
    assert not plan["due"], "Vừa chơi xong thì chưa câu nào đến hạn"
    order = [q["id"] for q in plan["early"]]
    assert len(order) == 4, "Nhưng vẫn phải có câu để luyện ngay"
    assert set(order[:2]) == {qs[1]["id"], qs[3]["id"]}, "Câu từng sai phải đứng trước"


def test_every_answered_question_gets_a_schedule(bot, clock):
    st = bot.state
    qs = questions(st)
    answer(st, qs[0], 1)
    answer(st, qs[1], 2)
    answer(st, qs[2], 3)
    due = {q["id"]: datetime.fromisoformat(st.review[q["id"]]["due"]) for q in qs[:3]}
    assert due[qs[0]["id"]] == T0 + timedelta(days=3), "Đúng ngay lần đầu: ôn lại sau 3 ngày"
    assert due[qs[1]["id"]] == T0 + timedelta(days=1), "Từng sai: mai ôn lại"
    assert due[qs[2]["id"]] == T0 + timedelta(days=1)
    clock.days(1)
    plan = st.review_plan()
    assert {q["id"] for q in plan["due"]} == {qs[1]["id"], qs[2]["id"]}
    clock.days(2)
    assert len(st.review_plan()["due"]) == 3


def test_schedule_grows_1_3_7_14_30_and_resets_on_wrong(bot, clock):
    st = bot.state
    q = questions(st)[0]
    answer(st, q, 2)
    gaps = []
    for _ in range(5):
        clock.now = datetime.fromisoformat(st.review[q["id"]]["due"])
        info = st.review_answer(q, True)
        assert info == {"counted": True, "points": 2}
        gaps.append((datetime.fromisoformat(st.review[q["id"]]["due"]) - clock.now).days)
    assert gaps == [3, 7, 14, 30, 30]
    clock.now = datetime.fromisoformat(st.review[q["id"]]["due"])
    st.review_answer(q, False)
    assert (datetime.fromisoformat(st.review[q["id"]]["due"]) - clock.now).days == 1, "Sai thì quay về ngày mai"
    assert st.review[q["id"]]["last"] is False


def test_practice_gives_no_points_and_keeps_schedule(bot):
    st = bot.state
    q = questions(st)[0]
    answer(st, q, 1)
    before_points, before_due = st.progress.points, st.review[q["id"]]["due"]
    for _ in range(5):
        assert st.review_answer(q, True) == {"counted": False, "points": 0}
    assert st.progress.points == before_points, "Luyện thêm không được cộng điểm"
    assert st.review[q["id"]]["due"] == before_due, "Luyện thêm mà đúng thì lịch giữ nguyên"
    st.review_answer(q, False)
    assert st.review[q["id"]]["last"] is False, "Luyện thêm mà sai thì mai phải gặp lại"


def test_points_cannot_be_farmed_by_repeating_sessions(bot, clock):
    st = bot.state
    for q in questions(st, n=6):
        answer(st, q, 2)
    clock.days(1)
    rv = ReviewScene(bot)
    bot.scenes.reset(rv)
    bot.tick(2)
    assert len(rv.plan["due"]) == 6
    start = st.progress.points
    run_session(bot, rv)
    assert st.progress.points == start + 12 and rv.gained == 12
    for _ in range(3):
        bot.press(rv.group, "Ôn tiếp")
        assert not rv.plan["due"]
        run_session(bot, rv)
    assert st.progress.points == start + 12, "Ôn lại ngay không được thêm điểm"


def test_session_is_limited_to_ten_and_rotates(bot):
    st = bot.state
    qs = questions(st, n=14)
    for q in qs:
        answer(st, q, 1)
    rv = ReviewScene(bot)
    bot.scenes.reset(rv)
    bot.tick(2)
    first = [q["id"] for q in rv.queue]
    assert len(first) == 10
    run_session(bot, rv)
    bot.press(rv.group, "Ôn tiếp")
    second = [q["id"] for q in rv.queue]
    assert set(second) - set(first), "Phiên sau phải đưa ra các câu chưa ôn"


def test_scope_tabs_filter_by_level(bot):
    st = bot.state
    answer(st, st.levels["man1"]["questions"][0], 1)
    answer(st, st.levels["man2"]["questions"][0], 1)
    st.progress.completed_levels.add("man1")
    rv = ReviewScene(bot)
    bot.scenes.reset(rv)
    bot.tick(2)
    assert rv.total == 2
    bot.press(rv.group, st.levels["man2"]["level"]["period_label"])
    assert rv.total == 1 and rv.queue[0]["id"] == st.levels["man2"]["questions"][0]["id"]
    bot.press(rv.group, "Tất cả")
    assert rv.total == 2
    in_level = ReviewScene(bot, "man1")
    assert in_level.total == 1, "Mở từ map thì ôn riêng màn đó"


def test_wrong_answers_are_listed_and_badge_is_given(bot):
    st = bot.state
    qs = questions(st, n=3)
    for q in qs:
        answer(st, q, 1)
    rv = ReviewScene(bot)
    bot.scenes.reset(rv)
    bot.tick(2)
    run_session(bot, rv, wrong_ids={qs[1]["id"]})
    assert rv.correct == 2 and [q["id"] for q in rv.wrong] == [qs[1]["id"]]
    assert "chuyen_can" in st.badges
    bot.tick(3)
    press_key(bot, pygame.K_ESCAPE)


def test_old_saves_without_schedule_can_still_review(bot):
    st = bot.state
    qs = questions(st, n=3)
    st.from_dict({"solved": [q["id"] for q in qs], "review": {qs[0]["id"]: {"stage": 0, "due": "2000-01-01T00:00:00+00:00", "last": False, "attempts": 2}}})
    plan = st.review_plan()
    assert [q["id"] for q in plan["due"]] == [qs[0]["id"]]
    assert {q["id"] for q in plan["early"]} == {qs[1]["id"], qs[2]["id"]}
    st.review_answer(qs[1], True)
    assert qs[1]["id"] in st.review, "Câu chưa có lịch, ôn xong thì được xếp lịch"


def test_broken_schedule_entry_does_not_crash(bot):
    st = bot.state
    q = questions(st)[0]
    st.solved.add(q["id"])
    st.review[q["id"]] = {"stage": None, "due": "hỏng"}
    plan = st.review_plan()
    assert [x["id"] for x in plan["due"]] == [q["id"]]
    st.review_answer(q, True)
    datetime.fromisoformat(st.review[q["id"]]["due"])


def test_extra_questions_join_the_review(bot):
    st = bot.state
    item = st.extras["discoveries"][0]
    answer(st, item["question"], 2)
    plan = st.review_plan(item["level"])
    assert item["question"]["id"] in {q["id"] for q in plan["early"]}


def test_level_summary_counts_only_weak_questions(bot):
    st = bot.state
    qs = questions(st, n=4)
    answer(st, qs[0], 1)
    answer(st, qs[1], 1)
    answer(st, qs[2], 2)
    assert [q["id"] for q in st.weak_questions("man1")] == [qs[2]["id"]]
    summary = LevelSummaryScene(bot, "man1", 0, 50)
    bot.scenes.reset(summary)
    bot.tick(2)
    assert any("1 câu cần xem lại" in b.label for b in summary.group.buttons)
    bot.press(summary.group, "Ôn tập ngay")
    assert isinstance(bot.scenes.top, ReviewScene) and bot.scenes.top.total == 3


def test_question_label_shows_progress(bot):
    st = bot.state
    for q in questions(st, n=2):
        answer(st, q, 1)
    rv = ReviewScene(bot)
    bot.scenes.reset(rv)
    bot.tick(2)
    bot.press(rv.group, "Bắt đầu ôn tập")
    sc = bot.scenes.top
    assert sc.label.startswith("Ôn tập 1/2") and "luyện thêm" in sc.label
    bot.tick(2)
