"""Hành động thẩm định và thông báo (Req 5.2, 5.4, 7.4)."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import created_col, enum_col, uuid_pk


class ReviewActionKind(StrEnum):
    submit = "submit"
    approve = "approve"
    reject = "reject"
    restore = "restore"


class ReviewAction(Base):
    __tablename__ = "review_actions"
    __table_args__ = (Index("ix_review_actions_entity", "entity_type", "entity_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_versions.id", ondelete="SET NULL")
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[ReviewActionKind] = mapped_column(
        enum_col(ReviewActionKind, "review_action_kind"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    checked_citation_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list, server_default="{}"
    )
    created_at: Mapped[datetime] = created_col()


class Notification(Base):
    """Thông báo cho người dùng: Admin_Portal (từ chối nội dung) và Game_Client (báo lỗi)."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read", "user_id", "read_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_col()
