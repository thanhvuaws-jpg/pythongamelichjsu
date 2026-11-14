"""Dựng Content_Bundle của một Màn_Chơi (Req 5.1, 7.3, 16.3, 29.1–29.3).

Nguyên tắc:
- Mọi thực thể lấy từ ảnh chụp `published_version_id`, không lấy giá trị đang sửa, nên
  nội dung Đã_Xuất_Bản được chỉnh sửa vẫn giữ bản cũ trong bundle (Req 5.5).
- Tham chiếu cứng của Màn_Chơi phải có bản xuất bản, nếu không thì 409
  `UNPUBLISHED_REFERENCES` kèm danh sách thiếu (Req 29.1–29.2): chính Màn_Chơi; Nhiệm_Vụ,
  Sự_Kiện, Lớp_Bản_Đồ thuộc màn; Mục_Tiêu của Nhiệm_Vụ và đích của Mục_Tiêu; Địa_Điểm,
  Nhân_Vật, Sự_Kiện, media mà các thực thể trên trỏ tới.
- Mảnh_Ghép/Câu_Hỏi chỉ gắn với Sự_Kiện (không phải đích Mục_Tiêu) mà chưa xuất bản là
  bản đang soạn, không được đưa vào bundle và không chặn xuất bản.
- Câu_Hỏi bỏ `correct_answer`, `explanation`, `answer_basis` (Req 16.3); Câu_Hỏi đang
  `hidden_by_report` bị loại (Req 7.3). Trích dẫn trường `explanation` cũng bị loại vì
  giải thích chỉ trả về qua `POST /answers`.
- Nội dung bundle được mã hóa JSON ổn định (sort_keys) để sha256 lặp lại được.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.registry import ContentKind, kind_of
from app.errors import AppError
from app.models import (
    ATTRIBUTION_REQUIRED,
    Bundle,
    Citation,
    ContentStatus,
    ContentVersion,
    Event,
    HistorianNote,
    Level,
    MapLayer,
    Media,
    Objective,
    ObjectiveKind,
    Quest,
    Source,
    SourceStatus,
    User,
)
from app.schemas.content import ContentType
from app.storage import Storage, StorageError

BUNDLE_FORMAT = 1
# Trường câu hỏi được phép đưa ra client; mọi trường khác (đáp án, giải thích) bị loại
QUESTION_PUBLIC_FIELDS = ("event_id", "kind", "difficulty", "prompt", "options", "is_fiction")
HIDDEN_CITATION_FIELDS = {ContentType.questions: {"explanation"}}

OBJECTIVE_TARGET: dict[ObjectiveKind, ContentType] = {
    ObjectiveKind.go_to: ContentType.places,
    ObjectiveKind.collect: ContentType.fragments,
    ObjectiveKind.dialogue: ContentType.dialogues,
    ObjectiveKind.answer: ContentType.questions,
}

Snap = dict[str, Any]


def bundle_path(level_id: uuid.UUID, version_no: int, bundle_id: uuid.UUID) -> str:
    # Hậu tố id để lần thử lại sau khi commit lỗi không đụng tệp đã tải (Storage không ghi đè)
    return f"bundles/level_{level_id}/v{version_no}-{bundle_id.hex[:12]}.json"


def encode_bundle(bundle: dict[str, Any]) -> tuple[bytes, str]:
    """JSON UTF-8 ổn định và sha256 hex của nó."""
    data = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return data, hashlib.sha256(data).hexdigest()


def _option_key(question_id: str, option: Snap) -> str:
    return hashlib.sha256(f"{question_id}:{option.get('id')}".encode()).hexdigest()


def public_question(q: Snap) -> Snap:
    """Chỉ giữ trường công khai. Phương án được sắp theo băm (ổn định, không liên quan
    đáp án) để câu sắp xếp thứ tự không lộ đáp án qua thứ tự đã soạn."""
    out = {"id": q["id"], **{k: q.get(k) for k in QUESTION_PUBLIC_FIELDS}}
    out["options"] = sorted(q.get("options") or [], key=lambda o: _option_key(q["id"], o))
    return out


def event_out(e: Snap) -> Snap:
    """Gom Mốc_Thời_Gian thành `date` theo định dạng bundle."""
    out = {
        k: v
        for k, v in e.items()
        if k not in ("date_start", "date_end", "date_precision", "lunar_date_text")
    }
    out["date"] = (
        {
            "start": e["date_start"],
            "end": e.get("date_end") or e["date_start"],
            "precision": e["date_precision"],
            "lunar_text": e.get("lunar_date_text"),
        }
        if e.get("date_start")
        else None
    )
    return out


def _ids(values: Any) -> set[str]:
    return {str(v) for v in values if v}


@dataclass
class _Collector:
    """Tải ảnh chụp đã xuất bản và ghi lại tham chiếu còn thiếu."""

    session: AsyncSession
    missing: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    loaded: dict[ContentType, dict[str, Snap]] = field(default_factory=dict)
    hidden: set[str] = field(default_factory=set)

    def bucket(self, slug: ContentType) -> dict[str, Snap]:
        return self.loaded.setdefault(slug, {})

    def miss(self, slug: str, id_: str, status: str, ref: str) -> None:
        entry = {"type": slug, "id": id_, "status": status, "ref": ref}
        self.missing.setdefault((slug, id_), entry)

    async def _query(self, kind: ContentKind, *conds: ColumnElement[bool]) -> dict[str, Snap]:
        model = kind.model
        rows = await self.session.execute(
            select(model.id, model.hidden_by_report, ContentVersion.snapshot)
            .join(ContentVersion, ContentVersion.id == model.published_version_id)
            .where(model.status != ContentStatus.archived, *conds)
        )
        out: dict[str, Snap] = {}
        for id_, hidden, snap in rows:
            out[str(id_)] = {"id": str(id_), **snap}
            if hidden:
                self.hidden.add(str(id_))
        self.bucket(kind.slug).update(out)
        return out

    async def where_snapshot(
        self, slug: ContentType, key: str, values: set[str]
    ) -> dict[str, Snap]:
        """Thực thể đã xuất bản có `snapshot[key]` thuộc `values`."""
        if not values:
            return {}
        kind = kind_of(slug)
        return await self._query(kind, ContentVersion.snapshot[key].astext.in_(sorted(values)))

    async def by_ids(self, slug: ContentType, ids: set[str], ref: str) -> dict[str, Snap]:
        """Tải theo id; id không có bản xuất bản bị ghi vào danh sách thiếu."""
        have = self.bucket(slug)
        need = {i for i in ids if i not in have}
        if need:
            kind = kind_of(slug)
            await self._query(kind, kind.model.id.in_([uuid.UUID(i) for i in need]))
            await self._record_missing(kind, need - set(have), ref)
        return {i: have[i] for i in ids if i in have}

    async def unpublished_members(
        self, slug: ContentType, cond: ColumnElement[bool], ref: str
    ) -> None:
        """Thành viên (theo cột hiện tại) chưa từng được xuất bản cũng chặn xuất bản."""
        model = kind_of(slug).model
        rows = await self.session.execute(
            select(model.id, model.status).where(
                cond, model.published_version_id.is_(None), model.status != ContentStatus.archived
            )
        )
        for id_, status in rows:
            self.miss(slug.value, str(id_), status.value, ref)

    async def _record_missing(self, kind: ContentKind, ids: set[str], ref: str) -> None:
        if not ids:
            return
        rows = await self.session.execute(
            select(kind.model.id, kind.model.status).where(
                kind.model.id.in_([uuid.UUID(i) for i in ids])
            )
        )
        found = {str(i): s.value for i, s in rows}
        for i in ids:
            self.miss(kind.slug.value, i, found.get(i, "not_found"), ref)


async def _citations(
    session: AsyncSession, loaded: dict[ContentType, dict[str, Snap]]
) -> tuple[dict[str, Snap], dict[str, Snap], dict[tuple[str, str], list[str]]]:
    """Trích dẫn (nguồn đã duyệt) của mọi thực thể trong bundle."""
    citations: dict[str, Snap] = {}
    sources: dict[str, Snap] = {}
    by_entity: dict[tuple[str, str], list[str]] = {}
    for slug, items in loaded.items():
        if not items:
            continue
        kind = kind_of(slug)
        hidden_fields = HIDDEN_CITATION_FIELDS.get(slug, set())
        rows = await session.execute(
            select(Citation, Source)
            .join(Source, Source.id == Citation.source_id)
            .where(
                Citation.entity_type == kind.entity_type,
                Citation.entity_id.in_([uuid.UUID(i) for i in items]),
                Source.status == SourceStatus.approved,
            )
            .order_by(Citation.created_at, Citation.id)
        )
        for cit, src in rows:
            if cit.field_path in hidden_fields:
                continue
            cid, sid = str(cit.id), str(src.id)
            citations[cid] = {
                "source_id": sid,
                "field_path": cit.field_path,
                "locator": cit.locator,
                "quote": cit.quote,
                "is_verbatim_quote": cit.is_verbatim_quote,
            }
            sources[sid] = {
                "title": src.title,
                "authors": src.authors,
                "translators": src.translators,
                "publisher": src.publisher,
                "year": src.year,
                "edition": src.edition,
                "volume": src.volume,
                "tier": src.tier,
            }
            by_entity.setdefault((slug.value, str(cit.entity_id)), []).append(cid)
    return citations, sources, by_entity


async def _media(
    session: AsyncSession, storage: Storage, ids: set[str], col: _Collector
) -> dict[str, Snap]:
    if not ids:
        return {}
    rows = await session.scalars(select(Media).where(Media.id.in_([uuid.UUID(i) for i in ids])))
    out = {
        str(m.id): {
            "url": storage.public_url(m.storage_path),
            "mime": m.mime,
            "owner": m.owner,
            "license": m.license.value,
            "license_url": m.license_url,
            "source_url": m.source_url,
            "attribution": m.attribution,
            "attribution_required": m.license in ATTRIBUTION_REQUIRED,  # Req 8.3
        }
        for m in rows
    }
    for i in ids - set(out):
        col.miss("media", i, "not_found", "media")
    return out


async def build_bundle(
    session: AsyncSession, level: Level, version_no: int, storage: Storage
) -> dict[str, Any]:
    """Dựng dict bundle; ném 409 UNPUBLISHED_REFERENCES nếu thiếu tham chiếu."""
    col = _Collector(session)
    lid = str(level.id)
    T = ContentType

    level_snap = (await col.by_ids(T.levels, {lid}, "level")).get(lid)

    quests = await col.where_snapshot(T.quests, "level_id", {lid})
    await col.unpublished_members(T.quests, Quest.level_id == level.id, "level.quests")
    objectives = await col.where_snapshot(T.objectives, "quest_id", set(quests))
    quest_uuids = [uuid.UUID(q) for q in quests]
    if quest_uuids:
        await col.unpublished_members(
            T.objectives, Objective.quest_id.in_(quest_uuids), "quest.objectives"
        )
    events = await col.where_snapshot(T.events, "level_id", {lid})
    await col.unpublished_members(T.events, Event.level_id == level.id, "level.events")
    map_layers = await col.where_snapshot(T.map_layers, "level_id", {lid})
    await col.unpublished_members(T.map_layers, MapLayer.level_id == level.id, "level.map_layers")

    # Đích của Mục_Tiêu
    targets: dict[ContentType, set[str]] = {}
    for o in objectives.values():
        slug = OBJECTIVE_TARGET.get(ObjectiveKind(o["kind"]))
        if slug and o.get("target_id"):
            targets.setdefault(slug, set()).add(str(o["target_id"]))

    fragments = dict(await col.where_snapshot(T.fragments, "event_id", set(events)))
    fragments |= await col.by_ids(T.fragments, targets.get(T.fragments, set()), "objective.target")
    questions = dict(await col.where_snapshot(T.questions, "event_id", set(events)))
    questions |= await col.by_ids(T.questions, targets.get(T.questions, set()), "objective.target")
    questions = {k: v for k, v in questions.items() if k not in col.hidden}  # Req 7.3
    dialogues = dict(
        await col.by_ids(T.dialogues, targets.get(T.dialogues, set()), "objective.target")
    )
    # Hội_Thoại đã xuất bản đặt tại Địa_Điểm của màn (Req 11.2)
    level_places = _ids(level_snap["place_ids"]) if level_snap else set()
    dialogues |= await col.where_snapshot(T.dialogues, "place_id", level_places)

    # Sự_Kiện của Mảnh_Ghép/Câu_Hỏi là đích Mục_Tiêu nhưng thuộc màn khác
    extra_events = _ids(x["event_id"] for x in [*fragments.values(), *questions.values()])
    events = dict(events) | await col.by_ids(T.events, extra_events - set(events), "content.event")

    place_ids = _ids(level_snap["place_ids"] if level_snap else [])
    place_ids |= _ids(e.get("place_id") for e in events.values())
    place_ids |= _ids(f.get("place_id") for f in fragments.values())
    place_ids |= _ids(d.get("place_id") for d in dialogues.values())
    place_ids |= targets.get(T.places, set())
    places = await col.by_ids(T.places, place_ids, "place")

    person_ids = _ids(p for e in events.values() for p in e.get("person_ids", []))
    person_ids |= _ids(d.get("speaker_person_id") for d in dialogues.values())
    persons = await col.by_ids(T.persons, person_ids, "person")

    links = await col.where_snapshot(T.causal_links, "from_event_id", set(events))
    links = {k: v for k, v in links.items() if str(v["to_event_id"]) in events}

    media_ids = _ids(f.get("media_id") for f in fragments.values())
    media_ids |= _ids(p.get("portrait_media_id") for p in persons.values())
    media_ids |= _ids(m.get("media_id") for m in map_layers.values())
    media = await _media(session, storage, media_ids, col)

    if col.missing:
        missing = sorted(col.missing.values(), key=lambda m: (m["type"], m["id"]))
        raise AppError(
            409,
            "UNPUBLISHED_REFERENCES",
            f"Màn chơi tham chiếu {len(missing)} nội dung chưa ở trạng thái Đã xuất bản",
            {"missing": missing},
        )
    assert level_snap is not None

    # Chỉ lấy trích dẫn của thực thể thực sự có trong bundle
    col.loaded[T.questions] = questions
    col.loaded[T.causal_links] = links
    citations, sources, by_entity = await _citations(session, col.loaded)

    def with_cits(slug: ContentType, items: dict[str, Snap]) -> list[Snap]:
        return [
            {**v, "citations": by_entity.get((slug.value, k), [])} for k, v in sorted(items.items())
        ]

    notes: dict[str, list[Snap]] = {}
    if events:
        rows = await session.scalars(
            select(HistorianNote)
            .where(HistorianNote.event_id.in_([uuid.UUID(e) for e in events]))
            .order_by(HistorianNote.created_at)
        )
        for n in rows:
            variants = [
                {**v, "citation_ids": [c for c in v.get("citation_ids", []) if c in citations]}
                for v in n.variants
            ]
            notes.setdefault(str(n.event_id), []).append(
                {
                    "id": str(n.id),
                    "field_path": n.field_path,
                    "variants": variants,
                    "default_variant_idx": n.default_variant_idx,
                    "note": n.note,
                }
            )

    frag_by_event: dict[str, list[str]] = {}
    for k, f in sorted(fragments.items()):
        frag_by_event.setdefault(str(f["event_id"]), []).append(k)
    q_by_event: dict[str, list[str]] = {}
    for k, q in sorted(questions.items()):
        q_by_event.setdefault(str(q["event_id"]), []).append(k)

    obj_by_quest: dict[str, list[Snap]] = {}
    for o in sorted(objectives.values(), key=lambda o: (o["order_no"], o["id"])):
        obj_by_quest.setdefault(str(o["quest_id"]), []).append(o)

    return {
        "format": BUNDLE_FORMAT,
        "level": {**level_snap, "version": version_no},
        "places": with_cits(T.places, places),
        "persons": with_cits(T.persons, persons),
        "events": [
            {
                **event_out(e),
                "historian_notes": notes.get(e["id"], []),
                "fragment_ids": frag_by_event.get(e["id"], []),
                "question_ids": q_by_event.get(e["id"], []),
            }
            for e in with_cits(T.events, events)
        ],
        "causal_links": with_cits(T.causal_links, links),
        "fragments": with_cits(T.fragments, fragments),
        "dialogues": with_cits(T.dialogues, dialogues),
        "questions": [
            {**public_question(q), "citations": q["citations"]}
            for q in with_cits(T.questions, questions)
        ],
        "quests": [
            {**q, "objectives": obj_by_quest.get(q["id"], [])}
            for q in sorted(with_cits(T.quests, quests), key=lambda q: (q["order_no"], q["id"]))
        ],
        "map_layers": with_cits(T.map_layers, map_layers),
        "citations": citations,
        "sources": sources,
        "media": media,
    }


async def publish_level(
    session: AsyncSession, level_id: uuid.UUID, actor: User, storage: Storage
) -> Bundle:
    """Kiểm tra, dựng, tải bundle lên Storage và ghi bảng `bundles` (Req 29.3).

    Khóa hàng Màn_Chơi để hai lần xuất bản đồng thời không trùng `version_no`.
    Commit do router thực hiện.
    """
    level = await session.scalar(select(Level).where(Level.id == level_id).with_for_update())
    if level is None:
        raise AppError(404, "CONTENT_NOT_FOUND", "Không tìm thấy Màn chơi")
    current = await session.scalar(
        select(func.max(Bundle.version_no)).where(Bundle.level_id == level_id)
    )
    version_no = (current or 0) + 1
    bundle = await build_bundle(session, level, version_no, storage)
    data, digest = encode_bundle(bundle)
    bundle_id = uuid.uuid4()
    path = bundle_path(level_id, version_no, bundle_id)
    try:
        await storage.put(path, data, "application/json")
    except StorageError as exc:
        raise AppError(
            502, "STORAGE_UNAVAILABLE", "Không tải được gói nội dung lên, vui lòng thử lại"
        ) from exc
    row = Bundle(
        id=bundle_id,
        level_id=level_id,
        version_no=version_no,
        storage_path=path,
        sha256=digest,
        size_bytes=len(data),
        created_by=actor.id,
    )
    session.add(row)
    return row
