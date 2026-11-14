"""Định dạng lỗi thống nhất {error: {code, message, details, request_id}}."""

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")

_HTTP_CODES = {
    400: ("BAD_REQUEST", "Yêu cầu không hợp lệ"),
    401: ("UNAUTHORIZED", "Cần đăng nhập"),
    403: ("FORBIDDEN", "Không có quyền thực hiện thao tác này"),
    404: ("NOT_FOUND", "Không tìm thấy tài nguyên"),
    405: ("METHOD_NOT_ALLOWED", "Phương thức không được hỗ trợ"),
    409: ("CONFLICT", "Xung đột trạng thái"),
    429: ("RATE_LIMITED", "Quá nhiều yêu cầu, vui lòng thử lại sau"),
}


class AppError(Exception):
    """Lỗi nghiệp vụ có mã ổn định để client xử lý."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        self.headers = headers


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": _request_id(request),
        }
    }
    return JSONResponse(body, status_code=status_code, headers=headers)


def _log_server_error(request: Request, status_code: int, exc: Exception | None = None) -> None:
    # Chỉ ghi method/path/request_id; không ghi header hay body (Req 34.2)
    logger.error(
        "server_error",
        exc_info=exc,
        extra={
            "request_id": _request_id(request),
            "method": request.method,
            "endpoint": request.url.path,
            "status": status_code,
        },
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    if exc.status_code >= 500:
        _log_server_error(request, exc.status_code, exc)
    return error_response(
        request, exc.status_code, exc.code, exc.message, exc.details, headers=exc.headers
    )


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code >= 500:
        _log_server_error(request, exc.status_code, exc)
    code, default_msg = _HTTP_CODES.get(exc.status_code, ("HTTP_ERROR", "Lỗi yêu cầu"))
    # Thay thông điệp mặc định tiếng Anh của Starlette bằng tiếng Việt
    is_default = exc.detail == HTTPStatus(exc.status_code).phrase
    custom = isinstance(exc.detail, str) and exc.detail and not is_default
    message = exc.detail if custom else default_msg
    return error_response(request, exc.status_code, code, message, headers=exc.headers)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
        for e in exc.errors()
    ]
    return error_response(
        request, 422, "VALIDATION_ERROR", "Dữ liệu gửi lên không hợp lệ", {"fields": fields}
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    _log_server_error(request, 500, exc)
    return error_response(request, 500, "INTERNAL", "Lỗi máy chủ, vui lòng thử lại sau")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
