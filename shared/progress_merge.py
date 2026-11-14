"""Hợp nhất tiến trình cục bộ và trên máy chủ (Req 19.4).

Các trường tập hợp lấy hợp; các trường trạng thái (vị trí bản đồ, Dòng_Thời_Gian,...)
lấy theo `updated_at` mới hơn. Hàm giao hoán, kết hợp và lũy đẳng.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SET_FIELDS = (
    "completed_objectives",
    "collected_fragments",
    "unlocked_events",
    "unlocked_places",
    "unlocked_quests",
    "clues",
)
LWW_FIELDS = ("current_level", "map_pos", "timeline_state")


def _pick_newer(a: Mapping[str, Any], b: Mapping[str, Any]) -> Mapping[str, Any]:
    ta, tb = a.get("updated_at") or "", b.get("updated_at") or ""
    if ta != tb:
        return a if ta > tb else b
    # Hòa: chọn tất định theo biểu diễn để đảm bảo giao hoán
    return a if repr(sorted(a.items())) >= repr(sorted(b.items())) else b


def merge(server: Mapping[str, Any], client: Mapping[str, Any]) -> dict[str, Any]:
    """`updated_at` là chuỗi ISO 8601 UTC (so sánh theo thứ tự từ điển)."""
    newer = _pick_newer(server, client)
    out: dict[str, Any] = {}
    for f in SET_FIELDS:
        vals = set(server.get(f) or ()) | set(client.get(f) or ())
        if vals or f in server or f in client:
            out[f] = sorted(vals)
    for f in LWW_FIELDS:
        if f in newer:
            out[f] = newer[f]
        elif f in server or f in client:
            out[f] = (server if f in server else client)[f]
    out["tutorial_done"] = bool(server.get("tutorial_done")) or bool(client.get("tutorial_done"))
    out["updated_at"] = max(server.get("updated_at") or "", client.get("updated_at") or "") or None
    return out
