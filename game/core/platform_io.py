"""Lưu dữ liệu cục bộ: localStorage trên web (pygbag), file JSON trên desktop."""

from __future__ import annotations

import json
import sys
from pathlib import Path

IS_WEB = sys.platform == "emscripten"
_KEY = "sukydieutra.save.v1"
_FILE = Path(__file__).resolve().parent.parent / ".save" / "progress.json"


def _window():
    import platform  # pygbag gắn `window` (JS) vào module platform

    return platform.window


def read_key(key: str) -> str | None:
    """Đọc một giá trị trang chơi ghi vào localStorage, như vai trò và điểm được tặng. Trên máy tính thì không có."""
    if not IS_WEB:
        return None
    try:
        return _window().localStorage.getItem(key)
    except (AttributeError, TypeError):
        return None


def load_save() -> dict | None:
    try:
        raw = _window().localStorage.getItem(_KEY) if IS_WEB else _FILE.read_text(encoding="utf-8")
        return json.loads(raw) if raw else None
    except (OSError, ValueError, AttributeError, TypeError):
        return None


def write_save(data: dict) -> None:
    # Chuỗi Python đi sang JavaScript trong pygbag bị đọc sai mã khi có chữ có dấu, nên ghi JSON thuần ASCII
    raw = json.dumps(data, ensure_ascii=True)
    try:
        if IS_WEB:
            _window().localStorage.setItem(_KEY, raw)
        else:
            _FILE.parent.mkdir(parents=True, exist_ok=True)
            _FILE.write_text(raw, encoding="utf-8")
    except (OSError, AttributeError, TypeError):
        pass  # không lưu được thì game vẫn chạy tiếp
