"""Máy trạng thái thẩm định (Req 2.2, 3.3, 5.2–5.4).

    draft ──submit──▶ pending ──approve──▶ published
      ▲                  │
      └─────reject───────┘
    published ──sửa──▶ draft (published_version_id giữ nguyên, Req 5.5)

Quy tắc nguồn (`check_submit_rules`) chạy khi submit và chạy lại khi approve vì nguồn có
thể bị gỡ khỏi danh mục giữa chừng. Mọi thao tác ghi `review_actions` và `audit_log`
trong cùng giao dịch với thay đổi trạng thái.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.registry import ContentKind
from app.content.service import latest_version
from app.content.validators import (
    CitationFact,
    SubmitSubject,
    Violation,
    check_submit_rules,
    raise_if_violations,
)
from app.errors import AppError
from app.models import (
    AuditLog,
    Citation,
    ContentMixin,
    ContentStatus,
    Dialogue,
    Event,
    Fragment,
    HistorianNote,
    Notification,
    Question,
    ReviewAction,
    ReviewActionKind,
    Source,
    User,
)
from app.reports.service import resolve_on_approval

# action → (trạng thái nguồn hợp lệ, trạng thái đích)
TRANSITIONS: dict[ReviewActionKind, tuple[ContentStatus, ContentStatus]] = {
    ReviewActionKind.submit: (ContentStatus.draft, ContentStatus.pending),
    ReviewActionKind.approve: (ContentStatus.pending, ContentStatus.published),
    ReviewActionKind.reject: (ContentStatus.pending, ContentStatus.draft),
}

_TRANSITION_MSG = {
    ReviewActionKind.submit: "Chỉ gửi thẩm định được nội dung ở trạng thái Bản nháp",
    ReviewActionKind.approve: "Chỉ phê duyệt được nội dung đang Chờ thẩm định",
    ReviewActionKind.reject: "Chỉ từ chối được nội dung đang Chờ thẩm định",
}


def next_status(current: ContentStatus, action: ReviewActionKind) -> ContentStatus:
    source, target = TRANSITIONS[action]
    if current != source:
        raise AppError(
            409,
            "INVALID_TRANSITION",
            _TRANSITION_MSG[action],
            {"status": current.value, "action": action.value},
        )
    return target


def ensure_not_self_review(entity: ContentMixin, reviewer: User) -> None:
    """Req 5.3: tác giả hoặc người sửa gần nhất không được tự duyệt."""
    if reviewer.id in (entity.author_id, entity.last_editor_id):
        raise AppError(
            403,
            "SELF_APPROVAL",
            "Không thể phê duyệt nội dung do chính mình soạn hoặc chỉnh sửa gần nhất",
        )


# ---------------------------------------------------------------- dựng SubmitSubject


async def citation_facts(
    session: AsyncSession, kind: ContentKind, entity_id: uuid.UUID
) -> tuple[list[CitationFact], list[uuid.UUID]]:
    rows = await session.execute(
        select(Citation, Source)
        .join(Source, Source.id == Citation.source_id)
        .where(Citation.entity_type == kind.entity_type, Citation.entity_id == entity_id)
    )
    facts, ids = [], []
    for cit, src in rows:
        ids.append(cit.id)
        facts.append(
            CitationFact(
                source_id=src.id,
                source_status=src.status,
                tier=src.tier,
                field_path=cit.field_path,
                is_verbatim_quote=cit.is_verbatim_quote,
            )
        )
    return facts, ids


async def _basis_is_fiction(
    session: AsyncSession, question: Question, extra: list[Violation]
) -> bool:
    """Câu hỏi dựa vào hư cấu khi bản thân nó hoặc một căn cứ đáp án có cờ hư cấu (Req 4.4)."""
    fiction = question.is_fiction
    for basis in question.answer_basis or []:
        target_id = uuid.UUID(str(basis["id"]))
        if basis["type"] == "fragments":
            frag = await session.get(Fragment, target_id)
            if frag is None:
                extra.append(Violation("ANSWER_BASIS_NOT_FOUND", "Không tìm thấy Mảnh ghép căn cứ"))
                continue
            fiction |= frag.is_fiction
        else:
            dlg = await session.get(Dialogue, target_id)
            if dlg is None:
                extra.append(Violation("ANSWER_BASIS_NOT_FOUND", "Không tìm thấy Hội thoại căn cứ"))
                continue
            node_id = basis.get("node_id")
            nodes = [n for n in dlg.nodes if node_id is None or n.get("id") == node_id]
            if node_id is not None and not nodes:
                extra.append(
                    Violation("ANSWER_BASIS_NOT_FOUND", f"Không tìm thấy node '{node_id}'")
                )
            fiction |= dlg.is_fiction or any(n.get("is_fiction", True) for n in nodes)
    return fiction


async def build_subject(
    session: AsyncSession, kind: ContentKind, entity: ContentMixin
) -> tuple[SubmitSubject, list[Violation]]:
    """Trả về subject cho `check_submit_rules` và vi phạm phát sinh khi tra tham chiếu."""
    extra: list[Violation] = []
    strict: list[str] = []
    verbatim: list[str] = []
    event_published: bool | None = None
    depends_on_fiction = False

    if isinstance(entity, Event):
        if entity.date_start is not None:
            strict.append("date")  # Req 2.3: Mốc_Thời_Gian
        strict += [f"numeric_facts.{k}" for k in entity.numeric_facts or {}]
    elif isinstance(entity, Dialogue):
        verbatim += [f"node:{n['id']}" for n in entity.nodes if n.get("is_verbatim_quote")]
    elif isinstance(entity, Question):
        event = await session.get(Event, entity.event_id)
        # Sự kiện đang được sửa lại vẫn có bản Đã_Xuất_Bản chạy trong bundle
        event_published = event is not None and (
            event.status == ContentStatus.published or event.published_version_id is not None
        )
        depends_on_fiction = await _basis_is_fiction(session, entity, extra)
        if entity.historian_note_id is not None:
            note = await session.get(HistorianNote, entity.historian_note_id)
            if note is None or note.event_id != entity.event_id:
                extra.append(
                    Violation(
                        "HISTORIAN_NOTE_MISMATCH",
                        "Ghi chú sử học không thuộc Sự kiện của câu hỏi",
                        "historian_note_id",
                    )
                )

    subject = SubmitSubject(
        entity_type=kind.entity_type,
        is_fiction=entity.is_fiction,
        strict_fields=tuple(strict),
        verbatim_fields=tuple(verbatim),
        event_published=event_published,
        depends_on_fiction=depends_on_fiction,
    )
    return subject, extra


async def check_rules(
    session: AsyncSession, kind: ContentKind, entity: ContentMixin
) -> list[uuid.UUID]:
    """Ném 422 nếu vi phạm; trả về id trích dẫn đã kiểm tra."""
    subject, extra = await build_subject(session, kind, entity)
    facts, ids = await citation_facts(session, kind, entity.id)
    raise_if_violations([*check_submit_rules(subject, facts), *extra])
    return ids


# ---------------------------------------------------------------- thao tác


def _record(
    session: AsyncSession,
    kind: ContentKind,
    entity: ContentMixin,
    actor: User,
    action: ReviewActionKind,
    before: ContentStatus,
    version_id: uuid.UUID | None,
    reason: str | None = None,
    checked: list[uuid.UUID] | None = None,
) -> None:
    session.add(
        ReviewAction(
            id=uuid.uuid4(),
            entity_type=kind.entity_type,
            entity_id=entity.id,
            version_id=version_id,
            reviewer_id=actor.id,
            action=action,
            reason=reason,
            checked_citation_ids=checked or [],
        )
    )
    session.add(
        AuditLog(
            actor_id=actor.id,
            action=f"content_{action.value}",
            target_type=kind.entity_type,
            target_id=str(entity.id),
            before={"status": before.value},
            after={
                "status": entity.status.value,
                "version_id": str(version_id) if version_id else None,
                "reason": reason,
            },
        )
    )


async def submit(
    session: AsyncSession, kind: ContentKind, entity: ContentMixin, actor: User
) -> None:
    before = entity.status
    target = next_status(before, ReviewActionKind.submit)
    checked = await check_rules(session, kind, entity)
    version = await latest_version(session, kind, entity.id)
    entity.status = target
    _record(
        session,
        kind,
        entity,
        actor,
        ReviewActionKind.submit,
        before,
        version and version.id,
        checked=checked,
    )


async def approve(
    session: AsyncSession,
    kind: ContentKind,
    entity: ContentMixin,
    reviewer: User,
    confirm_historian_note: bool,
) -> None:
    before = entity.status
    target = next_status(before, ReviewActionKind.approve)
    ensure_not_self_review(entity, reviewer)
    checked = await check_rules(session, kind, entity)
    if isinstance(entity, Question) and entity.historian_note_id and not confirm_historian_note:
        raise AppError(  # Req 3.3
            422,
            "HISTORIAN_NOTE_UNCONFIRMED",
            "Câu hỏi kiểm tra trường có Ghi chú sử học; cần xác nhận đáp án theo phương án "
            "mặc định trước khi xuất bản",
            {"historian_note_id": str(entity.historian_note_id)},
        )
    version = await latest_version(session, kind, entity.id)
    if version is None:
        raise AppError(409, "INVALID_TRANSITION", "Nội dung chưa có phiên bản để xuất bản")
    entity.status = target
    entity.published_version_id = version.id  # Req 5.2
    # Bản sửa được duyệt: đóng Báo_Cáo_Sai_Sót đã xác nhận, bỏ ẩn Câu_Hỏi (Req 7.3, 7.4)
    await resolve_on_approval(session, kind.entity_type, entity.id, reviewer)
    _record(
        session,
        kind,
        entity,
        reviewer,
        ReviewActionKind.approve,
        before,
        version.id,
        checked=checked,
    )


async def reject(
    session: AsyncSession, kind: ContentKind, entity: ContentMixin, reviewer: User, reason: str
) -> None:
    before = entity.status
    target = next_status(before, ReviewActionKind.reject)
    version = await latest_version(session, kind, entity.id)
    entity.status = target
    reason = reason.strip()
    _record(
        session,
        kind,
        entity,
        reviewer,
        ReviewActionKind.reject,
        before,
        version and version.id,
        reason=reason,
    )
    if entity.author_id is not None:  # Req 5.4: thông báo tác giả trong Admin_Portal
        session.add(
            Notification(
                id=uuid.uuid4(),
                user_id=entity.author_id,
                kind="content_rejected",
                payload={
                    "entity_type": kind.entity_type,
                    "type": kind.slug.value,
                    "entity_id": str(entity.id),
                    "reason": reason,
                    "reviewer_id": str(reviewer.id),
                },
            )
        )
