"""Đọc ảnh chụp Đã_Xuất_Bản của nội dung (Req 5.5).

Máy chủ chấm điểm và tính mở khóa theo đúng bản đang chạy trong Content_Bundle,
không theo giá trị đang được Biên_Tập_Viên sửa.
"""

import uuid
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.models import (
    Citation,
    ContentMixin,
    ContentStatus,
    ContentVersion,
    Event,
    Fragment,
    Level,
    Objective,
    Place,
    Quest,
    Question,
    Source,
    SourceStatus,
)

Snap = dict[str, Any]


async def published(
    session: AsyncSession, model: type[ContentMixin], *conds: ColumnElement[bool]
) -> dict[str, Snap]:
    """id → ảnh chụp đã xuất bản (kèm `id`, `_hidden`) của thực thể chưa lưu trữ."""
    rows = await session.execute(
        select(model.id, model.hidden_by_report, ContentVersion.snapshot)
        .join(ContentVersion, ContentVersion.id == model.published_version_id)
        .where(model.status != ContentStatus.archived, *conds)
    )
    return {str(i): {**snap, "id": str(i), "_hidden": hidden} for i, hidden, snap in rows}


def by_snapshot(key: str, value: str) -> ColumnElement[bool]:
    return ContentVersion.snapshot[key].astext == value


async def load_levels(session: AsyncSession) -> list[Snap]:
    """Mọi Màn_Chơi đã xuất bản ở dạng giống Content_Bundle, sắp theo `order_no`.

    Chỉ gồm phần QuestEngine cần: level, quests (kèm objectives), places, events, fragments.
    """
    levels = await published(session, Level)
    quests = await published(session, Quest)
    objectives = await published(session, Objective)
    places = await published(session, Place)
    events = await published(session, Event)
    fragments = await published(session, Fragment)

    obj_by_quest: dict[str, list[Snap]] = {}
    for o in objectives.values():
        obj_by_quest.setdefault(str(o["quest_id"]), []).append(o)

    out: list[Snap] = []
    for lid, lv in levels.items():
        lv_events = [e for e in events.values() if str(e.get("level_id")) == lid]
        event_ids = {e["id"] for e in lv_events}
        out.append(
            {
                "level": lv,
                "quests": [
                    {**q, "objectives": obj_by_quest.get(qid, [])}
                    for qid, q in quests.items()
                    if str(q["level_id"]) == lid
                ],
                "places": [places[str(p)] for p in lv.get("place_ids", []) if str(p) in places],
                "events": lv_events,
                "fragments": [f for f in fragments.values() if str(f["event_id"]) in event_ids],
            }
        )
    out.sort(key=lambda b: (b["level"]["order_no"], b["level"]["id"]))
    return out


async def load_question(session: AsyncSession, question_id: uuid.UUID) -> Snap:
    """Câu_Hỏi đã xuất bản, chưa bị ẩn do báo lỗi (Req 7.3); ngược lại 404."""
    q = await session.get(Question, question_id)
    if (
        q is None
        or q.published_version_id is None
        or q.status == ContentStatus.archived
        or q.hidden_by_report
    ):
        raise AppError(404, "QUESTION_NOT_FOUND", "Không tìm thấy câu hỏi")
    version = await session.get(ContentVersion, q.published_version_id)
    assert version is not None
    return {**version.snapshot, "id": str(q.id)}


async def question_citations(session: AsyncSession, question_id: uuid.UUID) -> list[Snap]:
    """Trích_Dẫn của Câu_Hỏi (gồm phần giải thích) từ nguồn đã duyệt (Req 16.2)."""
    rows = await session.execute(
        select(Citation, Source)
        .join(Source, Source.id == Citation.source_id)
        .where(
            Citation.entity_type == Question.__tablename__,
            Citation.entity_id == question_id,
            Source.status == SourceStatus.approved,
        )
        .order_by(Citation.created_at, Citation.id)
    )
    return [
        {
            "id": str(c.id),
            "field_path": c.field_path,
            "locator": c.locator,
            "quote": c.quote,
            "is_verbatim_quote": c.is_verbatim_quote,
            "source": {
                "id": str(s.id),
                "title": s.title,
                "authors": s.authors,
                "translators": s.translators,
                "publisher": s.publisher,
                "year": s.year,
                "edition": s.edition,
                "volume": s.volume,
                "tier": s.tier,
            },
        }
        for c, s in rows
    ]
