"""Bảng xếp hạng, lớp học, báo cáo sai sót (Req 7, 22, 26)."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CHAR, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import created_col, enum_col, updated_col, uuid_pk


class ReportStatus(StrEnum):
    new = "new"
    confirmed = "confirmed"
    rejected = "rejected"
    resolved = "resolved"


class LeaderboardCache(Base):
    """Top 100 đã tính sẵn theo khóa ('week', 'month', 'all', 'class:<id>:<period>')."""

    __tablename__ = "leaderboard_cache"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # [{user_id, display_name, avatar_url, points, rank}]
    data: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Classroom(Base):
    """Lớp_Học do Giáo_Viên tạo; `join_code` 6 ký tự chữ và số (Req 26.1)."""

    __tablename__ = "classes"

    id: Mapped[uuid.UUID] = uuid_pk()
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    join_code: Mapped[str] = mapped_column(CHAR(6), unique=True, nullable=False)
    created_at: Mapped[datetime] = created_col()


class ClassMember(Base):
    __tablename__ = "class_members"

    class_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    joined_at: Mapped[datetime] = created_col()


class ErrorReport(Base):
    """Báo_Cáo_Sai_Sót (Req 7). `hidden_question_ids` là Câu_Hỏi bị ẩn khi xác nhận sai."""

    __tablename__ = "error_reports"
    __table_args__ = (
        Index("ix_error_reports_entity", "entity_type", "entity_id"),
        Index("ix_error_reports_status", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    reporter_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    counter_source: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[ReportStatus] = mapped_column(
        enum_col(ReportStatus, "report_status"), default=ReportStatus.new, nullable=False
    )
    handled_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolution: Mapped[str | None] = mapped_column(Text)
    hidden_question_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list, server_default="{}"
    )
    created_at: Mapped[datetime] = created_col()
    updated_at: Mapped[datetime] = updated_col()
