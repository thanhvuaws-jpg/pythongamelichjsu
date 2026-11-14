"""Endpoint Lớp_Học (Req 26.1–26.5)."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import TEACHER, CurrentUser, require_role
from app.classroom.service import (
    class_progress,
    create_class,
    ensure_class_teacher,
    join_class,
    my_classes,
    progress_csv,
)
from app.db import get_session
from app.models import User

router = APIRouter(prefix="/api/v1/classes", tags=["classroom"])
Session = Annotated[AsyncSession, Depends(get_session)]
Teacher = Annotated[User, Depends(require_role(TEACHER))]


class ClassIn(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]


class JoinIn(BaseModel):
    code: Annotated[str, Field(min_length=6, max_length=10)]


class ClassOut(BaseModel):
    id: uuid.UUID
    name: str
    join_code: str | None
    is_teacher: bool
    member_count: int = 0
    created_at: datetime


@router.post("", response_model=ClassOut, status_code=201)
async def create(body: ClassIn, session: Session, user: Teacher) -> ClassOut:
    cls = await create_class(session, user, body.name)
    await session.commit()
    return ClassOut(
        id=cls.id,
        name=cls.name,
        join_code=cls.join_code,
        is_teacher=True,
        created_at=cls.created_at,
    )


@router.post("/join", response_model=ClassOut)
async def join(body: JoinIn, session: Session, user: CurrentUser) -> ClassOut:
    cls = await join_class(session, user, body.code)
    await session.commit()
    return next(ClassOut(**c) for c in await my_classes(session, user) if c["id"] == cls.id)


@router.get("", response_model=list[ClassOut])
async def list_mine(session: Session, user: CurrentUser) -> list[ClassOut]:
    return [ClassOut(**c) for c in await my_classes(session, user)]


@router.get("/{class_id}/progress")
async def progress(class_id: uuid.UUID, session: Session, user: Teacher) -> dict[str, Any]:
    cls = await ensure_class_teacher(session, user, class_id)
    return await class_progress(session, cls)


@router.get("/{class_id}/export.csv")
async def export_csv(class_id: uuid.UUID, session: Session, user: Teacher) -> Response:
    cls = await ensure_class_teacher(session, user, class_id)
    data = progress_csv(await class_progress(session, cls))
    return Response(
        data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="class_{cls.join_code}.csv"'},
    )
