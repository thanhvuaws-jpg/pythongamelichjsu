"""Chấm đáp án cho 5 Loại_Câu_Hỏi (Req 16.1, 16.2). Chỉ chạy phía máy chủ.

Định dạng `correct_answer` / `answer`:
    single   : "<option_id>"
    multi    : ["<option_id>", ...]           (so khớp tập)
    order    : ["<item_id>", ...]             (so khớp danh sách)
    match    : {"<left_id>": "<right_id>"}    (so khớp từ điển cặp)
    map_pick : {"lat": float, "lon": float}   (Haversine ≤ tolerance_km)
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

EARTH_RADIUS_KM = 6371.0088
DEFAULT_TOLERANCE_KM = 10.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def grade(question: Mapping[str, Any], answer: Any) -> bool:
    """Trả True khi `answer` đúng. Đáp án sai định dạng được coi là sai."""
    kind, correct = question["kind"], question["correct_answer"]
    try:
        match kind:
            case "single":
                return isinstance(answer, str) and answer == correct
            case "multi":
                return isinstance(answer, list) and set(answer) == set(correct)
            case "order":
                return isinstance(answer, list) and list(answer) == list(correct)
            case "match":
                return isinstance(answer, Mapping) and dict(answer) == dict(correct)
            case "map_pick":
                tol = question.get("tolerance_km") or DEFAULT_TOLERANCE_KM
                d = haversine_km(
                    float(answer["lat"]), float(answer["lon"]),
                    float(correct["lat"]), float(correct["lon"]),
                )
                return d <= float(tol)
    except (KeyError, TypeError, ValueError):
        return False
    raise ValueError(f"Loại_Câu_Hỏi không hỗ trợ: {kind}")
