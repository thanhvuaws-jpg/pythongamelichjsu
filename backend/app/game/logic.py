"""Phần thuần logic: đọc nội dung game, tính điểm từ bản lưu, tổng hợp thống kê.

Game chấm câu hỏi ở trình duyệt nên bản lưu người chơi gửi lên có thể bị sửa. Vì vậy máy chủ
không tin con số điểm trong bản lưu mà tính lại từ danh sách câu đã giải: chỉ câu có thật mới
được tính, mỗi câu một lần, nên điểm không thể vượt quá mức tối đa của game. Muốn chống gian
lận triệt để thì phải chuyển việc chấm lên máy chủ.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from shared.scoring import TIMELINE_BONUS, points_for

LEVEL_FILES = ("man1.json", "man2.json", "man3.json")
EXTRA_KINDS = ("discoveries", "cases", "sides", "documents")
REF_NAMESPACE = uuid.UUID("7a3f1c52-6c1e-4f0b-9b57-3f5a2c8e1d44")
HARDEST_LIMIT = 10


@dataclass(frozen=True)
class GameContent:
    questions: dict[str, dict[str, Any]] = field(default_factory=dict)
    levels: list[dict[str, Any]] = field(default_factory=list)
    relics: int = 0
    extras: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


@lru_cache
def load_content(content_dir: str) -> GameContent:
    root = Path(content_dir)
    questions: dict[str, dict[str, Any]] = {}
    levels: list[dict[str, Any]] = []
    relics = 0
    for name in LEVEL_FILES:
        bundle = json.loads((root / name).read_text(encoding="utf-8"))
        level = bundle["level"]
        levels.append({"id": level["id"], "title": level["title"]})
        relics += len(bundle["relics"])
        for q in bundle["questions"]:
            questions[q["id"]] = {
                "difficulty": q.get("difficulty", 1),
                "prompt": q["prompt"],
                "level": level["id"],
            }
    extras = json.loads((root / "extras.json").read_text(encoding="utf-8"))
    for kind in EXTRA_KINDS:
        for item in extras.get(kind, []):
            q = item["question"]
            questions[q["id"]] = {
                "difficulty": q.get("difficulty", 1),
                "prompt": q["prompt"],
                "level": item["level"],
            }
    return GameContent(questions=questions, levels=levels, relics=relics, extras=extras)


def ref_id(kind: str, key: str) -> uuid.UUID:
    """Sổ điểm dùng UUID làm khoá nên đổi mã chữ của game sang UUID cố định."""
    return uuid.uuid5(REF_NAMESPACE, f"{kind}:{key}")


def _strings(value: Any) -> set[str]:
    return {x for x in value if isinstance(x, str)} if isinstance(value, list) else set()


def _attempt(save: dict[str, Any], qid: str) -> int:
    attempts = save.get("attempts")
    n = attempts.get(qid, 1) if isinstance(attempts, dict) else 1
    return n if isinstance(n, int) and n >= 1 else 1


def score_items(save: dict[str, Any], content: GameContent) -> dict[tuple[str, str], int]:
    """Các khoản điểm từ bản lưu: {(loại, mã): điểm}. Câu bỏ cuộc, câu không có thật không tính."""
    items: dict[tuple[str, str], int] = {}
    solved = _strings(save.get("solved")) - _strings(save.get("gave_up"))
    for qid in solved:
        question = content.questions.get(qid)
        if question is None:
            continue
        points = points_for(question["difficulty"], _attempt(save, qid))
        if points > 0:
            items[("question", qid)] = points
    known_levels = {level["id"] for level in content.levels}
    for level_id in _strings(save.get("timeline_done")) & known_levels:
        items[("timeline_bonus", level_id)] = TIMELINE_BONUS
    return items


def total_score(save: dict[str, Any], content: GameContent) -> int:
    return sum(score_items(save, content).values())


def aggregate(saves: list[dict[str, Any]], content: GameContent) -> dict[str, Any]:
    """Thống kê chung cho quản trị viên, tính từ bản lưu của mọi người chơi."""
    n = len(saves)
    tries: dict[str, list[int]] = {}
    gave_up: dict[str, int] = {}
    level_done = dict.fromkeys((level["id"] for level in content.levels), 0)
    skills: dict[str, int] = {}
    arena: dict[str, int] = {}
    counts = {"discovered": 0, "case_done": 0, "side_done": 0, "skirmish_done": 0, "doc_done": 0}
    stamps = points = 0
    for save in saves:
        points += total_score(save, content)
        stamps += len(_strings(save.get("stamps")))
        attempts = save.get("attempts") if isinstance(save.get("attempts"), dict) else {}
        for qid, value in attempts.items():
            if qid in content.questions and isinstance(value, int) and value >= 1:
                tries.setdefault(qid, []).append(value)
        for qid in _strings(save.get("gave_up")):
            gave_up[qid] = gave_up.get(qid, 0) + 1
        for level_id in _strings(save.get("completed_levels")):
            if level_id in level_done:
                level_done[level_id] += 1
        for sid in (
            save.get("skill_levels", {}) if isinstance(save.get("skill_levels"), dict) else ()
        ):
            skills[sid] = skills.get(sid, 0) + 1
        for bot in _strings(save.get("arena_wins")):
            arena[bot] = arena.get(bot, 0) + 1
        for key in counts:
            counts[key] += len(_strings(save.get(key)))
    hardest = sorted(
        (
            {
                "id": qid,
                "prompt": content.questions[qid]["prompt"],
                "players": len(values),
                "avg_attempts": round(sum(values) / len(values), 2),
                "gave_up": gave_up.get(qid, 0),
            }
            for qid, values in tries.items()
        ),
        key=lambda row: (-row["avg_attempts"], -row["gave_up"], -row["players"], row["id"]),
    )[:HARDEST_LIMIT]
    return {
        "players_with_save": n,
        "avg_points": round(points / n, 1) if n else 0,
        "avg_stamps": round(stamps / n, 1) if n else 0,
        "total_relics": content.relics,
        "total_questions": len(content.questions),
        "levels": [
            {"id": lv["id"], "title": lv["title"], "completed": level_done[lv["id"]]}
            for lv in content.levels
        ],
        "hardest_questions": hardest,
        "skills": skills,
        "arena_wins": arena,
        "activity": counts,
    }
