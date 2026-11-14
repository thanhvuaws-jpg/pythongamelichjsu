"""Middleware gán request_id cho mỗi yêu cầu."""

import re
import uuid

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
