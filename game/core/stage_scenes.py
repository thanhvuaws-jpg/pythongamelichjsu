"""Kịch bản từng nhịp hồi ức, khoá theo thẻ `"stage"` trong nội dung.

Nguyên tắc: cảnh chỉ minh hoạ đúng những gì lời kể (đã có nguồn) nói tới, không thêm tình tiết. Nhãn chữ chỉ ghi địa danh,
mốc thời gian hoặc cụm từ có sẵn trong lời kể. Cảnh thời hiện đại không vẽ máu, không vẽ người ngã xuống, giống phần
trận đánh, để trân trọng những người đã hy sinh; không vẽ hình nhân vật lịch sử hiện đại. Các mốc thời gian dồn trong
khoảng 6 đến 8 giây đầu, đủ cho người đọc nhanh vẫn thấy diễn biến chính.
"""

from __future__ import annotations

import math
import random

import pygame

from core import sprites
from core.cinematic import turtle_sprite
from core.stage import (
    ELDERS,
    FRENCH,
    PEOPLE,
    VIET_MINH,
    Actor,
    Stage,
    bac_bo_phu,
    banner_six,
    bike,
    bunker,
    cached,
    cannon,
    chicken,
    dinh_lang,
    drum,
    flag_frames,
    glow,
    gunboat,
    horse,
    icon,
    opera_house,
    orange,
    podium,
    prop,
)

BEATS: dict[str, tuple[str, object]] = {}
DIRT = [(96, 70, 44), (120, 92, 60), (80, 58, 36)]
SPARK = [(255, 236, 170), (255, 196, 90)]
WARM = (255, 210, 120)


def beat(key: str, bg: str):
    def deco(fn):
        BEATS[key] = (bg, fn)
        return fn

    return deco


# ----- hình nhỏ dùng riêng ở vài cảnh -----
def _plank_bridge() -> pygame.Surface:
    def build():
        low = pygame.Surface((34, 12), pygame.SRCALPHA)
        pygame.draw.rect(low, (40, 28, 20), (0, 3, 34, 7))
        pygame.draw.rect(low, (150, 116, 76), (1, 4, 32, 5))
        for x in range(3, 34, 4):
            pygame.draw.line(low, (96, 70, 44), (x, 4), (x, 8))
        for x in (2, 31):
            pygame.draw.rect(low, (40, 28, 20), (x, 8, 2, 4))
        return sprites.sepia(sprites.scaled(low, 4))

    return cached("plank_bridge", build)


def _note() -> pygame.Surface:
    def build():
        low = pygame.Surface((7, 9), pygame.SRCALPHA)
        pygame.draw.ellipse(low, (250, 214, 110), (0, 5, 4, 4))
        pygame.draw.line(low, (250, 214, 110), (3, 6), (3, 0))
        pygame.draw.line(low, (250, 214, 110), (3, 0), (6, 2))
        return sprites.scaled(low, 3)

    return cached("note", build)


def _window() -> pygame.Surface:
    def build():
        s = pygame.Surface((14, 16), pygame.SRCALPHA)
        s.fill((255, 214, 120, 230))
        pygame.draw.rect(s, (120, 80, 40), s.get_rect(), 2)
        return s

    return cached("window", build)


def _wall_piece() -> pygame.Surface:
    return prop("luy_dat")  # Cổ Loa là thành đất


# ----- trợ giúp kịch bản -----
def _flags(d: Stage, items: list[Actor], every=5, kind="ta", start=2):
    for a in items[start::every]:
        d.flag(0, 0, kind, follow=a)


def _alerts(d: Stage, items, t0, t1=None, step=3):
    for a in items[::step]:
        d.carry(a, icon("emote_alert", 3, True), dy=-56, t_in=t0, t_out=t1, layer=1, pop=True)


def _sparks_from(d: Stage, items, t0, t1, period=0.16, dy=-30, toward=1):
    """Chớp lửa đầu nòng súng, chỉ có ánh sáng, không vẽ người trúng đạn."""

    def flash():
        alive = [a for a in items if a.visible(d.t)]
        if alive:
            x, y = random.choice(alive).pos(d.t)
            d.fx.burst(x + 18 * toward, y + dy, 4, SPARK, 160, 0.16, 3, 0, kind="spark")

    d.every(t0, t1, period, flash)


def _bonfire_halo(d: Stage, x, y, r=60, t_in=0.0, t_out=None):
    d.thing(glow(r, (255, 170, 80), 80), x, y, layer=1, anchor="center", t_in=t_in, t_out=t_out)


def _along(points, t0, t1):
    """Đặt các mốc thời gian dọc một đường gấp khúc, đi đều từ t0 tới t1."""
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:], strict=False)]
    total = sum(lengths) or 1.0
    speed = total / max(0.1, t1 - t0)
    return speed, total, lengths


def _partial(points, lengths, dist):
    out = [points[0]]
    left = dist
    for (a, b), seg in zip(zip(points, points[1:], strict=False), lengths, strict=False):
        if left >= seg:
            out.append(b)
            left -= seg
            continue
        k = left / seg if seg else 0
        out.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
        break
    return out


# =========================== Màn 1: Ngô Quyền đến nhà Trần ===========================
@beat("ai_chau:join", "san_dien")
def _join(d: Stage):
    d.label("Ái Châu", 150, 80, 0.3)
    d.actor("Noble", 640, 246, "down", scale=4)
    d.actor(d.ally[0], 560, 240, "down")
    d.actor(d.ally[0], 720, 240, "down")
    d.troop(("Master", "Monk2", "OldMan3"), 250, 300, 3, 3, (52, 46), "right")
    d.troop(("Master", "Monk2", "OldMan3"), 930, 300, 3, 3, (52, 46), "left")
    ngo = d.actor(d.ally_lead, 520, 470, "up", scale=4)
    d.path([ngo], 0.5, [(600, 420), (640, 352)], 90)
    d.kneel([ngo], 2.4, 4.0)
    bride = d.actor("Princess", 760, 244, "down", scale=4, t_in=3.8)
    d.path([bride], 4.0, [(724, 320), (700, 352)], 70)
    d.face([ngo], 5.4, "right")
    d.face([bride], 5.4, "left")
    d.label("Được gả con gái, giao giữ Ái Châu", 640, 140, 5.6)


@beat("ai_chau:drive_931", "thanh")
def _drive(d: Stage):
    d.label("Năm 931", 150, 80, 0.3)
    d.flag(700, 206, "dich", t_out=5.6)
    d.flag(700, 206, "ta", t_in=5.6, pop=True)
    foe = d.troop(d.foe, 760, 300, 4, 3, (44, 40), "left", "dich")
    ally = d.troop(d.ally, -260, 300, 5, 3, (44, 40), "right")
    _flags(d, ally)
    d.shift(ally, 0.3, 700, 0, 210)
    d.shift(foe, 2.8, -50, 0, 80)
    d.volley(ally[-5:], 760, 920, 290, 400, 1.2, 3.6, 0.22)
    d.fight(ally, 3.7, 5.6)
    d.fight(foe, 3.7, 5.2)
    d.clash(650, 730, 300, 410, 3.7, 5.2)
    d.fall(foe[:3], 4.2, 0.35)
    d.shift(foe[3:], 5.2, 900, 0, 230)
    d.cheer(ally, 6.0)
    d.label("Đuổi thứ sử Nam Hán", 640, 130, 5.8)


@beat("ai_chau:betray", "san_dien")
def _betray(d: Stage):
    d.label("Năm 937", 150, 80, 0.3)
    d.dim(0, 0, 0.35, 0.35)
    lord = d.actor("Noble", 640, 262, "down", scale=4)
    kieu = d.actor("NinjaGray", 1000, 330, "left", scale=4)
    d.path([kieu], 0.4, [(820, 320), (704, 272)], 170)
    d.fight([kieu], 2.0, 2.5)
    d.fall([lord], 2.2, principal=True)
    d.shake(2.2, 6)
    d.sound(2.2, "chem")
    d.fire(520, 200, 2.8)
    d.fire(760, 200, 3.1)
    d.dim(2.6, 3.6, 0.35, 0.5)
    army = d.troop(d.ally, -330, 330, 6, 3, (44, 38), "right", t_in=3.8)
    _flags(d, army, 6)
    d.shift(army, 3.9, 440, 0, 170)
    d.face([kieu], 4.6, "left")
    d.label("Ngô Quyền từ Ái Châu kéo quân ra hỏi tội", 420, 140, 4.6)


@beat("bien:nam_han", "bien")
def _nam_han(d: Stage):
    d.waves(60, 470, 16, -24)
    hull, crew = d.boat(240, 330, "dan", 110, "right", ("NinjaGray",))
    d.shift([hull, *crew], 0.3, 1200, 0, 300)
    d.label("Sang cầu cứu Nam Hán", 640, 110, 0.6, t_out=3.4)
    fleet = []
    for x, y in ((1380, 230), (1540, 230), (1700, 230), (1440, 380), (1600, 380), (1760, 380)):
        h, c = d.boat(x, y, "dich", 150, "left", (d.foe[0], d.foe_lead, d.foe[0]), sail=True, t_in=3.0)
        fleet += [h, *c]
    d.shift(fleet, 3.2, -900, 0, 130)
    d.label("Lưu Hoằng Tháo đem thuyền chiến sang", 640, 110, 3.8)


# =========================== Nhà Lý chống Tống ===========================
@beat("tong:raid", "thanh")
def _raid(d: Stage):
    d.label("Cuối năm 1075", 160, 80, 0.3)
    foe = d.troop(d.foe, 580, 290, 4, 2, (48, 40), "left", "dich")
    ally = d.troop(d.ally, -300, 300, 6, 3, (44, 38), "right")
    _flags(d, ally, 6)
    d.shift(ally, 0.3, 600, 0, 220)
    d.volley(ally, 520, 780, 180, 250, 0.8, 3.4, 0.2)
    for i, (x, name) in enumerate(((300, "Khâm Châu"), (640, "Liêm Châu"), (980, "Ung Châu"))):
        d.fire(x + (40 if i == 1 else 0), 250, 1.8 + i * 0.9)
        d.label(name, x, 120, 1.8 + i * 0.9)
    d.fight(ally, 3.2, 5.0)
    d.fight(foe, 3.2, 4.6)
    d.clash(540, 620, 290, 380, 3.2, 4.6)
    d.fall(foe[:3], 3.8, 0.3)
    d.shift(foe[3:], 4.6, 900, 0, 230)
    d.shift(ally, 5.6, -900, 0, 170)
    d.label("Phá xong thì rút về", 640, 180, 5.8, "dark")


def _song_bank(d: Stage) -> list[Actor]:
    return d.troop(d.foe, 110, 116, 16, 1, (68, 0), "down", "dich", jitter=8)


def _pontoon(d: Stage, t0, t1, x=600):
    def draw(s, t, ox, oy):
        k = max(0.0, min(1.0, (t - t0) / max(0.1, t1 - t0)))
        if k <= 0:
            return
        y_top, y_bot = 124, 124 + 132 * k
        for y in range(int(y_top), int(y_bot), 14):
            pygame.draw.rect(s, (40, 28, 20), (x - 40 + ox, y + oy, 80, 12))
            pygame.draw.rect(s, (156, 126, 88), (x - 38 + ox, y + 2 + oy, 76, 8))

    d.paint(draw, -1)


@beat("nhu_nguyet:cross", "nhu_nguyet")
def _cross(d: Stage):
    d.label("Sông Như Nguyệt", 640, 190, 0.3, t_out=2.2)
    d.waves(132, 250, 6, 20)
    _song_bank(d)
    ly = d.troop(d.ally, 110, 360, 12, 2, (68, 50), "up")
    _flags(d, ly, 7, start=3)
    _pontoon(d, 0.5, 2.0)
    for start, end in ((2.0, 5.4), (6.4, 9.6)):
        wave = d.troop(d.foe, 570, 100, 2, 3, (36, 30), "down", "dich", t_in=start)
        arrive = d.shift(wave, start + 0.2, 0, 170, 110)
        front = ly[6:10]
        d.shift(front, arrive - 0.6, 0, -24, 80)
        d.fight(wave, arrive, end)
        d.fight(front, arrive, end)
        d.clash(560, 660, 280, 340, arrive, end)
        d.volley(ly[12:], 540, 660, 150, 260, start + 0.3, end, 0.22)
        if start < 5:
            d.fall(wave[:2], arrive + 0.8, 0.3, away=(0, -1))
        d.shift(wave[2:] if start < 5 else wave, end, 0, -230, 150)
        d.shift(front, end + 0.2, 0, 24, 60)
    d.label("Vượt sông mấy lần đều bị đánh bật lại", 640, 190, 5.6)


@beat("nhu_nguyet:poem", "nhu_nguyet")
def _poem(d: Stage):
    d.dim(0, 0, 0.55, 0.55)
    d.waves(132, 250, 6, 12)
    song = _song_bank(d)
    ly = d.troop(d.ally, 90, 370, 12, 2, (68, 48), "up")
    halo = d.thing(glow(80, WARM, 120), 1088, 372, layer=1, anchor="center")
    halo.beat = (2.0, 0.12)

    def rings(s, t, ox, oy):
        if t < 0.8:
            return
        for k in range(3):
            age = (t - 0.8 + k * 0.7) % 2.1
            r = int(30 + age * 150)
            a = max(0, int(150 * (1 - age / 2.1)))
            size = (r // 6 * 6 + 6) * 2 + 4
            ring = cached(("ring", size), lambda size=size: pygame.Surface((size, size), pygame.SRCALPHA))
            ring.fill((0, 0, 0, 0))
            pygame.draw.circle(ring, (255, 220, 140, a), (size // 2, size // 2), r, 2)
            s.blit(ring, ring.get_rect(center=(1088 + ox, 372 + oy)))

    d.paint(rings, 1)
    scroll = d.thing(icon("scroll", 3, True), 1088, 330, layer=1, t_in=0.8, pop=True)
    scroll.track.go(0.8, 1088, 250, 30)
    scroll.bob = 3
    d.label("Đền thờ bên sông", 1088, 220, 0.6, t_out=3.0)
    d.face(ly, 0.9, "right")
    d.face(ly, 2.8, "up")
    d.cheer(ly, 3.0)
    _alerts(d, song, 3.2)
    d.shift(song, 3.4, 0, -14, 20)
    d.kneel(song[1::2], 4.0)
    d.label("Quân ta thêm hăng, quân Tống rụng rời", 640, 190, 4.4, "dark")


@beat("nhu_nguyet:counter", "nhu_nguyet")
def _nn_counter(d: Stage):
    d.label("Bến Như Nguyệt", 640, 190, 0.3, t_out=2.4)
    d.waves(132, 250, 6, 20)
    song = _song_bank(d)
    landing = []
    for x in (300, 640, 980):
        h, c = d.boat(x, 248, "ta", 120, "right", (d.ally[0], d.ally_lead, d.ally[0]))
        d.shift([h, *c], 0.4, 0, -88, 60)
        landing += c
    d.shift(landing, 2.0, 0, -26, 60)
    ly = d.troop(d.ally, 90, 380, 12, 2, (68, 48), "up")
    d.volley(ly, 100, 1180, 70, 120, 0.6, 3.6, 0.16)
    d.fight(landing, 2.5, 5.6)
    d.fight(song, 2.5, 5.2)
    d.clash(200, 1080, 96, 140, 2.5, 5.2, 0.22)
    d.fall(song[::2], 3.1, 0.15, away=(0, -1))
    d.shift(song[1::2], 4.4, 0, -220, 150)
    d.cheer(ly, 4.6)
    d.smoke(100, 1180, 40, 120, 4.8)
    d.label("Khí hậu độc, bệnh tật lan tràn, lương dần cạn", 640, 190, 5.6, "dark")


# =========================== Nhà Trần chống Mông - Nguyên ===========================
@beat("ha_song:ask", "song")
def _ask(d: Stage):
    d.label("Năm 1258", 150, 80, 0.3)
    d.waves(132, 316, 8, -20)
    d.smoke(0, 1280, 30, 110, 0.0, None, 0.25)
    hb, hieu = d.boat(560, 212, "dan", 120, "left", ("Master",))
    do = [d.actor("OldMan3", 1040, 360, "up"), d.actor(d.ally[0], 1090, 368, "up")]  # trên bờ: sử không ghi ông ở trên thuyền
    kb, king = d.boat(-140, 296, "ta", 150, "right", ("Noble", d.ally[0]))
    d.shift([kb, *king], 0.3, 600, 0, 230)
    d.label("Thái uý Nhật Hiệu", 560, 120, 1.6, t_out=4.2)
    d.label("“nhập Tống”", 560, 168, 2.8, "dark", t_out=4.4)
    d.shift([kb, *king], 4.4, 420, 0, 200)
    d.label("Thái sư Trần Thủ Độ", 1040, 120, 5.4)
    d.carry(do[0], icon("emote_talk", 3, True), dy=-58, t_in=6.2, layer=1, pop=True)


@beat("dong_bo_dau:counter", "song")
def _dbd(d: Stage):
    d.label("Đông Bộ Đầu", 150, 80, 0.3)
    d.waves(132, 316, 8, 24)
    for x in (760, 900, 1040, 1180):
        d.thing(prop("tent", 2), x, 388)
    foe = d.troop(d.foe, 760, 384, 7, 2, (60, 44), "left", "dich")
    landers = []
    for x, y in ((-200, 230), (-420, 230), (-300, 300), (-520, 300)):
        h, c = d.boat(x, y, "ta", 120, "right", (d.ally[0], d.ally_lead, d.ally[0]))
        d.shift([h, *c], 0.3, 560, 0, 260)
        landers += c
    d.shift(landers, 2.5, 140, 120, 140)
    d.shift(landers, 3.8, 190, 0, 170)
    d.fight(landers, 4.9, 6.4)
    d.fight(foe, 4.6, 6.0)
    d.clash(690, 790, 330, 440, 4.9, 6.0)
    d.fall(foe[:4], 5.4, 0.25)
    d.shift(foe[4:], 6.0, 700, -40, 230)
    d.cheer(landers, 6.6)
    d.label("Ít ngày sau đã lấy lại kinh thành", 640, 150, 6.6)


@beat("binh_than:orange", "song")
def _orange(d: Stage):
    d.label("Bến Bình Than, năm 1282", 200, 80, 0.3)
    d.waves(132, 316, 8, -14)
    d.boat(640, 262, "ta", 280, "right", ("Noble", "Master", "OldMan3", "Master", d.ally[0]))
    d.label("Vua và các vương hầu bàn việc nước", 640, 110, 0.6, t_out=3.4)
    guards = [d.actor(d.ally[0], 600, 400, "down"), d.actor(d.ally[0], 680, 400, "down")]
    boy = d.actor("Boy", 180, 452, "right", scale=4)
    d.path([boy], 0.3, [(560, 452), (630, 444)], 170)
    d.face([boy], 3.0, "up")
    d.fight(guards, 3.0, 3.6)
    d.shift([boy], 3.7, -60, 10, 60)
    servant = d.actor("Villager4", 640, 300, "down", t_in=4.2)
    d.path([servant], 4.2, [(600, 420)], 110)
    d.carry(servant, orange(), dy=-30, dx=14, t_in=4.2, t_out=5.5)
    d.carry(boy, orange(), dy=-34, dx=18, t_in=5.5, layer=1)
    d.shift([servant], 5.8, 40, -120, 110)
    d.label("Quả cam vua ban", 560, 340, 5.6)
    d.shake(6.6, 3)


@beat("binh_than:banner", "lang")
def _banner(d: Stage):
    boy = d.actor("Boy", 640, 382, "down", scale=4)
    d.thing(orange(True), 640, 398)
    d.at(0.4, lambda: d.fx.burst(640, 384, 12, [(236, 150, 40), (250, 190, 80)], 120, 0.6, 3, 300))
    d.label("Quả cam đã nát", 640, 300, 0.6, t_out=2.6)
    men = d.troop(("Villager", "Villager3", "Villager4"), -220, 300, 3, 2, (48, 40), "right")
    men2 = d.troop(("Villager", "Villager3", "Villager4"), 1330, 300, 3, 2, (48, 40), "left")
    d.shift(men, 1.0, 640, 0, 220)
    d.shift(men2, 1.0, -580, 0, 220)
    d.face(men + men2, 3.6, "down")
    d.thing(banner_six(), 712, 382, t_in=3.8, pop=True)
    d.thing(glow(60, WARM, 90), 726, 316, layer=1, anchor="center", t_in=3.8)
    d.face([boy], 4.0, "right")
    d.cheer(men + men2, 4.4)
    d.label("Lá cờ đề sáu chữ", 760, 230, 4.4)


def _court(d: Stage, ruler="Noble"):
    d.actor(ruler, 640, 236, "down", scale=4)
    d.actor(d.ally[0], 560, 232, "down")
    d.actor(d.ally[0], 720, 232, "down")


def _elders(d: Stage, walk_in: bool) -> list[Actor]:
    off = 900 if walk_in else 0
    left = d.troop(ELDERS, 230 - off, 312, 7, 3, (58, 52), "up", "dan")
    right = d.troop(ELDERS, 650 + off, 312, 7, 3, (58, 52), "up", "dan")
    if walk_in:
        d.shift(left, 0.3, off, 0, 300, 0.02)
        d.shift(right, 0.3, -off, 0, 300, 0.02)
        d.face(left + right, 4.0, "up")
    for x in (340, 520, 760, 940):
        d.thing(prop("table", 3), x, 300)
    return left + right


@beat("dien_hong:gather", "san_dien")
def _gather(d: Stage):
    d.label("Điện Diên Hồng, cuối năm 1284", 260, 80, 0.3)
    _court(d)
    _elders(d, True)
    d.label("Nên hoà hay nên đánh?", 640, 156, 4.2)


@beat("dien_hong:shout", "san_dien")
def _shout(d: Stage):
    _court(d)
    elders = _elders(d, False)
    shout = d.label("ĐÁNH!", 640, 150, 0.7, "big")
    shout.beat = (0.85, 0.08)
    d.cheer(elders, 0.7, None, 0.006)
    d.every(0.7, None, 0.85, lambda: d.fx.burst(random.uniform(260, 1020), random.uniform(260, 420), 3, SPARK, 60, 0.4, 3, -20, kind="spark"))


@beat("kiep_bac:hich", "trai")
def _hich(d: Stage):
    d.label("Kiếp Bạc", 150, 80, 0.3)
    ring = [d.actor(n, x, y, f) for n, x, y, f in (
        (d.ally[0], 330, 346, "right"), (d.ally_lead, 452, 346, "left"), (d.ally[0], 360, 420, "up"), (d.ally_lead, 430, 420, "up"))]
    hens = chicken()
    c1 = d.thing(hens, 372, 384, fps=6)
    c2 = d.thing([pygame.transform.flip(f, True, False) for f in hens], 414, 384, fps=6)
    for k in range(6):
        c1.track.go(0.2 + k * 0.5, 384 if k % 2 == 0 else 366, 384, 70)
        c2.track.go(0.2 + k * 0.5, 402 if k % 2 == 0 else 420, 384, 70)
    d.cheer(ring, 0.1, 3.2)
    gamblers = [d.actor(d.ally[0], 860, 350, "right"), d.actor(d.ally_lead, 960, 350, "left"), d.actor(d.ally[0], 910, 424, "up")]
    for x, y in ((898, 382), (918, 390), (930, 378)):
        d.thing(icon("coin", 3), x, y)
    d.work(gamblers, 0.1, 3.2)
    d.label("Chọi gà, đánh bạc", 640, 150, 0.8, t_out=3.0)
    lord = d.actor("Master", 640, 196, "down", scale=4, t_in=2.6)
    d.path([lord], 2.7, [(640, 268)], 70)
    d.carry(lord, icon("scroll", 4, True), dy=-80, t_in=3.4, layer=1, pop=True)
    d.face(ring + gamblers, 3.6, "up")
    d.goto(ring, 4.2, 540, 380, 110)
    d.goto(gamblers, 4.2, 760, 380, 110)
    d.face(ring + gamblers, 5.6, "up")
    d.label("Hịch tướng sĩ", 640, 150, 4.0)


@beat("thien_mac:hold", "song")
def _hold(d: Stage):
    d.label("Thiên Mạc, đầu năm 1285", 220, 80, 0.3)
    d.waves(132, 316, 8, -30)
    fleet = []
    for x, y, crew in ((520, 222, (d.ally[0], d.ally[0])), (700, 296, ("Noble", d.ally[0])), (880, 222, (d.ally[0], d.ally[0]))):
        h, c = d.boat(x, y, "ta", 130, "left", crew)
        fleet += [h, *c]
    d.shift(fleet, 0.4, -1400, 0, 190)
    d.label("Vua rút lui", 560, 160, 0.9, t_out=3.6)
    tran = d.actor(d.ally_lead, 520, 404, "right", scale=4)
    men = d.troop(d.ally, 400, 366, 2, 3, (40, 36), "right")
    foe = d.troop(d.foe, 1300, 352, 5, 3, (46, 40), "left", "dich")
    d.shift(foe, 0.5, -680, 0, 230)
    d.fight([tran] + men, 3.4, None)
    d.fight(foe, 3.4, None)
    d.clash(540, 640, 340, 430, 3.4, 6.4)
    for a, (x, y) in zip(foe[10:14], ((470, 392), (472, 440), (574, 372), (580, 444)), strict=True):
        a.track.go(5.4, x, y, 170)
        a.faces.append((6.4, "right" if x < 520 else "left"))
    d.kneel([tran], 6.2)
    d.label("Trần Bình Trọng chặn giặc, bị bắt", 640, 190, 6.4, "dark")


@beat("thien_mac:counter", "song")
def _tm_counter(d: Stage):
    d.waves(132, 316, 8, 40)
    army = d.troop(d.ally, -520, 340, 8, 3, (46, 40), "right")
    _flags(d, army, 7)
    foe = d.troop(d.foe, 560, 352, 5, 3, (46, 40), "left", "dich")
    d.shift(army, 0.3, 900, 0, 200)
    d.fall(foe[:5], 2.2, 0.2)
    d.shift(foe[5:], 2.4, 900, 0, 230)
    for x, y in ((-260, 230), (-480, 296)):
        h, c = d.boat(x, y, "ta", 120, "right", (d.ally[0], d.ally_lead))
        d.shift([h, *c], 0.3, 1000, 0, 220)
    for x, name in ((340, "Hàm Tử"), (640, "Chương Dương"), (940, "Tây Kết")):
        d.label(name, x, 160, 1.2)
    d.label("Toa Đô tử trận", 940, 212, 3.4, "dark")
    d.label("Thoát Hoan chạy về nước", 640, 100, 4.6, "dark")
    d.cheer(army, 5.0)


@beat("van_don:grain", "bien")
def _van_don(d: Stage):
    d.label("Vân Đồn", 640, 70, 0.3)
    d.waves(60, 470, 16, -20)
    grain = []
    for i, (x, y) in enumerate(((1380, 236), (1560, 236), (1460, 364), (1650, 364), (1760, 236))):
        h, c = d.boat(x, y, "dich", 160, "left", (d.foe[0],), sail=True)
        bags = [d.carry(c[0], icon("rice_bag", 3), dy=4, dx=dx) for dx in (-46, 40)]
        d.shift([h, *c], 0.0, -500, 0, 130)
        grain.append((h, c, bags, i))
    d.label("Thuyền lương Trương Văn Hổ", 960, 140, 0.8, t_out=3.4)
    tran = []
    for x, y in ((-160, 300), (-380, 300), (-260, 420)):
        h, c = d.boat(x, y, "ta", 120, "right", (d.ally[0], d.ally_lead, d.ally[0]))
        d.shift([h, *c], 1.0, 640, 0, 230)
        tran += c
    d.volley(tran, 860, 1220, 200, 340, 2.4, 5.2, 0.14)
    for h, c, bags, i in grain:
        burn = 3.0 + i * 0.45
        d.fire(0, 6, burn, follow=c[0])
        h.sink = (burn + 1.6, 2.4)
        d.hide(c + bags, burn + 2.0)
        d.at(burn + 1.6, lambda h=h, b=burn: d.fx.splash(*h.pos(b + 1.6), 14))
    d.label("Lúa gạo đổ xuống biển", 960, 140, 5.2, "dark")


# =========================== Khởi nghĩa Lam Sơn ===========================
@beat("minh:loot", "lang")
def _loot(d: Stage):
    for i, (x, y) in enumerate(((190, 246), (544, 186), (896, 246), (1150, 252))):
        d.fire(x - 30, y, 0.2 + i * 0.4)
        d.fire(x + 34, y - 16, 0.5 + i * 0.4)
    workers = d.troop(("Villager", "Villager3", "Villager4"), -260, 404, 4, 1, (48, 0), "right", "dan")
    guards = [d.actor(d.foe[0], -20, 404, "right", "dich"), d.actor(d.foe_lead, -320, 404, "right", "dich")]
    for a in workers:
        d.carry(a, prop("crate", 2), dy=-44)
    d.shift(workers + guards, 0.2, 1700, 0, 90)
    burner = d.actor(d.foe[0], 640, 330, "right", "dich")
    d.work([burner], 0.4)
    d.fire(724, 338, 0.0)
    for k in range(7):
        t = 0.8 + k * 0.85
        book = d.thing(icon("book", 2), 652, 300, t_in=t, t_out=t + 0.55)
        book.track.go(t, 718, 322, 130)
        book.spin = 640
    d.label("Làng xóm cháy", 220, 80, 0.6)
    d.label("Thợ giỏi bị đưa đi", 640, 80, 1.8)
    d.label("Sách vở bị đốt", 1060, 80, 3.0)


@beat("minh:burn", "lang")
def _burn(d: Stage):
    d.dim(0, 0, 0.3, 0.3)
    for x, y in ((190, 246), (544, 186), (896, 246), (1150, 252)):
        d.fire(x - 30, y, 0.0, scale=3)
        d.fire(x + 40, y - 20, 0.3, scale=2)
    d.smoke(0, 1280, 60, 260, 0.0, None, 0.18)
    torch = d.troop(d.foe, 780, 330, 3, 2, (64, 50), "left", "dich")
    for a in torch[:3]:
        d.fire(14, -40, 0.0, scale=1, smoke=False, follow=a)
    people = d.troop(PEOPLE, 420, 340, 5, 2, (50, 40), "left", "dan")
    d.shift(people, 0.3, -900, 30, 170, 0.05)
    d.shift(torch, 1.4, -180, 0, 60)
    d.label("“Nướng dân đen trên ngọn lửa hung tàn”", 640, 140, 0.8, "dark")


@beat("lam_son:rise", "rung")
def _rise(d: Stage):
    d.label("Lam Sơn, năm 1418", 180, 80, 0.3)
    d.actor("Noble", 640, 290, "down", scale=4)
    dr = d.thing(drum(), 536, 300)
    dr.beat = (0.85, 0.12)
    d.every(0.2, None, 0.85, lambda: d.fx.burst(536, 252, 3, [(240, 220, 180)], 70, 0.3, 3, 0, kind="spark"))
    d.flag(704, 292, "ta", t_in=1.6, pop=True)
    d.label("Bình Định Vương", 640, 180, 2.0)
    left = d.troop(d.ally + ("Villager3",), -300, 350, 5, 3, (46, 40), "right")
    right = d.troop(d.ally + ("Villager3",), 1300, 350, 5, 3, (46, 40), "left")
    d.shift(left, 0.3, 610, 0, 230)
    d.shift(right, 0.3, -600, 0, 230)
    d.face(left + right, 3.2, "up")
    d.cheer(left + right, 3.4, 5.0)
    for i, (tx, ty) in enumerate(((-60, 120), (1340, 120), (-60, 440), (1340, 440))):
        sc = d.thing(icon("scroll", 3, True), 640, 232, layer=1, t_in=2.4 + i * 0.2, t_out=4.8)
        sc.track.go(2.4 + i * 0.2, tx, ty, 420)
    d.label("Truyền hịch khắp nơi", 640, 130, 2.6, t_out=4.8)
    d.troop(d.foe, 34, 170, 1, 4, (0, 80), "right", "dich", t_in=5.0)
    d.troop(d.foe, 1246, 170, 1, 4, (0, 80), "left", "dich", t_in=5.0)
    d.label("Quân ít, lương thiếu, bốn bề là giặc", 640, 130, 5.2, "dark")


def _camp(d: Stage, night=False):
    for x, y in ((960, 236), (1120, 224), (1210, 300)):
        d.thing(prop("tent", 2), x, y)
    if night:
        for x, y in ((1000, 330), (1150, 360)):
            d.fire(x, y, 0.0, scale=1, smoke=False)
            _bonfire_halo(d, x, y - 12, 70)


@beat("chi_linh:siege", "rung")
def _siege(d: Stage):
    d.label("Núi Chí Linh", 160, 80, 0.3)
    diggers = [d.actor(n, x, y, "down") for n, x, y in (
        (d.ally[0], 300, 404), (d.ally_lead, 420, 432), (d.ally[0], 860, 412), ("Villager3", 980, 440), (d.ally_lead, 1100, 404))]
    d.work(diggers, 0.2, 4.4)
    for i in range(9):
        x, y = diggers[i % 5].pos(0)
        t = 0.6 + i * 0.45
        yam = d.thing(icon("yam", 3), x + 22, y, t_in=t, t_out=t + 0.9, pop=True)
        yam.track.go(t, x + 22, y - 28, 50)
    d.label("Cạn lương, đào củ mài", 640, 140, 0.8, t_out=3.6)
    left = d.troop(d.foe, -60, 180, 1, 4, (0, 80), "right", "dich")
    right = d.troop(d.foe, 1340, 180, 1, 4, (0, 80), "left", "dich")
    top = d.troop(d.foe, 300, 100, 6, 1, (136, 0), "down", "dich")
    d.shift(left, 0.4, 140, 0, 34)
    d.shift(right, 0.4, -140, 0, 34)
    d.shift(top, 0.4, 0, 24, 8)
    loi = d.actor("Noble", 640, 316, "down", scale=4)
    for name, x, y, f in ((d.ally_lead, 560, 330, "right"), (d.ally[0], 720, 330, "left"), (d.ally_lead, 600, 372, "up"), (d.ally[0], 680, 372, "up")):
        d.actor(name, x, y, f)
    d.carry(loi, icon("emote_question", 3, True), dy=-86, t_in=4.4, layer=1, pop=True)
    d.label("Ai mặc áo bào của ta đi phá vây?", 640, 140, 4.6)


@beat("chi_linh:le_lai", "rung")
def _le_lai(d: Stage):
    _camp(d)
    foe = d.troop(d.foe, 900, 330, 5, 3, (52, 44), "left", "dich")
    lai = d.actor("Noble", 110, 384, "right", mount=True)
    banner = d.flag(0, 0, "ta")
    banner.follow = (lai, 18, -62)
    men = d.troop(d.ally, -190, 350, 3, 2, (44, 40), "right")
    d.shift([lai], 0.6, 620, 0, 230)
    d.shift(men, 0.8, 600, 0, 200)
    d.label("Lê Lai mặc áo chủ tướng", 400, 160, 0.8, t_out=3.4)
    _alerts(d, foe, 2.6, 4.2)
    d.label("Giặc tưởng đó là Lê Lợi", 900, 160, 2.8, "dark", t_out=5.4)
    d.goto(foe, 3.1, 830, 380, 150)
    d.fight([lai] + men, 3.7, 6.0)
    d.fight(foe, 3.7, 6.2)
    d.clash(690, 820, 330, 420, 3.7, 6.0, 0.22)
    d.kneel([lai], 6.0)  # các sách chép Lê Lai bị bắt rồi bị giết, không chép ông ngã giữa trận
    banner.t_out = 6.0
    d.label("Ông bị giặc bắt rồi giết hại", 730, 250, 6.3, "dark")


@beat("chi_linh:escape", "rung")
def _escape(d: Stage):
    d.dim(0, 0, 0.62, 0.62)
    _camp(d, night=True)
    sleepers = d.troop(d.foe, 930, 372, 4, 2, (62, 50), "left", "dich")
    d.kneel(sleepers, 0.0)
    d.label("Giặc lơi lỏng", 1060, 160, 0.6, "dark", t_out=3.2)
    line = []
    for i in range(11):
        name = "Noble" if i == 4 else d.ally[i % 2]
        line.append(d.actor(name, 640 + i * 44, 444 - (i % 2) * 8, "left"))
    d.shift(line, 0.3, -1300, 0, 80)
    d.label("Thoát khỏi vòng vây trong đêm", 520, 160, 2.6, "dark")


@beat("tra_lan:advance", "thanh")
def _tra_lan(d: Stage):
    d.label("Trà Lân, năm 1424", 180, 80, 0.3)
    foe = d.troop(d.foe, 590, 290, 3, 2, (48, 40), "left", "dich")
    ally = d.troop(d.ally, -300, 300, 6, 3, (44, 38), "right")
    _flags(d, ally, 6)
    d.shift(ally, 0.3, 600, 0, 230)
    d.fight(ally, 3.0, 4.2)
    d.fight(foe, 3.0, 4.0)
    d.clash(550, 610, 290, 380, 3.0, 4.0)
    d.fall(foe[:2], 3.6, 0.3)
    d.shift(foe[2:], 4.0, 900, 0, 230)

    def breach():
        d.fx.splinters(640, 240, 22)
        d.fx.debris(640, 230, 12)
        d.fx.shake(6)
        d.audio.play("va")

    d.at(4.0, breach)
    d.flag(640, 206, "ta", t_in=4.4, pop=True)
    d.label("Phá vỡ thành luỹ", 640, 140, 4.2)
    vill = d.troop(("Villager", "Woman", "OldWoman", "Villager4"), 1320, 330, 4, 2, (50, 46), "left", "dan", t_in=4.8)
    kids = [d.actor("Boy", 1350 + i * 70, 436, "left", "dan", t_in=4.8) for i in range(2)]
    for a in vill[::2]:
        d.carry(a, icon("rice_bag", 3), dy=-50)
    d.shift(vill + kids, 5.0, -420, 0, 130)
    d.label("Dân nhiều nơi kéo đến theo", 920, 190, 5.6)


@beat("tot_dong:ambush", "dong_lay")
def _tot_dong(d: Stage):
    d.label("Tốt Động – Chúc Động", 210, 80, 0.3)
    column = d.troop(d.foe, -300, 300, 12, 1, (46, 0), "right", "dich", jitter=3)
    d.shift(column, 0.2, 900, 0, 260)
    for name, x, y in ((d.foe_lead, 300, 404), (d.foe[0], 540, 440)):
        rider = d.actor(name, x, y, "right", "dich", mount=True)
        d.shift([rider], 0.2, 14, 0, 4)
        d.every(0.4, None, 0.35, lambda x=x, y=y: d.fx.burst(x + random.uniform(-20, 20), y - 4, 4, DIRT, 90, 0.5, 4, 300))
    d.label("Ngựa sa lầy", 420, 470, 1.2, t_out=3.4)
    d.thing(_plank_bridge(), 864, 320)
    top = d.troop(d.ally, 480, 150, 8, 1, (80, 0), "down", t_in=2.4)
    bottom = d.troop(d.ally, 520, 456, 8, 1, (80, 0), "up", t_in=2.4)
    d.shake(2.4, 4)
    d.sound(2.4, "trong")
    d.label("Phục binh đổ ra", 640, 120, 2.4, t_out=4.6)
    d.shift(top, 2.6, 0, 106, 170)
    d.shift(bottom, 2.6, 0, -112, 170)
    d.fight(top + bottom, 3.4, 6.0)
    d.fight(column, 3.4, 5.6)
    d.clash(560, 1100, 270, 330, 3.4, 5.6, 0.2)

    # sử chỉ chép quân Minh tan vỡ, chết nhiều khi tháo chạy qua sông Ninh Kiều; không có nguồn nói cầu gãy
    d.at(4.4, lambda: d.fx.splash(864, 330, 18))
    d.label("Tan vỡ khi tháo chạy qua sông Ninh Kiều", 864, 200, 4.6)
    d.fall(column[5:8], 4.5, 0.1, away=(0, 1))
    d.fall(column[:5] + column[8:], 4.9, 0.15)


@beat("chi_lang:ma_yen", "hem_nui")
def _ma_yen(d: Stage):
    d.label("Mã Yên, Chi Lăng", 180, 80, 0.3)
    bait = d.troop(d.ally, 900, 254, 2, 2, (44, 50), "left")
    d.shift(bait, 0.2, -1100, 0, 230)
    lieu = d.actor(d.foe_lead, 1400, 296, "left", "dich", mount=True)
    column = d.troop(d.foe, 1480, 244, 6, 3, (48, 44), "left", "dich")
    d.shift([lieu], 0.5, -900, 0, 260)
    d.shift(column, 0.7, -820, 0, 240)
    d.label("Liễu Thăng đuổi tới", 1000, 140, 1.2, t_out=3.4)
    for x in (300, 980):
        dr = d.thing(drum(), x, 132, t_in=3.2, pop=True)
        dr.beat = (0.6, 0.15)
    d.every(3.2, None, 0.9, lambda: d.audio.play("trong"))
    top = d.troop(d.ally, 360, 168, 8, 1, (90, 0), "down", t_in=3.4)
    bottom = d.troop(d.ally, 380, 448, 8, 1, (90, 0), "up", t_in=3.4)
    d.shift(top, 3.5, 0, 52, 120)
    d.shift(bottom, 3.5, 0, -96, 120)
    d.fight(top + bottom, 4.3, 6.8)
    d.fight(column + [lieu], 4.3, 6.2)
    d.clash(420, 1000, 220, 350, 4.3, 6.2, 0.2)
    d.fall([lieu], 4.8, principal=True)
    d.label("Liễu Thăng bị chém tại trận", 500, 190, 5.0, "dark")
    d.fall(column[::2], 5.4, 0.1)
    d.shift(column[1::2], 5.8, 900, 0, 270)


@beat("xuong_giang:siege", "thanh")
def _xuong_giang(d: Stage):
    d.label("Thành Xương Giang", 180, 80, 0.3)
    for x in (300, 640, 980):
        d.flag(x, 214, "ta")
    d.label("Thành đã bị nghĩa quân chiếm", 640, 140, 0.8, t_out=3.4)
    rem = d.troop(d.foe, -360, 300, 5, 2, (46, 44), "right", "dich")
    d.shift(rem, 0.3, 700, 0, 240)
    _alerts(d, rem, 3.2, 4.4)
    for x in (380, 520, 660):
        d.thing(prop("tent", 2), x, 292, t_in=3.8, pop=True)
    d.label("Đóng trại ngoài đồng", 520, 190, 4.0, t_out=6.0)
    left = d.troop(d.ally, -200, 300, 2, 4, (44, 46), "right", t_in=4.2)
    right = d.troop(d.ally, 1300, 300, 2, 4, (44, 46), "left", t_in=4.2)
    bottom = d.troop(d.ally, 280, 520, 8, 1, (70, 0), "up", t_in=4.2)
    d.shift(left, 4.3, 360, 0, 220)
    d.shift(right, 4.3, -440, 0, 220)
    d.shift(bottom, 4.3, 0, -70, 120)
    d.fight(left + right + bottom, 6.0, 7.4)
    d.fight(rem, 6.0, 7.2)
    d.clash(300, 820, 290, 400, 6.0, 7.2, 0.22)
    d.kneel(rem[::2], 7.2, None, 0.1)
    d.label("Nhiều tướng bị bắt", 640, 190, 7.4, "dark")


@beat("hoi_the:oath", "song")
def _oath(d: Stage):
    d.label("Tháng 12/1427", 160, 80, 0.3)
    d.waves(132, 316, 8, 18)
    for i in range(4):
        t = 0.3 + i * 0.4
        lt = d.thing(icon("letter", 3, True), 200, 230, layer=1, t_in=t, t_out=t + 1.4)
        lt.track.go(t, 1080, 210 + 20 * i, 700)
    d.label("Nguyễn Trãi viết thư cho tướng giặc nhiều lần", 640, 110, 0.6, t_out=2.8)
    d.thing(prop("table", 3), 640, 386)
    d.smoke(632, 648, 344, 352, 0.0, None, 0.5)
    lead = d.actor("Noble", 430, 390, "right", scale=4)
    d.troop(d.ally, 300, 350, 2, 2, (44, 60), "right")
    foe_lead = d.actor(d.foe_lead, 850, 390, "left", "dich", scale=4)
    foe = d.troop(d.foe, 920, 350, 2, 2, (44, 60), "left", "dich")
    d.shift([lead], 2.4, 120, 0, 80)
    d.shift([foe_lead], 2.4, -120, 0, 80)
    d.label("Họp thề phía nam thành", 640, 300, 3.4, t_out=6.0)
    boats = []
    for x in (180, 420, 660):
        h, c = d.boat(x, 232, "dan", 120, "right", (d.foe[0], d.foe[0]), t_in=4.6)
        boats += [h, *c]
    d.shift(boats, 5.0, 1300, 0, 130)
    nags = [d.thing(horse(3)["right"], x, 446, fps=6, t_in=5.0) for x in (980, 1060)]
    d.shift(foe + [foe_lead] + nags, 5.4, 700, 0, 120)
    for a in foe[::2]:
        d.carry(a, icon("rice_bag", 3), dy=-50, t_in=5.0)
    d.label("Cấp thuyền, ngựa, lương cho về nước", 760, 190, 5.4)


@beat("binh_ngo:proclaim", "san_dien")
def _proclaim(d: Stage):
    d.label("Năm 1428", 150, 80, 0.3)
    _court(d)
    court = d.troop(("Master", "Monk2", "OldMan3", d.ally[0]), 300, 300, 5, 2, (50, 46), "up")
    court += d.troop(("Master", "Monk2", "OldMan3", d.ally[0]), 770, 300, 5, 2, (50, 46), "up")
    d.kneel(court, 0.6, 2.6, 0.02)
    d.label("Lê Lợi lên ngôi", 640, 140, 0.8, t_out=2.8)
    trai = d.actor("Master", 560, 264, "down")
    d.carry(trai, icon("scroll", 4, True), dy=-70, t_in=2.8, layer=1, pop=True)
    d.label("Bình Ngô đại cáo", 560, 150, 3.0)
    d.path([trai], 3.8, [(640, 300), (640, 380)], 80)
    left = d.troop(PEOPLE, -320, 420, 5, 1, (50, 0), "right", "dan", t_in=4.4)
    right = d.troop(PEOPLE, 1340, 420, 5, 1, (50, 0), "left", "dan", t_in=4.4)
    d.shift(left, 4.5, 560, 0, 200)
    d.shift(right, 4.5, -560, 0, 200)
    d.cheer(left + right + court, 6.6)
    d.label("Đọc to ở các nơi", 640, 200, 6.0, "dark")


# =========================== 1945 - 1954 ===========================
DELEGATES = ("Villager", "Villager3", "Villager4", "Hunter", "Woman", "OldMan3", "BoDoi")


@beat("tan_trao:delegates", "dinh")
def _delegates(d: Stage):
    d.label("Tân Trào, tháng 8/1945", 210, 80, 0.3)
    d.thing(dinh_lang(), 864, 262)
    d.label("Nhật đầu hàng Đồng minh", 640, 120, 0.8, "dark", t_out=3.6)
    for i in range(10):
        a = d.actor(DELEGATES[i % len(DELEGATES)], -40 - i * 96, 330 + (i % 3) * 32, "right", "dan")
        d.path([a], 0.1, [(880 + (i % 3) * 44, 290 + (i % 3) * 30)], 150)
    d.every(0.8, 9.0, 0.3, lambda: d.fx.splash(random.uniform(232, 340), random.uniform(330, 400), 5))
    d.label("Đại biểu lội suối, qua rừng về họp", 640, 170, 3.6)


@beat("tan_trao:congress", "dinh")
def _congress(d: Stage):
    d.label("Đình Tân Trào, 16 và 17/8/1945", 260, 80, 0.3)
    d.thing(dinh_lang(), 864, 262)
    seated = d.troop(DELEGATES, 690, 318, 6, 3, (52, 42), "up", "dan")
    d.kneel(seated, 0.0)
    d.paint(lambda s, t, ox, oy: pygame.draw.line(s, (60, 44, 30), (766 + ox, 330 + oy), (766 + ox, 100 + oy), 3), 0)
    fl = d.thing(flag_frames("vn"), 766, 300, fps=7, anchor="topleft", t_in=1.6)
    fl.track.go(1.8, 766, 104, 70)
    d.label("Lệnh tổng khởi nghĩa", 400, 160, 1.0)
    d.label("Uỷ ban Dân tộc giải phóng", 400, 210, 2.4)
    d.label("Cờ đỏ sao vàng", 900, 100, 4.6)
    d.label("Tiến quân ca", 400, 260, 5.6)
    for k in range(8):
        t = 5.6 + k * 0.4
        n = d.thing(_note(), 760 + (k % 3) * 40, 300, layer=1, t_in=t, t_out=t + 1.8)
        n.track.go(t, 740 + (k % 4) * 50, 180, 70)


@beat("ha_noi:uprising", "pho")
def _uprising(d: Stage):
    d.label("Hà Nội, 19/8/1945", 640, 70, 0.3)
    d.thing(opera_house(), 190, 262)
    d.label("Mít tinh ở Nhà hát Lớn", 190, 98, 0.6, t_out=2.4)
    crowd = d.troop(PEOPLE + ("BoDoi",), -40, 300, 9, 4, (46, 40), "right", "dan", jitter=8)
    _flags(d, crowd, 6, "vn")
    d.shift(crowd, 1.2, 640, 0, 110, 0.01)
    d.thing(bac_bo_phu(), 1140, 300)
    d.label("Bắc Bộ phủ", 1140, 120, 2.0)
    d.flag(1140, 160, "vn", t_in=5.4, pop=True)
    d.cheer(crowd, 6.4)
    d.label("Huế 23/8", 300, 140, 6.0, "dark")
    d.label("Sài Gòn 25/8", 640, 140, 6.6, "dark")
    d.label("Bảo Đại thoái vị 30/8", 980, 140, 7.2, "dark")


def _square(d: Stage, flags=True) -> list[Actor]:
    d.thing(podium(), 640, 252)
    d.paint(lambda s, t, ox, oy: pygame.draw.line(s, (60, 44, 30), (712 + ox, 236 + oy), (712 + ox, 104 + oy), 3), 0)
    d.thing(flag_frames("vn"), 712, 104, fps=7, anchor="topleft")
    crowd = d.troop(PEOPLE + ("BoDoi",), 90, 300, 20, 4, (56, 42), "up", "dan", jitter=8)
    if flags:
        _flags(d, crowd, 9, "vn", 3)
    return crowd


@beat("ba_dinh:crowd", "quang_truong")
def _ba_dinh(d: Stage):
    d.label("Quảng trường Ba Đình, chiều 2/9/1945", 300, 80, 0.3)
    crowd = _square(d)
    d.thing(icon("emote_talk", 4, True), 640, 172, layer=1, t_in=1.4, t_out=3.4, pop=True)
    d.label("“Tôi nói, đồng bào nghe rõ không?”", 640, 130, 1.6, t_out=3.6)
    d.cheer(crowd, 3.4, 5.8, 0.004)
    d.shake(3.4, 4)
    d.label("Cả quảng trường đáp lại", 640, 130, 3.8, "dark")


@beat("ba_dinh:after", "quang_truong")
def _ba_dinh_after(d: Stage):
    _square(d, flags=False)
    d.thing(glow(90, WARM, 110), 640, 170, layer=1, anchor="center", t_in=0.4, t_out=3.4)
    d.thing(icon("scroll", 4, True), 640, 196, layer=1, t_in=0.4, pop=True)
    d.label("Tuyên ngôn Độc lập", 640, 110, 0.7, t_out=3.0)
    d.dim(2.8, 4.0, 0.0, 0.42)
    for text, x, y, t in (("Đói kém", 230, 130, 3.4), ("Giặc dốt", 1050, 130, 4.0), ("Ngân khố trống rỗng", 260, 214, 4.6), ("Áp lực nước ngoài bốn phía", 1010, 214, 5.2)):
        d.label(text, x, y, t, "dark")


@beat("ha_noi:night1946", "pho")
def _night1946(d: Stage):
    d.label("Hà Nội, đêm 19/12/1946", 210, 80, 0.3)
    d.dim(0, 0, 0.42, 0.42)
    d.dim(1.2, 1.4, 0.42, 0.7)
    for x, y in ((90, 196), (150, 196), (300, 182), (420, 182), (576, 200), (760, 196), (860, 196), (1010, 182), (1110, 182)):
        d.thing(_window(), x, y, layer=1, anchor="center", t_out=1.2)
        d.thing(glow(30, WARM, 70), x, y, layer=1, anchor="center", t_out=1.2)
    for x in (240, 640, 1040):
        d.thing(glow(80, WARM, 60), x, 330, layer=1, anchor="center", t_out=1.2)
    d.label("Đèn tắt phụt", 640, 140, 1.3, "dark", t_out=3.2)
    shooters = d.troop(VIET_MINH, 110, 330, 2, 2, (60, 60), "right", t_in=1.4)
    shooters += d.troop(FRENCH, 1090, 350, 2, 2, (60, 60), "left", "dich", t_in=1.4)
    _sparks_from(d, shooters, 1.6, None, 0.12, -30)
    d.blasts(200, 1100, 300, 460, 2.0, None, 1.6, 0.6)
    squad = [d.actor("BoDoi", 330 + i * 36, 430 + (i % 2) * 18, "up") for i in range(4)]
    d.path(squad, 2.0, [(420, 300)], 190, 0.1)
    for a in squad:
        a.gaps.append((3.4, 4.6))
        a.track.jump(4.4, 700 + random.uniform(-20, 20), 300)
    d.at(3.9, lambda: (d.fx.debris(576, 232, 10), d.fx.smoke(576, 232, 3, 20)))
    d.path(squad, 4.6, [(760, 420)], 150, 0.08)
    d.label("Đục tường qua nhà nọ sang nhà kia", 640, 140, 3.6, "dark")
    d.label("Liên khu I", 1050, 80, 5.0)


@beat("ha_noi:withdraw", "song")
def _withdraw(d: Stage):
    d.dim(0, 0, 0.62, 0.62)
    d.waves(132, 316, 8, 16)
    d.label("Sáu mươi ngày đêm", 180, 80, 0.3)
    walkers = [d.actor("BoDoi", 760 + i * 52, 400 + (i % 2) * 24, "left") for i in range(10)]
    d.path(walkers, 0.3, [(340, 380)], 110, 0.18)
    for a in walkers:
        a.gaps.append((5.4, 99.0))
    for t0 in (0.6, 4.4):
        for x in (220, 400, 580):
            h, c = d.boat(x, 300, "dan", 100, "right", ("BoDoi", "BoDoi"), t_in=t0)
            d.shift([h, *c], t0 + 0.5, 0, -146, 46)
            d.hide([h, *c], t0 + 4.2)
    d.label("Vượt sông Hồng lên chiến khu", 640, 100, 3.0, "dark")


@beat("song_lo:ships", "song_nui")
def _song_lo(d: Stage):
    d.label("Sông Lô, thu đông 1947", 210, 80, 0.3)
    d.waves(132, 316, 8, -30)
    ships = [d.thing(gunboat(), x, y) for x, y in ((1400, 256), (1660, 304), (1920, 256))]
    for sh, stop in zip(ships, (500, 760, 1020), strict=True):
        _, x, _ = sh.track.end()
        d.shift([sh], 0.3, stop - x, 0, 330)
    d.thing(cannon(), 280, 424)
    d.thing(cannon(), 520, 452)
    gunners = d.troop(VIET_MINH, 200, 384, 3, 2, (60, 54), "right")
    d.label("Pháp đổ quân lên Việt Bắc", 760, 150, 0.6, t_out=2.8)
    for i, sh in enumerate(ships):
        t = 3.0 + i * 1.0
        d.at(t - 0.3, lambda: (d.fx.burst(300, 400, 8, SPARK, 160, 0.2, 4, 0, kind="spark"), d.audio.play("ban")))
        d.at(t, lambda sh=sh, t=t: (d.fx.explosion(*sh.pos(t), 1.2), d.fx.shake(5)))
        sh.sink = (t + 0.4, 2.6)
        d.every(t, t + 3.0, 0.25, lambda sh=sh: d.fx.smoke(sh.pos(d.t)[0], sh.pos(d.t)[1] - 40, 1, 20))
    d.fight(gunners, 2.6, 5.4)
    d.label("Tàu chiến bị đánh chìm", 760, 150, 4.0, "dark")
    d.label("Việt Bắc đứng vững", 640, 200, 6.6)


@beat("bien_gioi:ambush", "hem_nui")
def _route4(d: Stage):
    d.label("Đông Khê, tháng 9/1950", 220, 80, 0.3)
    d.thing(bunker(), 1100, 172, t_out=2.4)
    d.blasts(1020, 1180, 110, 180, 0.4, 2.4, 0.32)

    def fall_post():
        d.fx.explosion(1100, 150, 1.4)
        d.fx.shake(6)

    d.at(2.4, fall_post)
    d.flag(1100, 180, "vn", t_in=2.8, pop=True)
    column = d.troop(FRENCH, -400, 260, 10, 2, (52, 50), "right", "dich")
    d.shift(column, 0.2, 480, 0, 160)
    top = d.troop(VIET_MINH, 120, 160, 7, 1, (90, 0), "down", t_in=3.2)
    bottom = d.troop(VIET_MINH, 140, 444, 7, 1, (90, 0), "up", t_in=3.2)
    d.label("Đường số 4", 340, 120, 3.2)
    d.blasts(80, 600, 230, 340, 3.4, 6.0, 0.45)
    d.smoke(80, 600, 220, 330, 3.4, None, 0.25)
    d.fight(top + bottom, 3.4, 6.4)
    _sparks_from(d, top, 3.4, 6.4, 0.14, -20)
    _sparks_from(d, bottom, 3.4, 6.4, 0.14, -30)
    d.shift(column, 4.2, -900, 0, 230)
    d.label("Đoàn quân Pháp bị chặn đánh", 640, 120, 4.4, "dark")


@beat("dien_bien:porters", "rung")
def _porters(d: Stage):
    d.label("Đường ra mặt trận, 1953 – 1954", 260, 80, 0.3)
    for i in range(15):
        name = ("Villager", "Villager3", "Woman", "Villager4", "BoDoi")[i % 5]
        x0 = 1150 - i * 120
        a = d.actor(name, x0, 432 - max(0, x0) * 0.05, "right", "dan")
        d.path([a], 0.0, [(1400, 362)], 70)
        if i % 3 == 2:
            bk = d.thing(bike(), 0, 0)
            bk.follow = (a, 34, 2)
        else:
            d.carry(a, icon("rice_bag", 3), dy=-40, dx=-12)
    d.label("Dân công gùi gạo, thồ xe đạp xuyên rừng", 640, 130, 0.8, t_out=4.4)
    d.actor("BoDoi", 1030, 300, "right", t_in=4.4)
    gunner = d.actor("BoDoi", 996, 306, "right", t_in=4.4)
    d.kneel([gunner], 4.4)
    d.every(4.6, 7.4, 0.18, lambda: d.fx.burst(1066, 262, 4, SPARK, 160, 0.16, 3, 0, kind="spark"))
    d.label("Bế Văn Đàn, Mường Pồn, 12/1953", 1010, 200, 4.6)
    d.thing(glow(70, WARM, 90), 1020, 268, layer=1, anchor="center", t_in=7.4)


ROAD = [(0, 544), (512, 352), (896, 224), (1280, 160)]


def _rope(d: Stage, gun, lead: Actor, t0, t1):
    def draw(s, t, ox, oy):
        if not (t0 <= t < t1):
            return
        gx, gy = gun.pos(t)
        lx, ly = lead.pos(t)
        pygame.draw.line(s, (232, 212, 160), (gx + ox, gy - 16 + oy), (lx + ox, ly - 22 + oy), 3)

    d.paint(draw, -1)


@beat("dien_bien:pull_out", "doc_nui")
def _pull_out(d: Stage):
    d.label("Điện Biên Phủ, tháng 1/1954", 250, 80, 0.3)
    d.dim(0, 0, 0.5, 0.5)
    d.dim(1.6, 2.6, 0.5, 0.0)
    d.thing(prop("tent", 2), 200, 300)
    d.thing(glow(40, WARM, 130), 200, 270, layer=1, anchor="center", t_out=2.2)
    d.label("Nhiều đêm không ngủ", 220, 200, 0.6, "dark", t_out=2.2)
    g1 = d.thing(cannon(), 900, 232)
    g2 = d.thing(cannon(), 1070, 204)
    crew = [d.actor("BoDoi", x, y, "left") for x, y in ((820, 252), (858, 268), (990, 234), (1030, 224), (1130, 214), (1168, 222))]
    d.kneel(crew, 0.0, 4.6)
    courier = d.actor("BoDoi", -30, 560, "right", t_in=2.4)
    d.carry(courier, icon("letter", 3, True), dy=-50, t_in=2.4, layer=1)
    d.path([courier], 2.4, [(512, 352), (800, 262)], 330)
    d.label("Lệnh: lùi ngày, kéo pháo ra", 640, 140, 4.0)
    for gun, team, end in ((g1, crew[:3], (512, 352)), (g2, crew[3:], (700, 288))):
        gx, gy = gun.pos(0)
        dx, dy = end[0] - gx, end[1] - gy
        gun.track.go(5.0, end[0], end[1], 34)
        norm = math.hypot(dx, dy) or 1
        for i, a in enumerate(team):
            ax, ay = gx + dx / norm * 60 * (i + 1), gy + dy / norm * 60 * (i + 1)
            a.track.go(4.6, ax, ay, 120)
            a.track.go(5.0, ax + dx, ay + dy, 34)
        _rope(d, gun, team[-1], 5.0, 99)


@beat("dien_bien:to_vinh_dien", "doc_nui")
def _to_vinh_dien(d: Stage):
    gun = d.thing(cannon(), 520, 350)
    gun.track.go(0.2, 680, 296, 82)
    gun.track.go(2.4, 600, 322, 300)
    team = []
    for i in range(5):
        a = d.actor("BoDoi", 580 + i * 56, 330 - i * 19, "right")
        a.track.go(0.2, 740 + i * 56, 276 - i * 19, 82)
        team.append(a)
    d.shift(team, 2.4, 30, -10, 120)
    _rope(d, gun, team[-1], 0.2, 2.4)
    d.label("Dây kéo bị đứt giữa dốc", 640, 140, 2.4, "dark", t_out=4.4)
    d.shake(2.4, 3)
    hero = d.actor("BoDoi", 520, 412, "up")
    d.path([hero], 2.45, [(584, 340)], 260)
    d.kneel([hero], 2.85)
    d.shake(2.85, 5)
    d.sound(2.85, "va")
    d.dim(3.0, 4.0, 0.0, 0.3)
    hero.t_out = 3.8
    rise = d.thing(glow(36, (255, 236, 170), 170), 584, 320, layer=1, anchor="center", t_in=3.8)
    rise.track.go(3.8, 584, 140, 40)
    d.label("Tô Vĩnh Diện", 584, 220, 4.0)
    d.label("Pháo còn, người mất", 640, 120, 5.6, "dark")


def _strongpoint(d: Stage, x=900, y=252):
    d.thing(bunker(), x, y)
    d.thing(bunker(), x + 160, y - 30)
    d.thing(bunker(), x - 140, y - 40)
    for fx_ in range(x - 260, x + 300, 64):
        d.thing(prop("fence"), fx_, y + 70)


@beat("dien_bien:him_lam", "canh_dong")
def _him_lam(d: Stage):
    d.label("Him Lam, chiều 13/3/1954", 230, 80, 0.3)
    _strongpoint(d)
    d.blasts(680, 1160, 160, 300, 0.3, 2.8, 0.26, 1.0)
    d.smoke(680, 1160, 160, 300, 0.3, 6.0, 0.2)
    d.label("Pháo ta nổ vào Him Lam", 640, 130, 0.5, t_out=2.8)
    d.every(3.0, 5.3, 0.13, lambda: d.fx.burst(872, 238, 4, SPARK, 220, 0.15, 3, 0, kind="spark"))
    giot = d.actor("BoDoi", 520, 432, "right")
    d.path([giot], 3.0, [(860, 268)], 170)
    giot.t_out = 5.3
    d.thing(glow(40, (255, 236, 170), 170), 872, 244, layer=1, anchor="center", t_in=5.3)
    d.label("Phan Đình Giót", 860, 170, 5.4)
    squad = d.troop(VIET_MINH, -300, 340, 6, 2, (50, 50), "right", t_in=5.6)
    d.shift(squad, 5.8, 900, -60, 230)
    d.flag(900, 196, "vn", t_in=8.0, pop=True)
    d.label("Him Lam bị tiêu diệt ngay trong đêm", 640, 130, 8.2, "dark")


@beat("dien_bien:trenches", "canh_dong")
def _trenches(d: Stage):
    d.label("Cánh đồng Mường Thanh", 240, 80, 0.3)
    _strongpoint(d, 640, 250)
    lines = [
        [(-20, 470), (200, 430), (380, 370), (470, 320)],
        [(1300, 460), (1100, 410), (930, 360), (820, 320)],
        [(-20, 210), (200, 226), (360, 244)],
        [(1300, 190), (1100, 206), (920, 234)],
        [(640, 520), (650, 440), (640, 330)],
    ]
    t0, t1 = 0.3, 7.5
    specs = []
    for pts in lines:
        speed, total, lengths = _along(pts, t0, t1)
        specs.append((pts, lengths, speed))
        digger = d.actor("BoDoi", pts[0][0], pts[0][1], "right")
        tt = t0
        for px, py in pts[1:]:
            tt = digger.track.go(tt, px, py, speed)
        d.every(t0, t1, 0.3, lambda a=digger: d.fx.burst(*a.pos(d.t), 3, DIRT, 70, 0.4, 3, 260))

    def draw(s, t, ox, oy):
        k = max(0.0, min(1.0, (t - t0) / (t1 - t0)))
        for pts, lengths, _ in specs:
            seg = _partial(pts, lengths, sum(lengths) * k)
            if len(seg) >= 2:
                pts_s = [(x + ox, y + oy) for x, y in seg]
                pygame.draw.lines(s, (44, 32, 22), False, pts_s, 18)
                pygame.draw.lines(s, (92, 70, 48), False, pts_s, 8)

    d.paint(draw, -1)
    d.label("Đường hào siết dần lòng chảo", 640, 130, 2.0, "dark")
    d.label("Mưa ngập đến bụng, vẫn đào", 640, 180, 4.6)


@beat("dien_bien:a1", "canh_dong")
def _a1(d: Stage):
    d.label("Đồi A1, đêm 6/5/1954", 220, 80, 0.3, t_out=3.4)
    d.dim(0, 0, 0.6, 0.6)
    d.thing(prop("rock_big"), 640, 320, t_out=3.6)

    def boom():
        for dx, dy in ((0, 0), (-70, 24), (70, 14), (0, -46), (-30, 30)):
            d.fx.explosion(640 + dx, 236 + dy, 1.8)
        d.fx.debris(640, 240, 16)
        d.fx.shake(12)
        d.audio.play("no")

    d.at(1.2, boom)
    d.flash(1.2, 0.8)
    d.label("Khối bộc phá gần một tấn", 640, 140, 1.4, "dark", t_out=3.4)
    d.smoke(520, 760, 160, 300, 1.3, 4.0, 0.12)
    d.dim(3.0, 4.2, 0.6, 0.0)
    d.label("Chiều 7/5/1954", 210, 80, 3.6)
    d.thing(bunker(), 640, 330, t_in=3.6)
    d.label("Hầm De Castries", 640, 190, 4.0)
    squad = d.troop(VIET_MINH, -100, 360, 6, 2, (48, 46), "right", t_in=3.6)
    d.shift(squad, 3.8, 560, 0, 240)
    bearer = d.actor("BoDoi", 540, 400, "right", t_in=3.6)
    d.path([bearer], 3.8, [(624, 300)], 120)
    d.flag(652, 300, "qcqt", t_in=5.0, pop=True)
    d.cheer(squad, 6.0)
    d.kneel([squad[0]], 7.0)
    d.label("Tiếng súng im", 640, 130, 6.4, "dark")


# =========================== Truyền thuyết ===========================
def _gold_turtle() -> pygame.Surface:
    return cached("turtle3", lambda: turtle_sprite(3))


@beat("co_loa:build", "song")
def _co_loa_build(d: Stage):
    d.label("Truyền thuyết thành Cổ Loa", 240, 80, 0.3)
    d.waves(132, 316, 8, -14)
    d.actor("Noble", 360, 450, "up", scale=4)
    workers = d.troop(PEOPLE[:4], 460, 446, 7, 1, (90, 0), "up", "dan")
    d.work(workers, 0.0, 4.6)
    xs = list(range(430, 1080, 64))
    for start, end in ((0.3, 1.8), (2.1, 3.4), (5.0, None)):
        for i, x in enumerate(xs):
            d.thing(_wall_piece(), x, 400, t_in=start + i * 0.08, t_out=end, pop=True)
        if end is not None:
            d.at(end, lambda: (d.fx.debris(760, 360, 14), d.fx.smoke(760, 360, 4, 120), d.fx.shake(4)))
    d.label("Đắp đến đâu lở đến đó", 760, 220, 1.0, "dark", t_out=3.6)
    tur = d.thing(_gold_turtle(), 900, 300, layer=1, t_in=3.8, t_out=7.6, pop=True)
    tur.bob = 4
    d.thing(glow(110, (255, 220, 120), 110), 900, 250, layer=1, anchor="center", t_in=3.8, t_out=7.6)
    d.label("Rùa Vàng hiện lên", 900, 140, 4.0, t_out=7.0)
    claw = d.thing(glow(16, (255, 236, 160), 230), 860, 270, layer=1, anchor="center", t_in=5.8, t_out=7.0)
    claw.track.go(5.8, 380, 380, 380)
    for k in range(3):
        d.at(7.0 + k * 0.18, lambda: d.fx.volley(420, 330, 1300, 260, 10, 140, 760))
    d.label("Lẫy nỏ thần", 420, 300, 7.0)


@beat("co_loa:fall", "thanh_dat")
def _co_loa_fall(d: Stage):
    thuy = d.actor("NinjaGray", 640, 340, "up")
    d.path([thuy], 0.3, [(640, 270)], 70)
    d.thing(glow(16, (255, 236, 160), 230), 652, 220, layer=1, anchor="center", t_in=1.4, t_out=2.2)
    d.carry(thuy, glow(14, (255, 236, 160), 230), dy=-30, dx=12, t_in=2.2, t_out=4.4, layer=1)
    d.path([thuy], 2.2, [(660, 340), (1400, 380)], 150)
    d.label("Lẫy nỏ bị đánh tráo", 640, 140, 1.6, t_out=4.6)
    foe = d.troop(d.foe, 1320, 290, 5, 3, (46, 40), "left", "dich", t_in=4.2)
    d.shift(foe, 4.3, -700, 0, 220)
    for x in (300, 980):
        d.fire(x, 252, 5.0)
    d.label("Thành mất", 640, 140, 5.2, "dark")
    d.thing(prop("well"), 260, 440, t_in=5.8, pop=True)
    d.every(5.9, None, 0.3, lambda: d.fx.burst(260 + random.uniform(-18, 18), 404, 2, [(255, 255, 240), (230, 240, 255)], 40, 0.6, 3, -10, kind="spark"))
    d.label("Giếng Ngọc", 260, 340, 6.0)
