"""Kiểm tra toàn bộ nội dung game: id trùng, tham chiếu hỏng, đáp án sai định dạng, thiếu nguồn, sai thứ tự mốc.

Chạy: .venv/Scripts/python tools/check_content.py
Trả về mã lỗi 1 nếu có lỗi, nên dùng được trong CI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.histdate import HistDate  # noqa: E402

CONTENT = ROOT / "game" / "content"
LEVELS = ("man1.json", "man2.json", "man3.json")
ICONS = {"coc", "hich", "sach", "guom", "co", "co_sao", "an", "phao", "thuyen", "qua_cam", "no"}
PORTRAITS = {"cu_do", "cu_tu", "ba_cu", "lai_do", "cuu_binh", "tuong", "vua", "quan_van", "nghia_si", "bo_lao", "nu_si", "chien_si", "giac", "giac_tong", "giac_nguyen", "giac_minh", "tu_lieu"}  # khớp game/core/sprites.py PORTRAITS
SCENES = {"lang_co", "bach_dang", "thanh_co", "nhu_nguyet", "den_tran", "dien_hong", "van_don", "lam_son", "chi_lang", "ho_guom", "ba_dinh", "tan_trao", "dien_bien", "geneve", "vo_dai", "trai_quan", "huong_dan"}
FX = {"fire", "smoke", "arrows", "clash", "blast", "drum", "rain"}
KINDS = ("places", "relics", "persons", "events", "fragments", "dialogues", "questions", "battles", "artifacts")
MAX_NODE_CHARS = 330


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # console Windows mặc định không in được tiếng Việt
    errors: list[str] = []
    sources = json.loads((CONTENT / "sources.json").read_text(encoding="utf-8"))
    cites = sources["citations"]
    for cid, c in cites.items():
        if c["source"] not in sources["sources"]:
            errors.append(f"citation {cid}: nguồn lạ {c['source']}")
    bundles = [json.loads((CONTENT / n).read_text(encoding="utf-8")) for n in LEVELS]

    index: dict[str, dict] = {k: {} for k in KINDS}
    seen: dict[str, str] = {}
    for b in bundles:
        for kind in KINDS:
            for item in b.get(kind, []):
                iid = item["id"]
                if iid in seen:
                    errors.append(f"id trùng: {iid} ({seen[iid]} và {kind})")
                seen[iid] = kind
                index[kind][iid] = item

    def need(cond, msg):
        if not cond:
            errors.append(msg)

    def check_cites(owner, ids):
        for c in ids or []:
            need(c in cites, f"{owner}: citation lạ {c}")

    def check_node(owner, node):
        text = node.get("text", "")
        need(len(text) <= MAX_NODE_CHARS, f"{owner}: đoạn dài {len(text)} ký tự: {text[:40]}...")
        if node.get("portrait"):
            need(node["portrait"] in PORTRAITS, f"{owner}: chân dung lạ {node['portrait']}")
        if node.get("bg"):
            need(node["bg"] in SCENES, f"{owner}: cảnh lạ {node['bg']}")
        for f in node.get("fx", []) or []:
            need(f in FX, f"{owner}: hiệu ứng lạ {f}")
        check_cites(owner, node.get("cite"))
        if node.get("cine"):
            need(node["cine"] in ("lure", "ebb", "crash", "after", "sword", "turtle"), f"{owner}: nhịp diễn lại lạ {node['cine']}")
            need(node.get("memory"), f"{owner}: cảnh diễn lại phải nằm trong đoạn hồi ức")
        for tp in node.get("topics", []) or []:
            check_topic(owner, tp)

    def check_topic(owner, tp):
        if tp.get("needs"):
            need(tp["needs"] in index["fragments"], f"{owner}: chủ đề {tp['id']} cần mảnh ghép lạ {tp['needs']}")
        if tp.get("replay"):
            need(tp["replay"] in index["dialogues"], f"{owner}: kể lại đoạn lạ {tp['replay']}")
        for ln in tp.get("lines", []):
            check_node(f"{owner}/{tp['id']}", ln)

    for node in sources["intro"]["nodes"]:
        check_node("intro", node)

    used = {"dialogues": set(), "questions": set(), "fragments": set(), "battles": set()}
    for b in bundles:
        lid = b["level"]["id"]
        place_ids = {p["id"] for p in b["places"]}
        relic_ids = {r["id"] for r in b["relics"]}
        need(b["level"].get("cover") in SCENES, f"{lid}: ảnh bìa lạ")
        for r in b["relics"]:
            rid = r["id"]
            need(r["place"] in place_ids, f"{rid}: địa danh lạ {r['place']}")
            need(r.get("scene") in SCENES, f"{rid}: cảnh lạ {r.get('scene')}")
            need(r.get("keeper") in PORTRAITS, f"{rid}: người giữ ký ức lạ")
            need(not r.get("artifact") or r["artifact"] in index["artifacts"], f"{rid}: bảo vật lạ {r.get('artifact')}")
            for q in r.get("requires", []):
                need(q in relic_ids, f"{rid}: requires lạ {q}")
            kinds = set()
            for step in r["steps"]:
                (k, target), = step.items()
                mapping = {"story": "dialogues", "question": "questions", "fragment": "fragments", "battle": "battles"}
                need(k in mapping, f"{rid}: bước lạ {k}")
                need(target in index[mapping[k]], f"{rid}: {k} lạ {target}")
                used[mapping[k]].add(target)
                kinds.add(k)
            need("question" in kinds, f"{rid}: di tích không có câu hỏi")
            need("story" in kinds, f"{rid}: di tích không có câu chuyện")
            for tp in r.get("extra_talk", []) or []:
                check_topic(rid, tp)
        for e in b["events"]:
            check_cites(e["id"], e.get("citations"))
            need(e.get("citations"), f"{e['id']}: sự kiện thiếu nguồn")
            HistDate.from_bundle(e["date"])
            need(e["date"].get("label"), f"{e['id']}: thiếu nhãn ngày")
            for f in e.get("fragment_ids", []) or []:
                need(f in index["fragments"], f"{e['id']}: mảnh ghép lạ {f}")
                if f in index["fragments"]:
                    need(index["fragments"][f].get("event_id") == e["id"], f"{f}: event_id không khớp {e['id']}")
        events = {e["id"] for e in b["events"]}
        dates = {e["id"]: HistDate.from_bundle(e["date"]) for e in b["events"]}
        for link in b.get("causal_links", []):
            need(link["from_event_id"] in events and link["to_event_id"] in events, f"{lid}: quan hệ nhân quả có id lạ {link}")
            if link["from_event_id"] in dates and link["to_event_id"] in dates:
                need(not dates[link["to_event_id"]].definitely_before(dates[link["from_event_id"]]), f"{lid}: nhân quả ngược thời gian {link}")
        for f in b["fragments"]:
            need(f.get("citations"), f"{f['id']}: mảnh ghép thiếu nguồn")
            check_cites(f["id"], f.get("citations"))
            need(f.get("icon") in ICONS, f"{f['id']}: biểu tượng lạ {f.get('icon')}")
            need(f.get("event_id") in events, f"{f['id']}: sự kiện lạ {f.get('event_id')}")
        for a in b["artifacts"]:
            need(a["icon"] in ICONS, f"{a['id']}: biểu tượng lạ {a['icon']}")
        for p in b["persons"]:
            need(p["portrait"] in PORTRAITS, f"{p['id']}: chân dung lạ")
        for d in b["dialogues"]:
            need(d.get("bg") in SCENES, f"{d['id']}: cảnh lạ")
            for u in d.get("unlocks", []) or []:
                need(u in seen, f"{d['id']}: unlock lạ {u}")
            for node in d["nodes"]:
                check_node(d["id"], node)
                for u in node.get("unlock", []) or []:
                    need(u in seen, f"{d['id']}: unlock lạ {u}")
        for bt in b["battles"]:
            need(bt["kind"] in ("tide", "ambush", "siege"), f"{bt['id']}: loại trận lạ")
            need(bt.get("citations"), f"{bt['id']}: trận đánh thiếu nguồn")
            check_cites(bt["id"], bt.get("citations"))
        for q in b["questions"]:
            check_question(q, need, check_cites)

    for kind, ids in used.items():
        for iid in index[kind]:
            need(iid in ids, f"{kind} {iid}: không được dùng ở di tích nào")

    n = {k: len(v) for k, v in index.items()}
    forms = {}
    for q in index["questions"].values():
        key = q.get("style") or q["kind"]
        forms[key] = forms.get(key, 0) + 1
    print("Nội dung:", n)
    print("Dạng câu hỏi:", forms)
    if errors:
        print(f"\n{len(errors)} LỖI:")
        for e in errors:
            print(" -", e)
        return 1
    print("Không có lỗi.")
    return 0


def check_question(q, need, check_cites):
    qid, kind, ans = q["id"], q["kind"], q["correct_answer"]
    check_cites(qid, q.get("citations"))
    need(q.get("citations"), f"{qid}: câu hỏi thiếu nguồn")
    need(q.get("explanation"), f"{qid}: câu hỏi thiếu giải thích")
    need(q.get("difficulty") in (1, 2, 3), f"{qid}: độ khó lạ")
    if kind in ("single", "multi"):
        ids = [o["id"] for o in q["options"]]
        need(len(ids) == len(set(ids)), f"{qid}: lựa chọn trùng id")
        wanted = ans if kind == "multi" else [ans]
        need(all(a in ids for a in wanted), f"{qid}: đáp án không có trong lựa chọn")
        if kind == "multi":
            need(1 < len(wanted) < len(ids), f"{qid}: câu chọn nhiều nên có nhiều đáp án và có nhiễu")
    elif kind == "order":
        need(sorted(ans) == sorted(i["id"] for i in q["items"]), f"{qid}: đáp án sắp xếp không khớp danh sách")
    elif kind == "match":
        lefts = {i["id"] for i in q["left"]}
        rights = {i["id"] for i in q["right"]}
        need(set(ans) == lefts, f"{qid}: vế trái của đáp án không khớp")
        need(set(ans.values()) == rights, f"{qid}: vế phải của đáp án không khớp")
    elif kind == "map_pick":
        need("lat" in ans and "lon" in ans and q.get("tolerance_km"), f"{qid}: câu bản đồ thiếu toạ độ/sai số")
    else:
        need(False, f"{qid}: loại câu hỏi lạ {kind}")


if __name__ == "__main__":
    sys.exit(main())
