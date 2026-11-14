"""Mốc_Thời_Gian biểu diễn dạng khoảng [start, end] theo Độ_Chính_Xác (Req 15.2, 15.4)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any


class Precision(StrEnum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    YEAR_RANGE = "year_range"
    CENTURY = "century"


def _parse(value: date | str) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


@dataclass(frozen=True, slots=True)
class HistDate:
    """Khoảng ngày bao phủ một mốc. A chắc chắn sớm hơn B khi A.end < B.start."""

    start: date
    end: date
    precision: Precision

    @classmethod
    def from_parts(
        cls, start: date | str, end: date | str | None, precision: Precision | str
    ) -> HistDate:
        """Mở rộng `start` (và `end` nếu có) thành khoảng đầy đủ theo Độ_Chính_Xác."""
        p = Precision(precision)
        s = _parse(start)
        e = _parse(end) if end else s
        if p is Precision.MONTH:
            s = s.replace(day=1)
            e = e.replace(day=calendar.monthrange(e.year, e.month)[1])
        elif p in (Precision.YEAR, Precision.YEAR_RANGE):
            s = date(s.year, 1, 1)
            e = date(e.year, 12, 31)
        elif p is Precision.CENTURY:
            # Dùng date_start/date_end do Biên_Tập_Viên nhập là đầu và cuối thế kỷ
            s = date(s.year, 1, 1)
            e = date(e.year, 12, 31)
        if e < s:
            raise ValueError("date_end phải không sớm hơn date_start")
        return cls(s, e, p)

    @classmethod
    def from_bundle(cls, data: dict[str, Any]) -> HistDate:
        """Đọc trường `date` của Sự_Kiện trong Content_Bundle."""
        return cls.from_parts(data["start"], data.get("end"), data.get("precision", "day"))

    def sort_key(self) -> tuple[date, date]:
        return (self.start, self.end)

    def definitely_before(self, other: HistDate) -> bool:
        return self.end < other.start

    def overlaps(self, other: HistDate) -> bool:
        return not (self.definitely_before(other) or other.definitely_before(self))
