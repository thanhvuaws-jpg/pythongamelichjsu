"""Chấm đáp án và thưởng Dòng_Thời_Gian (Req 16.2, 18.1–18.5).

- Hàng `question_attempts` được khóa (SELECT ... FOR UPDATE) nên hai yêu cầu đồng thời
  của cùng Người_Chơi không cùng nhận là "lần thử 1".
- Điểm chỉ tính ở lần trả lời đúng đầu tiên; `score_ledger` UNIQUE(user, reason, ref)
  là lớp chặn cộng trùng thứ hai (Req 18.5).
- Mỗi lần chấm trả về đáp án đúng, giải thích và Trích_Dẫn (Req 16.2).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import now_utc
from app.errors import AppError
from app.models import QuestionAttempt, ReviewItem, ScoreLedger, ScoreReason
from app.play.published import load_question, question_citations
from shared.grading import grade
from shared.scoring import needs_review, points_for, timeline_bonus


@dataclass
class AnswerResult:
    correct: bool
    attempt_no: int
    points_awarded: int
    already_scored: bool
    first_correct: bool  # lần đúng đầu tiên của Người_Chơi với câu này
    added_to_review: bool
    question: dict[str, Any]
    citations: list[dict[str, Any]]


async def award(
    session: AsyncSession, user_id: uuid.UUID, reason: ScoreReason, ref_id: uuid.UUID, points: int
) -> int:
    """Ghi sổ cái một lần; trả số điểm thực sự được cộng (0 nếu đã có)."""
    if points <= 0:
        return 0
    inserted = await session.scalar(
        insert(ScoreLedger)
        .values(user_id=user_id, reason=reason, ref_id=ref_id, points=points)
        .on_conflict_do_nothing(constraint="uq_score_ledger_user_reason_ref")
        .returning(ScoreLedger.id)
    )
    return points if inserted is not None else 0


async def add_review_item(
    session: AsyncSession, user_id: uuid.UUID, question_id: uuid.UUID, now: datetime
) -> bool:
    inserted = await session.scalar(
        insert(ReviewItem)
        .values(user_id=user_id, question_id=question_id, stage=None, due_at=now)
        .on_conflict_do_nothing()
        .returning(ReviewItem.question_id)
    )
    return inserted is not None


async def _lock_attempt(
    session: AsyncSession, user_id: uuid.UUID, question_id: uuid.UUID
) -> QuestionAttempt:
    await session.execute(
        insert(QuestionAttempt)
        .values(user_id=user_id, question_id=question_id, attempts=0, scored=False)
        .on_conflict_do_nothing()
    )
    row = await session.scalar(
        select(QuestionAttempt)
        .where(QuestionAttempt.user_id == user_id, QuestionAttempt.question_id == question_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert row is not None
    return row


async def submit_answer(
    session: AsyncSession, user_id: uuid.UUID, question_id: uuid.UUID, answer: Any
) -> AnswerResult:
    question = await load_question(session, question_id)
    row = await _lock_attempt(session, user_id, question_id)
    row.attempts += 1
    attempt_no = row.attempts
    correct = grade(question, answer)

    points = 0
    added_to_review = False
    already_scored = row.scored
    first_correct = correct and row.first_correct_attempt is None
    if first_correct:
        row.first_correct_attempt = attempt_no
        if not row.scored:
            row.scored = True
            points = await award(
                session,
                user_id,
                ScoreReason.question,
                question_id,
                points_for(int(question["difficulty"]), attempt_no),
            )
        if needs_review(attempt_no):  # Req 18.3
            added_to_review = await add_review_item(session, user_id, question_id, now_utc())

    return AnswerResult(
        correct=correct,
        attempt_no=attempt_no,
        points_awarded=points,
        already_scored=already_scored,
        first_correct=first_correct,
        added_to_review=added_to_review,
        question=question,
        citations=await question_citations(session, question_id),
    )


def ensure_level_open(progress: dict[str, Any], level_id: uuid.UUID) -> None:
    lid = str(level_id)
    if lid in progress["unlocked_levels"]:
        return
    if lid in progress["locked_levels"]:
        raise AppError(
            409,
            "LEVEL_LOCKED",
            "Màn chơi chưa được mở khóa",
            {"missing": progress["locked_levels"][lid]},
        )
    raise AppError(404, "LEVEL_NOT_FOUND", "Không tìm thấy Màn chơi")


async def timeline_reward(
    session: AsyncSession, user_id: uuid.UUID, level_id: uuid.UUID, mistakes: int
) -> int:
    """50 điểm khi số lần đặt sai ≤ 2, tối đa một lần cho mỗi Màn_Chơi (Req 18.4)."""
    return await award(
        session, user_id, ScoreReason.timeline_bonus, level_id, timeline_bonus(mistakes)
    )
