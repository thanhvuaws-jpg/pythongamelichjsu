"""Điểm_Kiến_Thức theo Độ_Khó và lần thử (Req 18.1–18.4)."""

BASE_POINTS = {1: 10, 2: 20, 3: 30}
TIMELINE_BONUS = 50
TIMELINE_MAX_MISTAKES = 2


def points_for(difficulty: int, attempt_no: int) -> int:
    """Lần 1: đủ điểm; lần 2: 50% làm tròn xuống; từ lần 3: 0."""
    if attempt_no < 1:
        raise ValueError("attempt_no bắt đầu từ 1")
    base = BASE_POINTS[difficulty]
    if attempt_no == 1:
        return base
    if attempt_no == 2:
        return base // 2
    return 0


def needs_review(attempt_no: int) -> bool:
    """Câu trả lời đúng từ lần thử thứ 3 được đưa vào danh sách ôn tập (Req 18.3)."""
    return attempt_no >= 3


def timeline_bonus(mistakes: int) -> int:
    return TIMELINE_BONUS if mistakes <= TIMELINE_MAX_MISTAKES else 0
