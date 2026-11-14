"""Upload media có kiểm tra Giấy_Phép_Media (Req 8.1–8.2) và trang ghi công (Req 8.4)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.config import get_settings
from app.db import get_session
from app.errors import AppError
from app.models import (
    ATTRIBUTION_REQUIRED,
    AuditLog,
    Media,
    MediaLicense,
    Role,
    Source,
    SourceStatus,
    User,
)
from app.schemas.source import CreditMedia, CreditSource, CreditsOut, MediaOut
from app.storage import StorageError, get_storage

router = APIRouter(prefix="/api/v1", tags=["media"])
Session = Annotated[AsyncSession, Depends(get_session)]
Editor = Annotated[User, Depends(require_role(Role.editor))]

ALLOWED_LICENSES = ", ".join(m.value for m in MediaLicense)
_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
}


def sniff_mime(head: bytes) -> str | None:
    """Xác định loại tệp từ magic bytes, không tin Content-Type do client gửi."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"OggS"):
        return "audio/ogg"
    if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"
    return None


def parse_license(value: str) -> MediaLicense:
    try:
        return MediaLicense(value.strip().lower())
    except ValueError:
        raise AppError(
            400,
            "MEDIA_LICENSE_NOT_ALLOWED",
            f"Giấy phép không được phép. Chỉ chấp nhận: {ALLOWED_LICENSES}",
            {"allowed": [m.value for m in MediaLicense]},
        ) from None


def _required(**fields: str | None) -> None:
    missing = [k for k, v in fields.items() if not (v or "").strip()]
    if missing:
        raise AppError(
            400,
            "MEDIA_LICENSE_MISSING_FIELDS",
            f"Thiếu thông tin giấy phép: {', '.join(missing)}",
            {"fields": missing},
        )


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise AppError(
            400, "MEDIA_TOO_LARGE", f"Tệp vượt quá {limit // (1024 * 1024)} MB", {"max": limit}
        )
    if not data:
        raise AppError(400, "MEDIA_EMPTY", "Tệp rỗng")
    return data


def _media_out(m: Media) -> MediaOut:
    fields = {c: getattr(m, c) for c in MediaOut.model_fields if c != "url"}
    return MediaOut(**fields, url=get_storage().public_url(m.storage_path))


@router.post("/media", response_model=MediaOut, status_code=201)
async def upload_media(
    session: Session,
    user: Editor,
    file: Annotated[UploadFile, File()],
    owner: Annotated[str, Form(max_length=500)] = "",
    license: Annotated[str, Form(max_length=64)] = "",
    source_url: Annotated[str, Form(max_length=2000)] = "",
    license_url: Annotated[str | None, Form(max_length=2000)] = None,
    attribution: Annotated[str | None, Form(max_length=1000)] = None,
    permission_doc_ref: Annotated[str | None, Form(max_length=1000)] = None,
) -> MediaOut:
    # Kiểm tra giấy phép trước khi đọc tệp (Req 8.1, 8.2)
    _required(owner=owner, license=license, source_url=source_url)
    lic = parse_license(license)
    if lic == MediaLicense.written_permission:
        _required(permission_doc_ref=permission_doc_ref)
    if lic in ATTRIBUTION_REQUIRED and not (attribution or "").strip():
        attribution = f"{owner.strip()}, {lic.value.replace('_', '-').upper()}"

    s = get_settings()
    data = await _read_limited(file, s.media_max_bytes)
    mime = sniff_mime(data[:16])
    if mime is None or mime not in s.media_allowed_mime_set:
        raise AppError(
            400,
            "MEDIA_TYPE_NOT_ALLOWED",
            "Định dạng tệp không được hỗ trợ",
            {"allowed": sorted(s.media_allowed_mime_set)},
        )

    media_id = uuid.uuid4()
    path = f"{media_id.hex[:2]}/{media_id}.{_EXT[mime]}"
    try:
        await get_storage().put(path, data, mime)
    except StorageError as exc:
        raise AppError(502, "STORAGE_UNAVAILABLE", "Không lưu được tệp, vui lòng thử lại") from exc

    media = Media(
        id=media_id,
        storage_path=path,
        mime=mime,
        size_bytes=len(data),
        owner=owner.strip(),
        license=lic,
        source_url=source_url.strip(),
        license_url=(license_url or "").strip() or None,
        attribution=(attribution or "").strip() or None,
        permission_doc_path=(permission_doc_ref or "").strip() or None,
        uploaded_by=user.id,
    )
    session.add(media)
    session.add(
        AuditLog(
            actor_id=user.id,
            action="media_upload",
            target_type="media",
            target_id=str(media_id),
            after={"license": lic.value, "owner": media.owner, "path": path},
        )
    )
    await session.commit()
    await session.refresh(media)
    return _media_out(media)


@router.get("/public/credits", response_model=CreditsOut)
async def credits(session: Session) -> CreditsOut:
    """Công khai: Nguồn_Tin_Cậy đã duyệt và Giấy_Phép_Media (Req 8.4)."""
    sources = await session.scalars(
        select(Source)
        .where(Source.status == SourceStatus.approved)
        .order_by(Source.tier, Source.title)
    )
    media = await session.scalars(select(Media).order_by(Media.created_at))
    storage = get_storage()
    return CreditsOut(
        sources=[
            CreditSource(
                id=s.id,
                title=s.title,
                authors=s.authors,
                translators=s.translators,
                publisher=s.publisher,
                year=s.year,
                edition=s.edition,
                volume=s.volume,
                tier=s.tier,
            )
            for s in sources
        ],
        media=[
            CreditMedia(
                id=m.id,
                url=storage.public_url(m.storage_path),
                owner=m.owner,
                license=m.license,
                license_url=m.license_url,
                attribution=m.attribution,
                source_url=m.source_url,
            )
            for m in media
        ],
    )
