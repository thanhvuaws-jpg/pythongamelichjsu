"""Đánh giá Điều_Kiện_Mở_Khóa (`unlock_rule` JSON).

Cú pháp:
    {"all": [rule, ...]}            mọi điều kiện con đúng
    {"any": [rule, ...]}            ít nhất một điều kiện con đúng
    {"quest_done": "<id>"}          Nhiệm_Vụ đã hoàn thành
    {"level_done": "<id>"}          Màn_Chơi đã hoàn thành
    {"objective_done": "<id>"}      Mục_Tiêu đã hoàn thành
    {"min_points": 100}             Điểm_Kiến_Thức tối thiểu
`None` hoặc `{}` nghĩa là không có điều kiện (luôn mở).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

Rule = Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class UnlockContext:
    done_quests: frozenset[str] = field(default_factory=frozenset)
    done_levels: frozenset[str] = field(default_factory=frozenset)
    done_objectives: frozenset[str] = field(default_factory=frozenset)
    points: int = 0


def evaluate(rule: Rule, ctx: UnlockContext) -> bool:
    if not rule:
        return True
    if len(rule) != 1:
        # Nhiều khóa ở cùng cấp được hiểu như "all"
        return all(evaluate({k: v}, ctx) for k, v in rule.items())
    (key, value), = rule.items()
    match key:
        case "all":
            return all(evaluate(r, ctx) for r in value)
        case "any":
            return any(evaluate(r, ctx) for r in value)
        case "quest_done":
            return str(value) in ctx.done_quests
        case "level_done":
            return str(value) in ctx.done_levels
        case "objective_done":
            return str(value) in ctx.done_objectives
        case "min_points":
            return ctx.points >= int(value)
    raise ValueError(f"Điều kiện mở khóa không hỗ trợ: {key}")


def missing(rule: Rule, ctx: UnlockContext) -> list[dict[str, Any]]:
    """Liệt kê điều kiện lá còn thiếu, để hiển thị cho Người_Chơi (Req 9.4, 11.3)."""
    if evaluate(rule, ctx):
        return []
    assert rule is not None
    if len(rule) != 1:
        return [m for k, v in rule.items() for m in missing({k: v}, ctx)]
    (key, value), = rule.items()
    if key == "all":
        return [m for r in value for m in missing(r, ctx)]
    if key == "any":
        return [{"any": [m for r in value for m in missing(r, ctx)]}]
    return [dict(rule)]
