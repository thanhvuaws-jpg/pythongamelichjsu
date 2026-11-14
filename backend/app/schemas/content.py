"""Schema Pydantic cho từng loại nội dung (Req 28.1).

Schema `*In` mô tả toàn bộ trường nội dung (không gồm cột quản trị như status,
author_id). PATCH được hợp nhất với giá trị hiện tại rồi kiểm tra lại bằng cùng schema,
nên ràng buộc chéo trường (ngày bắt đầu/kết thúc, đáp án theo loại câu hỏi) luôn đúng.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import (
    CausalKind,
    ContentStatus,
    DatePrecision,
    FragmentKind,
    MapLayerKind,
    ObjectiveKind,
    QuestionKind,
)

Title = Annotated[str, Field(min_length=1, max_length=500)]
LongText = Annotated[str, Field(min_length=1, max_length=20000)]
Key = Annotated[str, Field(min_length=1, max_length=64)]
OrderNo = Annotated[int, Field(ge=1, le=10000)]
HistYear = Annotated[int, Field(ge=-3000, le=2100)]
JsonObj = dict[str, Any]


class ContentType(StrEnum):
    """Slug trên URL `/content/{type}`."""

    levels = "levels"
    places = "places"
    persons = "persons"
    events = "events"
    causal_links = "causal-links"
    map_layers = "map-layers"
    fragments = "fragments"
    dialogues = "dialogues"
    questions = "questions"
    quests = "quests"
    objectives = "objectives"
    badges = "badges"


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    is_fiction: bool = False  # Req 4.1


class LevelIn(_In):
    order_no: OrderNo
    title: Title
    period_label: Title
    intro: LongText
    place_ids: list[uuid.UUID] = []
    routes: list[JsonObj] = []
    unlock_rule: JsonObj | None = None
    map_bounds: JsonObj | None = None


class PlaceName(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    period: Title
    name: Title


class PlaceIn(_In):
    names: Annotated[list[PlaceName], Field(min_length=1)]
    modern_name: Title
    lat: Annotated[Decimal, Field(ge=-90, le=90)]
    lon: Annotated[Decimal, Field(ge=-180, le=180)]
    description: LongText | None = None
    unlock_rule: JsonObj | None = None


class PersonIn(_In):
    name: Title
    alt_names: list[Title] = []
    birth_year: HistYear | None = None
    death_year: HistYear | None = None
    birth_death_precision: DatePrecision | None = None
    bio: LongText | None = None
    portrait_media_id: uuid.UUID | None = None
    portrait_is_illustration: bool = True  # Req 14.4

    @model_validator(mode="after")
    def _years(self) -> "PersonIn":
        if self.birth_year and self.death_year and self.death_year < self.birth_year:
            raise ValueError("Năm mất phải sau năm sinh")
        return self


class EventIn(_In):
    title: Title
    summary: LongText | None = None
    description: LongText | None = None
    significance: LongText | None = None
    date_start: date | None = None
    date_end: date | None = None
    date_precision: DatePrecision | None = None
    lunar_date_text: Title | None = None  # Req 3.4
    era_name: Title | None = None
    place_id: uuid.UUID | None = None
    level_id: uuid.UUID | None = None
    person_ids: list[uuid.UUID] = []
    numeric_facts: dict[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")], Title] = {}

    @model_validator(mode="after")
    def _dates(self) -> "EventIn":
        if self.date_end and not self.date_start:
            raise ValueError("Có ngày kết thúc thì cần ngày bắt đầu")
        if self.date_start and self.date_precision is None:
            raise ValueError("Mốc thời gian cần Độ chính xác")
        if self.date_start and self.date_end and self.date_end < self.date_start:
            raise ValueError("Ngày kết thúc phải sau hoặc bằng ngày bắt đầu")
        return self


class CausalLinkIn(_In):
    from_event_id: uuid.UUID
    to_event_id: uuid.UUID
    kind: CausalKind
    note: LongText | None = None

    @model_validator(mode="after")
    def _distinct(self) -> "CausalLinkIn":
        if self.from_event_id == self.to_event_id:
            raise ValueError("Quan hệ nhân quả cần hai Sự kiện khác nhau")
        return self


class MapLayerIn(_In):
    level_id: uuid.UUID
    kind: MapLayerKind
    title: Title
    geojson: JsonObj | None = None
    media_id: uuid.UUID | None = None


class FragmentIn(_In):
    event_id: uuid.UUID
    place_id: uuid.UUID | None = None
    kind: FragmentKind
    title: Title
    body: LongText | None = None
    han_nom_original: LongText | None = None
    translation: LongText | None = None  # Req 13.2
    media_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _translation(self) -> "FragmentIn":
        if self.han_nom_original and not self.translation:
            raise ValueError("Trích đoạn Hán Nôm cần bản dịch tiếng Việt")
        return self


class DialogueChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: Title
    next: Key


class DialogueNode(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: Key
    speaker: Title
    text: LongText
    is_fiction: bool = True
    is_verbatim_quote: bool = False  # Req 4.3
    choices: Annotated[list[DialogueChoice], Field(max_length=4)] = []  # Req 14.2
    next: Key | None = None
    clue: LongText | None = None


class DialogueIn(_In):
    place_id: uuid.UUID | None = None
    speaker_person_id: uuid.UUID | None = None
    title: Title
    nodes: Annotated[list[DialogueNode], Field(min_length=1)]

    @model_validator(mode="after")
    def _links(self) -> "DialogueIn":
        ids = [n.id for n in self.nodes]
        if len(set(ids)) != len(ids):
            raise ValueError("Mã node hội thoại bị trùng")
        known = set(ids)
        targets = [c.next for n in self.nodes for c in n.choices]
        targets += [n.next for n in self.nodes if n.next]
        missing = sorted(set(targets) - known)
        if missing:
            raise ValueError(f"Node đích không tồn tại: {', '.join(missing)}")
        return self


class QuestionOption(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: Key
    text: Title
    side: Literal["left", "right"] | None = None  # dùng cho ghép cặp


class AnswerBasis(BaseModel):
    """Nội dung làm căn cứ đáp án, để chặn câu hỏi dựa vào hư cấu (Req 4.4)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["fragments", "dialogues"]
    id: uuid.UUID
    node_id: Key | None = None


def _is_num(x: Any) -> bool:
    return isinstance(x, int | float) and not isinstance(x, bool)


def _str_list(x: Any) -> bool:
    return isinstance(x, list) and all(isinstance(i, str) for i in x)


class QuestionIn(_In):
    event_id: uuid.UUID
    kind: QuestionKind
    difficulty: Annotated[int, Field(ge=1, le=3)]
    prompt: LongText
    options: list[QuestionOption] = []
    correct_answer: Any
    tolerance_km: Annotated[Decimal, Field(gt=0, le=1000)] | None = None
    explanation: LongText
    historian_note_id: uuid.UUID | None = None
    answer_basis: list[AnswerBasis] = []

    @model_validator(mode="after")
    def _answer(self) -> "QuestionIn":
        ids = [o.id for o in self.options]
        if len(set(ids)) != len(ids):
            raise ValueError("Mã phương án bị trùng")
        a, k = self.correct_answer, self.kind
        if k in (QuestionKind.single, QuestionKind.multi, QuestionKind.order) and len(ids) < 2:
            raise ValueError("Câu hỏi cần ít nhất hai phương án")
        if k == QuestionKind.single:
            ok = isinstance(a, str) and a in ids
        elif k == QuestionKind.multi:
            ok = _str_list(a) and bool(a) and len(set(a)) == len(a) and set(a) <= set(ids)
        elif k == QuestionKind.order:
            ok = _str_list(a) and sorted(a) == sorted(ids)
        elif k == QuestionKind.match:
            left = {o.id for o in self.options if o.side == "left"}
            right = {o.id for o in self.options if o.side == "right"}
            ok = (
                isinstance(a, dict)
                and bool(left)
                and set(a) == left
                and all(isinstance(v, str) and v in right for v in a.values())
            )
        else:  # map_pick
            ok = (
                isinstance(a, dict)
                and set(a) == {"lat", "lon"}
                and _is_num(a["lat"])
                and _is_num(a["lon"])
                and -90 <= a["lat"] <= 90
                and -180 <= a["lon"] <= 180
                and self.tolerance_km is not None
            )
        if not ok:
            raise ValueError(f"Đáp án đúng không khớp loại câu hỏi '{k.value}'")
        return self


class QuestIn(_In):
    level_id: uuid.UUID
    order_no: OrderNo
    title: Title
    central_question: LongText
    answer_summary: LongText | None = None
    is_optional: bool = False  # Req 9.5
    unlock_rule: JsonObj | None = None


class ObjectiveIn(_In):
    quest_id: uuid.UUID
    order_no: OrderNo
    kind: ObjectiveKind
    title: Title
    target_id: uuid.UUID | None = None
    required: bool = True

    @model_validator(mode="after")
    def _target(self) -> "ObjectiveIn":
        if self.kind != ObjectiveKind.timeline and self.target_id is None:
            raise ValueError("Mục tiêu cần target_id (trừ loại timeline)")
        return self


class BadgeIn(_In):
    name: Title
    description: LongText
    media_id: uuid.UUID | None = None
    condition: JsonObj

    @model_validator(mode="after")
    def _condition(self) -> "BadgeIn":
        if not isinstance(self.condition.get("type"), str):
            raise ValueError("Điều kiện Huy hiệu cần khóa 'type'")
        return self


# ---------------------------------------------------------------- trích dẫn, thẩm định


class CitationIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: uuid.UUID | None = None
    locator: Annotated[str, Field(max_length=500)] | None = None
    field_path: Annotated[str, Field(max_length=128)] = "*"
    quote: Annotated[str, Field(max_length=2000)] | None = None
    is_verbatim_quote: bool = False


class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    field_path: str
    locator: str
    quote: str | None
    is_verbatim_quote: bool


class ApproveIn(BaseModel):
    # Req 3.3: xác nhận đáp án theo phương án mặc định của Ghi_Chú_Sử_Học
    confirm_historian_note: bool = False


class RejectIn(BaseModel):
    reason: Annotated[str, Field(min_length=1, max_length=1000)]


# ---------------------------------------------------------------- đầu ra


class ContentOut(BaseModel):
    id: uuid.UUID
    type: ContentType
    status: ContentStatus
    is_fiction: bool
    author_id: uuid.UUID | None
    last_editor_id: uuid.UUID | None
    published_version_id: uuid.UUID | None
    hidden_by_report: bool
    created_at: datetime
    updated_at: datetime
    data: dict[str, Any]
    citations: list[CitationOut] = []


class ContentPage(BaseModel):
    items: list[ContentOut]
    total: int
    page: int
    page_size: int


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_no: int
    editor_id: uuid.UUID | None
    status_at_save: ContentStatus
    created_at: datetime
    is_published: bool = False


class VersionDetailOut(VersionOut):
    snapshot: dict[str, Any]


class FieldDiff(BaseModel):
    field: str
    before: Any
    after: Any


class DiffOut(BaseModel):
    a: int
    b: int
    changes: list[FieldDiff]


class ImportedRow(BaseModel):
    row: int
    type: ContentType
    id: uuid.UUID


class ImportRowError(BaseModel):
    row: int
    type: str | None
    errors: list[dict[str, Any]]


class ImportReport(BaseModel):
    total: int
    imported: list[ImportedRow]
    errors: list[ImportRowError]
