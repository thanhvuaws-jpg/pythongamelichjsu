"""Endpoint xuất bản Màn_Chơi (Req 29.1–29.3) và manifest bundle (Req 29.4)."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, require_role
from app.db import get_session
from app.models import AuditLog, Bundle, ContentStatus, Level, Role, User
from app.publish.bundler import publish_level
from app.storage import get_storage

router = APIRouter(prefix="/api/v1", tags=["publish"])
Session = Annotated[AsyncSession, Depends(get_session)]
Reviewer = Annotated[User, Depends(require_role(Role.reviewer))]


class BundleOut(BaseModel):
    level_id: uuid.UUID
    version: int
    sha256: str
    size_bytes: int
    url: str
    published_at: datetime


class ManifestItem(BundleOut):
    order_no: int


class ManifestOut(BaseModel):
    levels: list[ManifestItem]


def _out(b: Bundle) -> dict:
    return {
        "level_id": b.level_id,
        "version": b.version_no,
        "sha256": b.sha256,
        "size_bytes": b.size_bytes,
        "url": get_storage().public_url(b.storage_path),
        "published_at": b.created_at,
    }


@router.post("/levels/{level_id}/publish", response_model=BundleOut, status_code=201)
async def publish(level_id: uuid.UUID, session: Session, user: Reviewer) -> BundleOut:
    bundle = await publish_level(session, level_id, user, get_storage())
    session.add(
        AuditLog(
            actor_id=user.id,
            action="level_publish",
            target_type="levels",
            target_id=str(level_id),
            after={
                "version_no": bundle.version_no,
                "sha256": bundle.sha256,
                "path": bundle.storage_path,
            },
        )
    )
    await session.commit()
    await session.refresh(bundle)
    return BundleOut(**_out(bundle))


@router.get("/bundles/manifest", response_model=ManifestOut)
async def manifest(session: Session, _: CurrentUser) -> ManifestOut:
    """Phiên bản bundle mới nhất của mỗi Màn_Chơi chưa lưu trữ (Req 29.4)."""
    latest = (
        select(Bundle.level_id, func.max(Bundle.version_no).label("v"))
        .group_by(Bundle.level_id)
        .subquery()
    )
    rows = await session.execute(
        select(Bundle, Level.order_no)
        .join(latest, (latest.c.level_id == Bundle.level_id) & (latest.c.v == Bundle.version_no))
        .join(Level, Level.id == Bundle.level_id)
        .where(Level.status != ContentStatus.archived)
        .order_by(Level.order_no)
    )
    return ManifestOut(levels=[ManifestItem(**_out(b), order_no=o) for b, o in rows])
