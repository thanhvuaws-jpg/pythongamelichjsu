"""Hình các loại quái không có sẵn trong gói asset: kỵ binh, xe tăng, ụ súng, thuyền, máy bắn đá, xe quân sự.

- Kỵ binh: ghép lính (Mông Cổ, Minh) lên ngựa đen hoặc ngựa nâu của gói Ninja Adventure (CC0).
- Xe tăng: vẽ theo dáng xe tăng hạng nhẹ có tháp pháo, nòng dài, xích hai bên; chỉ có cỗ máy, không vẽ người.
- Ụ súng: vòng bao cát, nòng súng nhô ra; lô cốt: khối bê tông có lỗ châu mai.
- Máy bắn đá thời Tống: giàn gỗ kéo dây, không vẽ người kéo; xe vận tải, xe bọc thép thời chống Pháp: chỉ vẽ cỗ xe.
- Ụ pháo thời chống Pháp: khẩu pháo dã chiến sau dãy bao cát, không vẽ người.

Mọi hình có cùng dạng với sprites.Cast (walk, attack, dead, size) để trận đánh và map dùng như nhân vật thường.
`lift` là số điểm ảnh (khổ 16) mà tay người cưỡi cao hơn tay người đi bộ, để vẽ vũ khí đúng chỗ.
"""

from __future__ import annotations

import pygame

from core import sprites

OUTLINE = (20, 27, 27)
DIRS = ("down", "up", "left", "right")
_cache: dict = {}


class Drawn:
    def __init__(self, walk, attack, dead, size, lift=0, anchored=False):
        self.walk, self.attack, self.dead, self.size = walk, attack, dead, size
        self.lift = lift
        self.anchored = anchored  # công trình, cỗ máy: không bị đẩy lùi, không lướt né


def _scale(s: pygame.Surface, k: int) -> pygame.Surface:
    return pygame.transform.scale(s, (s.get_width() * k, s.get_height() * k))


# ---------------- kỵ binh ----------------
def _rider(char: str, horse: str, scale: int) -> Drawn:
    walk = sprites.image(f"char/{char}/walk.png")
    attack = sprites.image(f"char/{char}/attack.png")
    side = sprites.image(f"animal/horse_{horse}.png") if horse != "brown" else sprites.image("animal/horse.png")
    front = sprites.image(f"animal/horse_{horse}_front.png") if horse != "brown" else sprites.image("animal/horse_front.png")
    sw = side.get_width() // 2
    fw = front.get_width() // 2
    col = {d: c for c, d in enumerate(DIRS)}

    def torso(sheet, d, row=0, attack_sheet=False):
        c = col[d]
        frame = sheet.subsurface((c * 16, 0 if attack_sheet else row * 16, 16, 16))
        return frame.subsurface((0, 0, 16, 13))

    def compose(d, i, body):
        if d in ("left", "right"):
            h = side.subsurface((i * sw, 0, sw, 16))
            if d == "left":
                h = pygame.transform.flip(h, True, False)
            out = pygame.Surface((sw, 24), pygame.SRCALPHA)
            out.blit(h, (0, 8))
            out.blit(body, ((sw - 16) // 2 + (1 if d == "right" else -1), 1 + (i % 2)))
            return out
        h = front.subsurface((i * fw, 0, fw, 16))
        out = pygame.Surface((16, 24), pygame.SRCALPHA)
        if d == "down":  # đầu ngựa ở phía trước người cưỡi
            out.blit(body, (0, 0 + (i % 2)))
            out.blit(h, (0, 8))
        else:
            out.blit(h, (0, 8))
            out.blit(body, (0, 0 + (i % 2)))
        return out

    walk_frames = {d: [_scale(compose(d, r % 2, torso(walk, d, r)), scale) for r in range(4)] for d in DIRS}
    attack_frames = {d: _scale(compose(d, 0, torso(attack, d, attack_sheet=True)), scale) for d in DIRS}
    dead = _scale(sprites.image(f"char/{char}/dead.png"), scale)  # ngã ngựa
    return Drawn(walk_frames, attack_frames, dead, 16 * scale, lift=11)


# ---------------- xe tăng ----------------
OLIVE, OLIVE_D, OLIVE_L = (98, 106, 70), (66, 72, 46), (132, 140, 94)
STEEL, TRACK = (60, 60, 62), (36, 36, 38)


def _tank_side(frame: int, wreck: bool = False) -> pygame.Surface:
    s = pygame.Surface((26, 16), pygame.SRCALPHA)
    body, dark, light = ((70, 64, 58), (40, 36, 32), (96, 86, 76)) if wreck else (OLIVE, OLIVE_D, OLIVE_L)
    pygame.draw.rect(s, OUTLINE, (1, 10, 23, 6), border_radius=3)  # xích
    pygame.draw.rect(s, TRACK, (2, 11, 21, 4), border_radius=2)
    for i, x in enumerate(range(4, 22, 4)):  # bánh xe, xoay theo khung hình
        c = STEEL if (i + frame) % 2 else (90, 90, 92)
        pygame.draw.circle(s, c, (x, 13), 1)
    pygame.draw.rect(s, OUTLINE, (1, 6, 23, 5))  # thân
    pygame.draw.rect(s, body, (2, 7, 21, 3))
    pygame.draw.line(s, light, (2, 7), (22, 7))
    pygame.draw.rect(s, OUTLINE, (7, 2, 10, 5))  # tháp pháo
    pygame.draw.rect(s, dark, (8, 3, 8, 3))
    pygame.draw.line(s, light, (8, 3), (15, 3))
    if not wreck:
        pygame.draw.line(s, OUTLINE, (17, 4), (25, 4), 2)  # nòng pháo
        pygame.draw.line(s, STEEL, (17, 4), (24, 4))
    else:
        for x, y in ((9, 1), (12, 0), (14, 2)):
            s.set_at((x, y), (120, 116, 110))
    return s


def _tank_front(frame: int, back: bool = False) -> pygame.Surface:
    s = pygame.Surface((18, 16), pygame.SRCALPHA)
    for x in (1, 13):  # hai dải xích
        pygame.draw.rect(s, OUTLINE, (x, 6, 4, 10))
        pygame.draw.rect(s, TRACK, (x + 1, 7, 2, 8))
        for y in range(7 + frame % 2, 15, 2):
            s.set_at((x + 1, y), STEEL)
    pygame.draw.rect(s, OUTLINE, (4, 6, 10, 9))
    pygame.draw.rect(s, OLIVE, (5, 7, 8, 7))
    pygame.draw.rect(s, OUTLINE, (5, 2, 8, 6))
    pygame.draw.rect(s, OLIVE_D, (6, 3, 6, 4))
    if not back:  # miệng nòng pháo nhìn thẳng
        pygame.draw.circle(s, OUTLINE, (9, 9), 2)
        s.set_at((9, 9), (10, 10, 10))
    else:
        pygame.draw.line(s, OLIVE_L, (6, 10), (11, 10))
    return s


def _tank(scale: int) -> Drawn:
    walk = {
        "right": [_scale(_tank_side(i), scale) for i in range(4)],
        "left": [pygame.transform.flip(_scale(_tank_side(i), scale), True, False) for i in range(4)],
        "down": [_scale(_tank_front(i), scale) for i in range(4)],
        "up": [_scale(_tank_front(i, True), scale) for i in range(4)],
    }
    attack = {d: walk[d][0] for d in DIRS}
    dead = _scale(_tank_side(0, wreck=True), scale)
    return Drawn(walk, attack, dead, 16 * scale, anchored=True)


# ---------------- ụ súng ----------------
def _gun_nest(scale: int, ruined: bool = False) -> pygame.Surface:
    s = pygame.Surface((22, 14), pygame.SRCALPHA)
    sand, sand_d = (176, 152, 104), (132, 110, 72)
    pygame.draw.ellipse(s, OUTLINE, (0, 2, 22, 12))
    pygame.draw.ellipse(s, (40, 34, 28), (4, 5, 14, 6))  # hố bên trong
    for x, y in ((1, 6), (5, 3), (10, 2), (15, 3), (18, 6), (16, 10), (10, 11), (4, 10)):  # bao cát
        if ruined and (x + y) % 3 == 0:
            continue
        pygame.draw.ellipse(s, OUTLINE, (x - 1, y - 1, 6, 4))
        pygame.draw.ellipse(s, sand, (x, y, 4, 3))
        s.set_at((x + 1, y + 2), sand_d)
    if not ruined:
        pygame.draw.line(s, OUTLINE, (11, 7), (11, 0), 2)  # nòng súng chĩa lên
        pygame.draw.line(s, STEEL, (11, 7), (11, 1))
    return _scale(s, scale)


def _nest(scale: int) -> Drawn:
    img = _gun_nest(scale)
    walk = {d: [img] * 4 for d in DIRS}
    return Drawn(walk, dict.fromkeys(DIRS, img), _gun_nest(scale, True), 16 * scale, anchored=True)


# ---------------- thuyền, tàu (đánh từ trên bờ; chỉ vẽ con thuyền, không vẽ người) ----------------
def _boat_frames(img: pygame.Surface) -> dict[str, list[pygame.Surface]]:
    """Bốn khung nhấp nhô theo sóng, hai chiều trái phải; nhìn trước sau dùng hình ngang."""
    h = img.get_height()
    frames = []
    for dy in (0, 1, 2, 1):
        f = pygame.Surface((img.get_width(), h + 3), pygame.SRCALPHA)
        f.blit(img, (0, dy))
        frames.append(f)
    left = [pygame.transform.flip(f, True, False) for f in frames]
    return {"right": frames, "left": left, "down": frames, "up": left}


def _sinking(img: pygame.Surface) -> pygame.Surface:
    """Thuyền chìm: nghiêng, tối màu, chỉ còn nửa trên mặt nước."""
    tilt = pygame.transform.rotate(img, 14)
    tilt.fill((90, 90, 96), special_flags=pygame.BLEND_RGB_MULT)
    w, h = tilt.get_size()
    return tilt.subsurface((0, 0, w, int(h * 0.62))).copy()


def _junk(scale: int) -> Drawn:
    """Thuyền chiến Nguyên: thân sẫm, buồm nâu đỏ."""
    from core import fleet

    img = fleet.boat_sprite(30 * scale, (150, 136, 150), sail=(150, 62, 50))
    return Drawn(_boat_frames(img), dict.fromkeys(DIRS, img), _sinking(img), 16 * scale, anchored=True)


def _gunboat(scale: int, small: bool = False) -> Drawn:
    """Tàu chiến (hoặc ca nô nhỏ) màu thép: cabin, nòng pháo hoặc súng ở mũi."""
    from core import fleet

    width = (22 if small else 34) * scale
    img = fleet.boat_sprite(width, (124, 128, 136))
    w, h = img.get_size()
    cab_w, cab_h = (w // 4, h // 5) if small else (w // 3, h // 4)
    cab = pygame.Rect(w // 2 - cab_w // 2, h // 2 - cab_h, cab_w, cab_h)
    pygame.draw.rect(img, (38, 38, 42), cab.inflate(4, 4))
    pygame.draw.rect(img, (112, 116, 124), cab)
    pygame.draw.rect(img, (70, 110, 140), (cab.x + 4, cab.y + 4, cab.w - 8, max(3, cab.h // 4)))  # cửa kính
    gun_len = w // 6 if small else w // 4
    pygame.draw.line(img, (38, 38, 42), (cab.right, cab.y + cab.h // 2), (cab.right + gun_len, cab.y + cab.h // 2 - scale * 2), max(2, scale))
    if not small:
        pygame.draw.rect(img, (60, 60, 66), (cab.x + cab.w // 3, cab.y - scale * 4, scale * 3, scale * 4))  # ống khói
    return Drawn(_boat_frames(img), dict.fromkeys(DIRS, img), _sinking(img), 16 * scale, anchored=True)


def _grain_boat(scale: int, hull=(168, 146, 112), sail=(200, 182, 136)) -> Drawn:
    """Thuyền lương: trên boong chất bao lương. Thuyền Minh thân nâu nhạt buồm vải; thuyền Nguyên thân sẫm buồm nâu đỏ như
    thuyền chiến Nguyên để người chơi nhận ra cùng một đoàn."""
    from core import fleet

    img = fleet.boat_sprite(28 * scale, hull, sail=sail)
    w, h = img.get_size()
    deck = int(h * 0.66)  # mép boong
    xs = range(w // 6, w * 5 // 6 - 3 * scale, 4 * scale)
    for i, x in enumerate(xs):
        r = pygame.Rect(x, deck - 3 * scale - (i % 2) * scale, 5 * scale, 3 * scale)
        pygame.draw.ellipse(img, OUTLINE, r.inflate(scale, scale))
        pygame.draw.ellipse(img, (218, 200, 152), r)
        pygame.draw.line(img, (170, 150, 104), (r.centerx, r.y + scale), (r.centerx, r.bottom - scale), max(1, scale // 2))
    return Drawn(_boat_frames(img), dict.fromkeys(DIRS, img), _sinking(img), 16 * scale, anchored=True)


# ---------------- máy bắn đá thời Tống: giàn gỗ, cần dài, dây kéo; chỉ vẽ cỗ máy ----------------
WOOD, WOOD_D, WOOD_L = (138, 98, 58), (92, 62, 36), (176, 132, 84)
STONE = (128, 124, 116)


def _beam(s, a, b, color=WOOD, w=3):
    pygame.draw.line(s, OUTLINE, a, b, w)
    pygame.draw.line(s, color, a, b, max(1, w - 2))


def _catapult_img(thrown: bool = False, broken: bool = False) -> pygame.Surface:
    """Nhìn ngang: đế gỗ, khung chữ A, cần dài xoay quanh trục. Lúc nghỉ đầu dài hạ thấp có túi đá; lúc bắn cần hất lên."""
    s = pygame.Surface((26, 22), pygame.SRCALPHA)
    if broken:
        for a, b in (((2, 21), (22, 18)), ((6, 21), (13, 13)), ((15, 21), (24, 15)), ((3, 16), (12, 21))):
            _beam(s, a, b, WOOD_D)
        return s
    pygame.draw.rect(s, OUTLINE, (1, 18, 24, 4))
    pygame.draw.rect(s, WOOD_D, (2, 19, 22, 2))
    _beam(s, (6, 19), (13, 8))
    _beam(s, (20, 19), (13, 8))
    _beam(s, (9, 14), (17, 14), WOOD_D, 2)
    if not thrown:
        long_end, short_end = (2, 16), (19, 3)
        _beam(s, long_end, short_end, WOOD_L)
        pygame.draw.circle(s, OUTLINE, (3, 18), 2)
        pygame.draw.circle(s, STONE, (3, 18), 1)
    else:
        long_end, short_end = (23, 1), (8, 12)
        _beam(s, long_end, short_end, WOOD_L)
        pygame.draw.line(s, (70, 52, 34), long_end, (25, 6))  # túi đá đã buông
    for dx in (0, 2):  # dây kéo buông từ đầu ngắn xuống đất
        pygame.draw.line(s, (96, 74, 48), (short_end[0] + dx, short_end[1]), (short_end[0] + dx + 2, 18))
    pygame.draw.circle(s, OUTLINE, (13, 8), 2)
    s.set_at((13, 8), WOOD_L)
    return s


def _catapult(scale: int) -> Drawn:
    rest = _scale(_catapult_img(), scale)
    shot = _scale(_catapult_img(thrown=True), scale)
    flip = pygame.transform.flip
    walk = {"right": [rest] * 4, "left": [flip(rest, True, False)] * 4, "down": [rest] * 4, "up": [flip(rest, True, False)] * 4}
    attack = {"right": shot, "left": flip(shot, True, False), "down": shot, "up": flip(shot, True, False)}
    return Drawn(walk, attack, _scale(_catapult_img(broken=True), scale), 16 * scale, anchored=True)


# ---------------- xe quân sự thời chống Pháp: xe vận tải, xe bọc thép; chỉ vẽ cỗ xe ----------------
CANVAS = (124, 118, 84)


def _wheels(s, xs, y, frame, r=2):
    for i, x in enumerate(xs):
        pygame.draw.circle(s, OUTLINE, (x, y), r + 1)
        pygame.draw.circle(s, TRACK, (x, y), r)
        s.set_at((x + (1 if (i + frame) % 2 else -1), y), (110, 110, 112))


def _truck_side(frame: int, wreck: bool = False) -> pygame.Surface:
    """Xe vận tải nhìn ngang: thùng sau phủ bạt, cabin phía trước có kính."""
    s = pygame.Surface((28, 16), pygame.SRCALPHA)
    body, dark = ((72, 66, 60), (44, 40, 36)) if wreck else (OLIVE, OLIVE_D)
    pygame.draw.rect(s, OUTLINE, (1, 10, 26, 3))  # khung gầm
    if not wreck:
        pygame.draw.rect(s, OUTLINE, (1, 2, 17, 9), border_top_left_radius=4, border_top_right_radius=4)  # bạt
        pygame.draw.rect(s, CANVAS, (2, 3, 15, 7), border_top_left_radius=3, border_top_right_radius=3)
        for x in (6, 11):
            pygame.draw.line(s, (96, 92, 64), (x, 3), (x, 9))
    else:  # bạt cháy mất, chỉ còn khung
        for x in (3, 9, 15):
            pygame.draw.line(s, OUTLINE, (x, 4), (x, 10))
    pygame.draw.rect(s, OUTLINE, (18, 4, 7, 7))  # cabin
    pygame.draw.rect(s, body, (19, 5, 5, 5))
    pygame.draw.rect(s, (70, 110, 140) if not wreck else dark, (20, 5, 3, 2))  # kính
    pygame.draw.rect(s, OUTLINE, (24, 7, 4, 4))  # mũi xe
    pygame.draw.rect(s, dark, (25, 8, 2, 2))
    _wheels(s, (5, 10, 22), 13, frame)
    return s


def _truck_front(frame: int, back: bool = False) -> pygame.Surface:
    s = pygame.Surface((18, 16), pygame.SRCALPHA)
    if back:
        pygame.draw.rect(s, OUTLINE, (2, 2, 14, 10), border_top_left_radius=4, border_top_right_radius=4)
        pygame.draw.rect(s, CANVAS, (3, 3, 12, 8), border_top_left_radius=3, border_top_right_radius=3)
    else:
        pygame.draw.rect(s, OUTLINE, (3, 3, 12, 9))
        pygame.draw.rect(s, OLIVE, (4, 4, 10, 7))
        pygame.draw.rect(s, (70, 110, 140), (5, 5, 8, 2))
        for x in (5, 12):
            s.set_at((x, 9), (240, 226, 160))  # đèn pha
    pygame.draw.rect(s, OUTLINE, (2, 11, 14, 2))
    for x in (3, 14):
        pygame.draw.rect(s, OUTLINE, (x - 1, 12, 3, 4))
        pygame.draw.rect(s, TRACK, (x, 13 + frame % 2, 1, 2))
    return s


def _car_side(frame: int, wreck: bool = False) -> pygame.Surface:
    """Xe bọc thép bánh lốp nhìn ngang: thân thấp vát mũi, tháp nhỏ có nòng súng."""
    s = pygame.Surface((28, 16), pygame.SRCALPHA)
    body, dark, light = ((72, 66, 60), (44, 40, 36), (96, 88, 78)) if wreck else (OLIVE, OLIVE_D, OLIVE_L)
    hull = [(2, 6), (21, 6), (26, 9), (26, 11), (2, 11)]
    pygame.draw.polygon(s, OUTLINE, [(x + (1 if x > 14 else -1), y + (-1 if y < 9 else 1)) for x, y in hull])
    pygame.draw.polygon(s, body, hull)
    pygame.draw.line(s, light, (3, 7), (20, 7))
    pygame.draw.rect(s, OUTLINE, (9, 2, 9, 5))  # tháp
    pygame.draw.rect(s, dark, (10, 3, 7, 3))
    if not wreck:
        pygame.draw.line(s, OUTLINE, (17, 4), (25, 4), 2)  # nòng súng
        pygame.draw.line(s, STEEL, (17, 4), (24, 4))
    _wheels(s, (6, 13, 21), 13, frame)
    return s


def _car_front(frame: int, back: bool = False) -> pygame.Surface:
    s = pygame.Surface((18, 16), pygame.SRCALPHA)
    pygame.draw.rect(s, OUTLINE, (2, 6, 14, 7))
    pygame.draw.rect(s, OLIVE, (3, 7, 12, 5))
    pygame.draw.rect(s, OUTLINE, (5, 2, 8, 5))
    pygame.draw.rect(s, OLIVE_D, (6, 3, 6, 3))
    if not back:
        pygame.draw.circle(s, OUTLINE, (9, 5), 1)
        pygame.draw.line(s, OLIVE_D, (4, 10), (13, 10))
    for x in (2, 15):
        pygame.draw.rect(s, OUTLINE, (x - 1, 11, 3, 5))
        pygame.draw.rect(s, TRACK, (x, 12 + frame % 2, 1, 3))
    return s


def _vehicle(side, front, scale: int) -> Drawn:
    flip = pygame.transform.flip
    walk = {
        "right": [_scale(side(i), scale) for i in range(4)],
        "left": [flip(_scale(side(i), scale), True, False) for i in range(4)],
        "down": [_scale(front(i), scale) for i in range(4)],
        "up": [_scale(front(i, True), scale) for i in range(4)],
    }
    attack = {d: walk[d][0] for d in DIRS}
    return Drawn(walk, attack, _scale(side(0, wreck=True), scale), 16 * scale, anchored=True)


# ---------------- ụ pháo thời chống Pháp: khẩu pháo dã chiến sau vòng bao cát; chỉ vẽ khẩu pháo ----------------
def _cannon(fired: bool = False, ruined: bool = False) -> pygame.Surface:
    """Nhìn ngang, nòng chĩa sang phải: càng pháo chống xuống đất phía sau, bánh xe lớn, tấm chắn, nòng dài ngóc lên; phía
    trước là hai lớp bao cát. Lúc bắn nòng giật lùi, đầu nòng loé sáng."""
    s = pygame.Surface((30, 20), pygame.SRCALPHA)
    sand, sand_d, sand_l = (176, 152, 104), (132, 110, 72), (204, 184, 136)
    body, dark, light = ((70, 64, 58), (40, 36, 32), (96, 86, 76)) if ruined else (OLIVE, OLIVE_D, OLIVE_L)
    pygame.draw.line(s, OUTLINE, (1, 18), (12, 12), 4)  # càng pháo
    pygame.draw.line(s, dark, (2, 17), (12, 12), 2)
    if not ruined:
        back = 1 if fired else 0
        root, tip = (12 - back, 10 + back), (27 - back, 3 + back)
        pygame.draw.line(s, OUTLINE, root, tip, 5)  # nòng
        pygame.draw.line(s, body, root, tip, 3)
        pygame.draw.line(s, light, (root[0], root[1] - 1), (tip[0] - 1, tip[1] - 1))
        pygame.draw.rect(s, OUTLINE, (tip[0] - 1, tip[1] - 2, 3, 4))  # đầu nòng
        pygame.draw.line(s, OUTLINE, (12, 12), (20, 8), 3)  # ống hãm lùi dưới nòng
        pygame.draw.line(s, dark, (12, 12), (20, 8))
        if fired:
            pygame.draw.circle(s, (250, 210, 110), (28, 2), 2)
            pygame.draw.circle(s, (255, 248, 220), (28, 2), 1)
            pygame.draw.circle(s, (200, 196, 186), (25, 1), 1)
    else:
        pygame.draw.line(s, OUTLINE, (12, 11), (22, 16), 5)  # nòng gãy gục xuống
        pygame.draw.line(s, body, (12, 11), (22, 16), 3)
        for x, y, r in ((15, 5, 2), (18, 3, 2), (13, 2, 1)):  # khói
            pygame.draw.circle(s, (78, 74, 70), (x, y), r)
    pygame.draw.rect(s, OUTLINE, (13, 4, 6, 10))  # tấm chắn
    pygame.draw.rect(s, body, (14, 5, 4, 8))
    pygame.draw.line(s, light, (14, 5), (17, 5))
    pygame.draw.circle(s, OUTLINE, (12, 15), 5)  # bánh xe
    pygame.draw.circle(s, TRACK, (12, 15), 4)
    for a, b in (((9, 15), (15, 15)), ((12, 12), (12, 18)), ((10, 13), (14, 17)), ((10, 17), (14, 13))):
        pygame.draw.line(s, STEEL, a, b)
    pygame.draw.circle(s, (120, 120, 116), (12, 15), 1)
    for row, (y, xs) in enumerate(((16, range(17, 30, 4)), (13, range(19, 28, 4)))):  # hai lớp bao cát phía trước
        for i, x in enumerate(xs):
            if ruined and (i + row) % 2:
                continue
            pygame.draw.ellipse(s, OUTLINE, (x - 1, y - 1, 6, 5))
            pygame.draw.ellipse(s, sand, (x, y, 4, 3))
            s.set_at((x + 1, y), sand_l)
            s.set_at((x + 2, y + 2), sand_d)
    return s


def _artillery(scale: int) -> Drawn:
    flip = pygame.transform.flip
    img, shot = _scale(_cannon(), scale), _scale(_cannon(fired=True), scale)
    walk = {"right": [img] * 4, "left": [flip(img, True, False)] * 4, "down": [img] * 4, "up": [flip(img, True, False)] * 4}
    attack = {"right": shot, "left": flip(shot, True, False), "down": shot, "up": flip(shot, True, False)}
    return Drawn(walk, attack, _scale(_cannon(ruined=True), scale), 16 * scale, anchored=True)


FACTORIES = {
    "ThuyenNguyen": _junk,
    "ThuyenLuongNguyen": lambda k: _grain_boat(k, (150, 136, 150), (150, 62, 50)),
    "UPhao": _artillery,
    "TuongKyMinh": lambda k: _rider("TuongMinh", "brown", k),
    "ThuyenLuongMinh": _grain_boat,
    "MayBanDa": _catapult,
    "XeVanTai": lambda k: _vehicle(_truck_side, _truck_front, k),
    "XeBocThep": lambda k: _vehicle(_car_side, _car_front, k),
    "TauChien": _gunboat,
    "CaNo": lambda k: _gunboat(k, small=True),
    "KyBinhMongCo": lambda k: _rider("LinhNguyen", "black", k),
    "TuongKyMongCo": lambda k: _rider("TuongNguyen", "black", k),
    "KyBinhMinh": lambda k: _rider("LinhMinh", "brown", k),
    "XeTang": _tank,
    "USung": _nest,
}


def has(char: str) -> bool:
    return char in FACTORIES


def cast(char: str, scale: int = 4) -> Drawn:
    key = (char, scale)
    out = _cache.get(key)
    if out is None:
        out = FACTORIES[char](scale)
        _cache[key] = out
    return out
