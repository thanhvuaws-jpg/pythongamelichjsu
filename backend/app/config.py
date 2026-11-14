"""Cấu hình ứng dụng đọc từ biến môi trường hoặc backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Sử Ký Điều Tra API"
    environment: str = "dev"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://sukydieutra:devpassword@localhost:5432/sukydieutra"

    # Web_Shell, bản build WebAssembly và nội dung game; máy chủ phục vụ cả ba chung một địa chỉ
    web_dir: str = str(REPO_ROOT / "web")
    game_web_dir: str = str(REPO_ROOT / "build" / "sukydieutra" / "build" / "web")
    game_content_dir: str = str(REPO_ROOT / "game" / "content")

    # Bật khi chưa có dịch vụ gửi email: đăng ký xong dùng được ngay,
    # người dưới 16 tuổi do quản trị viên kích hoạt
    skip_email_verification: bool = False

    # Tài khoản quản trị đầu tiên, xem seed/create_admin.py
    admin_email: str = ""
    admin_password: str = ""
    # Tên miền riêng cho cổng quản trị, ví dụ admin.vtkt.online. Để trống: quản trị ở /admin/
    # của mọi tên miền. Có đặt thì "/" của tên miền này chuyển sang /admin/, còn /admin/ ở
    # tên miền khác chuyển sang tên miền này.
    admin_host: str = ""

    # Danh sách domain phân tách bằng dấu phẩy (Req 33.2)
    cors_origins: str = "http://localhost:8000,http://localhost:8080"

    supabase_url: str = ""
    supabase_service_key: str = ""
    health_timeout_s: float = 3.0

    # URL gốc của Web_Shell, dùng để dựng liên kết trong email và chuyển hướng OAuth
    web_base_url: str = "http://localhost:8080"

    # Xác thực (Req 23.3, 23.4, 23.6)
    jwt_secret: str = "dev-insecure-secret-change-me-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    verify_email_hours: int = 24
    password_reset_minutes: int = 30
    guardian_consent_days: int = 7
    lockout_max_failures: int = 5
    lockout_window_minutes: int = 15
    lockout_minutes: int = 15
    min_age_without_guardian: int = 16
    # Số ngày chờ trước khi job xóa hẳn dữ liệu cá nhân; phải < 30 (Req 25.5)
    account_purge_after_days: int = 0
    consent_version: str = "2026-01"
    refresh_cookie_name: str = "sk_refresh"
    # "lax" khi Web_Shell và API cùng site; "none" (kèm Secure) khi khác site
    refresh_cookie_samesite: str = "lax"

    # Email: console (dev) | smtp | resend
    email_backend: str = "console"
    email_from: str = "Sử Ký Điều Tra <no-reply@localhost>"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    resend_api_key: str = ""

    # Google OAuth 2.0 (Req 23.5)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Tên miền không được dùng làm Nguồn_Tin_Cậy, phân tách bằng dấu phẩy (Req 1.5).
    # So khớp cả tên miền con, ví dụ vi.wikipedia.org khớp wikipedia.org
    blocked_source_domains: str = (
        "wikipedia.org,facebook.com,fb.com,youtube.com,youtu.be,tiktok.com,"
        "x.com,twitter.com,instagram.com,threads.net,reddit.com,zalo.me,"
        "blogspot.com,wordpress.com,medium.com,substack.com,tumblr.com"
    )

    # Supabase Storage (Req 8)
    # Không cấu hình Supabase thì ở dev lưu vào thư mục local
    media_bucket: str = "media"
    media_local_dir: str = ".media"
    media_max_bytes: int = 10 * 1024 * 1024
    # Không cho SVG mặc định vì SVG có thể chứa script
    media_allowed_mime: str = "image/png,image/jpeg,image/webp,audio/ogg,audio/mpeg"

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, url: str) -> str:
        """Hosting thường đưa URL dạng postgres://...?sslmode=require, asyncpg cần dạng khác."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                url = "postgresql+asyncpg://" + url[len(prefix) :]
        return url.replace("sslmode=", "ssl=")

    @property
    def blocked_domain_set(self) -> frozenset[str]:
        parts = (d.strip().lower().lstrip(".") for d in self.blocked_source_domains.split(","))
        return frozenset(d for d in parts if d)

    @property
    def media_allowed_mime_set(self) -> frozenset[str]:
        return frozenset(m.strip() for m in self.media_allowed_mime.split(",") if m.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"

    @model_validator(mode="after")
    def _check_prod_secrets(self) -> "Settings":
        if not self.is_dev and (self.jwt_secret.startswith("dev-") or len(self.jwt_secret) < 32):
            raise ValueError("JWT_SECRET phải được đặt (≥ 32 ký tự) ngoài môi trường dev")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
