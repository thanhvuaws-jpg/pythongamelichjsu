"""Lưu nội dung kèm phiên bản (Req 5.5, 6.1).

- Mỗi lần lưu ghi một `content_versions` chứa ảnh chụp toàn bộ trường nội dung.
- Sửa nội dung (kể cả đã xuất bản) đưa về Bản_Nháp để đi lại quy trình thẩm định;
  `published_version_id` giữ nguyên nên Content_Bundle vẫn dùng bản đã duyệt.
"""

import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.registry import ContentKind
from app.errors import AppError
from app.models import ContentMixin, ContentStatus, ContentVersion, User


def snapshot(kind: ContentKind, entity: ContentMixin) -> dict[str, Any]:
    """Giá trị trường nội dung dạng JSON, chuẩn hóa qua schema của loại."""
    raw = {f: getattr(entity, f) for f in kind.fields}
    return kind.schema.model_validate(raw).model_dump(mode="json")


def _column_values(kind: ContentKind, data: BaseModel) -> dict[str, Any]:
    # Cột JSONB nhận dạng JSON (UUID → str); cột khác giữ kiểu Python (date, Decimal, UUID)
    py, js = data.model_dump(), data.model_dump(mode="json")
    table = kind.model.__table__  # type: ignore[attr-defined]
    return {f: js[f] if isinstance(table.c[f].type, JSONB) else py[f] for f in kind.fields}


async def latest_version(
    session: AsyncSession, kind: ContentKind, entity_id: uuid.UUID
) -> ContentVersion | None:
    return await session.scalar(
        select(ContentVersion)
        .where(
            ContentVersion.entity_type == kind.entity_type,
            ContentVersion.entity_id == entity_id,
        )
        .order_by(ContentVersion.version_no.desc())
        .limit(1)
    )


async def add_version(
    session: AsyncSession, kind: ContentKind, entity: ContentMixin, editor: User
) -> ContentVersion:
    current = await session.scalar(
        select(func.max(ContentVersion.version_no)).where(
            ContentVersion.entity_type == kind.entity_type,
            ContentVersion.entity_id == entity.id,
        )
    )
    version = ContentVersion(
        id=uuid.uuid4(),
        entity_type=kind.entity_type,
        entity_id=entity.id,
        version_no=(current or 0) + 1,
        snapshot=snapshot(kind, entity),
        editor_id=editor.id,
        status_at_save=entity.status,
    )
    session.add(version)
    return version


async def flush_or_reference_error(session: AsyncSession) -> None:
    """Đổi lỗi khóa ngoại/ràng buộc DB thành 400 thay vì 500."""
    try:
        await session.flush()
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.orig, "__cause__", None), "constraint_name", None)
        raise AppError(
            400,
            "INVALID_REFERENCE",
            "Dữ liệu tham chiếu tới nội dung không tồn tại hoặc vi phạm ràng buộc",
            {"constraint": constraint},
        ) from exc


async def create_entity(
    session: AsyncSession,
    kind: ContentKind,
    data: BaseModel,
    user: User,
    entity_id: uuid.UUID | None = None,
) -> tuple[ContentMixin, ContentVersion]:
    entity = kind.model(
        id=entity_id or uuid.uuid4(),
        status=ContentStatus.draft,
        author_id=user.id,
        last_editor_id=user.id,
        hidden_by_report=False,
        **_column_values(kind, data),
    )
    session.add(entity)
    await flush_or_reference_error(session)
    version = await add_version(session, kind, entity, user)
    await flush_or_reference_error(session)
    return entity, version


async def get_entity(
    session: AsyncSession, kind: ContentKind, entity_id: uuid.UUID, lock: bool = False
) -> ContentMixin:
    stmt = select(kind.model).where(kind.model.id == entity_id)
    if lock:
        stmt = stmt.with_for_update()
    entity = (await session.execute(stmt)).scalar_one_or_none()
    if entity is None:
        raise AppError(404, "CONTENT_NOT_FOUND", "Không tìm thấy nội dung")
    return entity


async def save_fields(
    session: AsyncSession,
    kind: ContentKind,
    entity: ContentMixin,
    data: BaseModel,
    user: User,
    status: ContentStatus = ContentStatus.draft,
) -> ContentVersion:
    """Ghi giá trị mới, đặt trạng thái và tạo phiên bản. Không đụng `published_version_id`."""
    for key, value in _column_values(kind, data).items():
        setattr(entity, key, value)
    entity.status = status
    entity.last_editor_id = user.id
    await flush_or_reference_error(session)
    version = await add_version(session, kind, entity, user)
    await flush_or_reference_error(session)
    return version


async def mark_edited(
    session: AsyncSession, kind: ContentKind, entity: ContentMixin, user: User
) -> ContentVersion:
    """Thay đổi ngoài trường nội dung (ví dụ trích dẫn) cũng tính là một lần sửa."""
    current = kind.schema.model_validate(snapshot(kind, entity))
    return await save_fields(session, kind, entity, current, user)
