"""Schema API chơi game (Req 16.2, 18, 19, 20, 21)."""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

Id = Annotated[str, Field(min_length=1, max_length=64)]
IdList = Annotated[list[Id], Field(max_length=5000)]


class ProgressIn(BaseModel):
    """Phần tiến trình do Game_Client gửi. Trường mở khóa bị bỏ qua (máy chủ tự tính)."""

    model_config = ConfigDict(extra="ignore")

    completed_objectives: IdList = []
    collected_fragments: IdList = []
    clues: IdList = []
    current_level: Id | None = None
    map_pos: dict[str, Any] | None = None
    # {level_id: [event_id, ...]} thứ tự thẻ đang đặt
    timeline_state: dict[Id, IdList] | None = None
    tutorial_done: bool = False
    updated_at: datetime | None = None

    def to_data(self) -> dict[str, Any]:
        data = self.model_dump(mode="json", exclude_none=True)
        if self.updated_at is not None:
            # merge so sánh chuỗi ISO UTC theo thứ tự từ điển; giờ không múi coi như UTC
            ts = self.updated_at
            ts = ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts.astimezone(UTC)
            data["updated_at"] = ts.isoformat()
        return data


class AnswerIn(BaseModel):
    question_id: uuid.UUID
    answer: Any


class AnswerOut(BaseModel):
    correct: bool
    attempt_no: int
    points_awarded: int
    total_points: int
    already_scored: bool
    correct_answer: Any
    explanation: str
    citations: list[dict[str, Any]]
    added_to_review: bool
    new_badges: list[dict[str, Any]] = []


class TimelineCompleteIn(BaseModel):
    level_id: uuid.UUID
    mistakes: Annotated[int, Field(ge=0, le=10000)]


class TimelineCompleteOut(BaseModel):
    bonus_awarded: int
    total_points: int
    progress: dict[str, Any]
    new_badges: list[dict[str, Any]] = []


class ReviewQuestionOut(BaseModel):
    id: str
    event_id: str
    kind: str
    difficulty: int
    prompt: str
    options: list[dict[str, Any]]
    stage: int | None
    due_at: datetime
    last_result: bool | None


class ReviewSessionOut(BaseModel):
    level_id: uuid.UUID
    questions: list[ReviewQuestionOut]


class ReviewAnswerIn(AnswerIn):
    pass


class ReviewAnswerOut(BaseModel):
    correct: bool
    correct_answer: Any
    explanation: str
    citations: list[dict[str, Any]]
    event_id: str
    stage: int
    next_due_at: datetime
    review_points_awarded: int
    review_points_total: int


class BadgeOut(BaseModel):
    id: str
    name: str
    description: str
    media_id: str | None
    condition: dict[str, Any]
    earned: bool
    awarded_at: datetime | None


class NotificationOut(BaseModel):
    id: uuid.UUID
    kind: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime
