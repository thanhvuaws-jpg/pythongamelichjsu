"""GET /health: trạng thái kết nối Content_Store và Media_Store (Req 33.5)."""

import asyncio
import logging

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import ping_db

router = APIRouter(tags=["ops"])
logger = logging.getLogger("app.health")


async def check_db() -> str:
    try:
        await asyncio.wait_for(ping_db(), timeout=get_settings().health_timeout_s)
        return "ok"
    except Exception as exc:  # noqa: BLE001 - trạng thái lỗi được trả về, không ném
        logger.warning("health_db_failed", extra={"error": type(exc).__name__})
        return "error"


async def check_storage() -> str:
    s = get_settings()
    if not s.supabase_url or not s.supabase_service_key:
        return "not_configured"
    headers = {
        "apikey": s.supabase_service_key,
        "Authorization": f"Bearer {s.supabase_service_key}",
    }
    try:
        async with httpx.AsyncClient(timeout=s.health_timeout_s) as client:
            resp = await client.get(
                f"{s.supabase_url.rstrip('/')}/storage/v1/bucket", headers=headers
            )
        return "ok" if resp.status_code == 200 else "error"
    except httpx.HTTPError as exc:
        logger.warning("health_storage_failed", extra={"error": type(exc).__name__})
        return "error"


@router.get("/health")
async def health() -> JSONResponse:
    db, storage = await asyncio.gather(check_db(), check_storage())
    # Kho media là tuỳ chọn, chỉ báo lỗi khi đã cấu hình mà không kết nối được
    healthy = db == "ok" and storage in ("ok", "not_configured")
    body = {"status": "ok" if healthy else "degraded", "database": db, "storage": storage}
    return JSONResponse(body, status_code=200 if healthy else 503)
