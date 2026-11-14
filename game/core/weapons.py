"""Vũ khí cầm trên tay: ảnh, cách cầm khi đi, cách vung khi đánh, vệt chém, hiệu ứng riêng từng loại.

Ảnh cầm tay lấy từ gói Ninja Adventure (CC0): chuôi ở trên, lưỡi chĩa xuống. Muốn lưỡi chĩa theo góc `a` (độ, trục y
hướng lên) thì xoay ảnh `a + 90` độ quanh điểm cầm. Nỏ không có trong gói nên tự vẽ cùng nét.

Mỗi loại một cách đánh:
- gậy: quất mạnh, đẩy lùi xa, bụi gỗ văng;
- đao, mã tấu: chém vòng cung, vệt sáng trắng;
- kiếm: chém nhanh, vệt xanh nhạt; bảo kiếm thêm vệt vàng và tia sáng;
- giáo: đâm thẳng, với xa hơn;
- đại đao: bổ chậm mà rộng, rung màn hình, quét được nhiều đối thủ;
- cung, nỏ: bắn tên bay thật; nỏ chậm hơn nhưng mũi tên nặng hơn.
"""

from __future__ import annotations

import math

import pygame

from core import sprites

OUTLINE = (20, 27, 27)
ART = {
    "gay_tre": "weapon/stick.png", "dao_sat": "weapon/katana.png", "giao_dai": "weapon/lance.png", "kiem_thep": "weapon/sword2.png",
    "cung_ten": "weapon/bow.png", "ma_tau": "weapon/bigsword.png", "dai_dao": "weapon/lance2.png", "bao_kiem": "weapon/sword.png",
    "no_go": None, "phao": None, "sung": None, "ten_thuyen": None, "da_ban": None,
}
# vũ khí của cỗ máy, công sự, thuyền (tên bắn từ thuyền, pháo, súng, đá của máy bắn đá): không vẽ trên tay
NO_HAND = {"phao", "sung", "ten_thuyen", "da_ban"}
KIND = {
    "gay_tre": "gay", "dao_sat": "dao", "giao_dai": "giao", "no_go": "no", "kiem_thep": "kiem", "cung_ten": "cung",
    "ma_tau": "dao", "dai_dao": "dai_dao", "bao_kiem": "bao_kiem", "phao": "phao", "sung": "sung", "ten_thuyen": "cung",
    "da_ban": "phao",
}
# move: swing (chém vòng), thrust (đâm), cleave (bổ rộng), shoot (bắn); time: thời gian vung; cd: hồi đòn
STYLE = {
    None: {"move": "none", "time": 0.22, "cd": 0.42, "reach": 1.0, "knock": 1.0, "dmg": 1.0},
    "gay": {"move": "swing", "time": 0.24, "cd": 0.42, "reach": 1.0, "knock": 1.7, "dmg": 1.0, "trail": (236, 214, 150)},
    "dao": {"move": "swing", "time": 0.22, "cd": 0.42, "reach": 1.0, "knock": 1.0, "dmg": 1.0, "trail": (255, 242, 218)},
    "kiem": {"move": "swing", "time": 0.18, "cd": 0.36, "reach": 1.0, "knock": 0.9, "dmg": 1.0, "trail": (214, 232, 255)},
    "bao_kiem": {"move": "swing", "time": 0.18, "cd": 0.36, "reach": 1.1, "knock": 1.0, "dmg": 1.0, "trail": (255, 214, 110)},
    "giao": {"move": "thrust", "time": 0.2, "cd": 0.46, "reach": 1.35, "knock": 1.3, "dmg": 1.0, "trail": (240, 240, 236)},
    "dai_dao": {"move": "cleave", "time": 0.32, "cd": 0.62, "reach": 1.3, "knock": 2.0, "dmg": 1.25, "trail": (255, 170, 110)},
    "cung": {"move": "shoot", "time": 0.18, "cd": 0.5, "reach": 5.0, "knock": 0.4, "dmg": 0.9, "speed": 760},
    "no": {"move": "shoot", "time": 0.2, "cd": 0.7, "reach": 5.0, "knock": 0.8, "dmg": 1.3, "speed": 980},
    "phao": {"move": "shoot", "time": 0.3, "cd": 1.4, "reach": 5.0, "knock": 1.5, "dmg": 1.7, "speed": 620},
    "sung": {"move": "shoot", "time": 0.12, "cd": 0.55, "reach": 5.0, "knock": 0.3, "dmg": 0.65, "speed": 980},
}
# điểm cầm trong khung 16x16 khi đi và khi vung (khung vẽ chân ở giữa đáy)
HAND = {"down": (13, 13), "up": (2, 13), "right": (8, 13), "left": (7, 13)}
ATTACK_HAND = {"down": (13, 13), "up": (3, 9), "right": (14, 11), "left": (1, 11)}
HELD = {"down": -70.0, "up": -110.0, "right": -55.0, "left": -125.0}
FACING_ANGLE = {"right": 0.0, "up": 90.0, "left": 180.0, "down": -90.0}
_cache: dict = {}


def kind(item_id: str | None) -> str | None:
    return KIND.get(item_id) if item_id else None


def style(item_id: str | None) -> dict:
    return STYLE[kind(item_id)]


def _crossbow() -> pygame.Surface:
    """Nỏ: báng gỗ dọc, cánh nỏ ngang ở đầu, lẫy đồng; vẽ theo quy ước lưỡi chĩa xuống."""
    s = pygame.Surface((11, 13), pygame.SRCALPHA)
    wood, dark, bronze, string = (150, 98, 56), (96, 60, 34), (206, 150, 74), (236, 226, 196)
    pygame.draw.rect(s, OUTLINE, (4, 0, 3, 12))
    pygame.draw.line(s, wood, (5, 1), (5, 11))
    s.set_at((5, 4), bronze)
    s.set_at((5, 5), bronze)
    for x in range(0, 11):  # cánh nỏ cong nhẹ
        y = 9 + (1 if x in (0, 10) else 0) + (0 if 2 < x < 8 else 0)
        s.set_at((x, y), dark)
        s.set_at((x, y - 1), OUTLINE if x in (0, 10) else wood)
    for x in range(1, 10):
        s.set_at((x, 7), string)
    s.set_at((5, 12), (220, 220, 230))
    return s


def _bamboo(img: pygame.Surface) -> pygame.Surface:
    """Gậy tre: đổi thân gậy sang màu tre, giữ mấu đốt."""
    s = img.copy()
    for y in range(s.get_height()):
        for x in range(s.get_width()):
            r, g, b, a = s.get_at((x, y))
            if a and (r, g, b) != OUTLINE[:3] and r + g + b > 120:
                s.set_at((x, y), (176, 170, 86, 255) if y % 4 else (124, 118, 56, 255))
    return s


def image(item_id: str, scale: int) -> pygame.Surface | None:
    """Ảnh vũ khí ở độ phóng `scale`, lưỡi chĩa xuống."""
    if item_id not in KIND or item_id in NO_HAND:
        return None
    key = (item_id, scale)
    img = _cache.get(key)
    if img is None:
        path = ART.get(item_id)
        base = _crossbow() if path is None else sprites.image(path)
        if item_id == "gay_tre":
            base = _bamboo(base)
        img = pygame.transform.scale(base, (base.get_width() * scale, base.get_height() * scale))
        _cache[key] = img
    return img


def grip(item_id: str, img: pygame.Surface) -> tuple[float, float]:
    """Điểm cầm trên ảnh: cung cầm ở giữa, nỏ cầm gần báng, còn lại cầm ở chuôi."""
    w, h = img.get_size()
    if kind(item_id) == "cung":
        return w / 2, h / 2
    if kind(item_id) == "no":
        return w / 2, h * 0.25
    return w / 2, h * 0.08


def placed(item_id: str, scale: int, at: tuple[float, float], angle: float) -> tuple[pygame.Surface, pygame.Rect] | None:
    """Ảnh vũ khí đã xoay và chỗ đặt sao cho điểm cầm nằm đúng `at`, lưỡi chĩa theo `angle` (độ, trục y hướng lên)."""
    img = image(item_id, scale)
    if img is None:
        return None
    gx, gy = grip(item_id, img)
    w, h = img.get_size()
    turn = angle + 90.0
    rot = pygame.transform.rotate(img, turn)
    # vị trí điểm cầm so với tâm ảnh, xoay cùng ảnh (pygame xoay ngược chiều kim đồng hồ, trục y hướng xuống)
    ox, oy = gx - w / 2, gy - h / 2
    r = math.radians(turn)
    rx, ry = ox * math.cos(r) + oy * math.sin(r), -ox * math.sin(r) + oy * math.cos(r)
    return rot, rot.get_rect(center=(at[0] - rx, at[1] - ry))


def blit(surface: pygame.Surface, item_id: str, scale: int, at: tuple[float, float], angle: float) -> None:
    out = placed(item_id, scale, at, angle)
    if out:
        surface.blit(*out)


def held_sprite(item_id: str | None, facing: str, scale: int) -> tuple[pygame.Surface, int, int, bool] | None:
    """Vũ khí ở tư thế cầm khi đi: ảnh, độ lệch so với chân nhân vật, có nằm sau lưng không. Lưu sẵn cho đỡ tốn."""
    if not item_id or item_id not in KIND or item_id in NO_HAND:
        return None
    key = ("held", item_id, facing, scale)
    out = _cache.get(key)
    if out is None:
        angle, behind = held(facing)
        img, rect = placed(item_id, scale, hand_at(facing, (0, 0), scale), angle)
        out = (img, rect.x, rect.y, behind)
        _cache[key] = out
    return out


def hand_at(facing: str, foot: tuple[float, float], scale: int, attacking: bool = False, bob: float = 0.0) -> tuple[float, float]:
    """Toạ độ điểm cầm trên màn hình khi khung nhân vật vẽ đứng chân tại `foot`."""
    hx, hy = (ATTACK_HAND if attacking else HAND)[facing]
    return foot[0] + (hx - 8) * scale, foot[1] + (hy - 16) * scale + bob


def held(facing: str) -> tuple[float, bool]:
    """Góc cầm khi đi và vũ khí có nằm sau lưng không (quay lưng thì vũ khí khuất sau người)."""
    return HELD[facing], facing == "up"


def _ease(k: float) -> float:
    return 1 - (1 - max(0.0, min(1.0, k))) ** 2


def swing(item_id: str, facing: str, k: float, aim: float | None = None) -> tuple[float, float]:
    """Góc lưỡi và độ đẩy tới (theo tỉ lệ thân người) ở thời điểm `k` (0 → 1) của đòn đánh."""
    move = style(item_id)["move"]
    base = FACING_ANGLE[facing]
    if move == "thrust":
        return base, math.sin(math.pi * min(1.0, k)) * 0.55
    if move == "shoot":
        a = base if aim is None else aim
        return a, -0.12 * math.sin(math.pi * min(1.0, k * 2))  # giật nhẹ khi bắn
    spread = 250.0 if move == "cleave" else 180.0
    e = _ease(k)
    if facing == "left":
        return 180.0 - (110.0 - spread * e), 0.0
    if facing == "down":
        return 10.0 - spread * e, 0.0
    if facing == "up":
        return 170.0 - spread * e, 0.0
    return 110.0 - spread * e, 0.0


def trail(surface: pygame.Surface, item_id: str, facing: str, k: float, at: tuple[float, float], length: float) -> None:
    """Vệt chém: dải hình quạt phía sau lưỡi, nhạt dần."""
    st = style(item_id)
    if st["move"] not in ("swing", "cleave") or k >= 1.0:
        return
    a1, _ = swing(item_id, facing, k)
    a0, _ = swing(item_id, facing, max(0.0, k - 0.45))
    if abs(a1 - a0) < 4:
        return
    color = st["trail"]
    r_in, r_out = length * 0.35, length * (1.25 if st["move"] == "cleave" else 1.05)
    n = 10
    pad = int(r_out + 4)
    layer = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        b0, b1 = math.radians(a0 + (a1 - a0) * t0), math.radians(a0 + (a1 - a0) * t1)
        alpha = int(30 + 170 * t1 * (1 - k * 0.6))
        pts = [(pad + math.cos(b0) * r_in, pad - math.sin(b0) * r_in), (pad + math.cos(b0) * r_out, pad - math.sin(b0) * r_out),
               (pad + math.cos(b1) * r_out, pad - math.sin(b1) * r_out), (pad + math.cos(b1) * r_in, pad - math.sin(b1) * r_in)]
        pygame.draw.polygon(layer, (*color, alpha), pts)
    surface.blit(layer, (at[0] - pad, at[1] - pad))


def arrow(item_id: str) -> pygame.Surface | list[pygame.Surface]:
    """Thứ bay ra khi bắn, đầu quay sang phải: tên cung, tên nỏ, đạn pháo, đạn súng."""
    key = ("arrow", item_id)
    img = _cache.get(key)
    if img is None:
        k = kind(item_id)
        if item_id == "da_ban":  # hòn đá của máy bắn đá: khối đá xám
            low = pygame.Surface((7, 6), pygame.SRCALPHA)
            pygame.draw.ellipse(low, OUTLINE, (0, 0, 7, 6))
            pygame.draw.ellipse(low, (128, 124, 116), (1, 1, 5, 4))
            low.set_at((2, 1), (176, 172, 162))
            low.set_at((4, 3), (92, 88, 82))
            img = pygame.transform.scale(low, (21, 18))
        elif k == "phao":
            img = sprites.strip("fx/canonball.png", 5, 3)
        elif k == "sung":
            img = pygame.Surface((10, 4), pygame.SRCALPHA)
            pygame.draw.ellipse(img, (40, 36, 30), (0, 0, 10, 4))
            pygame.draw.line(img, (230, 210, 150), (6, 1), (9, 1))
        else:
            base = sprites.image("fx/arrow.png")
            img = pygame.transform.scale(base, (base.get_width() * 3, base.get_height() * 3))
            if k == "no":  # tên nỏ ngắn, mập
                img = pygame.transform.scale(img, (int(img.get_width() * 0.8), int(img.get_height() * 1.2)))
        _cache[key] = img
    return img
