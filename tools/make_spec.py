"""Sinh docs/YEU_CAU_CHI_TIET.md: bản yêu cầu chi tiết đến từng vật thể, bảng số liệu lấy thẳng từ code nên luôn khớp game.

Chạy: .venv/Scripts/python tools/make_spec.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "game"))
from core import progression, rpg, weapons  # noqa: E402

CONTENT = ROOT / "game" / "content"
OUT = ROOT / "docs" / "YEU_CAU_CHI_TIET.md"

# Ngoại hình từng loại quái (khớp với tools/make_soldiers.py và core/mobart.py)
LOOK = {
    "LinhTong": "mũ sắt sẫm có che gáy, giáp vảy xám, đai đỏ",
    "TuongTong": "mũ sắt có tua đỏ, viền vàng, giáp vảy, quần đỏ",
    "LinhNguyen": "mũ sắt tròn viền lông, tai che bằng lông, áo choàng cài vạt chéo, đai da",
    "TuongNguyen": "mũ viền lông có chùm lông đỏ, áo choàng đỏ viền vàng",
    "LinhMinh": "mũ sắt hình bát có chóp nhọn và tua đỏ, áo bông đỏ",
    "TuongMinh": "mũ bát viền vàng có tua đỏ, áo đỏ sẫm viền vàng",
    "KyBinhMongCo": "lính Mông Cổ cưỡi ngựa đen",
    "TuongKyMongCo": "tướng Mông Cổ cưỡi ngựa đen",
    "KyBinhMinh": "lính Minh cưỡi ngựa nâu",
    "TuongKyMinh": "tướng Minh cưỡi ngựa nâu",
    "ThuyenLuongNguyen": "thuyền thân sẫm buồm nâu đỏ như thuyền chiến Nguyên, trên boong chất bao lương (chỉ vẽ con thuyền)",
    "UPhao": "khẩu pháo dã chiến màu ô liu: càng pháo, bánh xe, tấm chắn, nòng dài, hai lớp bao cát phía trước (không có người)",
    "LoCot": "khối bê tông có lỗ châu mai, bao cát quanh nóc (công trình, không có người)",
    "USung": "vòng bao cát, nòng súng nhô lên (công sự, không có người)",
    "XeTang": "xe tăng hạng nhẹ màu ô liu, tháp pháo, nòng dài, xích hai bên (cỗ máy, không vẽ người)",
}
MOVE = {"swing": "chém vòng cung", "thrust": "đâm thẳng, với xa hơn", "cleave": "bổ rộng, rung màn hình",
        "shoot": "bắn đạn bay thật", "none": "đánh tay không"}
FX = {
    "gay": "quất mạnh, đẩy lùi xa, vụn gỗ văng, vệt vàng nhạt", "dao": "vệt chém cong trắng, tia lửa",
    "kiem": "vệt chém kép xanh nhạt, tia lửa", "bao_kiem": "vệt vàng, tia sáng vàng toé ra",
    "giao": "mũi giáo lao tới, vết cắt", "dai_dao": "vòng chém lớn, đất đá văng, rung màn hình",
    "cung": "mũi tên bay, cắm vào thì toé tia nhỏ", "no": "tên nỏ ngắn mập, bay nhanh, nặng hơn tên cung",
    "phao": "đạn pháo bay chậm, trúng mạnh", "sung": "đạn nhỏ bắn liên tục",
}
LOOK_ITEM = {
    "ao_vai": "áo nâu vải thô", "giap_da": "áo da nâu, vạt chéo viền sáng", "giap_bong": "áo đỏ chần chỉ ngang, đai vàng",
    "giap_vay": "giáp xám có vảy sáng xen kẽ, đai đỏ", "giap_dong": "giáp màu đồng có vảy vàng, quần đỏ",
    "khan_chit": "khăn đen quấn đầu, đuôi khăn sau gáy", "non_la": "nón lá chóp có vòng nan, rộng hơn đầu",
    "mu_da": "mũ da nâu có viền", "mu_sat": "mũ sắt có vành vàng và chùm lông đỏ",
    "dep_rom": "bàn chân màu rơm", "giay_vai": "bàn chân màu vải sẫm", "ung_da": "ủng da nâu cao hai hàng điểm ảnh",
    "bao_tay_vai": "bàn tay quấn vải trắng ngà", "gang_da": "bàn tay màu da nâu", "gang_sat": "bàn tay màu thép",
}


def _quan(q) -> str:
    return f"{q[0]}–{q[1]}" if isinstance(q, (tuple, list)) else str(q)


def items_table() -> str:
    rows = ["| Ô | Món | Cấp | Giá (quan) | Chỉ số | Hiện trên người / cách đánh | Ghi chú |", "|---|---|---|---|---|---|---|"]
    for iid, it in rpg.ITEMS.items():
        slot = rpg.SLOT_NAMES[it["slot"]]
        if it["slot"] == "vu_khi":
            k = weapons.kind(iid)
            look = f"{MOVE[weapons.STYLE[k]['move']]}; {FX[k]}"
        else:
            look = LOOK_ITEM.get(iid, "")
        rows.append(f"| {slot} | {it['name']} | {it['level']} | {it['price']} | {rpg.item_text(it)} | {look} | {it['desc']} |")
    return "\n".join(rows)


def mobs_table(sources) -> str:
    rows = ["| Quái | Ngoại hình | Vũ khí | Cấp | Máu | Sức đánh | Tốc độ | Lối đánh | Chiêu | Thưởng (KN / tiềm năng / quan) | Dòng “Sử ghi” khi hạ lần đầu |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for mid, m in rpg.MOBS.items():
        w = rpg.ITEMS.get(m.get("weapon"), {}).get("name") or {"phao": "pháo", "sung": "súng"}.get(m.get("weapon"), "—")
        skills = ", ".join(progression.skill_info(s)["name"] for s in m.get("skills", ())) or "—"
        fact, cite = rpg.MOB_FACTS.get(mid, ("", ""))
        src = sources["citations"].get(cite, {})
        rows.append(f"| {m['name']} | {LOOK.get(m['char'], m['char'])} | {w} | {m['level']} | {m['hp']} | {m['power']} | {m['speed']} | "
                    f"{m.get('style', 'melee')} | {skills} | {m['exp']} / {m['tiem']} / {_quan(m['quan'])} | {fact} ({src.get('locator', cite)}) |")
    return "\n".join(rows)


def bosses_table() -> str:
    rows = ["| Ở đâu | Tên | Ngoại hình | Cấp | Máu | Chiêu | Thưởng |", "|---|---|---|---|---|---|---|"]
    for lid, b in rpg.BOSSES.items():
        skills = ", ".join(progression.skill_info(s)["name"] for s in b["skills"])
        rows.append(f"| Mật thư cuối {lid} | {b['name']} | {LOOK.get(b['char'], b['char'])} | {b['level']} | {b['hp']} | {skills} | "
                    f"{b['exp']} KN, {b['tiem']} tiềm năng, {b['quan']} quan |")
    for fid, b in rpg.ELITES.items():
        skills = ", ".join(progression.skill_info(s)["name"] for s in b["skills"])
        rows.append(f"| Vùng luyện {fid} | {b['name']} | {LOOK.get(b['char'], b['char'])} | {b['level']} | {b['hp']} | {skills} | "
                    f"{b['exp']} KN, {b['tiem']} tiềm năng, {b['quan']} quan, 1 thuốc nam; hồi sinh sau {int(rpg.ELITE_RESPAWN)} giây |")
    return "\n".join(rows)


def zones_table(levels) -> str:
    rows = ["| Chặng | Di tích | Bóng giặc quanh di tích | Kẻ canh mật thư cuối |", "|---|---|---|---|"]
    for lid, data in levels.items():
        mandatory = [r for r in data["relics"] if not r.get("optional")]
        final = mandatory[-1]["id"] if mandatory else None
        for r in data["relics"]:
            mobs = ", ".join(rpg.MOBS[m]["name"] for m in rpg.ZONE_MOBS.get(r["id"], ()))
            first = rpg.ZONE_MOBS.get(r["id"], ("",))[0]
            guard = rpg.BOSSES[lid]["name"] + " (trùm cả chặng)" if r["id"] == final else rpg.MOBS[first]["chief"]
            has_scroll = any("fragment" in s for s in r["steps"])
            rows.append(f"| {data['level']['title']} | {r['title']} | {mobs} | {guard if has_scroll else '—'} |")
    return "\n".join(rows)


def fields_text(fields, sources) -> str:
    out = []
    for f in fields.values():
        out.append(f"### {f['title']}\n")
        out.append(f"- Thuộc chặng `{f['parent']}`, mở khi xong di tích `{f['requires']}`; vào bằng biển chỉ đường “{f['gate_name']}”.")
        out.append(f"- {f['sub']}. Thời tiết `{f.get('weather')}`, nhạc `{f.get('music')}`.")
        for zid, kinds in f["camps"].items():
            z = f["zones"][zid]
            names = ", ".join(rpg.MOBS[k]["name"] for k in kinds)
            elite = f" + kẻ mạnh nhất vùng: {rpg.ELITES[f['id']]['name']}" if zid == f.get("elite_zone") else ""
            out.append(f"- Trại `{zid}` (kiểu `{z['theme']}`, ô {z['at']}): {names}{elite}.")
        e = f["elder"]
        out.append(f"- Người kể chuyện (hư cấu): {e['name']}. Lời kể:")
        for ln in e["lines"]:
            cites = "; ".join(sources["citations"][c]["locator"] for c in ln.get("cite", []))
            out.append(f"  - “{ln['text']}”" + (f" — nguồn: {cites}" if cites else " — lời dặn của nhân vật hư cấu"))
        q = e["question"]
        right = next(o["text"] for o in q["options"] if o["id"] == q["correct_answer"])
        out.append(f"- Câu hỏi: {q['prompt']} Đáp án: {right}. Trả lời đúng lần đầu thưởng {rpg.FIELD_TALK_REWARD}.")
        for npc in f.get("npcs", []):
            out.append(f"- Lính NPC ({npc['char']}): " + " / ".join(npc["lines"]))
        out.append("")
    return "\n".join(out)


def main() -> None:
    sources = json.loads((CONTENT / "sources.json").read_text(encoding="utf-8"))
    fields = json.loads((CONTENT / "fields.json").read_text(encoding="utf-8"))
    levels = {lid: json.loads((CONTENT / f"{lid}.json").read_text(encoding="utf-8")) for lid in ("man1", "man2", "man3")}
    realms = "\n".join(f"| {r['name']} | {r['cap']} | {r['need']} | x{r['mult']:.2f} |" for r in rpg.REALMS)
    skills = "\n".join(f"| {s['name']} | {s['desc']} | {progression.needs_text(s['needs'])} | {s['cd']} giây |" for s in progression.SKILLS.values())
    text = f"""# Yêu cầu chi tiết: “Sử Ký Điều Tra”, game nhập vai học lịch sử Việt Nam

Bản này mở rộng yêu cầu gốc của nhóm thành mô tả đến từng vật thể trong game. Bảng số liệu được sinh tự động từ code
(`tools/make_spec.py`), nên đúng với bản đang chạy. Phần nào là hư cấu của trò chơi đều ghi rõ.

## 1. Mục tiêu và nguyên tắc

- Mục tiêu: người chơi thấy vui khi học sử. Mọi thứ làm nhân vật mạnh lên đều phải đi qua việc học sử: cày quái chỉ lên
  được tới giới hạn cảnh giới, muốn đột phá phải có tinh hoa, mà tinh hoa chỉ có khi chìm vào hồi ức, khám phá, ghép tư liệu,
  điều tra; điểm kỹ năng chỉ có khi trả lời đúng, đóng dấu di tích.
- Đúng sử: mỗi câu kể, câu hỏi, dòng “Sử ghi” phải gắn mã trích dẫn trong `game/content/sources.json`. Chỗ còn tranh luận ghi
  “Ghi chú sử học”; truyền thuyết ghi rõ là truyền thuyết. Không bịa chi tiết cho đẹp.
- Hư cấu có đánh dấu: người kể chuyện, già làng, thợ rèn, võ sinh, bóng giặc, cảnh giới, tiềm năng, tiền quan là phần trò chơi.
- Không máu me; thời 1945 – 1954 không có quái là người (chỉ đồn bốt, lô cốt, ụ súng, xe tăng), không vẽ chân dung lãnh tụ hiện đại.
- Tên trùm, kẻ cầm đầu là tên theo chức (“Bách hộ quân Nguyên”, “Tướng tiên phong Mông Cổ”), không gán cho người có thật.
- Lối chơi lấy cảm hứng từ thể loại game nhập vai cày cấp; không chép tên, nhân vật, hình ảnh của game nào.

## 2. Vòng chơi

1. Già làng Cụ Đồ Sử giao việc: di tích tiếp theo và câu hỏi lớn ở đó.
2. Tới di tích, nghe người giữ ký ức kể, chìm vào hồi ức (trận đánh, hội nghị diễn lại), trả lời câu hỏi, nhặt mật thư, vào trận.
3. Quanh di tích có bóng giặc đúng thời: bấm F đánh ngay trên map để lấy kinh nghiệm, tiềm năng, quan, thuốc nam.
4. Mật thư cuối của di tích có kẻ cầm đầu canh; mật thư cuối của chặng có trùm. Thua thì bị đưa về chỗ già làng, trùm yếu dần
   mỗi lần thua (tối đa 45%) để không ai bị kẹt.
5. Xong di tích: đóng dấu, về báo cáo già làng nhận thưởng và việc tiếp theo.
6. Học xong di tích nhất định thì mở đường sang vùng luyện của thời đó.
7. Dùng tiềm năng tăng chỉ số (K), quan mua đồ ở lò rèn, điểm kỹ năng học chiêu, tinh hoa đột phá cảnh giới.
8. Đủ di tích thì dựng dòng thời gian, qua cổng sang chặng sau.
9. Qua cổng cuối Màn 3 là đoạn kết (`scenes/ending.py`), bảy cảnh tự chạy, có nguồn: các mốc giữ nước 938–1954; lá cờ
   “Quyết chiến Quyết thắng” trên nóc hầm chỉ huy địch ở Điện Biên Phủ chiều 7/5/1954; Hiệp định Giơnevơ tháng 7/1954 (vĩ
   tuyến 17 tạm thời, hẹn tổng tuyển cử 7/1956); Đại đoàn 308 vào tiếp quản Hà Nội giữa phố treo cờ đỏ sao vàng ngày
   10/10/1954; lễ chào cờ 15 giờ ở sân Cột Cờ; trang nói rõ đến 30/4/1975 đất nước mới thống nhất; tổng kết hành trình của
   người chơi. Sau đó là lời dặn của Cụ Đồ Sử. Phím cách sang cảnh sau, mũi tên trái lùi lại, Esc bỏ qua. Đi hết game thì màn
   hình tựa đề có nút "Xem lại đoạn kết".

## 3. Nhân vật

### Cảnh giới

| Cảnh giới | Cấp tối đa | Tinh hoa cần | Nhân chỉ số |
|---|---|---|---|
{realms}

Tinh hoa: mỗi hồi ức chìm vào lần đầu +{rpg.ESSENCE['memory']}, mỗi khám phá +{rpg.ESSENCE['discovery']}, mỗi tư liệu ghép xong
+{rpg.ESSENCE['document']}, mỗi vụ điều tra +{rpg.ESSENCE['case']}. Lời dẫn đầu và lời kết không tính.

### Chỉ số (mua bằng tiềm năng, bậc n tốn {rpg.STAT_COST} x n, tối đa {progression.STAT_MAX} bậc)

Sức đánh +8% sát thương mỗi bậc; Thể lực +12 máu; Nhanh nhẹn +4% tốc độ; Trí tuệ −4% thời gian hồi chiêu. Mỗi cấp thêm
{rpg.LEVEL_HP} máu và {int(rpg.LEVEL_DMG * 100)}% sát thương.

### Kỹ năng (học bằng điểm kỹ năng)

| Kỹ năng | Tác dụng | Điều kiện mở | Hồi chiêu |
|---|---|---|---|
{skills}

## 4. Trang bị: món nào cũng hiện lên người, vũ khí nào cũng có cách đánh và hiệu ứng riêng

Ngoại hình người chơi vẽ lại theo bộ đồ (`game/core/outfit.py`): áo đổi màu và hoa văn, mũ đổi phần đầu (không đội gì thì
là tóc búi), giày đổi bàn chân, găng đổi bàn tay. Vũ khí cầm trên tay khi đi; khi đánh thì vung, đâm, bổ hoặc bắn theo loại,
có vệt chém và hiệu ứng trúng đòn (`game/core/weapons.py`). Quái và võ sinh cũng cầm vũ khí đúng loại.

{items_table()}

## 5. Quái

{mobs_table(sources)}

### Bóng giặc quanh từng di tích

{zones_table(levels)}

### Trùm và kẻ mạnh nhất vùng

{bosses_table()}

## 6. Vùng luyện

Map phụ, mỗi vùng gắn với một sự kiện có thật. Quái hồi sinh sau {int(rpg.RESPAWN)} giây, kẻ mạnh nhất vùng sau
{int(rpg.ELITE_RESPAWN)} giây. Cổng ở mép tây đưa về map chính, đứng đúng chỗ biển chỉ đường.

{fields_text(fields, sources)}
## 7. Nhân vật phụ

- Cụ Đồ Sử (già làng, hư cấu): giao việc, nghe báo cáo, trao thưởng, dựng dòng thời gian.
- Thợ rèn (hư cấu): đứng gần chỗ xuất phát mỗi chặng, bán đồ.
- Người giữ ký ức ở từng di tích (hư cấu): kể chuyện có nguồn, hỏi câu hỏi.
- Võ sinh thách đấu (hư cấu): thỉnh thoảng đi tới hỏi đấu; Y nhận lời, N từ chối, đi xa là coi như bỏ chạy. Mạnh lên theo cấp người chơi.

## 8. Sổ bóng giặc

Mỗi loại quái một trang (phím G). Hạ được lần đầu thì mở dòng “Sử ghi” về đội quân đó kèm nguồn (bảng ở mục 5); chưa hạ thì
chỉ thấy bóng đen và gợi ý nơi gặp. Biến việc đánh quái thành việc sưu tầm kiến thức.

## 9. Chơi nhiều người

- Thế giới chung: người chơi đã đăng nhập thấy nhau trên cùng map, mặc đúng bộ đồ, cầm đúng vũ khí, có tên và cấp.
- Tổ đội tối đa 4 người (lưu trong bảng `parties`, `party_members`): đồng đội đứng gần nhau khi một người hạ quái thì
  người kia được chia một nửa kinh nghiệm và tiềm năng.
- Đồng minh (bảng `alliances`): luôn thấy bạn mình đang chơi hay vắng, đang ở chặng nào.
- Bấm vào một người chơi khác trên map: hiện bảng trạng thái của họ (hình nhân vật mặc đúng đồ, cấp, cảnh giới, lực chiến,
  đồ đang dùng) cùng các nút Mời vào tổ đội, Kết đồng minh, Thách đấu. Lời mời tới hiện thành thẻ ở góc trên phải màn chơi
  của người được mời, có nút Đồng ý, Từ chối và đếm lùi 60 giây.
- Thách đấu thật: hai người cùng map, người được mời bấm Đồng ý thì cả hai cùng được đưa tới võ đài, mỗi người tự điều
  khiển nhân vật của mình (không có bot). Mỗi máy gửi trạng thái khoảng 15 lần mỗi giây qua WebSocket; đòn trúng do máy người
  ra đòn báo sang, máy bị đánh tự trừ máu nên né và thế thủ vẫn có tác dụng. Máy chủ phân xử khi có người gục, rút lui, rời
  game hoặc hết 90 giây (ai còn nhiều máu hơn thì thắng), lưu kết quả của cả hai vào bảng `duel_records`. Thách đấu không
  dùng thuốc nam hay cá nướng.
- Lời nói nhanh: 12 câu có sẵn (“Cùng ôn bài nhé!”...) ở bảng Bạn chơi.
- Chat gõ tự do (phím L, ô gõ nằm ở trang chơi nên dùng được bộ gõ tiếng Việt): kênh cùng map miễn phí, lời chat hiện trên
  đầu người nói và trong khung ở góc dưới trái; kênh thế giới tới mọi người đang online, hiện ở góc trên phải, mỗi tin tốn
  {rpg.WORLD_CHAT_COST} quan (game trừ trong bản lưu trước khi gửi). Máy chủ làm sạch câu chữ, tối đa 120 ký tự, tự che từ
  tục, chặn gửi dồn (cùng map 1 giây một tin, thế giới {rpg.WORLD_CHAT_GAP:g} giây một tin), gửi 20 tin thế giới gần nhất
  cho người mới vào.
- Đang đánh quái trên map: màn trận che map nhưng vẫn gửi vị trí kèm "đang đánh ai, ở đâu", người cùng map thấy mình vung
  vũ khí vào con quái đó và dòng "đang đánh …". Thách đấu cũng vậy.
- Người chơi máy (`backend/app/world/bots.py`): máy chủ tự cho chạy suốt, kể cả khi không ai online; không gắn với tài
  khoản nào. Quản trị viên thêm, xoá ở trang quản trị, mục "Người chơi máy" (chọn map, việc hay làm: cày quái, làm nhiệm vụ
  hay cả hai, số bot, cấp đầu, tên); tối đa 60 bot, lưu ở bảng `bot_players` nên khởi động lại không mất. Bot hiện trong
  danh sách người cùng map như người chơi khác (tên, cấp, đồ, "đang đánh …"), nói câu có sẵn, hạ 3 quái thì lên một cấp, mời
  tổ đội hay thách đấu thì báo "đang bận". Máy chủ đọc bản đồ đi được ở `backend/app/world/botmaps.json`, xuất bằng
  `tools/export_botmaps.py` (đổi map thì chạy lại; có test báo khi file cũ). Bot không đụng quái gần người chơi thật,
  không đụng kẻ canh, kẻ mạnh nhất vùng, trùm, thuyền.
- Ai hạ quái (người hay bot) thì người cùng map cũng thấy con đó ngã (tin `mob_kill`, `mob_down`), rồi mọc lại sau 30 giây.
- Bảng vàng ở map đầu, gần chỗ xuất phát: 20 người nhiều điểm học sử nhất và 20 người sức mạnh cao nhất toàn máy chủ
  (`GET /api/v1/game/honor`, chỉ có tên hiển thị). Trang chơi lấy mỗi phút rồi để vào localStorage cho game đọc.
- Kỹ thuật: trang chơi giữ WebSocket `/api/v1/world/ws`, game trong khung đọc ghi qua `window.parent.SKNet`; máy chủ chỉ giữ
  vị trí trong bộ nhớ, chặn giá trị lạ, giới hạn tần suất gửi. Không có máy chủ thì game vẫn chơi một mình.

## 10. Điều khiển

WASD hoặc bấm chuột: đi · E: nói chuyện · F: đánh quái · H: gọi chiến mã (từ cấp {rpg.HORSE_LEVEL}) · R: cưỡi ngựa có sẵn ·
B: túi đồ · G: sổ bóng giặc · P: bạn chơi · L: chat · K: tu luyện · T: tư liệu · J: lộ trình · M: bản đồ · N: sổ tay. Các bảng
cũng mở được từ nút ba gạch ở góc trên phải (bấm vào mới xổ danh sách, có ghi phím tắt). Trong trận: chuột trái chém (giữ
chuột để chém liên tục, phím cách cũng chém được), Shift né, giữ chuột phải để đi theo con trỏ, 1–4 kỹ năng, Q uống thuốc,
E ăn cá nướng.

## 11. Asset

- Gói Ninja Adventure của Pixel-Boy và AAA, giấy phép CC0 (https://pixel-boy.itch.io/ninja-adventure-asset-pack), bản đầy đủ tải
  ngày 12/11/2026: nhân vật, thú, hiệu ứng, âm thanh, nhạc; thêm vũ khí cầm tay (gậy, đao, giáo, kiếm, đại đao, cung), ngựa đen,
  hiệu ứng chém kép, đạn pháo.
- Tự vẽ bằng code: lính Tống, Nguyên, Minh, Đại Việt, nghĩa quân, bộ đội (`tools/make_soldiers.py`); ngoại hình người chơi theo đồ
  (`core/outfit.py`); nỏ, kỵ binh, xe tăng, ụ súng (`core/mobart.py`, `core/weapons.py`); icon đồ và kỹ năng (`tools/make_icons.py`);
  nhà cửa, cung điện, thành luỹ (`core/buildings.py`); chiến mã (`core/chienma.py`).

## 12. Tiêu chí hoàn thành

- Mọi bảng trên khớp code (sinh lại bằng `tools/make_spec.py`).
- Bộ kiểm thử tự động chơi hết game, kiểm tra: quái đứng ở ô đi được, mỗi chặng đúng một trùm, thời 1945 – 1954 không có quái
  là người, mỗi loại quái có dòng sử có nguồn, vũ khí có ảnh và cách đánh, đồ đổi ngoại hình, vùng luyện mở đúng lúc và quay về đúng chỗ.
- Nhóm đối chiếu từng câu kể, câu hỏi, dòng “Sử ghi” với sách gốc trước khi nộp; nhật ký rà soát ở `docs/RA_SOAT_SU_LIEU.md`.

## 13. Mở rộng tiếp

- Thêm vùng luyện: Chương Dương – Hàm Tử (1285), Chi Lăng (1427), Đường số 4 (1950), mỗi vùng cần tìm nguồn trước khi viết.
- Thêm loại quái: thuyền chiến Nguyên trên sông (đánh khi chèo thuyền), voi chiến (nếu tìm được nguồn đúng thời và đúng phe).
"""
    OUT.write_text(text, encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
