"""Thực thể nội dung lịch sử và lối chơi kèm cột chung (Req 1.1, 3.4, 4.1, 9.1, 21.1).

Mỗi thực thể có `status`, `is_fiction`, `author_id`, `last_editor_id`,
`published_version_id` (trỏ tới ảnh chụp đang chạy trong Content_Bundle) và
`hidden_by_report`. Tên bảng cũng là `entity_type` dùng trong `citations` và
`content_versions`.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import created_col, enum_col, updated_col, uuid_pk


class ContentStatus(StrEnum):
    """Trạng_Thái_Nội_Dung."""

    draft = "draft"
    pending = "pending"
    published = "published"
    archived = "archived"


class DatePrecision(StrEnum):
    """Độ_Chính_Xác của Mốc_Thời_Gian."""

    day = "day"
    month = "month"
    year = "year"
    year_range = "year_range"
    century = "century"


class CausalKind(StrEnum):
    cause_of = "cause_of"
    leads_to = "leads_to"
    context_of = "context_of"


class MapLayerKind(StrEnum):
    boundary = "boundary"
    route = "route"
    ancient_place = "ancient_place"


class FragmentKind(StrEnum):
    text = "text"
    artifact_image = "artifact_image"
    old_map = "old_map"
    photo = "photo"


class QuestionKind(StrEnum):
    single = "single"
    multi = "multi"
    order = "order"
    match = "match"
    map_pick = "map_pick"


class ObjectiveKind(StrEnum):
    go_to = "go_to"
    collect = "collect"
    dialogue = "dialogue"
    answer = "answer"
    timeline = "timeline"


CONTENT_STATUS = enum_col(ContentStatus, "content_status")
DATE_PRECISION = enum_col(DatePrecision, "date_precision")


def _user_ref() -> Mapped[uuid.UUID | None]:
    return mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


def _ref(target: str, nullable: bool = True, ondelete: str = "SET NULL") -> Any:
    return mapped_column(ForeignKey(target, ondelete=ondelete), nullable=nullable, index=True)


def _uuid_array() -> Mapped[list[uuid.UUID]]:
    return mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list, server_default="{}"
    )


class ContentVersion(Base):
    """Ảnh chụp toàn bộ trường của một lần lưu (Req 6.1); giữ ≥ 3 năm (Req 6.4)."""

    __tablename__ = "content_versions"
    __table_args__ = (
        UniqueConstraint(
            "entity_type", "entity_id", "version_no", name="uq_content_versions_entity_version"
        ),
        Index("ix_content_versions_entity", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Không đặt FK để phiên bản tồn tại sau khi người dùng bị xóa
    editor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status_at_save: Mapped[ContentStatus] = mapped_column(CONTENT_STATUS, nullable=False)
    created_at: Mapped[datetime] = created_col()


class ContentMixin:
    """Cột chung của mọi thực thể nội dung."""

    id: Mapped[uuid.UUID] = uuid_pk()
    status: Mapped[ContentStatus] = mapped_column(
        CONTENT_STATUS, default=ContentStatus.draft, nullable=False, index=True
    )
    is_fiction: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    author_id: Mapped[uuid.UUID | None] = _user_ref()
    last_editor_id: Mapped[uuid.UUID | None] = _user_ref()
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_versions.id", ondelete="SET NULL")
    )
    hidden_by_report: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = created_col()
    updated_at: Mapped[datetime] = updated_col()


class Level(ContentMixin, Base):
    """Màn_Chơi (Req 9.1). Nhiệm_Vụ có thứ tự nằm ở `quests.order_no`."""

    __tablename__ = "levels"

    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    period_label: Mapped[str] = mapped_column(Text, nullable=False)
    intro: Mapped[str] = mapped_column(Text, nullable=False)
    place_ids: Mapped[list[uuid.UUID]] = _uuid_array()
    # [{"from": place_id, "to": place_id, "path": [[lat, lon], ...]}] (Req 11.1)
    routes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    unlock_rule: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    map_bounds: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Place(ContentMixin, Base):
    """Địa_Điểm có tên lịch sử theo giai đoạn (Req 10.3)."""

    __tablename__ = "places"
    __table_args__ = (
        CheckConstraint("lat BETWEEN -90 AND 90", name="lat_range"),
        CheckConstraint("lon BETWEEN -180 AND 180", name="lon_range"),
    )

    # [{"period": "Trần", "name": "Vạn Kiếp"}]
    names: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    modern_name: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    lon: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unlock_rule: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Person(ContentMixin, Base):
    """Nhân_Vật."""

    __tablename__ = "persons"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    alt_names: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default="{}"
    )
    birth_year: Mapped[int | None] = mapped_column(Integer)
    death_year: Mapped[int | None] = mapped_column(Integer)
    birth_death_precision: Mapped[DatePrecision | None] = mapped_column(DATE_PRECISION)
    bio: Mapped[str | None] = mapped_column(Text)
    portrait_media_id: Mapped[uuid.UUID | None] = _ref("media.id")
    portrait_is_illustration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Event(ContentMixin, Base):
    """Sự_Kiện với Mốc_Thời_Gian dạng khoảng theo Độ_Chính_Xác (Req 3.4)."""

    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("date_end IS NULL OR date_end >= date_start", name="date_order"),
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    significance: Mapped[str | None] = mapped_column(Text)
    date_start: Mapped[date | None] = mapped_column(Date)
    date_end: Mapped[date | None] = mapped_column(Date)
    date_precision: Mapped[DatePrecision | None] = mapped_column(DATE_PRECISION)
    lunar_date_text: Mapped[str | None] = mapped_column(Text)
    era_name: Mapped[str | None] = mapped_column(Text)
    place_id: Mapped[uuid.UUID | None] = _ref("places.id")
    level_id: Mapped[uuid.UUID | None] = _ref("levels.id")
    person_ids: Mapped[list[uuid.UUID]] = _uuid_array()
    # {"casualties": "...", "troops": "..."}; mỗi khóa cần 2 nguồn (Req 2.3)
    numeric_facts: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )


class CausalLink(ContentMixin, Base):
    """Quan_Hệ_Nhân_Quả có hướng giữa hai Sự_Kiện."""

    __tablename__ = "causal_links"
    __table_args__ = (CheckConstraint("from_event_id <> to_event_id", name="distinct_events"),)

    from_event_id: Mapped[uuid.UUID] = _ref("events.id", nullable=False, ondelete="CASCADE")
    to_event_id: Mapped[uuid.UUID] = _ref("events.id", nullable=False, ondelete="CASCADE")
    kind: Mapped[CausalKind] = mapped_column(enum_col(CausalKind, "causal_kind"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class MapLayer(ContentMixin, Base):
    """Lớp_Bản_Đồ gắn với một Màn_Chơi (Req 10.5)."""

    __tablename__ = "map_layers"

    level_id: Mapped[uuid.UUID] = _ref("levels.id", nullable=False, ondelete="CASCADE")
    kind: Mapped[MapLayerKind] = mapped_column(
        enum_col(MapLayerKind, "map_layer_kind"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    geojson: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    media_id: Mapped[uuid.UUID | None] = _ref("media.id")


class Fragment(ContentMixin, Base):
    """Mảnh_Ghép tư liệu (Req 13)."""

    __tablename__ = "fragments"

    event_id: Mapped[uuid.UUID] = _ref("events.id", nullable=False, ondelete="RESTRICT")
    place_id: Mapped[uuid.UUID | None] = _ref("places.id")
    kind: Mapped[FragmentKind] = mapped_column(
        enum_col(FragmentKind, "fragment_kind"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    han_nom_original: Mapped[str | None] = mapped_column(Text)
    translation: Mapped[str | None] = mapped_column(Text)
    media_id: Mapped[uuid.UUID | None] = _ref("media.id")


class Dialogue(ContentMixin, Base):
    """Hội_Thoại; cờ hư cấu và trích nguyên văn ở mức từng node (Req 4.1, 4.3)."""

    __tablename__ = "dialogues"

    place_id: Mapped[uuid.UUID | None] = _ref("places.id")
    speaker_person_id: Mapped[uuid.UUID | None] = _ref("persons.id")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    # [{id, speaker, text, is_fiction, is_verbatim_quote, choices:[{text, next}], clue}]
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)


class Question(ContentMixin, Base):
    """Câu_Hỏi. `answer_basis` liệt kê nội dung làm căn cứ đáp án (Req 4.4)."""

    __tablename__ = "questions"
    __table_args__ = (CheckConstraint("difficulty IN (1, 2, 3)", name="difficulty_range"),)

    event_id: Mapped[uuid.UUID] = _ref("events.id", nullable=False, ondelete="RESTRICT")
    kind: Mapped[QuestionKind] = mapped_column(
        enum_col(QuestionKind, "question_kind"), nullable=False
    )
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    correct_answer: Mapped[Any] = mapped_column(JSONB, nullable=False)
    tolerance_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    # Câu hỏi kiểm tra trường có Ghi_Chú_Sử_Học → cần xác nhận khi duyệt (Req 3.3)
    historian_note_id: Mapped[uuid.UUID | None] = _ref("historian_notes.id")
    # [{"type": "fragments" | "dialogues", "id": "..."}]
    answer_basis: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )


class Quest(ContentMixin, Base):
    """Nhiệm_Vụ."""

    __tablename__ = "quests"

    level_id: Mapped[uuid.UUID] = _ref("levels.id", nullable=False, ondelete="CASCADE")
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    central_question: Mapped[str] = mapped_column(Text, nullable=False)
    answer_summary: Mapped[str | None] = mapped_column(Text)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unlock_rule: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Objective(ContentMixin, Base):
    """Mục_Tiêu; `target_id` trỏ tới Địa_Điểm/Mảnh_Ghép/Hội_Thoại/Câu_Hỏi theo `kind`."""

    __tablename__ = "objectives"

    quest_id: Mapped[uuid.UUID] = _ref("quests.id", nullable=False, ondelete="CASCADE")
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[ObjectiveKind] = mapped_column(
        enum_col(ObjectiveKind, "objective_kind"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Badge(ContentMixin, Base):
    """Huy_Hiệu (Req 21.1)."""

    __tablename__ = "badges"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    media_id: Mapped[uuid.UUID | None] = _ref("media.id")
    # {"type": "level_complete", "level_id": "..."}
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


CONTENT_MODELS: tuple[type[ContentMixin], ...] = (
    Level,
    Place,
    Person,
    Event,
    CausalLink,
    MapLayer,
    Fragment,
    Dialogue,
    Question,
    Quest,
    Objective,
    Badge,
)
