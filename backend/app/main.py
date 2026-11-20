"""Điểm vào FastAPI: CORS, request_id, định dạng lỗi, health; vòng chạy người chơi máy."""

import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import health
from app.auth import google
from app.auth import router as auth_router
from app.classroom import router as classroom_router
from app.config import get_settings
from app.content import importer, media, sources
from app.content import router as content_router
from app.errors import register_error_handlers
from app.game import router as game_router
from app.leaderboard import router as leaderboard_router
from app.logging_config import setup_logging
from app.middleware import (
    REQUEST_ID_HEADER,
    AdminHostMiddleware,
    FreshPagesMiddleware,
    GameBundleFallbackMiddleware,
    RequestIdMiddleware,
)
from app.play import router as play_router
from app.privacy import router as privacy_router
from app.publish import router as publish_router
from app.reports import router as reports_router
from app.review import router as review_router
from app.storage import LOCAL_MEDIA_ROUTE, uses_supabase
from app.users import router as users_router
from app.world import router as world_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Người chơi máy chạy suốt đời ứng dụng, dừng gọn khi máy chủ tắt."""
    task = asyncio.create_task(world_router.run_bots())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    # Middleware thêm sau chạy ngoài cùng: RequestId bao ngoài CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(FreshPagesMiddleware)
    if Path(settings.game_web_dir).is_dir():
        app.add_middleware(GameBundleFallbackMiddleware, game_dir=settings.game_web_dir)
    if settings.admin_host:
        app.add_middleware(AdminHostMiddleware, admin_host=settings.admin_host)
    register_error_handlers(app)

    app.include_router(health.router)
    app.include_router(auth_router.router)
    app.include_router(google.router)
    app.include_router(sources.router)
    app.include_router(media.router)
    # /content/import phải đăng ký trước /content/{type}
    app.include_router(importer.router)
    app.include_router(content_router.router)
    app.include_router(review_router.router)
    app.include_router(publish_router.router)
    app.include_router(play_router.router)
    app.include_router(leaderboard_router.router)
    app.include_router(classroom_router.router)
    app.include_router(reports_router.router)
    app.include_router(users_router.router)
    app.include_router(privacy_router.router)
    app.include_router(game_router.router)
    app.include_router(world_router.router)

    if not uses_supabase(settings):
        # Không có Supabase: phục vụ media đã upload từ thư mục local (dev, hoặc VPS có volume)
        Path(settings.media_local_dir).mkdir(parents=True, exist_ok=True)
        app.mount(LOCAL_MEDIA_ROUTE, StaticFiles(directory=settings.media_local_dir), name="media")

    # Game và các trang web chạy chung địa chỉ với API. Gắn sau cùng vì "/" nhận mọi đường dẫn.
    if Path(settings.game_web_dir).is_dir():
        app.mount("/game", StaticFiles(directory=settings.game_web_dir, html=True), name="game")
    if Path(settings.web_dir).is_dir():
        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
    return app


app = create_app()
