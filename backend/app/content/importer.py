"""Nhập hàng loạt CSV/JSON vào Bản_Nháp (Req 28.5).

Định dạng:
- JSON: `[{"type": "events", "data": {...}, "id": "<uuid tùy chọn>"}, ...]` hoặc
  `{"items": [...]}`. Có thể kèm `"citations": [CitationIn, ...]` cho từng dòng.
- CSV: một loại nội dung mỗi tệp (`type` truyền qua query). Mỗi cột là một trường;
  ô trống bỏ qua; ô chứa list/dict/bool/số viết dạng JSON (ví dụ `["a","b"]`, `true`).
  Cột `id` tùy chọn để dòng sau tham chiếu dòng trước.

Mỗi dòng chạy trong SAVEPOINT riêng: dòng lỗi được hoàn tác và ghi vào báo cáo,
các dòng hợp lệ vẫn được nhập.
"""

import csv
import io
import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.content.registry import kind_of
from app.content.router import validation_details
from app.content.service import create_entity
from app.content.validators import CitationDraft, SourceRef, validate_citation
from app.db import get_session
from app.errors import AppError
from app.models import AuditLog, Citation, Role, Source, User
from app.schemas.content import (
    CitationIn,
    ContentType,
    ImportedRow,
    ImportReport,
    ImportRowError,
)

router = APIRouter(prefix="/api/v1/content", tags=["content"])
Session = Annotated[AsyncSession, Depends(get_session)]
Editor = Annotated[User, Depends(require_role(Role.editor))]

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 2000


class RowError(Exception):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__("row error")
        self.errors = errors


def _bad_file(message: str) -> AppError:
    return AppError(400, "IMPORT_FILE_INVALID", message)


def _cell(value: str) -> Any:
    v = value.strip()
    if not v:
        return None
    if (
        v[0] in "[{"
        or v in ("true", "false", "null")
        or v.lstrip("-").replace(".", "", 1).isdigit()
    ):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return v
    return v


def parse_csv(text: str, type_: ContentType) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise _bad_file("Tệp CSV thiếu dòng tiêu đề")
    rows = []
    for raw in reader:
        if None in raw:
            raise _bad_file(f"Dòng {reader.line_num} có nhiều cột hơn tiêu đề")
        data = {k.strip(): _cell(v or "") for k, v in raw.items() if k and k.strip()}
        row_id = data.pop("id", None)
        rows.append(
            {
                "type": type_.value,
                "id": row_id,
                "data": {k: v for k, v in data.items() if v is not None},
            }
        )
    return rows


def parse_json(text: str) -> list[dict[str, Any]]:
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise _bad_file(f"JSON không hợp lệ: dòng {exc.lineno}") from exc
    items = doc.get("items") if isinstance(doc, dict) else doc
    if not isinstance(items, list):
        raise _bad_file("JSON cần là danh sách hoặc đối tượng có khóa 'items'")
    return items


def _row_parts(item: Any, default_type: ContentType | None) -> tuple[Any, ...]:
    if not isinstance(item, dict):
        raise RowError([{"loc": [], "msg": "Dòng phải là đối tượng JSON"}])
    raw_type = item.get("type") or (default_type.value if default_type else None)
    try:
        slug = ContentType(raw_type)
    except ValueError:
        raise RowError(
            [{"loc": ["type"], "msg": f"Loại nội dung không hợp lệ: {raw_type}"}]
        ) from None
    data = item.get("data")
    if not isinstance(data, dict):
        raise RowError([{"loc": ["data"], "msg": "Thiếu đối tượng 'data'"}])
    row_id = None
    if item.get("id") not in (None, ""):
        try:
            row_id = uuid.UUID(str(item["id"]))
        except ValueError:
            raise RowError([{"loc": ["id"], "msg": "id phải là UUID"}]) from None
    cits = item.get("citations") or []
    if not isinstance(cits, list):
        raise RowError([{"loc": ["citations"], "msg": "citations phải là danh sách"}])
    return slug, data, row_id, cits


async def _import_row(
    session: AsyncSession, item: Any, default_type: ContentType | None, user: User
) -> ImportedRow | tuple[str | None, list[dict[str, Any]]]:
    slug, data, row_id, raw_cits = _row_parts(item, default_type)
    kind = kind_of(slug)
    try:
        payload = kind.schema.model_validate(data)
        cits = [CitationIn.model_validate(c) for c in raw_cits]
    except ValidationError as exc:
        raise RowError(validation_details(exc)["fields"]) from exc

    cit_errors: list[dict[str, Any]] = []
    for i, c in enumerate(cits):
        src = await session.get(Source, c.source_id) if c.source_id else None
        check = validate_citation(
            CitationDraft(c.source_id, c.locator, c.field_path),
            SourceRef(src.id, src.status, src.tier) if src else None,
        )
        if check.missing_fields:
            cit_errors.append(
                {"loc": ["citations", i], "msg": f"Thiếu trường: {', '.join(check.missing_fields)}"}
            )
        if check.source_not_in_catalog:
            cit_errors.append(
                {"loc": ["citations", i], "msg": "Nguồn không thuộc Danh mục nguồn đã duyệt"}
            )
    if cit_errors:
        raise RowError(cit_errors)

    try:
        entity, _ = await create_entity(session, kind, payload, user, entity_id=row_id)
    except AppError as exc:
        raise RowError([{"loc": [], "msg": exc.message, **exc.details}]) from exc
    for c in cits:
        session.add(
            Citation(
                id=uuid.uuid4(),
                source_id=c.source_id,
                entity_type=kind.entity_type,
                entity_id=entity.id,
                field_path=c.field_path,
                locator=(c.locator or "").strip(),
                quote=c.quote or None,
                is_verbatim_quote=c.is_verbatim_quote,
                created_by=user.id,
            )
        )
    await session.flush()
    return ImportedRow(row=0, type=slug, id=entity.id)


async def run_import(
    session: AsyncSession, items: list[Any], default_type: ContentType | None, user: User
) -> ImportReport:
    if len(items) > MAX_ROWS:
        raise _bad_file(f"Tối đa {MAX_ROWS} dòng mỗi lần nhập")
    imported: list[ImportedRow] = []
    errors: list[ImportRowError] = []
    for n, item in enumerate(items, start=1):
        raw_type = item.get("type") if isinstance(item, dict) else None
        try:
            async with session.begin_nested():
                row = await _import_row(session, item, default_type, user)
            imported.append(row.model_copy(update={"row": n}))
        except RowError as exc:
            errors.append(
                ImportRowError(
                    row=n, type=raw_type or (default_type and default_type.value), errors=exc.errors
                )
            )
    session.add(
        AuditLog(
            actor_id=user.id,
            action="content_import",
            target_type="content",
            after={"total": len(items), "imported": len(imported), "errors": len(errors)},
        )
    )
    await session.commit()
    return ImportReport(total=len(items), imported=imported, errors=errors)


@router.post("/import", response_model=ImportReport)
async def import_content(
    session: Session,
    user: Editor,
    file: Annotated[UploadFile, File()],
    type: Annotated[ContentType | None, Query()] = None,
) -> ImportReport:
    raw = await file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise _bad_file("Tệp vượt quá 5 MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise _bad_file("Tệp cần mã hóa UTF-8") from exc
    name = (file.filename or "").lower()
    is_json = name.endswith(".json") or text.lstrip()[:1] in ("[", "{")
    if is_json:
        items = parse_json(text)
    else:
        if type is None:
            raise _bad_file("Nhập CSV cần tham số 'type' (ví dụ ?type=events)")
        items = parse_csv(text, type)
    return await run_import(session, items, type, user)
