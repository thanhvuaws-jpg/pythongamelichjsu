"""Endpoint Báo_Cáo_Sai_Sót (Req 7.1–7.4)."""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, require_role
from app.db import get_session
from app.models import ErrorReport, ReportStatus, Role, User
from app.reports.service import create_report, entity_title, handle_report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
Session = Annotated[AsyncSession, Depends(get_session)]
Reviewer = Annotated[User, Depends(require_role(Role.reviewer))]

EntityType = Literal["events", "fragments", "questions"]


class ReportIn(BaseModel):
    entity_type: EntityType
    entity_id: uuid.UUID
    description: Annotated[str, Field(min_length=1, max_length=1000)]
    counter_source: Annotated[str | None, Field(max_length=1000)] = None


class ReportHandleIn(BaseModel):
    status: Literal["confirmed", "rejected"]
    resolution: Annotated[str | None, Field(max_length=2000)] = None


class ReportOut(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    description: str
    counter_source: str | None
    status: ReportStatus
    resolution: str | None
    created_at: datetime


class ReportAdminOut(ReportOut):
    reporter_id: uuid.UUID | None
    handled_by: uuid.UUID | None
    hidden_question_ids: list[uuid.UUID]
    entity_title: str | None = None


class ReportPage(BaseModel):
    total: int
    items: list[ReportAdminOut]


class ReportHandleOut(BaseModel):
    report: ReportAdminOut
    rebuilt_bundles: list[dict[str, Any]]


def _admin_out(r: ErrorReport, title: str | None = None) -> ReportAdminOut:
    return ReportAdminOut(
        id=r.id,
        entity_type=r.entity_type,
        entity_id=r.entity_id,
        description=r.description,
        counter_source=r.counter_source,
        status=r.status,
        resolution=r.resolution,
        created_at=r.created_at,
        reporter_id=r.reporter_id,
        handled_by=r.handled_by,
        hidden_question_ids=list(r.hidden_question_ids),
        entity_title=title,
    )


@router.post("", response_model=ReportOut, status_code=201)
async def submit_report(body: ReportIn, session: Session, user: CurrentUser) -> ReportOut:
    r = await create_report(
        session, user, body.entity_type, body.entity_id, body.description, body.counter_source
    )
    await session.commit()
    return ReportOut(**_admin_out(r).model_dump(include=set(ReportOut.model_fields)))


@router.get("", response_model=ReportPage)
async def list_reports(
    session: Session,
    _: Reviewer,
    status: ReportStatus | None = ReportStatus.new,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ReportPage:
    """Hàng đợi trong Admin_Portal; mặc định chỉ báo cáo Mới (Req 7.2)."""
    conds = [ErrorReport.status == status] if status else []
    total = await session.scalar(select(func.count()).select_from(ErrorReport).where(*conds))
    rows = await session.scalars(
        select(ErrorReport)
        .where(*conds)
        .order_by(ErrorReport.created_at, ErrorReport.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_admin_out(r, await entity_title(session, r)) for r in rows]
    return ReportPage(total=int(total or 0), items=items)


@router.patch("/{report_id}", response_model=ReportHandleOut)
async def handle(
    report_id: uuid.UUID, body: ReportHandleIn, session: Session, user: Reviewer
) -> ReportHandleOut:
    r, rebuilt = await handle_report(
        session, report_id, user, ReportStatus(body.status), body.resolution
    )
    await session.commit()
    await session.refresh(r)
    return ReportHandleOut(report=_admin_out(r), rebuilt_bundles=rebuilt)


@router.get("/mine", response_model=list[ReportOut])
async def my_reports(session: Session, user: CurrentUser) -> list[ReportOut]:
    rows = await session.scalars(
        select(ErrorReport)
        .where(ErrorReport.reporter_id == user.id)
        .order_by(ErrorReport.created_at.desc())
        .limit(100)
    )
    return [
        ReportOut(**_admin_out(r).model_dump(include=set(ReportOut.model_fields))) for r in rows
    ]
