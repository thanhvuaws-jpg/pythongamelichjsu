"""Ánh xạ slug `/content/{type}` → model + schema. `entity_type` là tên bảng."""

from dataclasses import dataclass

from pydantic import BaseModel

from app.models import (
    Badge,
    CausalLink,
    ContentMixin,
    Dialogue,
    Event,
    Fragment,
    Level,
    MapLayer,
    Objective,
    Person,
    Place,
    Quest,
    Question,
)
from app.schemas.content import (
    BadgeIn,
    CausalLinkIn,
    ContentType,
    DialogueIn,
    EventIn,
    FragmentIn,
    LevelIn,
    MapLayerIn,
    ObjectiveIn,
    PersonIn,
    PlaceIn,
    QuestIn,
    QuestionIn,
)


@dataclass(frozen=True)
class ContentKind:
    slug: ContentType
    model: type[ContentMixin]
    schema: type[BaseModel]

    @property
    def entity_type(self) -> str:
        return self.model.__tablename__  # type: ignore[attr-defined]

    @property
    def fields(self) -> list[str]:
        return list(self.schema.model_fields)


REGISTRY: dict[ContentType, ContentKind] = {
    k.slug: k
    for k in (
        ContentKind(ContentType.levels, Level, LevelIn),
        ContentKind(ContentType.places, Place, PlaceIn),
        ContentKind(ContentType.persons, Person, PersonIn),
        ContentKind(ContentType.events, Event, EventIn),
        ContentKind(ContentType.causal_links, CausalLink, CausalLinkIn),
        ContentKind(ContentType.map_layers, MapLayer, MapLayerIn),
        ContentKind(ContentType.fragments, Fragment, FragmentIn),
        ContentKind(ContentType.dialogues, Dialogue, DialogueIn),
        ContentKind(ContentType.questions, Question, QuestionIn),
        ContentKind(ContentType.quests, Quest, QuestIn),
        ContentKind(ContentType.objectives, Objective, ObjectiveIn),
        ContentKind(ContentType.badges, Badge, BadgeIn),
    )
}


def kind_of(slug: ContentType) -> ContentKind:
    return REGISTRY[slug]
