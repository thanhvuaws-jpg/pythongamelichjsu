"""Lớp lưu trữ đối tượng trừu tượng: Supabase Storage (prod) hoặc thư mục local (dev)."""

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import httpx

from app.config import Settings, get_settings

LOCAL_MEDIA_ROUTE = "/media-files"


class StorageError(Exception):
    pass


class Storage(Protocol):
    async def put(self, path: str, data: bytes, content_type: str) -> None: ...

    def public_url(self, path: str) -> str: ...


class SupabaseStorage:
    def __init__(self, s: Settings) -> None:
        self.base = s.supabase_url.rstrip("/")
        self.bucket = s.media_bucket
        self.key = s.supabase_service_key

    async def put(self, path: str, data: bytes, content_type: str) -> None:
        url = f"{self.base}/storage/v1/object/{self.bucket}/{quote(path)}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": content_type,
            "x-upsert": "false",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, content=data, headers=headers)
        except httpx.HTTPError as exc:
            raise StorageError(type(exc).__name__) from exc
        if resp.status_code >= 300:
            raise StorageError(f"status {resp.status_code}")

    def public_url(self, path: str) -> str:
        return f"{self.base}/storage/v1/object/public/{self.bucket}/{quote(path)}"


class LocalStorage:
    """Chỉ dùng ở dev; tệp được phục vụ tại LOCAL_MEDIA_ROUTE."""

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    def _target(self, path: str) -> Path:
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root):
            raise StorageError("invalid path")
        return target

    async def put(self, path: str, data: bytes, content_type: str) -> None:
        target = self._target(path)

        def _write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as fh:  # không ghi đè
                fh.write(data)

        try:
            await asyncio.to_thread(_write)
        except OSError as exc:
            raise StorageError(type(exc).__name__) from exc

    def public_url(self, path: str) -> str:
        return f"{LOCAL_MEDIA_ROUTE}/{quote(path)}"


def uses_supabase(s: Settings) -> bool:
    return bool(s.supabase_url and s.supabase_service_key)


@lru_cache
def get_storage() -> Storage:
    s = get_settings()
    if uses_supabase(s):
        return SupabaseStorage(s)
    # Không có Supabase (cả khi chạy production trên VPS riêng): lưu vào thư mục local, nên
    # gắn volume cho thư mục này. Trước đây production bắt buộc Supabase, làm bảng xếp hạng
    # lỗi 500.
    return LocalStorage(s.media_local_dir)
