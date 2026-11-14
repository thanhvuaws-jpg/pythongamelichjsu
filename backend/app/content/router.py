"""CRUD chung `/api/v1/content/{type}` và trích dẫn của nội dung (Req 2.1, 5.5, 6.1, 28.1)."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, Response
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.content.registry import ContentKind, kind_of
from app.content.service import (
    create_entity,
    get_entity,
    mark_edited,
    save_fields,
    snapshot,
)
from app.content.validators import CitationDraft, SourceRef, ensure_valid_citation
from app.db import get_session
from app.errors import AppError
from app.models import Citation, ContentMixin, ContentStatus, Role, Source, User
from app.schemas.content import CitationIn, CitationOut, ContentOut, ContentPage, ContentType

router = APIRouter(prefix="/api/v1/content", tags=["content"])
Session = Annotated[AsyncSession, Depends(get_session)]
Editor = Annotated[User, Depends(require_role(Role.editor))]

PAGE_SIZE_MAX = 50


def validation_details(exc: ValidationError) -> dict[str, Any]:
    return {
        "fields": [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
            for e in exc.errors(include_url=False, include_input=False)
        ]
    }


def parse_payload(kind: ContentKind, payload: dict[str, Any]) -> Any:
    try:
        return kind.schema.model_validate(payload)
    except ValidationError as exc:
        raise AppError(
            422, "VALIDATION_ERROR", "Dữ liệu gửi lên không hợp lệ", validation_details(exc)
        ) from exc


async def load_citations(
    session: AsyncSession, kind: ContentKind, entity_id: uuid.UUID
) -> list[Citation]:
    rows = await session.scalars(
        select(Citation)
        .where(Citation.entity_type == kind.entity_type, Citation.entity_id == entity_id)
        .order_by(Citation.created_at)
    )
    return list(rows)


def content_out(
    kind: ContentKind, entity: ContentMixin, citations: list[Citation] | None = None
) -> ContentOut:
    return ContentOut(
        id=entity.id,
        type=kind.slug,
        status=entity.status,
        is_fiction=entity.is_fiction,
        author_id=entity.author_id,
        last_editor_id=entity.last_editor_id,
        published_version_id=entity.published_version_id,
        hidden_by_report=entity.hidden_by_report,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        data=snapshot(kind, entity),
        citations=[CitationOut.model_validate(c) for c in citations or []],
    )


async def content_response(
    session: AsyncSession, kind: ContentKind, entity: ContentMixin
) -> ContentOut:
    await session.refresh(entity)
    return content_out(kind, entity, await load_citations(session, kind, entity.id))


def _ensure_editable(entity: ContentMixin) -> None:
    if entity.status == ContentStatus.archived:
        raise AppError(409, "INVALID_TRANSITION", "Nội dung đã lưu trữ, không sửa được")


@router.get("/{type}", response_model=ContentPage)
async def list_content(
    type: ContentType,
    session: Session,
    _: Editor,
    status: ContentStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)] = PAGE_SIZE_MAX,
) -> ContentPage:
    kind = kind_of(type)
    stmt = select(kind.model)
    if status is not None:
        stmt = stmt.where(kind.model.status == status)
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await session.scalars(
        stmt.order_by(kind.model.updated_at.desc(), kind.model.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ContentPage(
        items=[content_out(kind, r) for r in rows], total=total, page=page, page_size=page_size
    )


@router.get("/{type}/{entity_id}", response_model=ContentOut)
async def get_content(
    type: ContentType, entity_id: uuid.UUID, session: Session, _: Editor
) -> ContentOut:
    kind = kind_of(type)
    entity = await get_entity(session, kind, entity_id)
    return content_out(kind, entity, await load_citations(session, kind, entity_id))


@router.post("/{type}", response_model=ContentOut, status_code=201)
async def create_content(
    type: ContentType,
    session: Session,
    user: Editor,
    payload: Annotated[dict[str, Any], Body()],
) -> ContentOut:
    kind = kind_of(type)
    entity, _ = await create_entity(session, kind, parse_payload(kind, payload), user)
    await session.commit()
    return await content_response(session, kind, entity)


@router.patch("/{type}/{entity_id}", response_model=ContentOut)
async def update_content(
    type: ContentType,
    entity_id: uuid.UUID,
    session: Session,
    user: Editor,
    payload: Annotated[dict[str, Any], Body()],
) -> ContentOut:
    """Hợp nhất trường gửi lên với giá trị hiện tại, kiểm tra lại toàn bộ rồi lưu Bản_Nháp."""
    kind = kind_of(type)
    entity = await get_entity(session, kind, entity_id, lock=True)
    _ensure_editable(entity)
    unknown = sorted(set(payload) - set(kind.fields))
    if unknown:
        raise AppError(
            422,
            "VALIDATION_ERROR",
            "Dữ liệu gửi lên không hợp lệ",
            {"fields": [{"loc": [f], "msg": "Trường không hợp lệ"} for f in unknown]},
        )
    data = parse_payload(kind, {**snapshot(kind, entity), **payload})
    await save_fields(session, kind, entity, data, user)
    await session.commit()
    return await content_response(session, kind, entity)


# ---------------------------------------------------------------- trích dẫn


async def _reopen_if_reviewed(
    session: AsyncSession, kind: ContentKind, entity: ContentMixin, user: User
) -> None:
    # Đổi trích dẫn của nội dung đang chờ duyệt/đã xuất bản → cần thẩm định lại
    if entity.status in (ContentStatus.pending, ContentStatus.published):
        await mark_edited(session, kind, entity, user)
    else:
        entity.last_editor_id = user.id


@router.post("/{type}/{entity_id}/citations", response_model=ContentOut, status_code=201)
async def add_citation(
    type: ContentType, entity_id: uuid.UUID, body: CitationIn, session: Session, user: Editor
) -> ContentOut:
    kind = kind_of(type)
    entity = await get_entity(session, kind, entity_id, lock=True)
    _ensure_editable(entity)
    source = await session.get(Source, body.source_id) if body.source_id else None
    ensure_valid_citation(  # Req 1.4, 2.1
        CitationDraft(body.source_id, body.locator, body.field_path),
        SourceRef(source.id, source.status, source.tier) if source else None,
    )
    session.add(
        Citation(
            id=uuid.uuid4(),
            source_id=body.source_id,
            entity_type=kind.entity_type,
            entity_id=entity.id,
            field_path=body.field_path,
            locator=(body.locator or "").strip(),
            quote=body.quote or None,
            is_verbatim_quote=body.is_verbatim_quote,
            created_by=user.id,
        )
    )
    await _reopen_if_reviewed(session, kind, entity, user)
    await session.commit()
    return await content_response(session, kind, entity)


@router.delete("/{type}/{entity_id}/citations/{citation_id}", status_code=204)
async def delete_citation(
    type: ContentType,
    entity_id: uuid.UUID,
    citation_id: uuid.UUID,
    session: Session,
    user: Editor,
) -> Response:
    kind = kind_of(type)
    entity = await get_entity(session, kind, entity_id, lock=True)
    _ensure_editable(entity)
    result = await session.execute(
        delete(Citation).where(
            Citation.id == citation_id,
            Citation.entity_type == kind.entity_type,
            Citation.entity_id == entity_id,
        )
    )
    if result.rowcount == 0:
        raise AppError(404, "CITATION_NOT_FOUND", "Không tìm thấy trích dẫn")
    await _reopen_if_reviewed(session, kind, entity, user)
    await session.commit()
    return Response(status_code=204)
