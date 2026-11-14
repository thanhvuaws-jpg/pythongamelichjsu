"""Luật sắp xếp Dòng_Thời_Gian (Req 15.2, 15.3, 15.4)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from shared.histdate import HistDate

KIND_LABEL = {
    "cause_of": "là nguyên nhân của",
    "leads_to": "dẫn đến",
    "context_of": "là bối cảnh của",
}

GENERIC_HINT = "Hãy xem lại Mốc_Thời_Gian của sự kiện trong Sổ tay điều tra."


def is_valid_placement(placed: Sequence[HistDate], new: HistDate, index: int) -> bool:
    """Chèn `new` vào vị trí `index` của `placed` có đúng thứ tự không.

    Sai khi một mốc đứng trước chắc chắn muộn hơn `new`, hoặc một mốc đứng sau chắc chắn
    sớm hơn `new`. Hai mốc chồng lấn (Độ_Chính_Xác thấp phủ nhau) hoán đổi được.
    """
    if not 0 <= index <= len(placed):
        raise IndexError("index ngoài phạm vi Dòng_Thời_Gian")
    if any(new.definitely_before(d) for d in placed[:index]):
        return False
    return not any(d.definitely_before(new) for d in placed[index:])


def is_valid_order(dates: Sequence[HistDate]) -> bool:
    """Toàn bộ danh sách đúng thứ tự khi không có cặp nào đảo ngược chắc chắn."""
    return all(
        not dates[j].definitely_before(dates[i])
        for i in range(len(dates))
        for j in range(i + 1, len(dates))
    )


def _link_hint(event_id: str, link: Mapping[str, Any], titles: Mapping[str, str]) -> str:
    src, dst = link["from_event_id"], link["to_event_id"]
    label = KIND_LABEL.get(link["kind"], "liên quan đến")
    if src == event_id:
        return f"Sự kiện này {label} «{titles.get(dst, '?')}», nên diễn ra trước sự kiện đó."
    return f"«{titles.get(src, '?')}» {label} sự kiện này, nên diễn ra trước."


def hint_for(
    event_id: str,
    neighbor_ids: Iterable[str],
    causal_links: Iterable[Mapping[str, Any]],
    titles: Mapping[str, str],
) -> str:
    """Gợi ý dựa trên Quan_Hệ_Nhân_Quả, ưu tiên liên kết với thẻ lân cận vị trí vừa đặt."""
    related = [
        link
        for link in causal_links
        if event_id in (link["from_event_id"], link["to_event_id"])
    ]
    if not related:
        return GENERIC_HINT
    neighbors = set(neighbor_ids)
    for link in related:
        other = link["to_event_id"] if link["from_event_id"] == event_id else link["from_event_id"]
        if other in neighbors:
            return _link_hint(event_id, link, titles)
    return _link_hint(event_id, related[0], titles)
