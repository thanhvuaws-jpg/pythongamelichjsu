"""Dữ liệu chơi của Người_Chơi (Req 18.5, 19.2, 20.6, 21.2).

`score_ledger` là sổ cái bất biến: UNIQUE(user_id, reason, ref_id) chặn cộng điểm trùng.
Bảng `notifications` đã tạo ở migration 0003 (models/review.py).
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import created_col, enum_col, updated_col


class ScoreReason(StrEnum):
    question = "question"
    timeline_bonus = "timeline_bonus"
    admin_bonus = "admin_bonus"


def _user_pk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


def _question_pk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)


class Progress(Base):
    """Tiến trình hợp nhất; `data` gồm cả trường do máy chủ tính lại (mở khóa, hoàn thành)."""

    __tablename__ = "progress"

    user_id: Mapped[uuid.UUID] = _user_pk()
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    updated_at: Mapped[datetime] = updated_col()


class QuestionAttempt(Base):
    __tablename__ = "question_attempts"

    user_id: Mapped[uuid.UUID] = _user_pk()
    question_id: Mapped[uuid.UUID] = _question_pk()
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_correct_attempt: Mapped[int | None] = mapped_column(Integer)
    scored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Thời điểm lần thử đầu, dùng tính chuỗi đúng ngay lần đầu cho Huy_Hiệu
    created_at: Mapped[datetime] = created_col()
    updated_at: Mapped[datetime] = updated_col()


class ScoreLedger(Base):
    __tablename__ = "score_ledger"
    __table_args__ = (
        UniqueConstraint("user_id", "reason", "ref_id", name="uq_score_ledger_user_reason_ref"),
        Index("ix_score_ledger_created_user", "created_at", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[ScoreReason] = mapped_column(
        enum_col(ScoreReason, "score_reason"), nullable=False
    )
    # question_id hoặc level_id tùy `reason`; không đặt FK
    ref_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = created_col()


class GameSave(Base):
    """Bản lưu của game theo tài khoản, để chơi tiếp ở máy khác; `points` do máy chủ tính lại."""

    __tablename__ = "game_saves"

    user_id: Mapped[uuid.UUID] = _user_pk()
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Điểm kỹ năng quản trị viên tặng; chỉ máy chủ sửa, bản lưu người chơi gửi lên không đụng tới
    bonus_skill_points: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    updated_at: Mapped[datetime] = updated_col()


class ReviewItem(Base):
    """Lịch ôn của một Câu_Hỏi. `stage=None` là chưa ôn lần nào (Req 20.3–20.4)."""

    __tablename__ = "review_items"
    __table_args__ = (Index("ix_review_items_user_due", "user_id", "due_at"),)

    user_id: Mapped[uuid.UUID] = _user_pk()
    question_id: Mapped[uuid.UUID] = _question_pk()
    stage: Mapped[int | None] = mapped_column(SmallInteger)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_result: Mapped[bool | None] = mapped_column(Boolean)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_col()


class ReviewPoints(Base):
    """Bộ đếm điểm Chế_Độ_Ôn_Tập, tách khỏi Điểm_Kiến_Thức (Req 20.6)."""

    __tablename__ = "review_points"

    user_id: Mapped[uuid.UUID] = _user_pk()
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = updated_col()


class UserBadge(Base):
    __tablename__ = "user_badges"

    user_id: Mapped[uuid.UUID] = _user_pk()
    badge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("badges.id", ondelete="CASCADE"), primary_key=True
    )
    awarded_at: Mapped[datetime] = created_col()
