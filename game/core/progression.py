"""Kỹ năng và chỉ số: kiếm bằng khám phá, trả lời lịch sử; dùng cả khi làm nhiệm vụ lẫn trên võ đài.

Điểm kỹ năng không cộng dồn lúc nhận mà tính lại từ tiến trình đã có (xem GameState.skill_points_earned), nên bản lưu cũ
vẫn đúng và không thể nhận trùng phần thưởng.
"""

from __future__ import annotations

STAT_MAX = 20
STATS = {
    "suc": {"name": "Sức đánh", "desc": "Mỗi điểm tăng 8% sát thương đòn đánh và kỹ năng.", "icon": "ui/sk_suc.png"},
    "the": {"name": "Thể lực", "desc": "Mỗi điểm tăng 12 máu tối đa trên võ đài và khi giao tranh.", "icon": "ui/sk_the.png"},
    "nhanh": {"name": "Nhanh nhẹn", "desc": "Mỗi điểm đi nhanh hơn 4%, cả trên map lẫn võ đài.", "icon": "ui/sk_nhanh.png"},
    "tri": {"name": "Trí tuệ", "desc": "Mỗi điểm giảm 4% thời gian hồi kỹ năng, cả trong các trận đánh lịch sử.", "icon": "ui/sk_tri.png"},
}
BASE_HP = 100
SKILL_MAX = 3
SLOTS = 4
# needs: số câu trả lời đúng hoặc số di tích đã đóng dấu mới học được, để việc học đi trước việc đánh
SKILLS = {
    "phong_lao": {"name": "Phóng lao", "desc": "Ném giáo thẳng vào đối thủ.", "cd": 2.5, "needs": ("answers", 3)},
    "dot_kich": {"name": "Đột kích", "desc": "Lướt nhanh tới và chém, né được đòn trong lúc lướt.", "cd": 4.0, "needs": ("relics", 1)},
    "ten_lua": {"name": "Tên lửa", "desc": "Bắn ba mũi lửa xoè ra, trúng thì cháy thêm vài giây.", "cd": 5.0, "needs": ("answers", 10)},
    "xoay_kiem": {"name": "Xoáy kiếm", "desc": "Chém một vòng quanh mình, đánh trúng mọi đối thủ ở gần.", "cd": 6.0, "needs": ("relics", 3)},
    "the_thu": {"name": "Thế thủ", "desc": "Giơ khiên, giảm mạnh sát thương trong chốc lát.", "cd": 8.0, "needs": ("answers", 15)},
    "hoi_khi": {"name": "Hồi khí", "desc": "Lấy lại một phần máu.", "cd": 10.0, "needs": ("relics", 5)},
    "chong_ngam": {"name": "Chông ngầm", "desc": "Rải chông dưới chân, đối thủ đạp phải thì mất máu và đi chậm. Học từ kế đóng cọc.", "cd": 7.0, "needs": ("answers", 22)},
    "no_lien_chau": {"name": "Nỏ liên châu", "desc": "Bắn liền năm mũi tên vào đối thủ gần nhất.", "cd": 6.0, "needs": ("answers", 28)},
    "hoa_cong": {"name": "Hoả công", "desc": "Đốt một vùng lửa trước mặt, đối thủ đứng trong lửa bị cháy dần. Học từ trận Vân Đồn đốt thuyền lương.", "cd": 9.0, "needs": ("relics", 8)},
    "hao_khi": {"name": "Hào khí", "desc": "Hô vang khí thế: sức đánh và tốc độ tăng trong sáu giây, đẩy lùi đối thủ ở sát bên.", "cd": 14.0, "needs": ("relics", 10)},
    "phi_ma": {"name": "Phi mã xung trận", "desc": "Gọi chiến mã phi thẳng tới, húc ngã mọi đối thủ trên đường phi.", "cd": 9.0, "needs": ("answers", 34)},
}
# Chiêu riêng của bot ở võ đài; người chơi không học được nên không nằm trong SKILLS
BOT_SKILLS = {
    "mua_ten": {"name": "Mưa tên", "cd": 6.0, "windup": 0.3},
    "chan_dia": {"name": "Chấn địa", "cd": 7.0, "windup": 0.65},
    "lien_hoan": {"name": "Liên hoàn đao", "cd": 5.0, "windup": 0.35},
    "phi_tieu": {"name": "Phi tiêu", "cd": 3.2, "windup": 0.3},
    "khoi_mu": {"name": "Khói mù", "cd": 8.0, "windup": 0.25},
    "xung_phong": {"name": "Xung phong", "cd": 6.5, "windup": 0.6},
}


def skill_info(sid: str) -> dict:
    return SKILLS.get(sid) or BOT_SKILLS[sid]


# Điểm kỹ năng cho từng việc
SP_FIRST_TRY = 1
SP_RELIC = 2
SP_LEVEL = 5
SP_SIDE = 2
SP_CASE = 3
SP_DISCOVERY = 1
SP_ARENA = 1
SP_SKIRMISH = 2
SP_DOCUMENT = 2


def skill_cost(next_level: int) -> int:
    """Học cấp 1 tốn 1 điểm, cấp 2 tốn 2, cấp 3 tốn 3."""
    return next_level


def needs_text(need: tuple[str, int]) -> str:
    kind, value = need
    return f"Cần trả lời đúng {value} câu" if kind == "answers" else f"Cần đóng dấu {value} di tích"
