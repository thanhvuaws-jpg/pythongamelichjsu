"""Lặp lại ngắt quãng cho Chế_Độ_Ôn_Tập (Req 20.2–20.4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

INTERVALS = (1, 3, 7, 14, 30)  # ngày
MAX_SESSION = 10


def next_review(stage: int | None, correct: bool) -> tuple[int, int]:
    """Trả (stage_mới, số_ngày). `stage=None` là câu chưa từng ôn. Sai → stage 0 (1 ngày)."""
    if not correct:
        return 0, INTERVALS[0]
    s = 0 if stage is None else min(stage + 1, len(INTERVALS) - 1)
    return s, INTERVALS[s]


def due_at(now: datetime, stage: int | None, correct: bool) -> tuple[int, datetime]:
    s, days = next_review(stage, correct)
    return s, now + timedelta(days=days)


@dataclass(frozen=True, slots=True)
class ReviewCandidate:
    question_id: str
    last_result: bool | None  # False = trả lời sai gần nhất
    attempts: int  # số lần thử khi chơi chính
    last_reviewed_at: datetime | None


def pick_review_questions(
    items: list[ReviewCandidate], limit: int = MAX_SESSION
) -> list[ReviewCandidate]:
    """Ưu tiên: trả lời sai > đúng sau nhiều lần thử > lâu chưa ôn nhất."""

    def key(c: ReviewCandidate):
        if c.last_result is False:
            group = 0
        elif c.attempts > 1:
            group = 1
        else:
            group = 2
        # Chưa ôn lần nào coi như lâu nhất
        ts = c.last_reviewed_at.timestamp() if c.last_reviewed_at else float("-inf")
        return (group, ts, c.question_id)

    return sorted(items, key=key)[:limit]
