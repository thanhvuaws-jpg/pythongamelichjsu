"""Endpoint chơi game (Req 7.4, 16.2, 18, 19, 20, 21, 22.5)."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser
from app.db import get_session
from app.models import Notification
from app.play.answers import ensure_level_open, submit_answer, timeline_reward
from app.play.badges import evaluate_badges, list_badges
from app.play.progress import read_progress, save_progress, total_points
from app.play.ratelimit import AnswerUser
from app.play.review import answer_review, review_session
from app.schemas.play import (
    AnswerIn,
    AnswerOut,
    BadgeOut,
    NotificationOut,
    ProgressIn,
    ReviewAnswerIn,
    ReviewAnswerOut,
    ReviewQuestionOut,
    ReviewSessionOut,
    TimelineCompleteIn,
    TimelineCompleteOut,
)

router = APIRouter(prefix="/api/v1", tags=["play"])
Session = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------- tiến trình


@router.get("/progress")
async def get_progress(session: Session, user: CurrentUser) -> dict[str, Any]:
    """Tiến trình gần nhất kèm trạng thái mở khóa do máy chủ tính (Req 19.2)."""
    return await read_progress(session, user.id)


@router.put("/progress")
async def put_progress(body: ProgressIn, session: Session, user: CurrentUser) -> dict[str, Any]:
    """Hợp nhất theo hợp các tập đã hoàn thành (Req 19.1, 19.4)."""
    result = await save_progress(session, user.id, body.to_data())
    result["new_badges"] = await evaluate_badges(session, user.id, result)
    await session.commit()
    return result


# ---------------------------------------------------------------- chấm điểm


@router.post("/answers", response_model=AnswerOut)
async def post_answer(body: AnswerIn, session: Session, user: AnswerUser) -> AnswerOut:
    """Chấm phía máy chủ, cộng điểm một lần (Req 16.2, 18.1–18.3, 18.5); 30/phút (Req 22.5)."""
    r = await submit_answer(session, user.id, body.question_id, body.answer)
    if r.first_correct:
        # Lần đúng đầu tiên có thể đổi điểm/mở khóa → xét Huy_Hiệu (Req 21.2)
        progress = await read_progress(session, user.id)
        new_badges = await evaluate_badges(session, user.id, progress)
        total = progress["points"]
    else:
        new_badges, total = [], await total_points(session, user.id)
    await session.commit()
    return AnswerOut(
        correct=r.correct,
        attempt_no=r.attempt_no,
        points_awarded=r.points_awarded,
        total_points=total,
        already_scored=r.already_scored,
        correct_answer=r.question["correct_answer"],
        explanation=r.question["explanation"],
        citations=r.citations,
        added_to_review=r.added_to_review,
        new_badges=new_badges,
    )


@router.post("/timeline/complete", response_model=TimelineCompleteOut)
async def post_timeline_complete(
    body: TimelineCompleteIn, session: Session, user: CurrentUser
) -> TimelineCompleteOut:
    """Đánh dấu Dòng_Thời_Gian xong; thưởng 50 điểm khi ≤ 2 lần đặt sai (Req 18.4)."""
    ensure_level_open(await read_progress(session, user.id), body.level_id)
    bonus = await timeline_reward(session, user.id, body.level_id, body.mistakes)
    progress = await save_progress(session, user.id, timeline_level=str(body.level_id))
    new_badges = await evaluate_badges(session, user.id, progress)
    await session.commit()
    return TimelineCompleteOut(
        bonus_awarded=bonus,
        total_points=progress["points"],
        progress=progress,
        new_badges=new_badges,
    )


# ---------------------------------------------------------------- ôn tập


@router.get("/review/{level_id}", response_model=ReviewSessionOut)
async def get_review(level_id: uuid.UUID, session: Session, user: CurrentUser) -> ReviewSessionOut:
    """Phiên Chế_Độ_Ôn_Tập ≤ 10 câu (Req 20.1, 20.2)."""
    questions = await review_session(session, user.id, level_id)
    return ReviewSessionOut(
        level_id=level_id, questions=[ReviewQuestionOut(**q) for q in questions]
    )


@router.post("/review/answers", response_model=ReviewAnswerOut)
async def post_review_answer(
    body: ReviewAnswerIn, session: Session, user: AnswerUser
) -> ReviewAnswerOut:
    """Cập nhật khoảng ôn 1-3-7-14-30 ngày; điểm vào review_points (Req 20.3, 20.4, 20.6)."""
    r = await answer_review(session, user.id, body.question_id, body.answer)
    await session.commit()
    return ReviewAnswerOut(
        correct=r.correct,
        correct_answer=r.question["correct_answer"],
        explanation=r.question["explanation"],
        citations=r.citations,
        event_id=str(r.question["event_id"]),
        stage=r.stage,
        next_due_at=r.next_due_at,
        review_points_awarded=r.points,
        review_points_total=r.total,
    )


# ---------------------------------------------------------------- hồ sơ


@router.get("/me/badges", response_model=list[BadgeOut])
async def my_badges(session: Session, user: CurrentUser) -> list[BadgeOut]:
    """Huy_Hiệu đã đạt và chưa đạt kèm điều kiện (Req 21.3)."""
    return [BadgeOut(**b) for b in await list_badges(session, user.id)]


@router.get("/me/notifications", response_model=list[NotificationOut])
async def my_notifications(
    session: Session,
    user: CurrentUser,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[NotificationOut]:
    """Thông báo trong Game_Client: Huy_Hiệu, kết quả Báo_Cáo_Sai_Sót (Req 7.4, 21.2)."""
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    rows = await session.scalars(
        stmt.order_by(Notification.created_at.desc(), Notification.id).limit(limit)
    )
    return [
        NotificationOut(
            id=n.id, kind=n.kind, payload=n.payload, read_at=n.read_at, created_at=n.created_at
        )
        for n in rows
    ]
