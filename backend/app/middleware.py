"""Middleware: request_id, trang HTML luôn mới, gói game cũ, tách tên miền quản trị."""

import re
import uuid
from pathlib import Path

from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "x-request-id"
_VALID_ID = re.compile(r"^[A-Za-z0-9\-]{8,64}$")


class RequestIdMiddleware:
    """Nhận X-Request-ID hợp lệ từ client hoặc sinh mới; lưu ở request.state và header phản hồi."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(REQUEST_ID_HEADER.encode(), b"").decode("latin-1")
        request_id = incoming if _VALID_ID.match(incoming) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).append(
                    (REQUEST_ID_HEADER.encode(), request_id.encode())
                )
            await send(message)

        await self.app(scope, receive, send_with_id)


class FreshPagesMiddleware:
    """Trang HTML luôn kèm Cache-Control: no-cache: trình duyệt hỏi lại máy chủ mỗi lần
    (không đổi thì máy chủ trả 304, rất nhẹ).

    Lỗi 20/11/2026: StaticFiles chỉ gửi ETag/Last-Modified, nên trình duyệt tự đoán
    /game/index.html còn mới và giữ bản cũ hàng giờ; F5 ở trang chơi cũng không tải lại vì khung
    game là tài nguyên con. Bản cũ gọi gói game đã bị thay nên kẹt ở "Loading, please wait".
    Trang đã tự đặt Cache-Control thì giữ nguyên.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_fresh(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                names = {k.lower() for k, _ in headers}
                ctype = next((v for k, v in headers if k.lower() == b"content-type"), b"")
                if ctype.startswith(b"text/html") and b"cache-control" not in names:
                    headers.append((b"cache-control", b"no-cache"))
            await send(message)

        await self.app(scope, receive, send_fresh)


class GameBundleFallbackMiddleware:
    """Gói game mang tên theo nội dung (tools/build_web.py): mỗi lần cập nhật đổi tên, xoá tên cũ.

    Trang game cũ còn trong bộ đệm của ai đó sẽ xin tên cũ: thay vì 404 rồi kẹt ở màn tải,
    chuyển sang gói hiện tại (307)."""

    _OLD = re.compile(r"^/game/sukydieutra-[0-9a-f]{12}\.tar\.gz$")

    def __init__(self, app: ASGIApp, game_dir: str) -> None:
        self.app = app
        self.game_dir = game_dir

    def _current(self) -> str | None:
        found = sorted(Path(self.game_dir).glob("sukydieutra-*.tar.gz"))
        return found[0].name if len(found) == 1 else None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or not self._OLD.match(path):
            await self.app(scope, receive, send)
            return
        current = self._current()
        if (Path(self.game_dir) / path.rsplit("/", 1)[1]).exists() or not current:
            await self.app(scope, receive, send)
            return
        headers = [
            (b"location", f"/game/{current}".encode("latin-1")),
            (b"content-length", b"0"),
            (b"cache-control", b"no-store"),
        ]
        await send({"type": "http.response.start", "status": 307, "headers": headers})
        await send({"type": "http.response.body", "body": b""})


class AdminHostMiddleware:
    """Tách cổng quản trị sang tên miền riêng (admin.vtkt.online): chỉ đổi hướng, không đổi quyền.

    - Tên miền quản trị, đường dẫn "/": chuyển sang /admin/.
    - Tên miền khác (trang người chơi), /admin hoặc /admin/...: chuyển sang tên miền quản trị.
    Quyền quản trị vẫn do API kiểm tra như cũ; /api/... dùng chung cho cả hai tên miền.
    """

    def __init__(self, app: ASGIApp, admin_host: str) -> None:
        self.app = app
        self.admin_host = admin_host.strip().lower()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        host = dict(scope["headers"]).get(b"host", b"").decode("latin-1").split(":")[0].lower()
        path = scope.get("path", "")
        dich = None
        if host == self.admin_host and path in ("", "/"):
            dich = "/admin/"
        elif host != self.admin_host and (path == "/admin" or path.startswith("/admin/")):
            query = scope.get("query_string", b"").decode("latin-1")
            dich = f"https://{self.admin_host}{path}" + (f"?{query}" if query else "")
        if dich is None:
            await self.app(scope, receive, send)
            return
        await send({"type": "http.response.start", "status": 302,
                    "headers": [(b"location", dich.encode("latin-1")), (b"content-length", b"0")]})
        await send({"type": "http.response.body", "body": b""})
