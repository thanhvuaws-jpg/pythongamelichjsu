from datetime import UTC, datetime

from app.classroom.service import CODE_ALPHABET, new_join_code, progress_csv
from app.leaderboard.service import Period, period_start, rank_rows


def test_week_starts_monday_midnight_vietnam_time():
    # Chủ nhật 2026-11-08 18:00 UTC = thứ Hai 2026-11-09 01:00 giờ Việt Nam
    now = datetime(2026, 11, 8, 18, 0, tzinfo=UTC)
    assert period_start(Period.week, now) == datetime(2026, 11, 8, 17, 0, tzinfo=UTC)
    # Chủ nhật 2026-11-08 16:59 UTC vẫn thuộc tuần bắt đầu thứ Hai 2026-11-02 (VN)
    now = datetime(2026, 11, 8, 16, 59, tzinfo=UTC)
    assert period_start(Period.week, now) == datetime(2026, 11, 1, 17, 0, tzinfo=UTC)
    assert period_start(Period.month, now) == datetime(2026, 10, 31, 17, 0, tzinfo=UTC)
    assert period_start(Period.all, now) is None


def test_rank_ties_share_rank():
    rows = [("a", "A", None, 30), ("b", "B", None, 20), ("c", "C", None, 20), ("d", "D", None, 5)]
    assert [r["rank"] for r in rank_rows(rows)] == [1, 2, 2, 4]
    assert "email" not in rank_rows(rows)[0]


def test_join_code_format():
    code = new_join_code()
    assert len(code) == 6 and set(code) <= set(CODE_ALPHABET)


def test_progress_csv_utf8_bom_and_formula_escape():
    report = {
        "level_count": 3,
        "members": [
            {
                "display_name": "=Nguyễn Văn A",
                "joined_at": datetime(2026, 11, 4, tzinfo=UTC),
                "points": 40,
                "completed_levels": ["L1"],
                "completed_level_titles": ["Bạch Đằng"],
                "accuracy": 0.5,
                "by_event": [{"event_id": "E", "event_title": "Trận Bạch Đằng", "accuracy": 0.5}],
            }
        ],
    }
    data = progress_csv(report)
    assert data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    assert "'=Nguyễn Văn A" in text
    assert "Trận Bạch Đằng: 50.0%" in text
