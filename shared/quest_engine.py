"""Bộ máy Nhiệm_Vụ thuần Python, dùng chung cho Game_Client và Backend_API.

Dữ liệu màn lấy từ Content_Bundle (dict). Engine giữ `Progress` và trả về danh sách
`Effect` sau mỗi hành động để Scene hiển thị (Req 9.3, 9.5, 12.3, 12.5, 13.3).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from shared.unlock import UnlockContext, evaluate, missing


# ---------- Effect ----------
@dataclass(frozen=True, slots=True)
class ObjectiveDone:
    quest_id: str
    objective_id: str


@dataclass(frozen=True, slots=True)
class QuestDone:
    quest_id: str


@dataclass(frozen=True, slots=True)
class Unlock:
    kind: str  # "quest" | "place" | "event"
    id: str


@dataclass(frozen=True, slots=True)
class ShowSummary:
    quest_id: str


@dataclass(frozen=True, slots=True)
class LevelDone:
    level_id: str


Effect = ObjectiveDone | QuestDone | Unlock | ShowSummary | LevelDone


# ---------- Progress ----------
@dataclass
class Progress:
    completed_objectives: set[str] = field(default_factory=set)
    collected_fragments: set[str] = field(default_factory=set)
    unlocked_events: set[str] = field(default_factory=set)
    timeline_done: set[str] = field(default_factory=set)  # level_id đã xong Dòng_Thời_Gian
    completed_levels: set[str] = field(default_factory=set)
    points: int = 0


# ---------- Engine ----------
class QuestEngine:
    def __init__(self, bundle: Mapping[str, Any], progress: Progress):
        self.level_id: str = str(bundle["level"]["id"])
        self.progress = progress
        # Sao chép để không sửa bundle gốc
        self.quests: list[dict[str, Any]] = [
            {**q, "objectives": sorted(q.get("objectives", []), key=lambda o: o.get("order_no", 0))}
            for q in sorted(bundle.get("quests", []), key=lambda q: q.get("order_no", 0))
        ]
        self.places: dict[str, dict[str, Any]] = {p["id"]: p for p in bundle.get("places", [])}
        # Giao diện hỏi hai tập này nhiều lần mỗi khung hình, nên lưu lại tới khi tiến trình đổi
        self._memo_key: tuple[int, int, int, int] | None = None
        self._memo_done: frozenset[str] | None = None
        self._memo_places: frozenset[str] | None = None
        self._event_fragments: dict[str, set[str]] = {}
        for f in bundle.get("fragments", []):
            if f.get("event_id"):
                self._event_fragments.setdefault(f["event_id"], set()).add(f["id"])
        for e in bundle.get("events", []):
            if e.get("fragment_ids"):
                self._event_fragments.setdefault(e["id"], set()).update(e["fragment_ids"])

    # ----- truy vấn -----
    def _quest_done(self, quest: Mapping[str, Any]) -> bool:
        required = [o for o in quest["objectives"] if o.get("required", True)]
        return all(o["id"] in self.progress.completed_objectives for o in required)

    def _check_memo(self) -> None:
        """Các tập trong Progress chỉ thêm chứ không bớt, nên độ dài đổi là tiến trình đã đổi."""
        p = self.progress
        key = (
            id(p.completed_objectives),
            len(p.completed_objectives),
            len(p.completed_levels),
            p.points,
        )
        if key != self._memo_key:
            self._memo_key = key
            self._memo_done = self._memo_places = None

    def done_quests(self) -> frozenset[str]:
        self._check_memo()
        if self._memo_done is None:
            self._memo_done = frozenset(q["id"] for q in self.quests if self._quest_done(q))
        return self._memo_done

    def context(self) -> UnlockContext:
        p = self.progress
        return UnlockContext(
            done_quests=self.done_quests(),
            done_levels=frozenset(p.completed_levels),
            done_objectives=frozenset(p.completed_objectives),
            points=p.points,
        )

    def available_quests(self) -> list[dict[str, Any]]:
        ctx = self.context()
        return [q for q in self.quests if evaluate(q.get("unlock_rule"), ctx)]

    def unlocked_places(self) -> frozenset[str]:
        self._check_memo()
        if self._memo_places is None:
            ctx = self.context()
            self._memo_places = frozenset(
                pid for pid, p in self.places.items() if evaluate(p.get("unlock_rule"), ctx)
            )
        return self._memo_places

    def place_missing(self, place_id: str) -> list[dict[str, Any]]:
        return missing(self.places[place_id].get("unlock_rule"), self.context())

    def active_objectives(self, quest_id: str) -> list[dict[str, Any]]:
        """Mục_Tiêu chưa xong mà mọi Mục_Tiêu bắt buộc đứng trước đã xong."""
        quest = next(q for q in self.quests if q["id"] == quest_id)
        done = self.progress.completed_objectives
        result = []
        for o in quest["objectives"]:
            if o["id"] not in done:
                result.append(o)
                if o.get("required", True):
                    break
        return result

    def is_level_complete(self) -> bool:
        """Mọi Nhiệm_Vụ bắt buộc xong và Dòng_Thời_Gian xong; bỏ qua nhiệm vụ phụ."""
        mandatory = [q for q in self.quests if not q.get("is_optional", False)]
        return self.level_id in self.progress.timeline_done and all(
            self._quest_done(q) for q in mandatory
        )

    # ----- hành động -----
    def on_arrive(self, place_id: str) -> list[Effect]:
        return self._complete("go_to", place_id)

    def on_collect(self, fragment_id: str) -> list[Effect]:
        effects: list[Effect] = []
        if fragment_id not in self.progress.collected_fragments:
            self.progress.collected_fragments.add(fragment_id)
            for event_id, frags in self._event_fragments.items():
                if (
                    fragment_id in frags
                    and event_id not in self.progress.unlocked_events
                    and frags <= self.progress.collected_fragments
                ):
                    self.progress.unlocked_events.add(event_id)
                    effects.append(Unlock("event", event_id))
        return effects + self._complete("collect", fragment_id)

    def on_dialogue_done(self, dialogue_id: str) -> list[Effect]:
        return self._complete("dialogue", dialogue_id)

    def on_question_correct(self, question_id: str) -> list[Effect]:
        return self._complete("answer", question_id)

    def on_battle_done(self, battle_id: str) -> list[Effect]:
        return self._complete("battle", battle_id)

    def on_timeline_done(self) -> list[Effect]:
        # Xét trạng thái trước khi thêm: Dòng_Thời_Gian thường là bước cuối cùng của màn
        was_complete = self.is_level_complete()
        self.progress.timeline_done.add(self.level_id)
        effects = self._complete("timeline", None)
        if not was_complete and self.is_level_complete():
            self.progress.completed_levels.add(self.level_id)
            effects.append(LevelDone(self.level_id))
        return effects

    # ----- nội bộ -----
    def _complete(self, kind: str, target_id: str | None) -> list[Effect]:
        before_quests = {q["id"] for q in self.available_quests()}
        before_places = self.unlocked_places()
        was_complete = self.is_level_complete()
        effects: list[Effect] = []

        for quest in self.available_quests():
            if self._quest_done(quest):
                continue
            for o in self.active_objectives(quest["id"]):
                if o["kind"] == kind and (kind == "timeline" or o.get("target_id") == target_id):
                    self.progress.completed_objectives.add(o["id"])
                    effects.append(ObjectiveDone(quest["id"], o["id"]))
            if self._quest_done(quest):
                effects += [QuestDone(quest["id"]), ShowSummary(quest["id"])]

        effects += [
            Unlock("quest", qid)
            for qid in [q["id"] for q in self.available_quests()]
            if qid not in before_quests
        ]
        effects += [Unlock("place", pid) for pid in sorted(self.unlocked_places() - before_places)]

        if not was_complete and self.is_level_complete():
            self.progress.completed_levels.add(self.level_id)
            effects.append(LevelDone(self.level_id))
        return effects
