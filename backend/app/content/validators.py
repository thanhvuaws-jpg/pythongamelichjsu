"""Quy tắc nguồn và trích dẫn, viết dạng hàm thuần để dùng khi lưu, submit và approve.

- `validate_citation`: Req 1.4, 2.1
- `blocked_domain`: Req 1.5
- `check_submit_rules`: Req 2.2–2.5, 4.3, 4.4

Các hàm không chạm DB; tầng gọi chịu trách nhiệm nạp nguồn/trích dẫn và dựng
`SubmitSubject` từ thực thể nội dung.
"""

import uuid
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from urllib.parse import urlsplit

from app.config import get_settings
from app.errors import AppError
from app.models import SourceStatus

# Thực thể là dữ kiện lịch sử, bắt buộc ≥1 trích dẫn Cấp 1/2 (Req 2.2)
FACT_ENTITY_TYPES = frozenset({"events", "persons", "places", "causal_links"})
QUESTION_TYPE = "questions"
EXPLANATION_FIELD = "explanation"
BLOCKED_DOMAIN_MESSAGE = "Chỉ dùng làm đầu mối tra cứu, cần trích từ tài liệu gốc"


def blocked_domains() -> frozenset[str]:
    """BLOCKED_DOMAINS đọc từ cấu hình `BLOCKED_SOURCE_DOMAINS`."""
    return get_settings().blocked_domain_set


def blocked_domain(url: str | None, blocked: Iterable[str] | None = None) -> str | None:
    """Trả về tên miền bị chặn mà `url` khớp (kể cả tên miền con), hoặc None."""
    if not url or not url.strip():
        return None
    raw = url.strip()
    if "://" not in raw:
        raw = f"//{raw}"
    host = (urlsplit(raw).hostname or "").lower().rstrip(".")
    if not host:
        return None
    for domain in blocked if blocked is not None else blocked_domains():
        if host == domain or host.endswith(f".{domain}"):
            return domain
    return None


def ensure_url_allowed(url: str | None) -> None:
    domain = blocked_domain(url)
    if domain:
        raise AppError(400, "SOURCE_DOMAIN_BLOCKED", BLOCKED_DOMAIN_MESSAGE, {"domain": domain})


# ---------------------------------------------------------------- trích dẫn


@dataclass(frozen=True)
class SourceRef:
    """Thông tin tối thiểu về nguồn để kiểm tra trích dẫn."""

    id: uuid.UUID
    status: SourceStatus
    tier: int | None


@dataclass(frozen=True)
class CitationDraft:
    source_id: uuid.UUID | None
    locator: str | None
    field_path: str | None = "*"


@dataclass
class CitationCheck:
    missing_fields: list[str] = field(default_factory=list)
    source_not_in_catalog: bool = False

    @property
    def ok(self) -> bool:
        return not self.missing_fields and not self.source_not_in_catalog


def validate_citation(c: CitationDraft, source: SourceRef | None) -> CitationCheck:
    """Trích dẫn cần nguồn thuộc Danh_Mục_Nguồn (đã duyệt) và locator (trang/mục/mã văn bản)."""
    result = CitationCheck()
    if c.source_id is None:
        result.missing_fields.append("source_id")
    if not (c.locator or "").strip():
        result.missing_fields.append("locator")
    if not (c.field_path or "").strip():
        result.missing_fields.append("field_path")
    if c.source_id is not None and (source is None or source.status != SourceStatus.approved):
        result.source_not_in_catalog = True
    return result


def ensure_valid_citation(c: CitationDraft, source: SourceRef | None) -> None:
    check = validate_citation(c, source)
    if check.missing_fields:
        raise AppError(
            400,
            "CITATION_MISSING_FIELDS",
            f"Thiếu trường: {', '.join(check.missing_fields)}",
            {"fields": check.missing_fields},
        )
    if check.source_not_in_catalog:
        raise AppError(
            400,
            "SOURCE_NOT_IN_CATALOG",
            "Nguồn không thuộc Danh mục nguồn đã duyệt",
            {"source_id": str(c.source_id)},
        )


# ---------------------------------------------------------------- quy tắc submit


@dataclass(frozen=True)
class CitationFact:
    """Trích dẫn đã lưu kèm thông tin nguồn tại thời điểm kiểm tra."""

    source_id: uuid.UUID
    source_status: SourceStatus
    tier: int | None
    field_path: str = "*"
    is_verbatim_quote: bool = False

    @property
    def counts(self) -> bool:
        # Nguồn có thể bị gỡ khỏi danh mục giữa submit và approve
        return self.source_status == SourceStatus.approved and self.tier in (1, 2, 3)


@dataclass(frozen=True)
class SubmitSubject:
    """Mô tả thực thể cần kiểm tra, do tầng nội dung dựng từ bản ghi.

    - `strict_fields`: trường cần ≥2 nguồn khác nhau, ≥1 Cấp 1 (Req 2.3), ví dụ
      `date` khi có Mốc_Thời_Gian, `numeric_facts.casualties`.
    - `verbatim_fields`: trường chứa trích nguyên văn (Req 4.3), ví dụ `node:n3`.
    - `event_published`, `depends_on_fiction`: chỉ dùng cho Câu_Hỏi (Req 2.5, 4.4).
    """

    entity_type: str
    is_fiction: bool = False
    strict_fields: tuple[str, ...] = ()
    verbatim_fields: tuple[str, ...] = ()
    event_published: bool | None = None
    depends_on_fiction: bool = False


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    field: str | None = None


def _tiers(cits: Iterable[CitationFact]) -> set[int]:
    return {c.tier for c in cits if c.counts and c.tier is not None}


def check_submit_rules(subject: SubmitSubject, citations: list[CitationFact]) -> list[Violation]:
    """Trả về danh sách vi phạm; rỗng nghĩa là được chuyển sang Chờ_Thẩm_Định/Đã_Xuất_Bản."""
    out: list[Violation] = []
    valid = [c for c in citations if c.counts]

    for c in citations:
        if not c.counts:
            out.append(
                Violation(
                    "SOURCE_NOT_APPROVED",
                    "Trích dẫn trỏ tới nguồn không còn thuộc Danh mục nguồn",
                    c.field_path,
                )
            )

    # Req 2.2 + 2.4
    if subject.entity_type in FACT_ENTITY_TYPES and not valid:
        out.append(
            Violation("CITATION_REQUIRED", "Cần ít nhất một trích dẫn từ nguồn Cấp 1 hoặc Cấp 2")
        )
    elif valid and not subject.is_fiction and not (_tiers(valid) & {1, 2}):
        out.append(
            Violation(
                "TIER12_REQUIRED",
                "Chỉ có trích dẫn Cấp 3, thiếu nguồn Cấp 1 hoặc Cấp 2",
            )
        )

    # Req 2.3: mốc thời gian, số liệu
    for fp in dict.fromkeys(subject.strict_fields):
        cits = [c for c in valid if c.field_path == fp]
        if len({c.source_id for c in cits}) < 2:
            out.append(
                Violation(
                    "FIELD_NEEDS_TWO_SOURCES",
                    f"Trường '{fp}' cần trích dẫn từ ít nhất hai nguồn khác nhau",
                    fp,
                )
            )
        if 1 not in _tiers(cits):
            out.append(
                Violation("FIELD_NEEDS_TIER1", f"Trường '{fp}' cần ít nhất một nguồn Cấp 1", fp)
            )

    # Req 4.3: trích nguyên văn cần nguồn Cấp 1 tại đúng trường
    verbatim = dict.fromkeys(
        [*subject.verbatim_fields, *(c.field_path for c in citations if c.is_verbatim_quote)]
    )
    for fp in verbatim:
        if 1 not in _tiers(c for c in valid if c.field_path == fp):
            out.append(
                Violation(
                    "VERBATIM_NEEDS_TIER1",
                    f"Đoạn trích nguyên văn ở '{fp}' cần trích dẫn văn bản gốc hoặc bản dịch Cấp 1",
                    fp,
                )
            )

    # Req 2.5, 4.4
    if subject.entity_type == QUESTION_TYPE:
        if not any(c.field_path == EXPLANATION_FIELD for c in valid):
            out.append(
                Violation(
                    "EXPLANATION_CITATION_REQUIRED",
                    "Phần giải thích đáp án cần ít nhất một trích dẫn",
                    EXPLANATION_FIELD,
                )
            )
        if not subject.event_published:
            out.append(Violation("EVENT_NOT_PUBLISHED", "Câu hỏi phải gắn với Sự kiện đã xuất bản"))
        if subject.depends_on_fiction:
            out.append(
                Violation(
                    "FICTION_BASED_QUESTION",
                    "Câu hỏi không được lấy đáp án từ nội dung hư cấu",
                )
            )
    return out


def raise_if_violations(violations: list[Violation]) -> None:
    """422 kèm `details.violations[]`; mã FICTION_BASED_QUESTION được ưu tiên."""
    if not violations:
        return
    is_fiction = any(v.code == "FICTION_BASED_QUESTION" for v in violations)
    raise AppError(
        422,
        "FICTION_BASED_QUESTION" if is_fiction else "SUBMIT_RULES_FAILED",
        violations[0].message if len(violations) == 1 else "Nội dung chưa đạt quy tắc nguồn",
        {"violations": [asdict(v) for v in violations]},
    )
