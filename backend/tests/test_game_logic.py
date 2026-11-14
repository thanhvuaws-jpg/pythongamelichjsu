"""Điểm xếp hạng tính từ bản lưu và thống kê: không cần cơ sở dữ liệu."""

from pathlib import Path

from app.config import Settings, get_settings
from app.game.logic import aggregate, load_content, ref_id, score_items, total_score
from shared.scoring import TIMELINE_BONUS

CONTENT_DIR = str(Path(__file__).resolve().parents[2] / "game" / "content")


def content():
    return load_content(CONTENT_DIR)


def test_default_content_dir_exists():
    assert Path(get_settings().game_content_dir, "man1.json").is_file()


def test_content_includes_main_and_extra_questions():
    c = content()
    assert "q_dl_1" in c.questions and "q_x_lq" in c.questions
    assert c.relics == 18
    assert [lv["id"] for lv in c.levels] == ["man1", "man2", "man3"]


def test_score_ignores_claimed_points_and_fake_questions():
    save = {"points": 999999, "solved": ["q_dl_1", "khong_co_that", 5], "attempts": {"q_dl_1": 1}}
    assert score_items(save, content()) == {("question", "q_dl_1"): 10}


def test_later_attempts_score_less_and_give_up_scores_nothing():
    c = content()
    assert total_score({"solved": ["q_dl_1"], "attempts": {"q_dl_1": 2}}, c) == 5
    assert total_score({"solved": ["q_dl_1"], "attempts": {"q_dl_1": 3}}, c) == 0
    assert (
        total_score({"solved": ["q_dl_1"], "gave_up": ["q_dl_1"], "attempts": {"q_dl_1": 1}}, c)
        == 0
    )


def test_timeline_bonus_only_for_real_levels():
    items = score_items({"timeline_done": ["man1", "man9"]}, content())
    assert items == {("timeline_bonus", "man1"): TIMELINE_BONUS}


def test_garbage_save_does_not_crash():
    c = content()
    for bad in (
        {},
        {"solved": "abc"},
        {"solved": None, "attempts": "x"},
        {"attempts": {"q_dl_1": "x"}, "solved": ["q_dl_1"]},
    ):
        assert total_score(bad, c) >= 0
    assert (
        aggregate([{"attempts": 5, "skill_levels": [], "stamps": None}], c)["players_with_save"]
        == 1
    )


def test_max_score_is_bounded_by_content():
    c = content()
    everything = {"solved": list(c.questions), "timeline_done": [lv["id"] for lv in c.levels]}
    assert (
        total_score(everything, c)
        == sum({1: 10, 2: 20, 3: 30}[q["difficulty"]] for q in c.questions.values())
        + 3 * TIMELINE_BONUS
    )


def test_ref_id_is_stable_and_distinct():
    assert ref_id("question", "q1") == ref_id("question", "q1")
    assert ref_id("question", "q1") != ref_id("question", "q2")
    assert ref_id("question", "man1") != ref_id("timeline_bonus", "man1")


def test_aggregate_finds_hardest_question_and_level_counts():
    c = content()
    saves = [
        {
            "attempts": {"q_dl_1": 3, "q_dl_2": 1},
            "gave_up": ["q_dl_1"],
            "completed_levels": ["man1"],
            "stamps": ["r_duong_lam"],
            "skill_levels": {"phong_lao": 2},
            "arena_wins": ["b_trai_lang"],
            "discovered": ["d_lang_ngo"],
        },
        {"attempts": {"q_dl_1": 2}, "completed_levels": [], "stamps": []},
    ]
    out = aggregate(saves, c)
    assert out["players_with_save"] == 2
    assert out["hardest_questions"][0]["id"] == "q_dl_1"
    assert out["hardest_questions"][0]["avg_attempts"] == 2.5
    assert out["hardest_questions"][0]["gave_up"] == 1
    assert out["levels"][0]["completed"] == 1
    assert out["avg_stamps"] == 0.5
    assert out["skills"] == {"phong_lao": 1}
    assert out["arena_wins"] == {"b_trai_lang": 1}
    assert out["activity"]["discovered"] == 1


def test_aggregate_with_no_players():
    out = aggregate([], content())
    assert (
        out["players_with_save"] == 0 and out["avg_points"] == 0 and out["hardest_questions"] == []
    )


def test_database_url_from_hosting_is_normalized():
    make = lambda url: Settings(database_url=url, _env_file=None).database_url  # noqa: E731
    assert make("postgres://u:p@h:5432/d") == "postgresql+asyncpg://u:p@h:5432/d"
    assert make("postgresql://u:p@h/d") == "postgresql+asyncpg://u:p@h/d"
    assert make("postgresql+asyncpg://u:p@h/d") == "postgresql+asyncpg://u:p@h/d"
    assert (
        make("postgresql://u:p@h/d?sslmode=require") == "postgresql+asyncpg://u:p@h/d?ssl=require"
    )
