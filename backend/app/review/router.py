"""Endpoint thẩm định và phiên bản nội dung.

- submit (Biên_Tập_Viên), approve/reject (Người_Thẩm_Định): Req 2.2, 3.3, 5.2–5.4
- versions, diff theo trường, restore: Req 6.1–6.3
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.content.registry import kind_of
from app.content.router import content_response, parse_payload
from app.content.service import get_entity, save_fields
from app.db import get_session
from app.errors import AppError
from app.models import (
    AuditLog,
    ContentStatus,
    ContentVersion,
    ReviewAction,
    ReviewActionKind,
    Role,
    User,
)
from app.review import workflow
from app.schemas.content import (
    ApproveIn,
    ContentOut,
    ContentType,
    DiffOut,
    FieldDiff,
    RejectIn,
    VersionDetailOut,
    VersionOut,
)

router = APIRouter(prefix="/api/v1/content", tags=["review"])
Session = Annotated[AsyncSession, Depends(get_session)]
Editor = Annotated[User, Depends(require_role(Role.editor))]
Reviewer = Annotated[User, Depends(require_role(Role.reviewer))]


@router.post("/{type}/{entity_id}/submit", response_model=ContentOut)
async def submit_content(
    type: ContentType, entity_id: uuid.UUID, session: Session, user: Editor
) -> ContentOut:
    kind = kind_of(type)
    entity = await get_entity(session, kind, entity_id, lock=True)
    await workflow.submit(session, kind, entity, user)
    await session.commit()
    return await content_response(session, kind, entity)


@router.post("/{type}/{entity_id}/approve", response_model=ContentOut)
async def approve_content(
    type: ContentType,
    entity_id: uuid.UUID,
    session: Session,
    user: Reviewer,
    body: ApproveIn | None = None,
) -> ContentOut:
    kind = kind_of(type)
    entity = await get_entity(session, kind, entity_id, lock=True)
    confirm = body.confirm_historian_note if body else False
    await workflow.approve(session, kind, entity, user, confirm)
    await session.commit()
    return await content_response(session, kind, entity)


@router.post("/{type}/{entity_id}/reject", response_model=ContentOut)
async def reject_content(
    type: ContentType, entity_id: uuid.UUID, body: RejectIn, session: Session, user: Reviewer
) -> ContentOut:
    kind = kind_of(type)
    entity = await get_entity(session, kind, entity_id, lock=True)
    await workflow.reject(session, kind, entity, user, body.reason)
    await session.commit()
    return await content_response(session, kind, entity)


# ---------------------------------------------------------------- phiên bản


async def _versions(
    session: AsyncSession, entity_type: str, entity_id: uuid.UUID
) -> list[ContentVersion]:
    rows = await session.scalars(
        select(ContentVersion)
        .where(ContentVersion.entity_type == entity_type, ContentVersion.entity_id == entity_id)
        .order_by(ContentVersion.version_no.desc())
    )
    return list(rows)


async def _version(
    session: AsyncSession, entity_type: str, entity_id: uuid.UUID, version_no: int
) -> ContentVersion:
    v = await session.scalar(
        select(ContentVersion).where(
            ContentVersion.entity_type == entity_type,
            ContentVersion.entity_id == entity_id,
            ContentVersion.version_no == version_no,
        )
    )
    if v is None:
        raise AppError(404, "VERSION_NOT_FOUND", f"Không tìm thấy phiên bản {version_no}")
    return v


def field_diff(a: dict[str, Any], b: dict[str, Any]) -> list[FieldDiff]:
    """Khác biệt theo từng trường cấp một của ảnh chụp (Req 6.2)."""
    keys = list(dict.fromkeys([*a, *b]))
    return [
        FieldDiff(field=k, before=a.get(k), after=b.get(k)) for k in keys if a.get(k) != b.get(k)
    ]


@router.get("/{type}/{entity_id}/versions", response_model=list[VersionOut])
async def list_versions(
    type: ContentType, entity_id: uuid.UUID, session: Session, _: Reviewer
) -> list[VersionOut]:
    kind = kind_of(type)
    entity = await get_entity(session, kind, entity_id)
    return [
        VersionOut.model_validate(v).model_copy(
            update={"is_published": v.id == entity.published_version_id}
        )
        for v in await _versions(session, kind.entity_type, entity_id)
    ]


@router.get("/{type}/{entity_id}/versions/{version_no}", response_model=VersionDetailOut)
async def get_version(
    type: ContentType, entity_id: uuid.UUID, version_no: int, session: Session, _: Reviewer
) -> VersionDetailOut:
    kind = kind_of(type)
    entity = await get_entity(session, kind, entity_id)
    v = await _version(session, kind.entity_type, entity_id, version_no)
    return VersionDetailOut.model_validate(v).model_copy(
        update={"is_published": v.id == entity.published_version_id}
    )


@router.get("/{type}/{entity_id}/diff", response_model=DiffOut)
async def diff_versions(
    type: ContentType,
    entity_id: uuid.UUID,
    session: Session,
    _: Reviewer,
    a: Annotated[int, Query(ge=1)],
    b: Annotated[int, Query(ge=1)],
) -> DiffOut:
    kind = kind_of(type)
    await get_entity(session, kind, entity_id)
    va = await _version(session, kind.entity_type, entity_id, a)
    vb = await _version(session, kind.entity_type, entity_id, b)
    return DiffOut(a=a, b=b, changes=field_diff(va.snapshot, vb.snapshot))


@router.post("/{type}/{entity_id}/restore/{version_no}", response_model=ContentOut)
async def restore_version(
    type: ContentType, entity_id: uuid.UUID, version_no: int, session: Session, user: Reviewer
) -> ContentOut:
    """Tạo phiên bản mới mang giá trị phiên bản cũ ở trạng thái Chờ_Thẩm_Định (Req 6.3).

    Bản Đã_Xuất_Bản hiện hành vẫn chạy cho đến khi bản khôi phục được phê duyệt. Người
    khôi phục trở thành người sửa gần nhất nên không tự duyệt được bản này.
    """
    kind = kind_of(type)
    entity = await get_entity(session, kind, entity_id, lock=True)
    if entity.status == ContentStatus.archived:
        raise AppError(409, "INVALID_TRANSITION", "Nội dung đã lưu trữ, không khôi phục được")
    old = await _version(session, kind.entity_type, entity_id, version_no)
    before = entity.status
    data = parse_payload(kind, old.snapshot)
    version = await save_fields(session, kind, entity, data, user, status=ContentStatus.pending)
    session.add(
        ReviewAction(
            id=uuid.uuid4(),
            entity_type=kind.entity_type,
            entity_id=entity.id,
            version_id=version.id,
            reviewer_id=user.id,
            action=ReviewActionKind.restore,
            reason=f"Khôi phục từ phiên bản {version_no}",
        )
    )
    session.add(
        AuditLog(
            actor_id=user.id,
            action="content_restore",
            target_type=kind.entity_type,
            target_id=str(entity.id),
            before={"status": before.value},
            after={
                "status": entity.status.value,
                "from_version": version_no,
                "version_no": version.version_no,
            },
        )
    )
    await session.commit()
    return await content_response(session, kind, entity)
