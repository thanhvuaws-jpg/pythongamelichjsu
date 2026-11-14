"""Logger JSON có lọc dữ liệu nhạy cảm (Req 34.2)."""

import json
import logging
import re
from datetime import UTC, datetime

SENSITIVE_KEY = re.compile(r"password|token|authorization|secret", re.IGNORECASE)
# Che giá trị dạng `password=...`, `"token": "..."`, `Bearer ...` trong chuỗi tự do
_INLINE = re.compile(
    r"""(?i)(["']?(?:\w*password\w*|\w*token\w*|authorization)["']?\s*[:=]\s*)(["']?)[^\s"',}&]+"""
)
_BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*")
REDACTED = "***"

_STD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


def redact(value):
    """Che đệ quy các khóa nhạy cảm trong dict/list và chuỗi."""
    if isinstance(value, dict):
        return {
            k: REDACTED if SENSITIVE_KEY.search(str(k)) else redact(v) for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    if isinstance(value, str):
        # Che Bearer trước để không để lộ phần token sau từ "Bearer"
        return _INLINE.sub(r"\1\2" + REDACTED, _BEARER.sub(REDACTED, value))
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, val in record.__dict__.items():
            if key not in _STD_ATTRS and not key.startswith("_"):
                payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(redact(payload), ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
