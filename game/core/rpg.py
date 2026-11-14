"""Lối chơi nhập vai: cấp, kinh nghiệm, tiềm năng, tiền quan, tinh hoa, cảnh giới, đồ trang bị, quái và trùm theo màn.

Vòng chơi: đánh quái để lên cấp, nhận tiềm năng để tăng chỉ số và tiền quan để mua đồ; còn kỹ năng chỉ học được bằng
điểm kỹ năng kiếm từ việc học sử. Cấp bị chặn theo cảnh giới, muốn đột phá phải đủ tinh hoa, mà tinh hoa chỉ có khi
chìm vào hồi ức, ghép tư liệu, khám phá, điều tra. Vậy cày quái mãi cũng không mạnh lên được nếu không học sử.

Quái là "bóng giặc" trong ký ức: quân xâm lược đúng thời của từng vùng. Màn 1945 – 1954 không có quái là người mà là
đồn bốt, lô cốt để phá, giữ đúng nguyên tắc không vẽ người ngã xuống ở giai đoạn này.

Tên đồ là đồ dùng chung của người xưa (đao, giáo, nỏ, nón lá...), không gán cho hiện vật có thật nào.
"""

from __future__ import annotations

import random

REALMS = (
    {"id": "tan_binh", "name": "Tân binh", "cap": 10, "need": 0, "mult": 1.00},
    {"id": "su_sinh", "name": "Sử sinh", "cap": 20, "need": 8, "mult": 1.12},
    {"id": "su_quan", "name": "Sử quan", "cap": 30, "need": 20, "mult": 1.25},
    {"id": "dai_su_quan", "name": "Đại sử quan", "cap": 40, "need": 36, "mult": 1.40},
)
LEVEL_HP = 8  # máu thêm mỗi cấp
LEVEL_DMG = 0.03  # sát thương thêm mỗi cấp
STAT_COST = 15  # tiềm năng cho mỗi bậc chỉ số: bậc n tốn 15 x n
# Tinh hoa: hồi ức 1, khám phá 1, tư liệu 2, vụ điều tra 2
ESSENCE = {"memory": 1, "discovery": 1, "document": 2, "case": 2}
# Thưởng khi học sử
ANSWER_EXP, ANSWER_QUAN = 18, 4
RELIC_EXP, RELIC_TIEM, RELIC_QUAN = 110, 25, 40  # nhận khi về báo cáo già làng
POTION_HEAL = 0.4
GRILL_HEAL = 0.25  # cá nướng hồi ít hơn thuốc nam nhưng tự câu, tự nướng được
ROD = "can_cau"
MAX_FISH, MAX_GRILL = 12, 10  # giỏ cá tươi, xâu cá nướng mang theo được tối đa
# Cá câu được: tên, màu hình trong gói asset, tỉ lệ cắn câu
FISH = {"ca_chep": ("Cá chép", "red", 40), "ca_tram": ("Cá trắm", "white", 35), "ca_ro": ("Cá rô", "yellow", 25)}
RESPAWN = 30.0  # giây để quái mọc lại
WORLD_CHAT_COST = 10  # mỗi tin chat kênh thế giới tốn 10 quan; chat với người cùng map thì miễn phí
WORLD_CHAT_GAP = 5.0  # giây tối thiểu giữa hai tin thế giới (máy chủ cũng chặn đúng mức này)
HORSE_LEVEL = 3  # cấp được triệu hồi chiến mã
DROP_POTION = 0.18  # tỉ lệ rơi thuốc nam khi hạ quái


def exp_need(level: int) -> int:
    """Kinh nghiệm cần để lên cấp kế tiếp. Chỉnh theo giả lập: làm nhiệm vụ và hạ chừng mười quái mỗi di tích thì cấp
    người chơi bám sát cấp quái của chặng đó suốt game."""
    return int(22 * level ** 1.4)


def stat_cost(next_level: int) -> int:
    return STAT_COST * next_level


SLOT_NAMES = {"vu_khi": "Vũ khí", "giap": "Áo giáp", "mu": "Mũ", "giay": "Giày", "gang": "Găng", "cong_cu": "Đồ nghề", "dung": "Vật phẩm"}
# dmg: sát thương thêm; hp: máu thêm; spd: tốc độ thêm; cd: giảm thời gian hồi kỹ năng
ITEMS = {
    # vũ khí
    "gay_tre": {"slot": "vu_khi", "name": "Gậy tre", "level": 1, "price": 0, "dmg": 0.05, "desc": "Gậy tre đực đẽo nhẵn, thứ có sẵn ở mọi làng."},
    "dao_sat": {"slot": "vu_khi", "name": "Đao sắt", "level": 3, "price": 60, "dmg": 0.12, "desc": "Đao một lưỡi rèn bằng sắt."},
    "giao_dai": {"slot": "vu_khi", "name": "Giáo dài", "level": 5, "price": 130, "dmg": 0.18, "desc": "Giáo cán dài mũi sắt, giữ đối thủ ở xa."},
    "no_go": {"slot": "vu_khi", "name": "Nỏ gỗ", "level": 7, "price": 210, "dmg": 0.20, "cd": 0.06,
              "desc": "Nỏ là vũ khí bắn xa quen thuộc của người Việt; ở Cổ Loa từng đào được cả kho mũi tên đồng."},
    "kiem_thep": {"slot": "vu_khi", "name": "Kiếm thép", "level": 10, "price": 340, "dmg": 0.30, "desc": "Kiếm hai lưỡi bằng thép tôi."},
    "cung_ten": {"slot": "vu_khi", "name": "Cung tên", "level": 12, "price": 420, "dmg": 0.30, "cd": 0.08, "spd": 0.03,
                 "desc": "Cung gỗ dây gai, tên tre; nhẹ, hồi chiêu nhanh."},
    "ma_tau": {"slot": "vu_khi", "name": "Mã tấu", "level": 15, "price": 650, "dmg": 0.42, "desc": "Lưỡi to bản, chém mạnh."},
    "dai_dao": {"slot": "vu_khi", "name": "Đại đao", "level": 19, "price": 900, "dmg": 0.52, "hp": 20, "desc": "Đao lớn cán dài, phải khoẻ mới múa được."},
    "bao_kiem": {"slot": "vu_khi", "name": "Bảo kiếm", "level": 24, "price": 1300, "dmg": 0.62, "cd": 0.05, "desc": "Kiếm rèn kỹ, sắc và bền. Đồ trong game, không phải hiện vật có thật."},
    # áo giáp
    "ao_vai": {"slot": "giap", "name": "Áo vải nâu", "level": 1, "price": 0, "hp": 10, "desc": "Áo vải nhuộm nâu của người làng."},
    "giap_da": {"slot": "giap", "name": "Áo giáp da", "level": 4, "price": 80, "hp": 35, "desc": "Áo làm từ da thuộc dày."},
    "giap_bong": {"slot": "giap", "name": "Áo bông dày", "level": 8, "price": 200, "hp": 60, "desc": "Áo nhồi bông nhiều lớp, đỡ được tên bắn."},
    "giap_vay": {"slot": "giap", "name": "Giáp vảy sắt", "level": 13, "price": 480, "hp": 100, "desc": "Những miếng sắt nhỏ kết chồng lên nhau như vảy."},
    "giap_dong": {"slot": "giap", "name": "Giáp lá đồng", "level": 20, "price": 1000, "hp": 160, "desc": "Áo gắn những lá đồng che ngực và vai."},
    # mũ
    "khan_chit": {"slot": "mu", "name": "Khăn chít", "level": 1, "price": 0, "spd": 0.02, "desc": "Khăn vải quấn đầu."},
    "non_la": {"slot": "mu", "name": "Nón lá", "level": 3, "price": 40, "spd": 0.04, "desc": "Nón lá che nắng che mưa."},
    "mu_da": {"slot": "mu", "name": "Mũ da", "level": 7, "price": 130, "spd": 0.05, "hp": 20, "desc": "Mũ da cứng, che đầu khỏi đòn chém."},
    "mu_sat": {"slot": "mu", "name": "Mũ sắt", "level": 14, "price": 520, "spd": 0.07, "hp": 50, "desc": "Mũ sắt có chóp và tua đỏ."},
    # giày
    "dep_rom": {"slot": "giay", "name": "Dép rơm", "level": 1, "price": 10, "spd": 0.03, "desc": "Dép kết bằng rơm, đi nhẹ chân."},
    "giay_vai": {"slot": "giay", "name": "Giày vải", "level": 6, "price": 120, "spd": 0.06, "desc": "Giày vải đế mềm, chạy nhanh."},
    "ung_da": {"slot": "giay", "name": "Ủng da", "level": 12, "price": 400, "spd": 0.08, "hp": 30, "desc": "Ủng da cổ cao, hợp đường dài."},
    # găng
    "bao_tay_vai": {"slot": "gang", "name": "Bao tay vải", "level": 2, "price": 25, "dmg": 0.03, "desc": "Quấn tay cho chắc cán vũ khí."},
    "gang_da": {"slot": "gang", "name": "Găng da", "level": 8, "price": 190, "dmg": 0.07, "cd": 0.03, "desc": "Găng da thuộc, cầm nỏ cầm đao đều chắc."},
    "gang_sat": {"slot": "gang", "name": "Găng bọc sắt", "level": 16, "price": 700, "dmg": 0.12, "hp": 25, "desc": "Mu bàn tay bọc sắt, đỡ được lưỡi đao."},
    # vật phẩm
    "thuoc_nam": {"slot": "dung", "name": "Thuốc nam", "level": 1, "price": 15, "heal": POTION_HEAL, "desc": "Thuốc sắc sẵn, uống giữa trận để hồi máu."},
    # tự làm ra, không bán: câu cá tươi rồi đem nướng ở bếp lửa của người câu cá
    "ca_tuoi": {"slot": "dung", "name": "Cá tươi", "level": 1, "price": 0, "craft": True,
                "desc": "Cá câu được ở sông hồ. Mang đến bếp lửa của người câu cá để nướng."},
    "ca_nuong": {"slot": "dung", "name": "Cá nướng", "level": 1, "price": 0, "craft": True, "heal": GRILL_HEAL, "key": "E",
                 "desc": "Cá xiên que tre nướng trên than. Ăn giữa trận để lại sức."},
    # đồ nghề
    "can_cau": {"slot": "cong_cu", "name": "Cần câu tre", "level": 1, "price": 20,
                "desc": "Cần tre, dây câu, lưỡi câu sắt. Đứng sát mép nước bấm C để thả câu, cá cắn thì bấm C lần nữa."},
}
STARTER = ("gay_tre", "ao_vai", "khan_chit")


def item_icon(item_id: str) -> str:
    return f"ui/item_{item_id}.png"


def item_text(item: dict) -> str:
    parts = []
    if item.get("dmg"):
        parts.append(f"+{round(item['dmg'] * 100)}% sát thương")
    if item.get("hp"):
        parts.append(f"+{item['hp']} máu")
    if item.get("spd"):
        parts.append(f"+{round(item['spd'] * 100)}% tốc độ")
    if item.get("cd"):
        parts.append(f"-{round(item['cd'] * 100)}% hồi chiêu")
    if item.get("heal"):
        parts.append(f"hồi {round(item['heal'] * 100)}% máu (phím {item.get('key', 'Q')} khi đang đánh)")
    return ", ".join(parts)


# Quái: char là nhân vật đã vẽ; style và smart dùng cho bộ não bot của trận đánh; chief là tên kẻ cầm đầu toán đó
MOBS = {
    "linh_nam_han": {"name": "Lính Nam Hán", "chief": "Đầu mục quân Nam Hán", "chief_char": "TuongTong", "char": "LinhTong", "level": 2,
                     "hp": 42, "power": 0.5, "speed": 150, "skills": [], "exp": 14, "tiem": 6, "quan": (2, 5), "smart": 0.15},
    "thuy_binh_nam_han": {"name": "Thuỷ binh Nam Hán", "chief": "Đầu mục thuỷ binh Nam Hán", "chief_char": "TuongTong", "char": "LinhTong",
                          "level": 3, "hp": 50, "power": 0.58, "speed": 160, "skills": ["phong_lao"], "exp": 18, "tiem": 7, "quan": (2, 6), "smart": 0.2},
    "linh_tong": {"name": "Lính Tống", "chief": "Chỉ huy toán lính Tống", "chief_char": "TuongTong", "char": "LinhTong", "level": 5,
                  "hp": 62, "power": 0.66, "speed": 165, "skills": ["phong_lao"], "exp": 26, "tiem": 9, "quan": (3, 7), "smart": 0.25},
    "cung_thu_tong": {"name": "Cung thủ Tống", "chief": "Chỉ huy cung thủ Tống", "chief_char": "TuongTong", "char": "LinhTong", "level": 6,
                      "hp": 60, "power": 0.75, "speed": 170, "skills": ["phi_tieu"], "style": "ranged", "exp": 32, "tiem": 12, "quan": (4, 9), "smart": 0.35},
    "linh_nguyen": {"name": "Lính Nguyên", "chief": "Bách hộ quân Nguyên", "chief_char": "TuongNguyen", "char": "LinhNguyen", "level": 8,
                    "hp": 85, "power": 0.85, "speed": 185, "skills": ["dot_kich"], "exp": 42, "tiem": 15, "quan": (5, 12), "smart": 0.4},
    "cung_thu_nguyen": {"name": "Cung thủ Nguyên", "chief": "Bách hộ cung thủ Nguyên", "chief_char": "TuongNguyen", "char": "LinhNguyen",
                        "level": 10, "hp": 90, "power": 0.95, "speed": 180, "skills": ["mua_ten", "phi_tieu"], "style": "ranged",
                        "exp": 54, "tiem": 19, "quan": (6, 14), "smart": 0.5},
    "linh_minh": {"name": "Lính Minh", "chief": "Bách hộ quân Minh", "chief_char": "TuongMinh", "char": "LinhMinh", "level": 12,
                  "hp": 120, "power": 1.0, "speed": 185, "skills": ["phong_lao", "lien_hoan"], "exp": 70, "tiem": 24, "quan": (8, 16), "smart": 0.5},
    "cung_thu_minh": {"name": "Cung thủ Minh", "chief": "Bách hộ cung thủ Minh", "chief_char": "TuongMinh", "char": "LinhMinh", "level": 15,
                      "hp": 125, "power": 1.1, "speed": 180, "skills": ["mua_ten", "no_lien_chau"], "style": "ranged",
                      "exp": 88, "tiem": 30, "quan": (9, 18), "smart": 0.6},
    "tran_thu_minh": {"name": "Lính trấn thủ Minh", "chief": "Thiên hộ trấn thủ Minh", "chief_char": "TuongMinh", "char": "LinhMinh", "level": 18,
                      "hp": 170, "power": 1.2, "speed": 185, "skills": ["chan_dia", "the_thu"], "style": "tank",
                      "exp": 110, "tiem": 36, "quan": (10, 22), "smart": 0.65},
    "don_bot": {"name": "Đồn bốt", "chief": "Đồn bốt kiên cố", "chief_char": "LoCot", "char": "LoCot", "level": 20, "hp": 240, "power": 1.15,
                "speed": 0, "skills": ["phi_tieu", "mua_ten"], "style": "ranged", "exp": 130, "tiem": 42, "quan": (14, 28), "smart": 0.4, "object": True},
    "lo_cot": {"name": "Lô cốt", "chief": "Lô cốt chỉ huy", "chief_char": "LoCot", "char": "LoCot", "level": 25, "hp": 340, "power": 1.3,
               "speed": 0, "skills": ["phi_tieu", "mua_ten", "chan_dia"], "style": "ranged", "exp": 170, "tiem": 55, "quan": (18, 34),
               "smart": 0.5, "object": True},
    # ---- quái ở vùng luyện ----
    "linh_mong_co": {"name": "Lính Mông Cổ", "chief": "Bách hộ quân Mông Cổ", "chief_char": "TuongNguyen", "char": "LinhNguyen", "level": 7,
                     "hp": 76, "power": 0.8, "speed": 180, "skills": ["dot_kich"], "exp": 38, "tiem": 14, "quan": (5, 11), "smart": 0.4,
                     "weapon": "dao_sat"},
    "cung_thu_mong_co": {"name": "Cung thủ Mông Cổ", "chief": "Bách hộ cung thủ Mông Cổ", "chief_char": "TuongNguyen", "char": "LinhNguyen",
                         "level": 8, "hp": 70, "power": 0.85, "speed": 185, "skills": ["mua_ten"], "style": "ranged", "exp": 44, "tiem": 16,
                         "quan": (5, 12), "smart": 0.45, "weapon": "cung_ten"},
    "ky_binh_mong_co": {"name": "Kỵ binh Mông Cổ", "chief": "Bách hộ kỵ binh Mông Cổ", "chief_char": "TuongKyMongCo", "char": "KyBinhMongCo",
                        "level": 10, "hp": 104, "power": 0.95, "speed": 240, "skills": ["xung_phong", "dot_kich"], "style": "assassin",
                        "exp": 58, "tiem": 20, "quan": (7, 15), "smart": 0.5, "weapon": "dao_sat"},
    "linh_giu_thanh_minh": {"name": "Lính giữ thành Minh", "chief": "Bách hộ giữ thành Minh", "chief_char": "TuongMinh", "char": "LinhMinh",
                            "level": 14, "hp": 150, "power": 1.05, "speed": 175, "skills": ["the_thu", "phong_lao"], "style": "tank",
                            "exp": 78, "tiem": 27, "quan": (8, 17), "smart": 0.55, "weapon": "giao_dai"},
    "ky_binh_minh": {"name": "Kỵ binh Minh", "chief": "Bách hộ kỵ binh Minh", "chief_char": "TuongMinh", "char": "KyBinhMinh", "level": 16,
                     "hp": 160, "power": 1.15, "speed": 245, "skills": ["xung_phong", "lien_hoan"], "style": "assassin", "exp": 96,
                     "tiem": 32, "quan": (9, 19), "smart": 0.6, "weapon": "giao_dai"},
    "u_sung": {"name": "Ụ súng", "chief": "Ụ súng kiên cố", "chief_char": "USung", "char": "USung", "level": 21, "hp": 210, "power": 1.1,
               "speed": 0, "skills": ["mua_ten"], "style": "ranged", "exp": 120, "tiem": 40, "quan": (12, 26), "smart": 0.4, "object": True,
               "weapon": "sung"},
    "xe_tang": {"name": "Xe tăng", "chief": "Xe tăng chỉ huy", "chief_char": "XeTang", "char": "XeTang", "level": 25, "hp": 330, "power": 1.3,
                "speed": 110, "skills": ["chan_dia"], "style": "ranged", "exp": 160, "tiem": 52, "quan": (16, 32), "smart": 0.45,
                "object": True, "weapon": "phao"},
    # ---- quái đợt hai: đánh trên sông, vây thành ----
    "thuyen_chien_nguyen": {"name": "Thuyền chiến Nguyên", "chief": "Lâu thuyền Nguyên", "chief_char": "ThuyenNguyen",
                            "char": "ThuyenNguyen", "level": 11, "hp": 240, "power": 1.0, "speed": 0, "skills": ["mua_ten"],
                            "style": "ranged", "exp": 64, "tiem": 22, "quan": (8, 16), "smart": 0.45, "object": True, "water": True,
                            "weapon": "ten_thuyen"},
    "linh_khien_minh": {"name": "Lính khiên Minh", "chief": "Bách hộ khiên Minh", "chief_char": "TuongMinh", "char": "LinhMinh",
                        "level": 17, "hp": 190, "power": 1.1, "speed": 170, "skills": ["the_thu", "phong_lao"], "style": "tank",
                        "exp": 100, "tiem": 34, "quan": (10, 20), "smart": 0.6, "weapon": "kiem_thep"},
    "tau_chien": {"name": "Tàu chiến", "chief": "Tàu chiến chỉ huy", "chief_char": "TauChien", "char": "TauChien", "level": 23,
                  "hp": 300, "power": 1.25, "speed": 0, "skills": ["chan_dia"], "style": "ranged", "exp": 145, "tiem": 48,
                  "quan": (15, 30), "smart": 0.45, "object": True, "water": True, "weapon": "phao"},
    "ca_no": {"name": "Ca nô", "chief": "Ca nô dẫn đường", "chief_char": "CaNo", "char": "CaNo", "level": 21, "hp": 170, "power": 1.0,
              "speed": 0, "skills": ["phi_tieu"], "style": "ranged", "exp": 110, "tiem": 38, "quan": (12, 24), "smart": 0.4,
              "object": True, "water": True, "weapon": "sung"},
    # ---- quái đợt ba: máy bắn đá bên sông Như Nguyệt, thuyền lương ở Diễn Châu, đoàn xe trên đường số 4 ----
    "may_ban_da_tong": {"name": "Máy bắn đá Tống", "chief": "Giàn bắn đá lớn", "chief_char": "MayBanDa", "char": "MayBanDa",
                        "level": 8, "hp": 170, "power": 0.85, "speed": 0, "skills": ["chan_dia"], "style": "ranged", "exp": 46,
                        "tiem": 16, "quan": (5, 12), "smart": 0.4, "object": True, "weapon": "da_ban"},
    "thuyen_luong_minh": {"name": "Thuyền lương Minh", "chief": "Thuyền lương lớn", "chief_char": "ThuyenLuongMinh",
                          "char": "ThuyenLuongMinh", "level": 13, "hp": 250, "power": 0.9, "speed": 0, "skills": ["mua_ten"],
                          "style": "ranged", "exp": 74, "tiem": 25, "quan": (14, 26), "smart": 0.4, "object": True, "water": True,
                          "weapon": "ten_thuyen"},
    "xe_van_tai": {"name": "Xe vận tải", "chief": "Xe chở đạn", "chief_char": "XeVanTai", "char": "XeVanTai", "level": 21, "hp": 220,
                   "power": 1.0, "speed": 0, "skills": ["phi_tieu"], "style": "ranged", "exp": 118, "tiem": 40, "quan": (14, 28),
                   "smart": 0.4, "object": True, "weapon": "sung"},
    "xe_boc_thep": {"name": "Xe bọc thép", "chief": "Xe bọc thép hộ tống", "chief_char": "XeBocThep", "char": "XeBocThep",
                    "level": 23, "hp": 280, "power": 1.2, "speed": 120, "skills": ["phi_tieu", "chan_dia"], "style": "ranged",
                    "exp": 140, "tiem": 46, "quan": (15, 30), "smart": 0.5, "object": True, "weapon": "sung"},
    # ---- quái đợt bốn: thuỷ binh và thuyền lương Nguyên ở Vân Đồn, ụ pháo ở Đông Khê ----
    "thuy_binh_nguyen": {"name": "Thuỷ binh Nguyên", "chief": "Bách hộ thuỷ binh Nguyên", "chief_char": "TuongNguyen",
                         "char": "LinhNguyen", "level": 12, "hp": 104, "power": 0.92, "speed": 178, "skills": ["phong_lao", "dot_kich"],
                         "exp": 64, "tiem": 22, "quan": (7, 15), "smart": 0.5, "weapon": "dao_sat"},
    "thuyen_luong_nguyen": {"name": "Thuyền lương Nguyên", "chief": "Thuyền lương đầu đoàn", "chief_char": "ThuyenLuongNguyen",
                            "char": "ThuyenLuongNguyen", "level": 13, "hp": 260, "power": 0.9, "speed": 0, "skills": ["mua_ten"],
                            "style": "ranged", "exp": 72, "tiem": 24, "quan": (14, 26), "smart": 0.4, "object": True,
                            "water": True, "weapon": "ten_thuyen"},
    "u_phao": {"name": "Ụ pháo", "chief": "Trận địa pháo", "chief_char": "UPhao", "char": "UPhao", "level": 24, "hp": 290,
               "power": 1.25, "speed": 0, "skills": ["chan_dia", "mua_ten"], "style": "ranged", "exp": 150, "tiem": 50,
               "quan": (16, 32), "smart": 0.45, "object": True, "weapon": "phao"},
}
# Kẻ mạnh nhất mỗi vùng luyện: đánh xong một lúc lại xuất hiện, thưởng nhiều (tên chung, không gán cho người có thật)
ELITES = {
    "f_dong_bo_dau": {"name": "Tướng tiên phong Mông Cổ", "char": "TuongKyMongCo", "level": 13, "hp": 420, "power": 1.25, "speed": 240,
                      "skills": ["xung_phong", "lien_hoan", "mua_ten"], "style": "assassin", "smart": 0.75, "aggro": 0.8,
                      "weapon": "ma_tau", "exp": 300, "tiem": 110, "quan": 140},
    "f_xuong_giang": {"name": "Chỉ huy giữ thành Xương Giang", "char": "TuongMinh", "scale": 5, "level": 19, "hp": 600, "power": 1.45,
                      "speed": 210, "skills": ["the_thu", "lien_hoan", "chan_dia", "hoi_khi"], "style": "tank", "smart": 0.8,
                      "aggro": 0.8, "weapon": "dai_dao", "exp": 520, "tiem": 190, "quan": 260},
    "f_chuong_duong": {"name": "Vạn hộ thuỷ quân Nguyên", "char": "TuongNguyen", "scale": 5, "level": 13, "hp": 440, "power": 1.3,
                       "speed": 215, "skills": ["lien_hoan", "mua_ten", "xung_phong"], "style": "tank", "smart": 0.75, "aggro": 0.8,
                       "weapon": "dai_dao", "exp": 320, "tiem": 115, "quan": 150},
    "f_dong_quan": {"name": "Thiên hộ giữ thành Đông Quan", "char": "TuongMinh", "scale": 5, "level": 21, "hp": 640, "power": 1.5,
                    "speed": 210, "skills": ["the_thu", "lien_hoan", "mua_ten", "hoi_khi"], "style": "tank", "smart": 0.8, "aggro": 0.8,
                    "weapon": "kiem_thep", "exp": 560, "tiem": 200, "quan": 280},
    "f_song_lo": {"name": "Tàu chỉ huy", "char": "TauChien", "scale": 5, "level": 25, "hp": 820, "power": 1.5, "speed": 0,
                  "skills": ["chan_dia", "mua_ten", "phi_tieu"], "style": "ranged", "smart": 0.6, "aggro": 0.85, "object": True,
                  "water": True, "weapon": "phao", "exp": 700, "tiem": 250, "quan": 360},
    "f_muong_thanh": {"name": "Lô cốt chỉ huy phân khu", "char": "LoCot", "scale": 5, "level": 27, "hp": 900, "power": 1.55, "speed": 0,
                      "skills": ["phi_tieu", "mua_ten", "chan_dia"], "style": "ranged", "smart": 0.6, "aggro": 0.85, "object": True,
                      "weapon": "sung", "exp": 800, "tiem": 280, "quan": 400},
    "f_nhu_nguyet": {"name": "Chỉ huy doanh trại Tống", "char": "TuongTong", "scale": 5, "level": 9, "hp": 320, "power": 1.1,
                     "speed": 200, "skills": ["the_thu", "phong_lao", "lien_hoan"], "style": "tank", "smart": 0.7, "aggro": 0.75,
                     "weapon": "giao_dai", "exp": 230, "tiem": 85, "quan": 110},
    "f_dien_chau": {"name": "Chỉ huy giữ thành Diễn Châu", "char": "TuongMinh", "scale": 5, "level": 17, "hp": 540, "power": 1.35,
                    "speed": 205, "skills": ["the_thu", "lien_hoan", "mua_ten"], "style": "tank", "smart": 0.75, "aggro": 0.8,
                    "weapon": "dai_dao", "exp": 440, "tiem": 160, "quan": 220},
    "f_bong_lau": {"name": "Xe bọc thép dẫn đầu", "char": "XeBocThep", "scale": 5, "level": 24, "hp": 780, "power": 1.45, "speed": 120,
                   "skills": ["phi_tieu", "chan_dia", "mua_ten"], "style": "ranged", "smart": 0.6, "aggro": 0.85, "object": True,
                   "weapon": "sung", "exp": 660, "tiem": 240, "quan": 340},
    "f_bien_van_don": {"name": "Thuyền chỉ huy đoàn thuyền lương", "char": "ThuyenLuongNguyen", "scale": 5, "level": 14, "hp": 470,
                       "power": 1.3, "speed": 0, "skills": ["mua_ten", "chan_dia", "phi_tieu"], "style": "ranged", "smart": 0.6,
                       "aggro": 0.85, "object": True, "water": True, "weapon": "ten_thuyen", "exp": 340, "tiem": 120, "quan": 165},
    "f_le_hoa": {"name": "Tướng kỵ đạo Vân Nam", "char": "TuongKyMinh", "level": 21, "hp": 620, "power": 1.45, "speed": 240,
                 "skills": ["xung_phong", "lien_hoan", "mua_ten"], "style": "assassin", "smart": 0.8, "aggro": 0.8,
                 "weapon": "dai_dao", "exp": 540, "tiem": 195, "quan": 270},
    "f_dong_khe": {"name": "Trận địa pháo trong đồn", "char": "UPhao", "scale": 5, "level": 26, "hp": 860, "power": 1.55, "speed": 0,
                   "skills": ["chan_dia", "mua_ten", "phi_tieu"], "style": "ranged", "smart": 0.6, "aggro": 0.85, "object": True,
                   "weapon": "phao", "exp": 760, "tiem": 270, "quan": 380},
}
ELITE_RESPAWN = 150.0
FIELD_TALK_REWARD = (120, 30, 50)  # nghe chuyện và trả lời đúng câu hỏi của người kể ở vùng luyện
# Quân xâm lược đúng thời của từng vùng: Bạch Đằng 938 là quân Nam Hán, Như Nguyệt 1077 là quân Tống, các trận nhà Trần là
# quân Mông – Nguyên, khởi nghĩa Lam Sơn là quân Minh. Thời 1945 – 1954 chỉ có đồn bốt, lô cốt.
ZONE_MOBS = {
    "r_duong_lam": ("linh_nam_han",), "r_trang_kenh": ("linh_nam_han", "thuy_binh_nam_han"), "r_co_loa": ("thuy_binh_nam_han", "linh_nam_han"),
    "r_nhu_nguyet": ("linh_tong", "cung_thu_tong"), "r_den_tran": ("linh_nguyen",), "r_kiep_bac": ("linh_nguyen", "cung_thu_nguyen"),
    "r_van_don": ("linh_nguyen",), "r_bai_coc": ("cung_thu_nguyen", "linh_nguyen"),
    "r_lam_kinh": ("linh_minh",), "r_le_lai": ("linh_minh", "cung_thu_minh"), "r_tra_lan": ("linh_minh",),
    "r_tot_dong": ("cung_thu_minh", "linh_minh"), "r_chi_lang": ("tran_thu_minh", "cung_thu_minh"), "r_ho_guom": ("tran_thu_minh",),
    "r_tan_trao": ("don_bot",), "r_ba_dinh": ("don_bot",), "r_bien_gioi": ("lo_cot",), "r_dien_bien": ("lo_cot",),
}
# Vũ khí quái cầm: giáo cho bộ binh, đao cho lính Nguyên (kỵ binh thảo nguyên quen dùng đao cong), cung nỏ cho cung thủ
MOB_WEAPONS = {
    "linh_nam_han": "giao_dai", "thuy_binh_nam_han": "dao_sat", "linh_tong": "giao_dai", "cung_thu_tong": "cung_ten",
    "linh_nguyen": "dao_sat", "cung_thu_nguyen": "cung_ten", "linh_minh": "giao_dai", "cung_thu_minh": "no_go",
    "tran_thu_minh": "dai_dao",
}
for _mid, _w in MOB_WEAPONS.items():
    MOBS[_mid]["weapon"] = _w
# Võ sinh ở võ đài và người thách đấu trên đường
BOT_WEAPONS = {
    "b_trai_lang": "gay_tre", "b_linh_tran": "giao_dai", "b_vo_sinh": "dao_sat", "b_tho_san": "cung_ten", "b_vo_su": "gay_tre",
    "b_xa_thu": "no_go", "b_cao_thu": "kiem_thep",
}
# Một dòng sử cho mỗi loại quái, hiện lần đầu hạ được; chỉ nêu điều sách giáo khoa và chính sử đã chép
MOB_FACTS = {
    "linh_nam_han": ("Nam Hán là nước ở vùng Quảng Đông, Quảng Tây ngày nay. Năm 938, thuỷ quân Nam Hán do Lưu Hoằng Tháo chỉ huy bị Ngô Quyền "
                     "đánh tan trên sông Bạch Đằng.", "c_tt_ngo"),
    "thuy_binh_nam_han": ("Quân Nam Hán theo đường biển vào cửa sông Bạch Đằng, nên Ngô Quyền cho đóng cọc ở lòng sông để chờ thuỷ triều.",
                          "c_tt_ngo"),
    "linh_tong": ("Năm 1076 – 1077, quân Tống tiến sang và bị chặn lại ở phòng tuyến sông Như Nguyệt.", "c_sgk_khang_chien"),
    "cung_thu_tong": ("Sau thất bại ở sông Như Nguyệt, nhà Tống phải chấp nhận giảng hoà và rút quân.", "c_sgk_khang_chien"),
    "linh_mong_co": ("Năm 1258, khi chưa lập ra nhà Nguyên, quân Mông Cổ lần đầu đánh vào Đại Việt và bị đẩy lui ở Đông Bộ Đầu.",
                     "c_tt_1258"),
    "cung_thu_mong_co": ("Quân Mông Cổ nổi tiếng giỏi cưỡi ngựa bắn cung, từng đánh chiếm nhiều vùng rộng lớn ở châu Á và châu Âu.",
                         "c_sgk_khang_chien"),
    "ky_binh_mong_co": ("Kỵ binh là sức mạnh chính của quân Mông Cổ. Năm 1258, nhà Trần dùng thuyền chiến đánh ở bến Đông Bộ Đầu bên sông Hồng.",
                        "c_tt_1258"),
    "linh_nguyen": ("Nhà Nguyên do người Mông Cổ lập ra năm 1271. Quân Nguyên sang đánh nước ta năm 1285 và năm 1287 – 1288.",
                    "c_sgk_khang_chien"),
    "cung_thu_nguyen": ("Cả ba lần kháng chiến chống Mông – Nguyên, quân dân nhà Trần đều thắng.", "c_sgk_khang_chien"),
    "linh_minh": ("Nhà Minh đặt ách đô hộ nước ta từ năm 1407. Khởi nghĩa Lam Sơn kéo dài mười năm mới đuổi được quân Minh.",
                  "c_sgk_khang_chien"),
    "cung_thu_minh": ("Cuối năm 1427, viện binh Minh bị đánh tan ở Chi Lăng và Xương Giang.", "c_tt_1427"),
    "tran_thu_minh": ("Tháng 12 năm 1427, tướng Minh là Vương Thông phải dự Hội thề Đông Quan, hẹn rút quân về nước.", "c_sgk_khang_chien"),
    "linh_giu_thanh_minh": ("Thành Xương Giang nằm trên đường từ Lạng Sơn về Đông Quan; nghĩa quân hạ thành trước khi viện binh Minh tới.",
                            "c_xuong_giang"),
    "ky_binh_minh": ("Đạo viện binh của Liễu Thăng tiến sang qua ải Chi Lăng vào năm 1427.", "c_tt_1427"),
    "don_bot": ("Trong kháng chiến chống Pháp, đối phương dựng đồn bốt dày đặc để giữ đường và giữ vùng.", "c_sgk_dbp"),
    "lo_cot": ("Tập đoàn cứ điểm Điện Biên Phủ có 49 cứ điểm, chia làm ba phân khu.", "c_dbp_tap_doan"),
    "u_sung": ("Muốn tiến sát cứ điểm, bộ đội đào hệ thống giao thông hào chằng chịt quanh lòng chảo.", "c_sgk_dbp"),
    "xe_tang": ("Xe tăng ở Điện Biên Phủ được chở lên bằng máy bay theo từng bộ phận rồi lắp lại trong lòng chảo.", "c_dbp_tap_doan"),
    "thuyen_chien_nguyen": ("Năm 1285, cánh quân Toa Đô theo đường thuỷ kéo về; nhà Trần chặn đánh ở bến Hàm Tử, rồi thắng lớn ở "
                            "Chương Dương.", "c_tt_1285"),
    "linh_khien_minh": ("Cuối năm 1426, nghĩa quân Lam Sơn vây thành Đông Quan; quân Minh do Vương Thông cầm đầu đóng chặt cửa thành cố "
                        "thủ.", "c_tt_1426"),
    "tau_chien": ("Thu đông 1947, một cánh quân Pháp theo đường thuỷ ngược sông Hồng vào sông Lô, tiến lên Tuyên Quang.", "c_ls_song_lo"),
    "ca_no": ("Ngày 24 tháng 10 năm 1947, ở Chí Đám vùng Đoan Hùng, bộ đội phục kích đoàn tàu chiến địch trên sông Lô.", "c_ls_song_lo"),
    "may_ban_da_tong": ("Năm 1077, quân Tống đóng ở bờ bắc sông Như Nguyệt, dựng máy bắn đá và bắc cầu phao để vượt sông, nhưng "
                        "đều bị đánh lui.", "c_tt_1077"),
    "thuyen_luong_minh": ("Năm 1425, Đô ty nhà Minh là Trương Hùng chở lương bằng hơn 300 chiếc thuyền đến Diễn Châu, bị Đinh Lễ "
                          "phục binh đánh, cướp được thuyền lương.", "c_tt_1425"),
    "xe_van_tai": ("Thu đông 1947, đường số 4 dọc biên giới Cao Bằng – Lạng Sơn là đường tiến quân và tiếp tế của Pháp; các đoàn xe "
                   "thường bị bộ đội phục kích.", "c_ls_bong_lau"),
    "xe_boc_thep": ("Ngày 30 tháng 10 năm 1947, ở đèo Bông Lau trên đường số 4, bộ đội tiêu diệt gọn một đoàn xe cơ giới của Pháp, "
                    "trong đó có xe bọc thép.", "c_ls_bong_lau"),
    "thuy_binh_nguyen": ("Cuối năm 1287, thuỷ quân Nguyên theo đường biển tiến vào nước ta, thuyền chiến đi trước, đoàn thuyền "
                         "lương đi sau.", "c_tt_1287"),
    "thuyen_luong_nguyen": ("Ở Vân Đồn, Trần Khánh Dư đánh đoàn thuyền lương Nguyên; sử chép ông bắt được lương thực khí giới "
                            "của giặc không xiết kể.", "c_tt_1287"),
    "u_phao": ("Cụm cứ điểm Đông Khê có pháo 105 ly, pháo cối, lô cốt và hầm ngầm. Ngày 16 – 18/9/1950, bộ đội vẫn hạ được, "
               "mở màn chiến dịch Biên giới.", "c_ls_dong_khe"),
}
CAMP_SIZE = 3
# Trùm gác mật thư cuối cùng của mỗi màn (tên chung, không gán cho nhân vật lịch sử cụ thể)
BOSSES = {
    "man1": {"name": "Tướng thuỷ quân Nguyên", "char": "TuongNguyen", "scale": 5, "level": 12, "hp": 420, "power": 1.3, "speed": 205,
             "skills": ["lien_hoan", "chan_dia", "mua_ten", "xung_phong"], "style": "tank", "smart": 0.75, "aggro": 0.75,
             "exp": 320, "tiem": 120, "quan": 150, "weapon": "dai_dao"},
    "man2": {"name": "Tướng trấn thủ quân Minh", "char": "TuongMinh", "scale": 5, "level": 20, "hp": 620, "power": 1.5, "speed": 215,
             "skills": ["lien_hoan", "khoi_mu", "mua_ten", "chan_dia", "hoi_khi"], "style": "assassin", "smart": 0.85, "aggro": 0.8,
             "exp": 600, "tiem": 220, "quan": 300, "weapon": "kiem_thep"},
    "man3": {"name": "Cứ điểm kiên cố", "char": "LoCot", "scale": 5, "level": 28, "hp": 950, "power": 1.6, "speed": 0,
             "skills": ["phi_tieu", "mua_ten", "chan_dia", "no_lien_chau"], "style": "ranged", "smart": 0.6, "aggro": 0.85,
             "exp": 900, "tiem": 320, "quan": 450, "object": True},
}
MOB_HP_GROWTH = 0.10  # mỗi cấp quái thêm 10% máu gốc
MOB_POWER_GROWTH = 0.06  # và 6% sức đánh gốc
BOSS_EASE = 0.15  # mỗi lần thua trùm, trùm yếu đi 15% (tối đa 45%) để người chơi không bị kẹt mãi


def mob_reward(mob: dict, player_level: int, rng: random.Random | None = None) -> tuple[int, int, int]:
    """Kinh nghiệm, tiềm năng, quan khi hạ một quái; đánh quái yếu hơn mình quá nhiều thì nhận ít."""
    rng = rng or random
    gap = player_level - mob["level"]
    k = 1.0 if gap <= 3 else max(0.2, 1.0 - 0.16 * (gap - 3))
    lo, hi = mob["quan"]
    return max(1, round(mob["exp"] * k)), max(1, round(mob["tiem"] * k)), rng.randint(lo, hi)


def guard_of(mob_id: str) -> dict:
    """Kẻ cầm đầu canh mật thư của một vùng: mạnh hơn lính thường hai cấp."""
    m = MOBS[mob_id]
    g = dict(m, name=m["chief"], char=m["chief_char"], level=m["level"] + 2, hp=round(m["hp"] * 2.2), power=round(m["power"] * 1.15, 2),
             exp=m["exp"] * 4, tiem=m["tiem"] * 4, quan=(m["quan"][1] * 3, m["quan"][1] * 4), smart=min(0.9, m.get("smart", 0.3) + 0.2))
    g["skills"] = list(dict.fromkeys([*m.get("skills", ()), "the_thu" if m.get("style") != "ranged" else "mua_ten"]))
    if not m.get("object") and m.get("style") != "ranged":
        g["weapon"] = "ma_tau"  # kẻ cầm đầu cầm đao lớn
    return g


def growth(level: int) -> tuple[float, float]:
    """Máu và sức đánh của quái tăng theo cấp, cùng nhịp với người chơi lên cấp, mua đồ, tăng chỉ số."""
    return 1 + MOB_HP_GROWTH * (level - 1), 1 + MOB_POWER_GROWTH * (level - 1)


def fight_spec(mob: dict, boss: bool = False, ease: float = 0.0) -> dict:
    """Mô tả đối thủ cho FightScene; `ease` làm trùm yếu đi sau mỗi lần người chơi thua."""
    weak = 1.0 - ease
    hp_k, pw_k = growth(mob["level"])
    spec = {
        "name": f"{mob['name']} (cấp {mob['level']})", "char": mob["char"], "hp": round(mob["hp"] * hp_k * weak),
        "power": round(mob["power"] * pw_k * weak, 3),
        "speed": mob["speed"], "skills": list(mob.get("skills", ())), "level": 1 + (mob["level"] >= 12) + (mob["level"] >= 24),
        "aggro": mob.get("aggro", 0.55), "smart": mob.get("smart", 0.3), "style": mob.get("style", "melee"),
    }
    if mob.get("scale"):
        spec["scale"] = mob["scale"]
    if mob.get("weapon"):
        spec["weapon"] = mob["weapon"]
    if boss:
        spec["name"] = f"TRÙM: {mob['name']}"
    return spec


def challenger_spec(bot: dict, player_level: int) -> dict:
    """Người thách đấu trên đường: lấy võ sinh ở võ đài, mạnh lên theo cấp người chơi để trận nào cũng đáng đánh."""
    k = 1.0 + 0.045 * max(0, player_level - 3)
    level = max(1, player_level + random.randint(-1, 2))
    return {
        "name": f"{bot['name']} (cấp {level})", "char": bot["char"], "hp": round(bot["hp"] * k), "power": round(bot["power"] * min(k, 1.6), 3),
        "speed": bot["speed"], "skills": list(bot.get("skills", ())), "level": bot.get("level", 1), "aggro": bot.get("aggro", 0.6),
        "smart": bot.get("smart", 0.4), "style": bot.get("style", "melee"), "mob_level": level, "weapon": BOT_WEAPONS.get(bot.get("id")),
    }


def challenger_reward(level: int) -> tuple[int, int, int]:
    return 20 + level * 9, 8 + level * 3, 10 + level * 4


def difficulty_color(player_level: int, mob_level: int) -> tuple[int, int, int]:
    """Tên quái màu xanh khi dễ, vàng khi ngang sức, đỏ khi mạnh hơn hẳn."""
    gap = mob_level - player_level
    if gap <= -3:
        return (150, 220, 150)
    if gap <= 2:
        return (243, 212, 140)
    return (240, 110, 90)
