"""Danh mục nguồn, trích dẫn, ghi chú sử học và media (Req 1, 2, 3, 8)."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import created_col, enum_col, updated_col, uuid_pk


class SourceStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class MediaLicense(StrEnum):
    """Danh sách giấy phép được phép (Req 8.2)."""

    public_domain = "public_domain"
    cc0 = "cc0"
    cc_by = "cc_by"
    cc_by_sa = "cc_by_sa"
    self_made = "self_made"
    written_permission = "written_permission"


# Giấy phép bắt buộc hiển thị dòng ghi công (Req 8.3)
ATTRIBUTION_REQUIRED = {MediaLicense.cc_by, MediaLicense.cc_by_sa}


class Source(Base):
    """Nguồn_Tin_Cậy. `publisher`/`year` có thể trống khi `pending` (nguồn seed chưa
    đối chiếu bản sách thực tế) nhưng bắt buộc khi duyệt."""

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("tier IS NULL OR tier IN (1, 2, 3)", name="tier_range"),
        CheckConstraint("status <> 'approved' OR tier IS NOT NULL", name="approved_has_tier"),
        Index("ix_sources_status", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[str | None] = mapped_column(Text)
    translators: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(Integer)
    edition: Mapped[str | None] = mapped_column(String(64))
    volume: Mapped[str | None] = mapped_column(String(64))
    tier: Mapped[int | None] = mapped_column(SmallInteger)
    isbn_or_archive_code: Mapped[str | None] = mapped_column(String(64))
    url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SourceStatus] = mapped_column(
        enum_col(SourceStatus, "source_status"), default=SourceStatus.pending, nullable=False
    )
    proposed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_col()
    updated_at: Mapped[datetime] = updated_col()


class Citation(Base):
    """Trích_Dẫn gắn ở mức trường (`field_path`) của một thực thể nội dung."""

    __tablename__ = "citations"
    __table_args__ = (Index("ix_citations_entity", "entity_type", "entity_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # 'date', 'casualties', 'description', 'explanation', 'node:<id>' hoặc '*'
    field_path: Mapped[str] = mapped_column(String(128), nullable=False, default="*")
    locator: Mapped[str] = mapped_column(Text, nullable=False)  # trang/mục/mã văn bản
    quote: Mapped[str | None] = mapped_column(Text)
    is_verbatim_quote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_col()


class HistorianNote(Base):
    """Ghi_Chú_Sử_Học (Req 3.1)."""

    __tablename__ = "historian_notes"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_path: Mapped[str] = mapped_column(String(128), nullable=False)
    # [{"value": "...", "citation_ids": ["..."]}]
    variants: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    default_variant_idx: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_col()
    updated_at: Mapped[datetime] = updated_col()


class Media(Base):
    """Tệp media kèm Giấy_Phép_Media (Req 8.1–8.2)."""

    __tablename__ = "media"

    id: Mapped[uuid.UUID] = uuid_pk()
    storage_path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    license: Mapped[MediaLicense] = mapped_column(
        enum_col(MediaLicense, "media_license"), nullable=False
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    license_url: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    permission_doc_path: Mapped[str | None] = mapped_column(Text)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_col()
