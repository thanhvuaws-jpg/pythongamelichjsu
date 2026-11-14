"""Kiểm tra một Content_Bundle JSON trước khi phát hành (Req 2.2, 8.1, 16.3, 16.4).

Chạy từ thư mục backend/:  python -m seed.check_bundle path/to/bundle.json [...]
Mã thoát 1 khi có lỗi, dùng được trong CI.

Kiểm tra:
- Mọi id tham chiếu tồn tại trong bundle.
- Sự_Kiện, Nhân_Vật, Địa_Điểm, Quan_Hệ_Nhân_Quả có ≥ 1 Trích_Dẫn Cấp 1 hoặc Cấp 2.
- Mọi media có Giấy_Phép_Media hợp lệ (chủ sở hữu, loại giấy phép được phép, nguồn).
- Câu_Hỏi: ≥ 30% Độ_Khó 2 và ≥ 20% Độ_Khó 3; không chứa đáp án hoặc giải thích.
"""

import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.models import MediaLicense

ALLOWED_LICENSES = {m.value for m in MediaLicense}
CITED_SECTIONS = ("events", "persons", "places", "causal_links")
LEAKED_QUESTION_FIELDS = ("correct_answer", "explanation", "answer_basis")
MIN_SHARE = {2: 0.30, 3: 0.20}  # Req 16.4

Bundle = dict[str, Any]


def _index(bundle: Bundle, section: str) -> dict[str, dict[str, Any]]:
    return {str(x["id"]): x for x in bundle.get(section) or []}


def _check_refs(
    errors: list[str], where: str, ids: Iterable[Any], known: dict[str, Any], what: str
) -> None:
    for i in ids:
        if i and str(i) not in known:
            errors.append(f"{where}: tham chiếu {what} '{i}' không có trong bundle")


def check_references(bundle: Bundle) -> list[str]:
    errors: list[str] = []
    idx = {s: _index(bundle, s) for s in (*CITED_SECTIONS, "fragments", "dialogues", "questions")}
    citations = bundle.get("citations") or {}
    sources = bundle.get("sources") or {}
    media = bundle.get("media") or {}
    level = bundle.get("level") or {}
    objective_target = {
        "go_to": idx["places"],
        "collect": idx["fragments"],
        "dialogue": idx["dialogues"],
        "answer": idx["questions"],
    }

    _check_refs(errors, "level", level.get("place_ids", []), idx["places"], "Địa điểm")
    for e in idx["events"].values():
        w = f"events/{e['id']}"
        _check_refs(errors, w, [e.get("place_id")], idx["places"], "Địa điểm")
        _check_refs(errors, w, e.get("person_ids", []), idx["persons"], "Nhân vật")
        _check_refs(errors, w, e.get("fragment_ids", []), idx["fragments"], "Mảnh ghép")
        _check_refs(errors, w, e.get("question_ids", []), idx["questions"], "Câu hỏi")
    for c in idx["causal_links"].values():
        ends = [c.get("from_event_id"), c.get("to_event_id")]
        _check_refs(errors, f"causal_links/{c['id']}", ends, idx["events"], "Sự kiện")
    for section in ("fragments", "questions"):
        for x in idx[section].values():
            _check_refs(
                errors, f"{section}/{x['id']}", [x.get("event_id")], idx["events"], "Sự kiện"
            )
    for f in idx["fragments"].values():
        _check_refs(errors, f"fragments/{f['id']}", [f.get("media_id")], media, "media")
    for p in idx["persons"].values():
        _check_refs(errors, f"persons/{p['id']}", [p.get("portrait_media_id")], media, "media")
    for d in idx["dialogues"].values():
        w = f"dialogues/{d['id']}"
        _check_refs(errors, w, [d.get("place_id")], idx["places"], "Địa điểm")
        _check_refs(errors, w, [d.get("speaker_person_id")], idx["persons"], "Nhân vật")
    for m in bundle.get("map_layers") or []:
        _check_refs(errors, f"map_layers/{m['id']}", [m.get("media_id")], media, "media")
    for q in bundle.get("quests") or []:
        for o in q.get("objectives") or []:
            target = objective_target.get(o.get("kind"))
            if target is not None:
                _check_refs(errors, f"objectives/{o['id']}", [o.get("target_id")], target, "đích")

    for section in (*CITED_SECTIONS, "fragments", "dialogues", "questions", "quests"):
        for x in bundle.get(section) or []:
            w = f"{section}/{x['id']}"
            _check_refs(errors, w, x.get("citations", []), citations, "trích dẫn")
    for cid, c in citations.items():
        _check_refs(errors, f"citations/{cid}", [c.get("source_id")], sources, "nguồn")
    return errors


def check_citations(bundle: Bundle) -> list[str]:
    """Req 2.2: thực thể lịch sử cần ≥ 1 trích dẫn từ nguồn Cấp 1 hoặc 2."""
    errors: list[str] = []
    citations = bundle.get("citations") or {}
    sources = bundle.get("sources") or {}
    for section in CITED_SECTIONS:
        for x in bundle.get(section) or []:
            if x.get("is_fiction"):
                continue
            tiers = {
                (sources.get(str(citations.get(c, {}).get("source_id"))) or {}).get("tier")
                for c in x.get("citations", [])
            }
            if not tiers & {1, 2}:
                errors.append(f"{section}/{x['id']}: thiếu trích dẫn nguồn Cấp 1 hoặc Cấp 2")
    return errors


def check_media(bundle: Bundle) -> list[str]:
    """Req 8.1–8.3: giấy phép đầy đủ và thuộc danh sách được phép."""
    errors: list[str] = []
    for mid, m in (bundle.get("media") or {}).items():
        w = f"media/{mid}"
        if m.get("license") not in ALLOWED_LICENSES:
            errors.append(f"{w}: giấy phép '{m.get('license')}' không được phép")
        for key in ("owner", "source_url"):
            if not str(m.get(key) or "").strip():
                errors.append(f"{w}: thiếu {key}")
        if m.get("attribution_required") and not str(m.get("attribution") or "").strip():
            errors.append(f"{w}: giấy phép yêu cầu ghi công nhưng thiếu attribution")
    return errors


def check_questions(bundle: Bundle) -> list[str]:
    """Req 16.3 (không lộ đáp án) và 16.4 (phân bổ Độ_Khó)."""
    errors: list[str] = []
    questions = bundle.get("questions") or []
    for q in questions:
        leaked = [k for k in LEAKED_QUESTION_FIELDS if k in q]
        if leaked:
            errors.append(f"questions/{q['id']}: bundle chứa trường bí mật {', '.join(leaked)}")
    if not questions:
        return [*errors, "Bundle không có Câu hỏi nào"]
    total = len(questions)
    for level, share in MIN_SHARE.items():
        n = sum(1 for q in questions if q.get("difficulty") == level)
        if n < share * total:
            errors.append(
                f"Độ khó {level}: {n}/{total} câu ({n / total:.0%}), cần tối thiểu {share:.0%}"
            )
    return errors


def check_bundle(bundle: Bundle) -> list[str]:
    return [
        *check_references(bundle),
        *check_citations(bundle),
        *check_media(bundle),
        *check_questions(bundle),
    ]


def main(argv: list[str]) -> int:
    if not argv:
        print("Cách dùng: python -m seed.check_bundle <bundle.json> [...]", file=sys.stderr)
        return 2
    failed = False
    for arg in argv:
        bundle = json.loads(Path(arg).read_text(encoding="utf-8"))
        errors = check_bundle(bundle)
        if errors:
            failed = True
            print(f"FAIL {arg}: {len(errors)} lỗi")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"OK {arg}: hợp lệ")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
