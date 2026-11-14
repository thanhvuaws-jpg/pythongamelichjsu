"""Chế_Độ_Ôn_Tập (Req 20.1–20.4, 20.6).

Ứng viên ôn tập là mọi Câu_Hỏi đã xuất bản của Màn_Chơi mà Người_Chơi đã thử ít nhất
một lần. Câu chưa có `review_items` được tạo khi trả lời lần đầu trong phiên ôn.
Điểm ôn tập cộng vào `review_points`, không vào `score_ledger` (Req 20.6).
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
from app.models import (
    ContentVersion,
    Event,
    Question,
    QuestionAttempt,
    ReviewItem,
    ReviewPoints,
)
from app.play.published import (
    by_snapshot,
    load_question,
    published,
    question_citations,
)
from app.publish.bundler import public_question
from shared.grading import grade
from shared.review_schedule import ReviewCandidate, due_at, pick_review_questions
from shared.scoring import BASE_POINTS


async def level_questions(session: AsyncSession, level_id: uuid.UUID) -> dict[str, dict[str, Any]]:
    events = await published(session, Event, by_snapshot("level_id", str(level_id)))
    if not events:
        return {}
    questions = await published(
        session,
        Question,
        ContentVersion.snapshot["event_id"].astext.in_(sorted(events)),
        Question.hidden_by_report.is_(False),  # Req 7.3
    )
    return questions


async def review_session(
    session: AsyncSession, user_id: uuid.UUID, level_id: uuid.UUID, limit: int = 10
) -> list[dict[str, Any]]:
    """Chọn ≤ 10 câu: sai > đúng sau nhiều lần thử > lâu chưa ôn nhất (Req 20.1–20.2)."""
    questions = await level_questions(session, level_id)
    if not questions:
        return []
    qids = [uuid.UUID(q) for q in questions]
    attempts = {
        str(a.question_id): a
        for a in await session.scalars(
            select(QuestionAttempt).where(
                QuestionAttempt.user_id == user_id, QuestionAttempt.question_id.in_(qids)
            )
        )
    }
    items = {
        str(r.question_id): r
        for r in await session.scalars(
            select(ReviewItem).where(
                ReviewItem.user_id == user_id, ReviewItem.question_id.in_(qids)
            )
        )
    }
    now = now_utc()
    candidates: list[ReviewCandidate] = []
    for qid in questions:
        att, item = attempts.get(qid), items.get(qid)
        if att is None and item is None:
            continue
        if item is not None:
            last_result = item.last_result
            last_reviewed = item.last_reviewed_at
        else:
            # Chưa ôn: kết quả chơi chính; chưa từng đúng coi như sai
            last_result = att is not None and att.first_correct_attempt is not None
            last_reviewed = None
        candidates.append(
            ReviewCandidate(
                question_id=qid,
                last_result=last_result,
                attempts=(att.first_correct_attempt or att.attempts) if att else 1,
                last_reviewed_at=last_reviewed,
            )
        )

    out = []
    for c in pick_review_questions(candidates, limit):
        item = items.get(c.question_id)
        q = public_question(questions[c.question_id])
        out.append(
            {
                **q,
                "event_id": str(q["event_id"]),
                "stage": item.stage if item else None,
                "due_at": item.due_at if item else now,
                "last_result": item.last_result if item else None,
            }
        )
    return out


@dataclass
class ReviewAnswerResult:
    correct: bool
    question: dict[str, Any]
    citations: list[dict[str, Any]]
    stage: int
    next_due_at: datetime
    points: int
    total: int


async def answer_review(
    session: AsyncSession, user_id: uuid.UUID, question_id: uuid.UUID, answer: Any
) -> ReviewAnswerResult:
    question = await load_question(session, question_id)
    attempted = await session.get(QuestionAttempt, (user_id, question_id))
    if attempted is None:
        raise AppError(409, "NOT_REVIEWABLE", "Câu hỏi chưa được trả lời trong lượt chơi chính")
    now = now_utc()
    await session.execute(
        insert(ReviewItem)
        .values(user_id=user_id, question_id=question_id, stage=None, due_at=now)
        .on_conflict_do_nothing()
    )
    item = await session.scalar(
        select(ReviewItem)
        .where(ReviewItem.user_id == user_id, ReviewItem.question_id == question_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert item is not None

    correct = grade(question, answer)
    stage, next_due = due_at(now, item.stage, correct)  # Req 20.3–20.4
    item.stage, item.due_at = stage, next_due
    item.last_result, item.last_reviewed_at = correct, now

    points = BASE_POINTS[int(question["difficulty"])] if correct else 0
    await session.execute(
        insert(ReviewPoints).values(user_id=user_id, total=0).on_conflict_do_nothing()
    )
    rp = await session.scalar(
        select(ReviewPoints)
        .where(ReviewPoints.user_id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert rp is not None
    rp.total += points
    return ReviewAnswerResult(
        correct=correct,
        question=question,
        citations=await question_citations(session, question_id),
        stage=stage,
        next_due_at=next_due,
        points=points,
        total=rp.total,
    )
