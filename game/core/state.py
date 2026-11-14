"""Trạng thái game: nạp nội dung, tiến trình, điểm, ôn tập, phần thưởng, lưu/đọc.

Luật chơi dùng lại từ `shared/` (quest_engine, grading, scoring, review_schedule) để client và
server không lệch nhau. Nội dung đợt 1 đọc từ game/content/*.json (có sẵn đáp án, chấm ở client);
khi nối API, điểm xếp hạng sẽ do server chấm.
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core import platform_io, progression, rpg
from shared.grading import grade
from shared.quest_engine import (
    LevelDone,
    ObjectiveDone,
    Progress,
    QuestDone,
    QuestEngine,
    Unlock,
)
from shared.review_schedule import ReviewCandidate, due_at, pick_review_questions
from shared.scoring import needs_review, points_for, timeline_bonus
from shared.unlock import UnlockContext, evaluate

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
LEVEL_FILES = ("man1.json", "man2.json", "man3.json")
SOURCES_FILE = "sources.json"
WORLDS_FILE = "worlds.json"
EXTRAS_FILE = "extras.json"
EXTRA_KINDS = ("discoveries", "cases", "sides", "documents")
REVIEW_SESSION = 10
REVIEW_POINTS = 2  # điểm ôn tập nhỏ để khuyến khích quay lại
REVIEW_MASTERED = 3  # đã ôn đúng liên tiếp tới mốc 14 ngày thì coi như đã thuộc
ROLE_KEY = "sukydieutra.role"
BONUS_KEY = "sukydieutra.bonus"
INDEXED = ("places", "persons", "events", "fragments", "dialogues", "questions", "battles", "relics", "artifacts")

# Danh hiệu ngoài các danh hiệu theo màn (khai báo trong level.badge)
GLOBAL_BADGES = {
    "nha_tham_hiem": {"name": "Nhà thám hiểm", "desc": "Đóng dấu 10 di tích trong Hộ chiếu di sản"},
    "bach_phat": {"name": "Bách phát bách trúng", "desc": "Trả lời đúng ngay lần đầu 15 câu hỏi"},
    "chuyen_can": {"name": "Sử quan chuyên cần", "desc": "Hoàn thành một phiên ôn tập"},
    "giu_su": {"name": "Người giữ sử", "desc": "Phục dựng đủ mọi tư liệu trong Kho tư liệu"},
    "tuong_tai": {"name": "Tướng tài", "desc": "Đạt 3 sao ở một trận đánh"},
}


def _now() -> datetime:
    return datetime.now(UTC)


def _build_quests(bundle: dict) -> None:
    """Mỗi di tích là một Nhiệm_Vụ: đến nơi rồi lần lượt qua các bước của di tích."""
    quests, place_by_id = [], {p["id"]: p for p in bundle["places"]}
    for order, relic in enumerate(bundle["relics"]):
        requires = relic.get("requires") or []
        rule = {"all": [{"quest_done": r} for r in requires]} if requires else None
        objectives = [{
            "id": f"{relic['id']}:0", "order_no": 0, "kind": "go_to", "target_id": relic["place"], "required": True,
        }]
        for i, step in enumerate(relic["steps"], 1):
            (kind, target), = step.items()
            mapped = {"story": "dialogue", "question": "answer", "fragment": "collect", "battle": "battle"}[kind]
            objectives.append({
                "id": f"{relic['id']}:{i}", "order_no": i, "kind": mapped, "target_id": target, "required": True,
            })
        quests.append({
            "id": relic["id"], "order_no": order, "title": relic["title"], "objectives": objectives,
            "central_question": relic.get("central_question", ""), "is_optional": relic.get("optional", False),
            "unlock_rule": rule,
        })
        place_by_id[relic["place"]]["unlock_rule"] = rule
    bundle["quests"] = quests


class GameState:
    def __init__(self):
        self.levels: dict[str, dict] = {}
        self.order: list[str] = []
        self.index: dict[str, dict[str, dict]] = {k: {} for k in INDEXED}
        self.level_of: dict[str, str] = {}
        self.sources = json.loads((CONTENT_DIR / SOURCES_FILE).read_text(encoding="utf-8"))
        self.worlds = json.loads((CONTENT_DIR / WORLDS_FILE).read_text(encoding="utf-8"))
        # Vùng luyện: map phụ để luyện tay, mỗi vùng gắn với một sự kiện có thật, mở khi học xong di tích liên quan
        self.fields = json.loads((CONTENT_DIR / "fields.json").read_text(encoding="utf-8"))
        for name in LEVEL_FILES:
            bundle = json.loads((CONTENT_DIR / name).read_text(encoding="utf-8"))
            _build_quests(bundle)
            lid = bundle["level"]["id"]
            self.levels[lid] = bundle
            self.order.append(lid)
            for kind in INDEXED:
                for item in bundle.get(kind, []):
                    self.index[kind][item["id"]] = item
                    self.level_of[item["id"]] = lid
        self.extras = json.loads((CONTENT_DIR / EXTRAS_FILE).read_text(encoding="utf-8"))
        for kind in EXTRA_KINDS:  # câu hỏi của phần khám phá dùng chung sổ câu hỏi nên vẫn vào được ôn tập
            for item in self.extras[kind]:
                question = item["question"]
                self.index["questions"][question["id"]] = question
                self.level_of[question["id"]] = item["level"]
        self.reset()
        self.load()

    # ---------- dữ liệu người chơi ----------
    def reset(self):
        self.progress = Progress()
        self.attempts: dict[str, int] = {}
        self.solved: set[str] = set()
        self.first_try: set[str] = set()
        self.review: dict[str, dict] = {}
        self.stamps: set[str] = set()
        self.owned_artifacts: set[str] = set()
        self.badges: set[str] = set()
        self.notebook: set[str] = set()
        self.clues: dict[str, str] = {}
        self.done_topics: set[str] = set()
        self.battle_stars: dict[str, int] = {}
        self.settings = {"violence": "day_du", "sound": True, "text_speed": 1.0}
        self.intro_done = False
        self.tutorial_seen = False
        self.player_pos: dict[str, list] = {}
        self.current_level: str | None = None
        self.finished = False
        self.gave_up: set[str] = set()
        self.stat_levels: dict[str, int] = {}
        self.skill_levels: dict[str, int] = {}
        self.equipped: list[str] = []
        self.arena_wins: set[str] = set()
        self.discovered: set[str] = set()
        self.case_done: set[str] = set()
        self.case_clues: dict[str, list[int]] = {}
        self.side_done: set[str] = set()
        self.side_state: dict[str, dict] = {}
        self.skirmish_done: set[str] = set()
        self.doc_pieces: dict[str, list[int]] = {}
        self.doc_done: set[str] = set()
        # nhập vai: cấp, kinh nghiệm, tiềm năng, tiền quan, cảnh giới, đồ, thuốc, hồi ức đã chìm vào, trùm đã hạ
        self.level = 1
        self.exp = 0
        self.tiem_nang = 0
        self.quan = 0
        self.realm = 0
        self.inventory: list[str] = list(rpg.STARTER)
        self.gear: dict[str, str] = {rpg.ITEMS[i]["slot"]: i for i in rpg.STARTER}
        self.potions = 2
        self.fish: dict[str, int] = {}  # cá tươi câu được, theo loại
        self.grilled = 0  # số xiên cá nướng mang theo
        self.memory_seen: set[str] = set()
        self.bosses_beaten: set[str] = set()  # mã di tích có kẻ canh mật thư đã bị hạ
        self.boss_tries: dict[str, int] = {}  # số lần thua mỗi trùm, để trùm yếu dần
        self.reports: list[str] = []  # di tích đã xong nhưng chưa về báo cáo già làng
        self.mobs_killed = 0
        self.duels_won = 0
        self.field_log: dict[str, dict] = {}  # mỗi vùng luyện: đã nghe chuyện chưa, đã hạ kẻ mạnh nhất mấy lần
        self.bestiary: set[str] = set()  # loại quái đã hạ ít nhất một lần, để xem lại dòng sử về chúng
        self.events: list[str] = []  # thông báo lên cấp, nhận tinh hoa... để màn đang mở hiện ra
        # Do máy chủ quyết định, trang chơi ghi vào localStorage; không nằm trong bản lưu
        self.is_admin = False
        self.bonus_points = 0
        self.bonus_skill_points = 0
        self._engines: dict[str, QuestEngine] = {}

    def to_dict(self) -> dict:
        p = self.progress
        return {
            "completed_objectives": sorted(p.completed_objectives),
            "collected_fragments": sorted(p.collected_fragments),
            "unlocked_events": sorted(p.unlocked_events),
            "timeline_done": sorted(p.timeline_done),
            "completed_levels": sorted(p.completed_levels),
            "points": p.points,
            "attempts": self.attempts,
            "solved": sorted(self.solved),
            "first_try": sorted(self.first_try),
            "review": self.review,
            "stamps": sorted(self.stamps),
            "artifacts": sorted(self.owned_artifacts),
            "badges": sorted(self.badges),
            "notebook": sorted(self.notebook),
            "clues": self.clues,
            "done_topics": sorted(self.done_topics),
            "battle_stars": self.battle_stars,
            "settings": self.settings,
            "intro_done": self.intro_done,
            "tutorial_seen": self.tutorial_seen,
            "player_pos": self.player_pos,
            "current_level": self.current_level,
            "finished": self.finished,
            "gave_up": sorted(self.gave_up),
            "stat_levels": self.stat_levels,
            "skill_levels": self.skill_levels,
            "equipped": self.equipped,
            "arena_wins": sorted(self.arena_wins),
            "discovered": sorted(self.discovered),
            "case_done": sorted(self.case_done),
            "case_clues": self.case_clues,
            "side_done": sorted(self.side_done),
            "side_state": self.side_state,
            "skirmish_done": sorted(self.skirmish_done),
            "doc_pieces": self.doc_pieces,
            "doc_done": sorted(self.doc_done),
            "rpg": {
                "level": self.level, "exp": self.exp, "tiem_nang": self.tiem_nang, "quan": self.quan, "realm": self.realm,
                "inventory": self.inventory, "gear": self.gear, "potions": self.potions, "fish": self.fish, "grilled": self.grilled,
                "memory_seen": sorted(self.memory_seen),
                "bosses_beaten": sorted(self.bosses_beaten), "mobs_killed": self.mobs_killed, "boss_tries": self.boss_tries,
                "reports": self.reports, "duels_won": self.duels_won, "field_log": self.field_log, "bestiary": sorted(self.bestiary),
                "power": self.power_rating(),  # máy chủ đọc để xếp Bảng vàng theo sức mạnh
            },
            "updated_at": _now().isoformat(),
        }

    def from_dict(self, d: dict) -> None:
        p = self.progress
        p.completed_objectives = set(d.get("completed_objectives", []))
        p.collected_fragments = set(d.get("collected_fragments", []))
        p.unlocked_events = set(d.get("unlocked_events", []))
        p.timeline_done = set(d.get("timeline_done", []))
        p.completed_levels = set(d.get("completed_levels", []))
        p.points = int(d.get("points", 0))
        self.attempts = dict(d.get("attempts", {}))
        self.solved = set(d.get("solved", []))
        self.first_try = set(d.get("first_try", []))
        self.review = dict(d.get("review", {}))
        self.stamps = set(d.get("stamps", []))
        self.owned_artifacts = set(d.get("artifacts", []))
        self.badges = set(d.get("badges", []))
        self.notebook = set(d.get("notebook", []))
        self.clues = dict(d.get("clues", {}))
        self.done_topics = set(d.get("done_topics", []))
        self.battle_stars = dict(d.get("battle_stars", {}))
        self.settings.update(d.get("settings", {}))
        self.intro_done = bool(d.get("intro_done", False))
        self.tutorial_seen = bool(d.get("tutorial_seen", False))
        self.player_pos = {k: v for k, v in d.get("player_pos", {}).items() if isinstance(v, list)}
        self.current_level = d.get("current_level")
        self.finished = bool(d.get("finished", False))
        self.gave_up = set(d.get("gave_up", []))
        self.stat_levels = {k: int(v) for k, v in d.get("stat_levels", {}).items() if k in progression.STATS}
        self.skill_levels = {k: int(v) for k, v in d.get("skill_levels", {}).items() if k in progression.SKILLS}
        self.equipped = [s for s in d.get("equipped", []) if s in self.skill_levels][: progression.SLOTS]
        self.arena_wins = set(d.get("arena_wins", []))
        self.discovered = set(d.get("discovered", []))
        self.case_done = set(d.get("case_done", []))
        self.case_clues = dict(d.get("case_clues", {}))
        self.side_done = set(d.get("side_done", []))
        self.side_state = dict(d.get("side_state", {}))
        self.skirmish_done = set(d.get("skirmish_done", []))
        pieces = d.get("doc_pieces", {})
        self.doc_pieces = {k: sorted({int(i) for i in v}) for k, v in pieces.items()} if isinstance(pieces, dict) else {}
        self.doc_done = set(d.get("doc_done", []))
        old = not isinstance(d.get("rpg"), dict)
        r = {} if old else d["rpg"]
        self.level = max(1, min(rpg.REALMS[-1]["cap"], int(r.get("level", 1))))
        self.exp = max(0, int(r.get("exp", 0)))
        self.tiem_nang = max(0, int(r.get("tiem_nang", 0)))
        self.quan = max(0, int(r.get("quan", 0)))
        self.realm = max(0, min(len(rpg.REALMS) - 1, int(r.get("realm", 0))))
        inv = [i for i in r.get("inventory", []) if i in rpg.ITEMS]
        self.inventory = [*[i for i in rpg.STARTER if i not in inv], *inv]
        gear = r.get("gear", {rpg.ITEMS[i]["slot"]: i for i in rpg.STARTER}) if isinstance(r.get("gear", {}), dict) else {}
        self.gear = {k: v for k, v in gear.items() if v in self.inventory and rpg.ITEMS[v]["slot"] == k}
        self.potions = max(0, int(r.get("potions", 2)))
        fish = r.get("fish", {}) if isinstance(r.get("fish", {}), dict) else {}
        self.fish = {k: max(0, min(rpg.MAX_FISH, int(v))) for k, v in fish.items() if k in rpg.FISH and int(v) > 0}
        self.grilled = max(0, min(rpg.MAX_GRILL, int(r.get("grilled", 0))))
        self.memory_seen = set(r.get("memory_seen", []))
        self.bosses_beaten = set(r.get("bosses_beaten", []))
        self.boss_tries = {k: int(v) for k, v in r.get("boss_tries", {}).items()} if isinstance(r.get("boss_tries"), dict) else {}
        # Bản lưu từ trước khi có lối chơi nhập vai: di tích đã đóng dấu thì cho về báo cáo để nhận thưởng bù
        reports = sorted(self.stamps) if old else r.get("reports", [])
        self.reports = [x for x in reports if x in self.stamps]
        self.mobs_killed = max(0, int(r.get("mobs_killed", 0)))
        self.duels_won = max(0, int(r.get("duels_won", 0)))
        self.bestiary = {m for m in r.get("bestiary", []) if m in rpg.MOBS}
        log = r.get("field_log", {})
        self.field_log = {k: dict(v) for k, v in log.items() if k in self.fields and isinstance(v, dict)} if isinstance(log, dict) else {}

    def load(self) -> None:
        data = platform_io.load_save()
        if isinstance(data, dict):
            try:
                self.from_dict(data)
            except (TypeError, ValueError, AttributeError):
                self.reset()
        self.refresh_external()

    def refresh_external(self) -> int:
        """Đọc lại vai trò và điểm được tặng. Trả về số điểm vừa được tặng thêm để báo cho người chơi.

        Vai trò trong game chỉ mở quyền đi lại trên máy của chính người đó. Các quyền thật như cộng điểm, khoá tài
        khoản đều do máy chủ kiểm tra.
        """
        self.is_admin = platform_io.read_key(ROLE_KEY) == "admin"
        raw = platform_io.read_key(BONUS_KEY)
        if not raw:
            return 0
        try:
            bonus = json.loads(raw)
            points, skill = int(bonus.get("points", 0)), int(bonus.get("skill_points", 0))
        except (ValueError, TypeError, AttributeError):
            return 0
        gained = points - self.bonus_points
        self.bonus_points, self.bonus_skill_points = points, max(0, skill)
        return gained

    @property
    def total_points(self) -> int:
        return self.progress.points + self.bonus_points

    def save(self) -> None:
        platform_io.write_save(self.to_dict())

    # ---------- màn chơi ----------
    def engine(self, level_id: str) -> QuestEngine:
        if level_id not in self._engines:
            self._engines[level_id] = QuestEngine(self.levels[level_id], self.progress)
        return self._engines[level_id]

    def level_unlocked(self, level_id: str) -> bool:
        ctx = UnlockContext(done_levels=frozenset(self.progress.completed_levels), points=self.progress.points)
        return evaluate(self.levels[level_id]["level"].get("unlock_rule"), ctx)

    def mandatory_relics(self, level_id: str) -> list[dict]:
        return [r for r in self.levels[level_id]["relics"] if not r.get("optional")]

    def relic_done(self, relic_id: str) -> bool:
        lid = self.level_of[relic_id]
        return relic_id in self.engine(lid).done_quests()

    def level_ratio(self, level_id: str) -> float:
        """Tỉ lệ hoàn thành màn: tính theo Mục_Tiêu bắt buộc, cộng thêm phần Dòng_Thời_Gian."""
        eng = self.engine(level_id)
        total = done = 0
        for q in eng.quests:
            if q.get("is_optional"):
                continue
            for o in q["objectives"]:
                total += 1
                done += o["id"] in self.progress.completed_objectives
        total += 1
        done += level_id in self.progress.timeline_done
        return done / max(1, total)

    def timeline_ready(self, level_id: str) -> bool:
        return all(self.relic_done(r["id"]) for r in self.mandatory_relics(level_id))

    def next_relic(self, level_id: str) -> dict | None:
        eng = self.engine(level_id)
        unlocked = eng.unlocked_places()
        for r in self.levels[level_id]["relics"]:
            if not self.relic_done(r["id"]) and r["place"] in unlocked and not r.get("optional"):
                return r
        return None

    # ---------- câu hỏi ----------
    def check(self, question: dict, answer: Any) -> bool:
        return grade(question, answer)

    def record_answer(self, question: dict, correct: bool) -> dict:
        """Ghi một lần trả lời. Điểm chỉ cộng một lần cho mỗi câu (Req 18)."""
        qid = question["id"]
        n = self.attempts.get(qid, 0) + 1
        self.attempts[qid] = n
        points = 0
        if correct and qid not in self.solved:
            points = points_for(question.get("difficulty", 1), n)
            self.progress.points += points
            self.solved.add(qid)
            if n == 1:
                self.first_try.add(qid)
            self.gain(rpg.ANSWER_EXP * question.get("difficulty", 1), 2, rpg.ANSWER_QUAN)
        if not correct or needs_review(n):
            self._schedule(qid, None, correct, n)
        elif qid not in self.review:
            # Đúng ngay hoặc đúng ở lần hai mà chưa có lịch: vẫn xếp lịch ôn, câu đúng ngay được giãn xa hơn
            self._schedule(qid, 0 if n == 1 else None, True, n)
        self.save()
        return {"points": points, "attempt": n}

    def give_up(self, question: dict) -> None:
        """Sau 3 lần sai: hiện đáp án, không có điểm, chắc chắn đưa vào ôn tập."""
        self.solved.add(question["id"])
        self.gave_up.add(question["id"])
        self._schedule(question["id"], None, False, self.attempts.get(question["id"], 3))
        self.save()

    def _schedule(self, qid: str, stage, correct: bool, attempts: int, reviewed: bool = False) -> None:
        new_stage, when = due_at(_now(), stage, correct)
        old = self.review.get(qid, {})
        self.review[qid] = {
            "stage": new_stage, "due": when.isoformat(), "last": correct, "attempts": attempts,
            "reviewed": _now().isoformat() if reviewed else old.get("reviewed"),
        }

    def _is_due(self, qid: str, now: datetime) -> bool:
        item = self.review.get(qid)
        if not item:
            return False
        try:
            return datetime.fromisoformat(item["due"]) <= now
        except (KeyError, TypeError, ValueError):
            return True  # lịch hỏng thì coi như đến hạn để câu đó được ôn rồi xếp lịch lại

    def review_plan(self, level_id: str | None = None, limit: int = REVIEW_SESSION) -> dict:
        """Lập một phiên ôn tối đa 10 câu trong số các câu đã gặp.

        `due`: câu đến hạn theo lịch 1-3-7-14-30 ngày, đúng thì giãn lịch và được điểm ôn tập.
        `early`: chưa đến hạn nhưng vẫn cho luyện thêm để ngay sau khi chơi đã ôn được, không tính điểm.
        Cả hai nhóm đều ưu tiên: câu từng sai, rồi câu phải thử nhiều lần, rồi câu lâu chưa ôn.
        """
        now = _now()
        questions = self.index["questions"]
        ids = [q for q in {*self.solved, *self.review} if q in questions]
        if level_id:
            ids = [q for q in ids if self.level_of.get(q) == level_id]
        due, early, next_due = [], [], None
        for qid in ids:
            item = self.review.get(qid, {})
            cand = self._cand(qid, item, self.attempts.get(qid, 1))
            if self._is_due(qid, now):
                due.append(cand)
                continue
            early.append(cand)
            if item.get("due"):
                when = datetime.fromisoformat(item["due"])
                next_due = when if next_due is None or when < next_due else next_due
        due_pick = pick_review_questions(due, limit)
        early_pick = pick_review_questions(early, limit - len(due_pick))
        days = None if next_due is None else max(1, int(-(-(next_due - now).total_seconds() // 86400)))
        return {
            "due": [questions[c.question_id] for c in due_pick],
            "early": [questions[c.question_id] for c in early_pick],
            "answered": len(ids),
            "due_total": len(due),
            "mastered": sum(1 for q in ids if (self.review.get(q, {}).get("stage") or 0) >= REVIEW_MASTERED),
            "next_due_days": days,
        }

    def review_due(self, level_id: str | None = None) -> list[dict]:
        """Các câu của một phiên ôn, câu đến hạn đứng trước."""
        plan = self.review_plan(level_id)
        return [*plan["due"], *plan["early"]]

    def weak_questions(self, level_id: str) -> list[dict]:
        """Câu từng trả lời sai hoặc phải thử nhiều lần trong một màn, để màn tổng kết nhắc ôn lại."""
        out = []
        for q in self.levels[level_id]["questions"]:
            item = self.review.get(q["id"])
            if item and (item.get("last") is False or item.get("attempts", 1) > 1):
                out.append(q)
        return out

    @staticmethod
    def _cand(qid: str, item: dict, attempts: int = 1) -> ReviewCandidate:
        when = datetime.fromisoformat(item["reviewed"]) if item.get("reviewed") else None
        return ReviewCandidate(qid, item.get("last"), item.get("attempts", attempts), when)

    def review_answer(self, question: dict, correct: bool) -> dict:
        """Ghi một câu ôn tập. Chỉ câu đến hạn mới đổi lịch và được điểm, nên không thể ôn đi ôn lại để lấy điểm."""
        qid = question["id"]
        item = self.review.get(qid)
        was_due = self._is_due(qid, _now())
        points = 0
        if was_due or item is None or not correct:
            # Đến hạn: đúng thì giãn lịch, sai thì quay về mai. Luyện thêm mà sai cũng quay về mai.
            stage = item.get("stage") if item and was_due else None
            attempts = item.get("attempts", 1) if item else self.attempts.get(qid, 1)
            self._schedule(qid, stage, correct, attempts, reviewed=True)
            if was_due and correct:
                points = REVIEW_POINTS
                self.progress.points += points
        else:
            item["reviewed"] = _now().isoformat()  # luyện thêm và đúng: giữ nguyên lịch, chỉ ghi nhận đã xem
        self.save()
        return {"counted": was_due, "points": points}

    # ---------- tư liệu ----------
    def documents(self, level_id: str | None = None) -> list[dict]:
        return [d for d in self.extras.get("documents", []) if level_id is None or d["level"] == level_id]

    def doc_got(self, doc: dict) -> list[int]:
        return self.doc_pieces.get(doc["id"], [])

    def doc_ready(self, doc: dict) -> bool:
        """Đã nhặt đủ mảnh mà chưa phục dựng."""
        return doc["id"] not in self.doc_done and len(set(self.doc_got(doc))) >= len(doc["pieces"])

    def take_piece(self, doc: dict, i: int) -> bool:
        got = self.doc_pieces.setdefault(doc["id"], [])
        if i in got or not 0 <= i < len(doc["pieces"]):
            return False
        got.append(i)
        got.sort()
        self.save()
        return True

    def restore_doc(self, doc: dict) -> bool:
        """Ghép xong một tư liệu; trả về True nếu vừa nhận thêm danh hiệu Người giữ sử."""
        self.doc_done.add(doc["id"])
        new_badge = False
        if all(d["id"] in self.doc_done for d in self.documents()) and "giu_su" not in self.badges:
            self.badges.add("giu_su")
            new_badge = True
        self.save()
        return new_badge

    # ---------- kỹ năng, chỉ số ----------
    def skill_points_earned(self) -> int:
        """Tính lại từ tiến trình, nên bản lưu cũ cũng có đủ điểm và không thể nhận trùng."""
        p = progression
        return (
            len(self.first_try) * p.SP_FIRST_TRY + len(self.stamps) * p.SP_RELIC
            + len(self.progress.completed_levels) * p.SP_LEVEL + len(self.side_done) * p.SP_SIDE
            + len(self.case_done) * p.SP_CASE + len(self.discovered) * p.SP_DISCOVERY
            + len(self.skirmish_done) * p.SP_SKIRMISH + len(self.arena_wins) * p.SP_ARENA
            + len(self.doc_done) * p.SP_DOCUMENT
            + self.bonus_skill_points
        )

    def skill_points_spent(self) -> int:
        """Điểm kỹ năng chỉ dùng để học kỹ năng; chỉ số mua bằng tiềm năng."""
        return sum(lv * (lv + 1) // 2 for lv in self.skill_levels.values())

    def skill_points_left(self) -> int:
        return self.skill_points_earned() - self.skill_points_spent()

    def need_progress(self, need) -> int:
        return len(self.solved - self.gave_up) if need[0] == "answers" else len(self.stamps)

    def skill_unlocked(self, sid: str) -> bool:
        need = progression.SKILLS[sid]["needs"]
        return self.need_progress(need) >= need[1]

    def stat_cost(self, sid: str) -> int:
        return rpg.stat_cost(self.stat_levels.get(sid, 0) + 1)

    def upgrade_stat(self, sid: str) -> bool:
        """Tăng một bậc chỉ số bằng tiềm năng kiếm được khi đánh quái và làm nhiệm vụ."""
        level = self.stat_levels.get(sid, 0)
        cost = rpg.stat_cost(level + 1)
        if self.tiem_nang < cost or level >= progression.STAT_MAX:
            return False
        self.tiem_nang -= cost
        self.stat_levels[sid] = level + 1
        self.save()
        return True

    def upgrade_skill(self, sid: str) -> bool:
        level = self.skill_levels.get(sid, 0)
        cost = progression.skill_cost(level + 1)
        if not self.skill_unlocked(sid) or level >= progression.SKILL_MAX or self.skill_points_left() < cost:
            return False
        self.skill_levels[sid] = level + 1
        if sid not in self.equipped and len(self.equipped) < progression.SLOTS:
            self.equipped.append(sid)
        self.save()
        return True

    def equipped_skills(self) -> list[str]:
        return [s for s in self.equipped if self.skill_levels.get(s, 0) > 0]

    def toggle_equip(self, sid: str) -> None:
        """Bỏ trang bị; hết chỗ thì kỹ năng mới thay vào chỗ của kỹ năng lắp sớm nhất."""
        if sid in self.equipped:
            self.equipped.remove(sid)
        elif self.skill_levels.get(sid, 0) > 0:
            if len(self.equipped) >= progression.SLOTS:
                self.equipped.pop(0)
            self.equipped.append(sid)
        self.save()

    def _gear(self, key: str) -> float:
        return sum(rpg.ITEMS[i].get(key, 0) for i in self.gear.values())

    def realm_mult(self) -> float:
        return rpg.REALMS[self.realm]["mult"]

    def max_hp(self) -> float:
        base = progression.BASE_HP + 12 * self.stat_levels.get("the", 0) + rpg.LEVEL_HP * (self.level - 1) + self._gear("hp")
        return base * self.realm_mult()

    def damage_mult(self) -> float:
        base = 1 + 0.08 * self.stat_levels.get("suc", 0) + rpg.LEVEL_DMG * (self.level - 1) + self._gear("dmg")
        return base * self.realm_mult()

    def speed_mult(self) -> float:
        return 1 + 0.04 * self.stat_levels.get("nhanh", 0) + self._gear("spd")

    def power_rating(self) -> int:
        """Sức mạnh tổng: con số để so với quái, tính từ máu, sát thương và tốc độ."""
        return round(self.max_hp() * self.damage_mult() * 3 + self.speed_mult() * 40)

    # ---------- nhập vai ----------
    def level_cap(self) -> int:
        return rpg.REALMS[self.realm]["cap"]

    def realm_name(self) -> str:
        return rpg.REALMS[self.realm]["name"]

    def gain(self, exp: int = 0, tiem: int = 0, quan: int = 0) -> list[str]:
        """Nhận kinh nghiệm, tiềm năng, tiền. Lên cấp tự động nhưng không vượt giới hạn của cảnh giới."""
        self.tiem_nang += tiem
        self.quan += quan
        msgs = []
        self.exp += exp
        while self.level < self.level_cap() and self.exp >= rpg.exp_need(self.level):
            self.exp -= rpg.exp_need(self.level)
            self.level += 1
            msgs.append(f"Lên cấp {self.level}! Máu và sức đánh tăng thêm.")
        if self.level >= self.level_cap():
            self.exp = min(self.exp, rpg.exp_need(self.level))
            if exp and self.exp >= rpg.exp_need(self.level):
                msgs.append(f"Đã tới giới hạn cảnh giới {self.realm_name()}. Cần tinh hoa để đột phá.")
        self.events.extend(msgs)
        return msgs

    def essence(self) -> int:
        """Tinh hoa: tính lại từ những gì đã học, nên không cộng trùng được."""
        e = rpg.ESSENCE
        return (len(self.memory_seen) * e["memory"] + len(self.discovered) * e["discovery"]
                + len(self.doc_done) * e["document"] + len(self.case_done) * e["case"])

    def next_realm(self) -> dict | None:
        return rpg.REALMS[self.realm + 1] if self.realm + 1 < len(rpg.REALMS) else None

    def can_break(self) -> bool:
        nxt = self.next_realm()
        return nxt is not None and self.level >= self.level_cap() and self.essence() >= nxt["need"]

    def breakthrough(self) -> bool:
        """Đột phá cảnh giới: mở giới hạn cấp mới, chỉ số nhân thêm."""
        if not self.can_break():
            return False
        self.realm += 1
        self.events.append(f"Đột phá thành công: {self.realm_name()}! Giới hạn cấp mở tới {self.level_cap()}.")
        self.gain()  # kinh nghiệm đang dồn có thể lên cấp tiếp
        self.save()
        return True

    def remember(self, dialogue_id: str) -> bool:
        """Chìm vào một hồi ức lần đầu thì nhận thức thêm tinh hoa."""
        if not dialogue_id or dialogue_id in self.memory_seen:
            return False
        self.memory_seen.add(dialogue_id)
        self.events.append(f"Nhận thức tinh hoa từ hồi ức: +{rpg.ESSENCE['memory']} (tổng {self.essence()})")
        return True

    def buy(self, item_id: str) -> str | None:
        """Mua đồ ở lò rèn; trả về lý do nếu không mua được."""
        item = rpg.ITEMS[item_id]
        if item.get("craft"):
            return "Món này không bán, phải tự làm ra."
        if item["slot"] != "dung" and item_id in self.inventory:
            return "Đã có món này rồi."
        if self.level < item["level"]:
            return f"Cần cấp {item['level']}."
        if self.quan < item["price"]:
            return f"Còn thiếu {item['price'] - self.quan} quan."
        self.quan -= item["price"]
        if item["slot"] == "dung":
            self.potions += 1
        else:
            self.inventory.append(item_id)
            self.gear[item["slot"]] = item_id  # đồ mới mua mặc luôn
        self.save()
        return None

    def equip(self, item_id: str) -> None:
        item = rpg.ITEMS[item_id]
        if item_id in self.inventory:
            if self.gear.get(item["slot"]) == item_id:
                del self.gear[item["slot"]]
            else:
                self.gear[item["slot"]] = item_id
            self.save()

    def report(self) -> list[dict]:
        """Báo cáo già làng mọi di tích đã xong: mỗi di tích nhận kinh nghiệm, tiềm năng, quan. Trả về các di tích vừa báo."""
        done = [self.index["relics"][r] for r in self.reports if r in self.index["relics"]]
        self.reports = []
        for _relic in done:
            self.gain(rpg.RELIC_EXP, rpg.RELIC_TIEM, rpg.RELIC_QUAN)
        if done:
            self.save()
        return done

    def win_mob(self, mob: dict, rng=None) -> tuple[int, int, int, bool]:
        """Hạ một quái trên map: nhận thưởng, có khi rơi thuốc nam."""
        exp, tiem, quan = rpg.mob_reward(mob, self.level, rng)
        self.mobs_killed += 1
        self.gain(exp, tiem, quan)
        drop = (rng or random).random() < rpg.DROP_POTION
        if drop:
            self.potions += 1
        self.save()
        return exp, tiem, quan, drop

    def boss_ease(self, key: str) -> float:
        return min(3, self.boss_tries.get(key, 0)) * rpg.BOSS_EASE

    # ----- câu cá, nướng cá -----
    def has_rod(self) -> bool:
        """Có cần câu và đang mang theo (mua xong là mang luôn; cất vào túi thì không câu được)."""
        return self.gear.get("cong_cu") == rpg.ROD

    def fish_count(self) -> int:
        return sum(self.fish.values())

    def catch(self, kind: str) -> bool:
        """Bỏ một con cá vào giỏ; giỏ đầy thì thả lại."""
        if kind not in rpg.FISH or self.fish_count() >= rpg.MAX_FISH:
            return False
        self.fish[kind] = self.fish.get(kind, 0) + 1
        self.save()
        return True

    def cook(self) -> int:
        """Nướng cá tươi trong giỏ thành cá nướng, đến khi đủ xâu mang theo. Trả về số con vừa nướng."""
        n = min(self.fish_count(), rpg.MAX_GRILL - self.grilled)
        left = n
        for kind in list(self.fish):
            take = min(left, self.fish[kind])
            self.fish[kind] -= take
            left -= take
            if not self.fish[kind]:
                del self.fish[kind]
        self.grilled += n
        if n:
            self.save()
        return n

    def eat_fish(self) -> bool:
        if self.grilled <= 0:
            return False
        self.grilled -= 1
        return True

    def use_potion(self) -> bool:
        if self.potions <= 0:
            return False
        self.potions -= 1
        return True

    def cd_mult(self) -> float:
        return max(0.4, 1 - 0.04 * self.stat_levels.get("tri", 0) - self._gear("cd"))

    def arena_unlocked(self, bot: dict) -> bool:
        need = bot.get("needs")
        return not need or self.need_progress(need) >= need[1]

    def arena_need_text(self, bot: dict) -> str:
        need = bot["needs"]
        return f"{progression.needs_text(need)} (hiện có {self.need_progress(need)})"

    # ---------- phần thưởng ----------
    def add_notebook(self, ids) -> None:
        self.notebook.update(ids or [])

    def collect_fragment(self, fragment_id: str) -> list:
        fragment = self.index["fragments"][fragment_id]
        effects = self.engine(self.level_of[fragment_id]).on_collect(fragment_id)
        self.add_notebook([fragment_id, fragment.get("event_id")])
        return effects

    def finish_relic(self, relic: dict) -> list[str]:
        """Đóng dấu và trao bảo vật khi xong di tích. Trả về danh sách thông báo."""
        msgs = []
        if relic["id"] not in self.stamps:
            self.stamps.add(relic["id"])
            msgs.append(f"Đóng dấu Hộ chiếu di sản: {relic['title']}")
            if relic["id"] not in self.reports:
                self.reports.append(relic["id"])
            msgs.append("Về báo cáo với già làng để nhận thưởng")
            self.add_notebook([relic["place"]])
        art = relic.get("artifact")
        if art and art not in self.owned_artifacts:
            self.owned_artifacts.add(art)
            msgs.append(f"Bảo vật mới: {self.index['artifacts'][art]['name']}")
        return msgs + self.check_badges()

    def check_badges(self) -> list[str]:
        msgs = []

        def award(key, name):
            if key not in self.badges:
                self.badges.add(key)
                msgs.append(f"Danh hiệu mới: {name}")

        for lid in self.order:
            level = self.levels[lid]["level"]
            if lid in self.progress.completed_levels and level.get("badge"):
                award(f"man:{lid}", level["badge"])
        if len(self.stamps) >= 10:
            award("nha_tham_hiem", GLOBAL_BADGES["nha_tham_hiem"]["name"])
        if len(self.first_try) >= 15:
            award("bach_phat", GLOBAL_BADGES["bach_phat"]["name"])
        if any(v >= 3 for v in self.battle_stars.values()):
            award("tuong_tai", GLOBAL_BADGES["tuong_tai"]["name"])
        return msgs

    def badge_info(self, key: str) -> dict:
        if key.startswith("man:"):
            level = self.levels[key[4:]]["level"]
            return {"name": level["badge"], "desc": f"Hoàn thành {level['title']}"}
        return GLOBAL_BADGES.get(key, {"name": key, "desc": ""})

    def all_badge_keys(self) -> list[str]:
        keys = [f"man:{lid}" for lid in self.order if self.levels[lid]["level"].get("badge")]
        return keys + list(GLOBAL_BADGES)

    def timeline_finished(self, level_id: str, mistakes: int) -> dict:
        first = level_id not in self.progress.timeline_done
        effects = self.engine(level_id).on_timeline_done()
        bonus = timeline_bonus(mistakes) if first else 0
        self.progress.points += bonus
        self.save()
        return {"bonus": bonus, "effects": effects}

    def citation_text(self, cite_ids) -> str:
        """Ghép trích dẫn thành một dòng: 'Tên nguồn — mục'."""
        out = []
        for cid in cite_ids or []:
            c = self.sources["citations"].get(cid)
            if c:
                s = self.sources["sources"].get(c["source"], {})
                out.append(f"{s.get('title', '?')} — {c['locator']}")
        return "; ".join(out)

    @staticmethod
    def effect_messages(effects, bundle: dict) -> list[str]:
        titles = {q["id"]: q["title"] for q in bundle.get("quests", [])}
        places = {p["id"]: p["name"] for p in bundle.get("places", [])}
        events = {e["id"]: e["title"] for e in bundle.get("events", [])}
        msgs = []
        for e in effects:
            if isinstance(e, QuestDone):
                msgs.append(f"Hoàn thành di tích: {titles.get(e.quest_id, '')}")
            elif isinstance(e, Unlock) and e.kind == "place":
                msgs.append(f"Mở khoá địa danh: {places.get(e.id, '')}")
            elif isinstance(e, Unlock) and e.kind == "event":
                msgs.append(f"Phục dựng sự kiện: {events.get(e.id, '')}")
            elif isinstance(e, LevelDone):
                msgs.append("Hoàn thành màn chơi!")
            elif isinstance(e, ObjectiveDone):
                continue
        return msgs
