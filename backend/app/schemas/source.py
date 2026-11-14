"""Schema Pydantic cho Danh_Mục_Nguồn và media."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models import MediaLicense, SourceStatus

Text = Annotated[str, Field(min_length=1, max_length=2000)]
ShortText = Annotated[str, Field(min_length=1, max_length=64)]
Year = Annotated[int, Field(ge=1, le=2100)]
Tier = Annotated[int, Field(ge=1, le=3)]


class SourceIn(BaseModel):
    title: Text
    authors: Text | None = None
    translators: Text | None = None
    publisher: Text
    year: Year
    edition: ShortText | None = None
    volume: ShortText | None = None
    # Biên_Tập_Viên chỉ đề xuất; Cấp_Nguồn chính thức do Người_Thẩm_Định chỉ định
    tier: Tier | None = None
    isbn_or_archive_code: ShortText | None = None
    url: Annotated[str, Field(max_length=2000)] | None = None
    notes: Text | None = None


class SourcePatch(BaseModel):
    title: Text | None = None
    authors: Text | None = None
    translators: Text | None = None
    publisher: Text | None = None
    year: Year | None = None
    edition: ShortText | None = None
    volume: ShortText | None = None
    tier: Tier | None = None
    isbn_or_archive_code: ShortText | None = None
    url: Annotated[str, Field(max_length=2000)] | None = None
    notes: Text | None = None


class SourceApproveIn(BaseModel):
    tier: Tier


class SourceRejectIn(BaseModel):
    reason: Annotated[str, Field(min_length=1, max_length=1000)]


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    authors: str | None
    translators: str | None
    publisher: str | None
    year: int | None
    edition: str | None
    volume: str | None
    tier: int | None
    isbn_or_archive_code: str | None
    url: str | None
    notes: str | None
    status: SourceStatus
    proposed_by: uuid.UUID | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class SourcePage(BaseModel):
    items: list[SourceOut]
    total: int
    page: int
    page_size: int


class MediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    storage_path: str
    url: str
    mime: str
    size_bytes: int
    owner: str
    license: MediaLicense
    source_url: str
    license_url: str | None
    attribution: str | None
    created_at: datetime


class CreditSource(BaseModel):
    id: uuid.UUID
    title: str
    authors: str | None
    translators: str | None
    publisher: str | None
    year: int | None
    edition: str | None
    volume: str | None
    tier: int | None


class CreditMedia(BaseModel):
    id: uuid.UUID
    url: str
    owner: str
    license: MediaLicense
    license_url: str | None
    attribution: str | None
    source_url: str


class CreditsOut(BaseModel):
    sources: list[CreditSource]
    media: list[CreditMedia]
