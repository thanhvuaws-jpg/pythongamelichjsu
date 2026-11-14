"""Endpoint /api/v1/sources: đề xuất, sửa, duyệt nguồn (Req 1.1–1.3, 1.5).

- Biên_Tập_Viên đề xuất nguồn ở trạng thái `pending` và sửa nguồn chưa được duyệt.
- Người_Thẩm_Định duyệt với Cấp_Nguồn do mình chỉ định, từ chối kèm lý do và là người
  duy nhất sửa được nguồn đã duyệt (nguồn đã duyệt đang được trích dẫn).
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import has_role, require_role
from app.auth.jwt import now_utc
from app.content.validators import ensure_url_allowed
from app.db import get_session
from app.errors import AppError
from app.models import AuditLog, Role, Source, SourceStatus, User
from app.schemas.source import (
    SourceApproveIn,
    SourceIn,
    SourceOut,
    SourcePage,
    SourcePatch,
    SourceRejectIn,
)

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])
Session = Annotated[AsyncSession, Depends(get_session)]
Editor = Annotated[User, Depends(require_role(Role.editor))]
Reviewer = Annotated[User, Depends(require_role(Role.reviewer))]

PAGE_SIZE_MAX = 50
_AUDIT_FIELDS = ("status", "tier", "title", "publisher", "year", "edition", "volume", "url")


def _snapshot(src: Source) -> dict[str, Any]:
    return {f: getattr(src, f) for f in _AUDIT_FIELDS}


def _audit(actor: User, action: str, src: Source, before: dict[str, Any] | None) -> AuditLog:
    return AuditLog(
        actor_id=actor.id,
        action=action,
        target_type="source",
        target_id=str(src.id),
        before=before,
        after=_snapshot(src),
    )


async def _get_source(session: AsyncSession, source_id: uuid.UUID, lock: bool = False) -> Source:
    stmt = select(Source).where(Source.id == source_id)
    if lock:
        stmt = stmt.with_for_update()
    src = (await session.execute(stmt)).scalar_one_or_none()
    if src is None:
        raise AppError(404, "SOURCE_NOT_FOUND", "Không tìm thấy nguồn")
    return src


@router.get("", response_model=SourcePage)
async def list_sources(
    session: Session,
    _: Editor,
    status: SourceStatus | None = None,
    tier: Annotated[int | None, Query(ge=1, le=3)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)] = PAGE_SIZE_MAX,
) -> SourcePage:
    stmt = select(Source)
    if status is not None:
        stmt = stmt.where(Source.status == status)
    if tier is not None:
        stmt = stmt.where(Source.tier == tier)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Source.title.ilike(like), Source.authors.ilike(like)))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await session.scalars(
        stmt.order_by(Source.title).offset((page - 1) * page_size).limit(page_size)
    )
    return SourcePage(
        items=[SourceOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{source_id}", response_model=SourceOut)
async def get_source(source_id: uuid.UUID, session: Session, _: Editor) -> SourceOut:
    return SourceOut.model_validate(await _get_source(session, source_id))


@router.post("", response_model=SourceOut, status_code=201)
async def propose_source(body: SourceIn, session: Session, user: Editor) -> SourceOut:
    ensure_url_allowed(body.url)
    src = Source(
        id=uuid.uuid4(),
        **body.model_dump(),
        status=SourceStatus.pending,  # Req 1.2
        proposed_by=user.id,
    )
    session.add(src)
    session.add(_audit(user, "source_propose", src, None))
    await session.commit()
    await session.refresh(src)
    return SourceOut.model_validate(src)


@router.patch("/{source_id}", response_model=SourceOut)
async def update_source(
    source_id: uuid.UUID, body: SourcePatch, session: Session, user: Editor
) -> SourceOut:
    src = await _get_source(session, source_id, lock=True)
    is_reviewer = has_role(user, Role.reviewer)
    if src.status == SourceStatus.approved and not is_reviewer:
        raise AppError(
            403,
            "SOURCE_LOCKED",
            "Nguồn đã duyệt chỉ Người thẩm định được sửa; hãy đề xuất nguồn mới nếu cần",
        )
    changes = body.model_dump(exclude_unset=True)
    if "url" in changes:
        ensure_url_allowed(changes["url"])
    for key in ("title", "publisher", "year"):
        if key in changes and changes[key] is None:
            raise AppError(
                400, "CITATION_MISSING_FIELDS", f"Thiếu trường: {key}", {"fields": [key]}
            )
    if src.status == SourceStatus.approved and changes.get("tier", src.tier) is None:
        raise AppError(400, "SOURCE_TIER_REQUIRED", "Nguồn đã duyệt phải có Cấp nguồn")
    if not changes:
        return SourceOut.model_validate(src)

    before = _snapshot(src)
    for key, value in changes.items():
        setattr(src, key, value)
    if src.status == SourceStatus.rejected:
        # Sửa nguồn bị từ chối nghĩa là đề xuất lại
        src.status = SourceStatus.pending
        src.rejection_reason = None
    session.add(_audit(user, "source_update", src, before))
    await session.commit()
    await session.refresh(src)
    return SourceOut.model_validate(src)


@router.post("/{source_id}/approve", response_model=SourceOut)
async def approve_source(
    source_id: uuid.UUID, body: SourceApproveIn, session: Session, user: Reviewer
) -> SourceOut:
    src = await _get_source(session, source_id, lock=True)
    if src.status != SourceStatus.pending:
        raise AppError(409, "INVALID_TRANSITION", "Chỉ duyệt được nguồn đang chờ thẩm định")
    if src.proposed_by == user.id:
        raise AppError(403, "SELF_APPROVAL", "Không thể tự duyệt nguồn do mình đề xuất")
    missing = [k for k in ("title", "publisher", "year") if getattr(src, k) in (None, "")]
    if missing:
        # Nguồn seed cần được đối chiếu thông tin xuất bản trước khi duyệt
        raise AppError(
            422,
            "SOURCE_INCOMPLETE",
            f"Cần bổ sung thông tin xuất bản: {', '.join(missing)}",
            {"fields": missing},
        )
    ensure_url_allowed(src.url)

    before = _snapshot(src)
    src.tier = body.tier  # Req 1.3: Cấp_Nguồn do Người_Thẩm_Định chỉ định
    src.status = SourceStatus.approved
    src.approved_by = user.id
    src.approved_at = now_utc()
    src.rejection_reason = None
    session.add(_audit(user, "source_approve", src, before))
    await session.commit()
    await session.refresh(src)
    return SourceOut.model_validate(src)


@router.post("/{source_id}/reject", response_model=SourceOut)
async def reject_source(
    source_id: uuid.UUID, body: SourceRejectIn, session: Session, user: Reviewer
) -> SourceOut:
    """Từ chối đề xuất hoặc gỡ nguồn khỏi danh mục (không xóa cứng vì có thể đang được trích)."""
    src = await _get_source(session, source_id, lock=True)
    if src.status == SourceStatus.rejected:
        raise AppError(409, "INVALID_TRANSITION", "Nguồn đã bị từ chối")
    before = _snapshot(src)
    src.status = SourceStatus.rejected
    src.rejection_reason = body.reason.strip()
    session.add(_audit(user, "source_reject", src, before))
    await session.commit()
    await session.refresh(src)
    return SourceOut.model_validate(src)
