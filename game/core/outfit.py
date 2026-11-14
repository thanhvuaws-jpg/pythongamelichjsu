"""Vẽ trang phục lên nhân vật Villager của gói Ninja Adventure (CC0): dùng cho lính các thời và cho chính người chơi.

Người chơi mặc gì thì ngoại hình đổi theo: áo giáp đổi màu áo và hoa văn (vải, da, áo bông, giáp vảy, giáp lá đồng), mũ
đổi phần đầu (tóc búi, khăn chít, nón lá, mũ da, mũ sắt), giày đổi phần bàn chân, găng đổi phần bàn tay. Khung 16x16 được
vẽ lại một lần cho mỗi bộ đồ rồi cất vào bộ nhớ đệm.
"""

from __future__ import annotations

import pygame

U = 16
OUTLINE = (20, 27, 27)
SKIN = {(242, 173, 125), (239, 145, 79), (209, 75, 52)}
SHIRT, SHIRT_LIGHT, SHIRT_DARK, PANTS = (84, 135, 137), (121, 184, 206), (46, 57, 57), (78, 72, 74)
DIRS = ("down", "up", "left", "right")
BASE = "Villager"


def _px(s, x, y):
    if 0 <= x < s.get_width() and 0 <= y < s.get_height():
        c = s.get_at((x, y))
        return tuple(c)[:3] if c[3] else None
    return None


def _set(s, x, y, color):
    if 0 <= x < s.get_width() and 0 <= y < s.get_height():
        s.set_at((x, y), (*color, 255))


def head_top(s) -> int | None:
    """Hàng viền trên cùng của đầu: hàng đầu tiên đủ rộng; ngọn vũ khí giơ lên chỉ rộng một hai điểm nên bị bỏ qua."""
    rows = [y for y in range(U) if sum(1 for x in range(U) if s.get_at((x, y))[3]) >= 6]
    return rows[0] if rows else None


def dress(frame: pygame.Surface, direction: str, st: dict, lying: bool = False) -> pygame.Surface:
    """Vẽ đè trang phục lên một khung 16x16. `lying` là khung ngã xuống: chỉ có mũ phần đỉnh đầu."""
    s = frame.copy()
    y0 = head_top(s)
    if y0 is None:
        return s
    if st.get("coat"):
        _body(s, direction, st, y0, lying)
    if st.get("shoes") and not lying:
        _feet(s, st["shoes"])
    if st.get("gloves"):
        _hands(s, st["gloves"], y0, lying)
    head = st.get("head", "helm")
    if head == "wrap":
        return _wrap(s, direction, st, y0, lying)
    if head == "hair":
        return _hair(s, direction, st, y0, lying)
    if head == "nonla":
        return s if lying else _nonla(s, st, y0)
    if head == "bare":
        return s
    return _helmet(s, direction, st, y0, lying)


def _body(s, direction, st, y0, lying):
    """Áo, quần, thắt lưng, vạt chéo, giáp vảy, áo bông chần."""
    body_from = y0 + (6 if lying else 10)
    for y in range(body_from, U):
        for x in range(U):
            c = _px(s, x, y)
            if c in (SHIRT, SHIRT_DARK):
                _set(s, x, y, st["coat"] if c == SHIRT else st["coat_dark"])
            elif c == SHIRT_LIGHT:
                _set(s, x, y, st["coat_light"])
            elif c == PANTS:
                _set(s, x, y, st["pants"])
    if lying:
        return
    belt_y = y0 + 11
    for x in range(U):
        if _px(s, x, belt_y) in (st["coat"], st["coat_dark"], st["coat_light"], st["pants"]):
            _set(s, x, belt_y, st["belt"])
    if st.get("diagonal") and direction == "down":  # vạt áo cài chéo
        for i, y in enumerate(range(y0 + 10, y0 + 13)):
            if _px(s, 6 + i, y) not in (None, OUTLINE):
                _set(s, 6 + i, y, st["trim"])
    if st.get("scales"):  # giáp vảy: chấm sáng xen kẽ
        for y in range(y0 + 10, U):
            for x in range(U):
                if (x + y) % 2 == 0 and _px(s, x, y) == st["coat"]:
                    _set(s, x, y, st["coat_light"])
    if st.get("quilt"):  # áo bông chần: đường chỉ ngang
        for y in range(y0 + 10, U, 2):
            for x in range(U):
                if _px(s, x, y) == st["coat"]:
                    _set(s, x, y, st["coat_dark"])
    if st.get("leggings"):  # xà cạp: hai hàng dưới cùng của ống quần sáng màu
        for y in (U - 3, U - 2):
            for x in range(U):
                if _px(s, x, y) == st["pants"]:
                    _set(s, x, y, st["leggings"])


def _feet(s, shoes):
    """Giày, dép, ủng: tô lại một hoặc hai hàng điểm dưới cùng của chân."""
    color, rows = shoes
    bottom = max((y for y in range(U) for x in range(U) if _px(s, x, y) not in (None, OUTLINE)), default=None)
    if bottom is None:
        return
    for y in range(bottom - rows + 1, bottom + 1):
        for x in range(U):
            if _px(s, x, y) not in (None, OUTLINE) and _px(s, x, y) not in SKIN:
                _set(s, x, y, color)


def _hands(s, gloves, y0, lying):
    """Găng tay: phần da ở dưới cổ là bàn tay."""
    color, dark = gloves
    for y in range(y0 + (7 if lying else 11), U):
        for x in range(U):
            c = _px(s, x, y)
            if c in SKIN:
                _set(s, x, y, dark if c == (209, 75, 52) else color)


def _hair(s, direction, st, y0, lying):
    """Tóc búi: người Việt xưa để tóc dài vấn lên đỉnh đầu."""
    hair, light = st["hair"], st["hair_light"]
    rows = range(y0 + 1, y0 + (3 if lying else 4)) if direction != "up" else range(y0 + 1, y0 + 9)
    for y in rows:
        for x in range(U):
            if _px(s, x, y) in SKIN:
                _set(s, x, y, light if y == y0 + 1 and 4 <= x <= 6 else hair)
    if direction in ("left", "right") and not lying:  # tóc mai hai bên
        side = (12, 13) if direction == "left" else (2, 3)
        for x in side:
            for y in range(y0 + 3, y0 + 6):
                if _px(s, x, y) in SKIN:
                    _set(s, x, y, hair)
    if not lying:  # búi tóc trên đỉnh
        cx = 7 if direction != "left" else 8
        for x in (cx - 1, cx, cx + 1):
            _set(s, x, y0 - 1, OUTLINE)
        _set(s, cx, y0, hair)
        _set(s, cx - 1, y0, hair)
        _set(s, cx + 1, y0, OUTLINE if direction != "up" else hair)
        _set(s, cx, y0 - 1, light)
    return s


def _nonla(s, st, y0):
    """Nón lá hình chóp, rộng hơn đầu, che xuống ngang trán."""
    straw, dark, light = st["straw"], st["straw_dark"], st["straw_light"]
    top = max(0, y0 - 2)
    brim = y0 + 3
    for y in range(top, brim + 1):
        half = 0.6 + (y - top) * (7.6 / max(1, brim - top))
        lo, hi = round(7.5 - half), round(7.5 + half)
        for x in range(lo, hi + 1):
            edge = x in (lo, hi) or y == top
            col = OUTLINE if edge else (light if x < 7 and y > top + 1 else straw)
            if not edge and (y - top) % 2 == 0 and y != brim:
                col = dark  # vòng nan nón
            _set(s, x, y, col)
    for x in range(0, U):  # vành nón
        if _px(s, x, brim) not in (None,):
            _set(s, x, brim, dark if 0 < x < U - 1 else OUTLINE)
    for x in range(1, U - 1):  # bóng vành nón đổ xuống trán
        if _px(s, x, brim + 1) in SKIN:
            _set(s, x, brim + 1, (190, 110, 70))
    return s


def _helmet(s, direction, st, y0, lying):
    """Mũ: chỉ tô lên phần da đầu nên giữ nguyên đường viền của nhân vật gốc."""
    helm_rows = range(y0 + 1, y0 + (4 if lying else 5))
    back_rows = range(y0 + 1, y0 + 9) if direction == "up" and not lying else ()
    for y in list(helm_rows) + list(back_rows):
        for x in range(U):
            if _px(s, x, y) in SKIN:
                light = y <= y0 + 2 and x <= 7
                _set(s, x, y, st["helm_light"] if light else st["helm"])
    if lying:
        return s
    rim_y = y0 + 4
    xs = [x for x in range(U) if _px(s, x, rim_y) not in (None,)]
    lo, hi = (min(xs), max(xs)) if xs else (0, -1)
    rim = st.get("rim_style", "band")
    if rim == "fur":  # dải lông dày hai hàng, lốm đốm
        for y in (rim_y - 1, rim_y):
            for x in range(lo + 1, hi):
                if _px(s, x, y) not in (None, OUTLINE):
                    _set(s, x, y, st["rim_dark"] if (x * 3 + y) % 4 == 0 else st["rim"])
    elif rim == "brim":  # vành sắt nhô ra hai bên
        for x in range(lo - 1, hi + 2):
            _set(s, x, rim_y, st["rim_dark"] if x in (lo - 1, hi + 1) else st["rim"])
    else:  # viền mũ gọn trong đầu
        for x in range(lo + 1, hi):
            if _px(s, x, rim_y) not in (None, OUTLINE):
                _set(s, x, rim_y, st["rim"])
    if st.get("leaves"):  # lá ngụy trang gài trên mũ
        for x, y in ((4, y0 + 1), (9, y0 + 2), (12, y0 + 3), (6, y0 + 3), (3, y0 + 3), (11, y0 + 1)):
            if _px(s, x, y) in (st["helm"], st["helm_light"]):
                _set(s, x, y, st["rim_dark"])
    if st.get("ribs") and direction in ("down", "up"):  # gân mũ bát
        for x in (5, 10):
            for y in range(y0 + 1, rim_y):
                if _px(s, x, y) in (st["helm"], st["helm_light"]):
                    _set(s, x, y, st["rim_dark"])
    flaps = st.get("flaps")  # tai che bằng lông (Nguyên) hoặc che gáy bằng sắt (Tống)
    if flaps:
        col, dark = (st["rim"], st["rim_dark"]) if flaps == "fur" else (st["helm"], st["rim_dark"])
        sides = {"down": (2, 13), "up": (2, 13), "left": (11, 12, 13), "right": (2, 3, 4)}[direction]
        depth = 3 if flaps == "fur" else 4
        for x in sides:
            for y in range(rim_y + 1, rim_y + 1 + depth):
                if _px(s, x, y) in SKIN:
                    _set(s, x, y, col if y < rim_y + depth else dark)
        if flaps == "guard" and direction == "up":
            for x in range(2, 14):
                if _px(s, x, rim_y + 4) in SKIN:
                    _set(s, x, rim_y + 4, st["rim_dark"])
    cx = 7
    top = st.get("top")
    if top in ("knob", "finial", "tassel", "plume"):
        _set(s, cx, y0 - 1, OUTLINE)
        _set(s, cx + 1, y0 - 1, OUTLINE)
        _set(s, cx, y0, st.get("knob", st["helm"]))
        _set(s, cx + 1, y0, st.get("knob", st["helm"]))
    if top in ("tassel", "plume"):
        plume = st["plume"]
        _set(s, cx, y0 - 2, OUTLINE)
        _set(s, cx + 1, y0 - 2, plume)
        if top == "plume":
            _set(s, cx + 2, y0 - 2, plume)
            _set(s, cx + 1, y0 - 3, plume)
            _set(s, cx + 2, y0 - 3, OUTLINE)
    return s


def _wrap(s, direction, st, y0, lying):
    """Khăn chít đầu: vải quấn quanh nửa trên đầu, có nếp gấp và đuôi khăn thả sau gáy."""
    cloth, dark, light = st["helm"], st["rim_dark"], st["helm_light"]
    rows = range(y0 + 1, y0 + (3 if lying else 5)) if direction != "up" else range(y0 + 1, y0 + 7)
    for y in rows:
        for x in range(U):
            if _px(s, x, y) in SKIN:
                fold = (y - y0) % 2 == 0 and not lying
                _set(s, x, y, dark if fold else (light if y == y0 + 1 and x < 8 else cloth))
    if lying:
        return s
    if direction == "up":  # nút khăn sau gáy và hai đuôi khăn
        for x, y in ((7, y0 + 3), (8, y0 + 3), (7, y0 + 7), (8, y0 + 8)):
            _set(s, x, y, dark)
        _set(s, 7, y0 + 6, cloth)
        _set(s, 8, y0 + 7, cloth)
    elif direction in ("left", "right"):
        tail_x = (12, 13) if direction == "left" else (2, 3)
        for i, x in enumerate(tail_x):
            for y in range(y0 + 4, y0 + 7 - i):
                if _px(s, x, y) in SKIN or _px(s, x, y) == OUTLINE:
                    _set(s, x, y, dark if y == y0 + 6 - i else cloth)
    return s


# ---------------- đồ của người chơi ----------------
HAIR = {"head": "hair", "hair": (40, 32, 30), "hair_light": (78, 64, 58)}
# Áo: màu áo, màu sáng, màu tối, quần, thắt lưng, viền; vảy hoặc đường chần
ARMOR = {
    None: {"coat": None},
    "ao_vai": {"coat": (128, 88, 56), "coat_light": (160, 116, 78), "coat_dark": (94, 62, 40), "pants": (70, 58, 50),
               "belt": (60, 42, 30), "trim": (60, 42, 30)},
    "giap_da": {"coat": (150, 96, 58), "coat_light": (190, 132, 84), "coat_dark": (104, 64, 36), "pants": (66, 54, 48),
                "belt": (52, 34, 22), "trim": (210, 170, 110), "diagonal": True},
    "giap_bong": {"coat": (178, 52, 44), "coat_light": (214, 88, 72), "coat_dark": (124, 32, 28), "pants": (60, 50, 46),
                  "belt": (226, 180, 70), "trim": (226, 180, 70), "quilt": True},
    "giap_vay": {"coat": (118, 124, 136), "coat_light": (178, 184, 194), "coat_dark": (76, 80, 92), "pants": (70, 58, 50),
                 "belt": (176, 48, 40), "trim": (176, 48, 40), "scales": True},
    "giap_dong": {"coat": (174, 122, 58), "coat_light": (232, 186, 92), "coat_dark": (120, 80, 38), "pants": (110, 40, 36),
                  "belt": (150, 40, 36), "trim": (232, 186, 92), "scales": True},
}
HATS = {
    None: HAIR,
    "khan_chit": {"head": "wrap", "helm": (44, 38, 36), "helm_light": (78, 70, 66), "rim_dark": (22, 20, 20)},
    "non_la": {"head": "nonla", "straw": (226, 208, 150), "straw_dark": (186, 162, 104), "straw_light": (246, 234, 190)},
    "mu_da": {"head": "helm", "helm": (128, 84, 52), "helm_light": (166, 114, 74), "rim": (88, 56, 34), "rim_dark": (58, 36, 22),
              "rim_style": "band"},
    "mu_sat": {"head": "helm", "helm": (126, 132, 144), "helm_light": (182, 188, 198), "rim": (226, 180, 70),
               "rim_dark": (166, 122, 40), "rim_style": "brim", "top": "plume", "plume": (214, 44, 40), "knob": (226, 180, 70)},
}
SHOES = {None: None, "dep_rom": ((214, 186, 110), 1), "giay_vai": ((44, 40, 46), 1), "ung_da": ((112, 70, 42), 2)}
GLOVES = {None: None, "bao_tay_vai": ((222, 208, 170), (176, 162, 126)), "gang_da": ((130, 86, 52), (92, 58, 36)),
          "gang_sat": ((156, 162, 172), (102, 108, 120))}
_cache: dict = {}


def hero_style(gear: dict) -> dict:
    st = {}
    st.update(ARMOR.get(gear.get("giap"), ARMOR[None]))
    st.update(HATS.get(gear.get("mu"), HAIR))
    st["shoes"] = SHOES.get(gear.get("giay"))
    st["gloves"] = GLOVES.get(gear.get("gang"))
    return st


class Outfit:
    """Khung hình như sprites.Cast nhưng vẽ theo bộ đồ đang mặc."""

    def __init__(self, gear: dict, scale: int):
        # nhập muộn để công cụ vẽ lính dùng được module này mà không cần nạp asset
        from core import sprites

        st = hero_style(gear)
        walk = sprites.image(f"char/{BASE}/walk.png")
        attack = sprites.image(f"char/{BASE}/attack.png")
        self.walk = {
            d: [sprites.scaled(dress(walk.subsurface((c * U, r * U, U, U)), d, st), scale) for r in range(4)]
            for c, d in enumerate(DIRS)
        }
        self.attack = {d: sprites.scaled(dress(attack.subsurface((c * U, 0, U, U)), d, st), scale) for c, d in enumerate(DIRS)}
        self.dead = sprites.scaled(dress(sprites.image(f"char/{BASE}/dead.png"), "down", st, lying=True), scale)
        self.size = U * scale


def hero_cast(gear: dict, scale: int = 4) -> Outfit:
    """Người chơi theo bộ đồ đang mặc (bỏ qua vũ khí, vũ khí vẽ riêng để còn vung)."""
    key = (tuple(sorted((k, v) for k, v in gear.items() if k in ("giap", "mu", "giay", "gang"))), scale)
    out = _cache.get(key)
    if out is None:
        out = Outfit(gear, scale)
        _cache[key] = out
    return out
