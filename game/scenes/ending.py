"""Đoạn kết: hiện khi bước qua cổng cuối của Màn 3, trước lời dặn của Cụ Đồ Sử. Xem lại được từ màn hình tựa đề.

Game dừng ở năm 1954, nên cảnh ăn mừng là những gì có thật năm ấy: lá cờ "Quyết chiến Quyết thắng" trên nóc hầm chỉ huy
địch ở Điện Biên Phủ (7/5/1954), Hiệp định Giơnevơ (tháng 7/1954), bộ đội về tiếp quản Hà Nội giữa rừng cờ hoa và lễ chào
cờ ở sân Cột Cờ (10/10/1954). Đất nước khi ấy còn tạm chia ở vĩ tuyến 17; trang cuối nói rõ phải đến 30/4/1975 đất nước
mới thống nhất, để người chơi không nhầm. Mỗi đoạn ghi nguồn ở góc lời dẫn.

Phím cách hoặc mũi tên phải sang đoạn sau, Esc bỏ qua tới lời dặn của Cụ Đồ Sử.
"""

from __future__ import annotations

import math

import pygame
from core import art, diorama, fonts, outfit, rpg, sprites, theme, ui
from core.scene import Scene

W, H = theme.WIDTH, theme.HEIGHT
CAPTION = pygame.Rect(40, 566, 1200, 132)
FADE = 0.4
OUTLINE = (24, 16, 14)
RED, YELLOW = (218, 37, 29), (255, 222, 0)
ROAD = 400  # cảnh Hà Nội: mép trên mặt đường
HOUSES = ((150, (226, 190, 110), 2), (120, (232, 214, 170), 3), (170, (214, 172, 150), 2), (130, (226, 190, 110), 2),
          (150, (232, 214, 170), 3), (120, (214, 172, 150), 2), (160, (226, 190, 110), 3), (140, (232, 214, 170), 2),
          (150, (214, 172, 150), 2))  # dãy nhà ống: bề ngang, màu tường, số tầng
# (tiêu đề, lời dẫn, số giây, hàm vẽ, cảnh nền, mã nguồn)
BEATS = (
    ("", "", 5.0, "_e_open", None, None),
    ("Điện Biên Phủ, chiều 7/5/1954", "Lá cờ “Quyết chiến Quyết thắng” tung bay trên nóc hầm chỉ huy của địch. Tướng Đờ Cát-xtơ-ri "
     "cùng toàn bộ bộ tham mưu bị bắt. Chiến dịch Điện Biên Phủ toàn thắng.", 9.0, "_e_dbp", "dien_bien", ("c_qs_dbp", "c_bt_dbp")),
    ("Hội nghị Giơnevơ, tháng 7/1954", "Hiệp định Giơnevơ được ký kết, hoà bình lập lại ở Đông Dương. Vĩ tuyến 17 chỉ là giới tuyến "
     "quân sự tạm thời; Hội nghị hẹn tháng 7/1956 tổng tuyển cử để thống nhất đất nước.", 9.0, "_e_gionevo", None,
     ("c_gionevo_1954",)),
    ("Hà Nội, ngày 10/10/1954", "Quân Pháp rút đi. Đại đoàn 308 tiến vào tiếp quản Thủ đô giữa rừng cờ hoa của nhân dân Hà Nội.",
     11.0, "_e_hanoi", None, ("c_thu_do_1954",)),
    ("Sân Cột Cờ, 15 giờ chiều 10/10/1954", "Lễ chào cờ đầu tiên của Thủ đô giải phóng. Lá cờ đỏ sao vàng tung bay trên Cột cờ Hà Nội.",
     9.0, "_e_cotco", None, ("c_thu_do_1954",)),
    ("Hơn hai mươi năm sau", "Cuộc tổng tuyển cử hẹn năm 1956 đã không diễn ra. Phải thêm hơn hai mươi năm nữa, đến ngày 30/4/1975, "
     "đất nước mới thống nhất, Bắc Nam sum họp một nhà.", 9.0, "_e_1975", None, ("c_sgk_1975",)),
    ("Hành trình của bạn", "Cảm ơn bạn đã đi hết chặng đường giữ nước. Bấm phím cách để nghe Cụ Đồ Sử dặn dò.", 9.0, "_e_you", None,
     None),
)
YEARS = ((938, "Bạch Đằng"), (1077, "Như Nguyệt"), (1288, "Bạch Đằng"), (1428, "Bình Ngô đại cáo"), (1945, "Tuyên ngôn Độc lập"),
         (1954, "Điện Biên Phủ"))
CROWD = ("Villager", "Villager3", "Villager4", "Woman", "Boy", "OldWoman", "OldMan", "Villager3")
_cache: dict = {}


def star_points(cx: float, cy: float, r: float, turn: float = -90) -> list[tuple[float, float]]:
    """Năm cánh sao đều, đỉnh hướng lên."""
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.382
        a = math.radians(turn + i * 36)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def flag_surface(w: int, h: int, text: str | None = None) -> pygame.Surface:
    """Cờ đỏ sao vàng (có thể kèm dòng chữ trên cờ), vẽ một lần cho mỗi cỡ."""
    key = ("flag", w, h, text)
    if key not in _cache:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill(RED)
        cy = h * 0.5 + (h * 0.08 if text else 0)
        pygame.draw.polygon(s, YELLOW, star_points(w * 0.5, cy, h * (0.28 if text else 0.33)))
        if text:
            f = fonts.font("bold", max(8, h // 9))
            fonts.text(s, text, f, YELLOW, (w // 2, max(2, h // 16)), "midtop")
        _cache[key] = s
    return _cache[key]


def draw_flag(screen, x: float, y: float, w: int, h: int, t: float, text: str | None = None, amp: float | None = None):
    """Cờ bay trong gió: cắt lá cờ thành từng dải dọc, đẩy lên xuống theo sóng, càng xa cán càng lượn nhiều."""
    src = flag_surface(w, h, text)
    amp = h * 0.08 if amp is None else amp
    step = 3
    for i in range(0, w, step):
        k = i / max(1, w)
        dy = math.sin(t * 6.0 - i * 0.09) * amp * k
        shade = 1.0 - 0.18 * (0.5 + 0.5 * math.sin(t * 6.0 - i * 0.09 + 1.2)) * k
        part = src.subsurface((i, 0, min(step, w - i), h)).copy()
        if shade < 0.99:
            v = int(255 * shade)
            part.fill((v, v, v, 255), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(part, (x + i, y + dy))


def draw_pole(screen, x: float, top: float, bottom: float, width: int = 4):
    pygame.draw.rect(screen, OUTLINE, (x - width // 2 - 1, top - 6, width + 2, bottom - top + 6))
    pygame.draw.rect(screen, (196, 186, 170), (x - width // 2, top - 5, width, bottom - top + 5))
    pygame.draw.circle(screen, (236, 196, 90), (int(x), int(top - 7)), width + 1)


class EndingScene(Scene):
    def __init__(self, app, then=None):
        super().__init__(app)
        self.then = then  # cảnh tiếp theo (lời dặn của Cụ Đồ Sử); None thì quay lại cảnh trước
        self.i = 0
        self.t = 0.0
        self.time = 0.0
        self.raised = False
        self.shade = pygame.Surface((W, H))
        self.shade.fill(theme.LACQUER)
        self.cites = self.state.sources.get("citations", {})
        self.books = self.state.sources.get("sources", {})
        self.app.audio.music("title")

    # ----- điều khiển -----
    def _done(self):
        if self.then is not None:
            self.app.scenes.replace(self.then)
        else:
            self.app.scenes.pop(None)

    def _goto(self, i: int):
        self.i = max(0, min(len(BEATS) - 1, i))
        self.t = 0.0
        self.raised = False

    @property
    def last(self) -> bool:
        return self.i == len(BEATS) - 1

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._done()
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_RIGHT, pygame.K_e):
                if self.last:
                    self._done()
                else:
                    self._goto(self.i + 1)
            elif event.key == pygame.K_LEFT:
                self._goto(self.i - 1)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.last:
                self._done()
            else:
                self._goto(self.i + 1)

    def update(self, dt):
        self.t += dt
        self.time += dt
        if self.t >= BEATS[self.i][2] and not self.last:
            self._goto(self.i + 1)

    # ----- tiện ích vẽ -----
    def _person(self, screen, name, x, y, facing="down", bob=0.0, scale=4):
        cast = sprites.cast(name, scale) if scale != 4 else sprites.cast(name)
        img = cast.walk[facing][0]
        screen.blit(img, img.get_rect(midbottom=(x, y - bob)))

    def _walker(self, screen, name, x, y, facing="right"):
        img = sprites.cast(name).walk[facing][int(self.time * 8 + x) % 4]
        screen.blit(img, img.get_rect(midbottom=(x, y)))

    def _hand_flag(self, screen, x, y, phase):
        """Lá cờ nhỏ cầm tay: cán chéo, cờ phất qua lại."""
        swing = math.sin(self.time * 7 + phase) * 6
        top = (x + 10 + swing, y - 78)
        pygame.draw.line(screen, OUTLINE, (x + 6, y - 34), top, 3)
        pygame.draw.line(screen, (210, 196, 170), (x + 6, y - 34), top, 1)
        draw_flag(screen, top[0], top[1], 30, 20, self.time + phase, amp=2.5)

    def _cheer(self, screen, k):
        if k > 0.55:
            for i, (x, y) in enumerate(((360, 300), (930, 320), (640, 250))):
                if int(self.time * 2 + i) % 3 != 2:
                    ui.tag(screen, "Hoan hô!", (x, y), theme.PAPER, theme.INK, 16, "midbottom")

    # ----- từng đoạn -----
    def _e_open(self, screen, k):
        screen.fill(theme.LACQUER)
        drum = art.drum(520, theme.GOLD_DARK, 110)
        screen.blit(drum, drum.get_rect(center=(W // 2, 250)))
        fonts.text(screen, "HƠN MỘT NGHÌN NĂM GIỮ NƯỚC", fonts.font("black", 50), theme.GOLD_LIGHT, (W // 2, 200), "center",
                   shadow=(60, 20, 14))
        fonts.text(screen, "Từ cọc gỗ Bạch Đằng đến lòng chảo Điện Biên", fonts.font("serif", 24), theme.PAPER, (W // 2, 258), "center",
                   shadow=(24, 16, 14))
        x0, gap = 130, 204
        pygame.draw.line(screen, theme.GOLD_DARK, (x0, 420), (x0 + gap * 5, 420), 4)
        for i, (year, name) in enumerate(YEARS):
            appear = min(1.0, max(0.0, k * 7 - i * 0.9))
            if appear <= 0:
                continue
            cx = x0 + i * gap
            pygame.draw.circle(screen, theme.LACQUER_RED, (cx, 420), int(16 * appear))
            pygame.draw.circle(screen, theme.GOLD_LIGHT, (cx, 420), int(16 * appear), 3)
            fonts.text(screen, year, fonts.font("black", 28), theme.GOLD_LIGHT, (cx, 380), "midbottom")
            fonts.text(screen, name, fonts.font("semi", 16), theme.PAPER, (cx, 450), "midtop")

    def _e_dbp(self, screen, k):
        cx, ground = 640, 470
        # căn hầm chỉ huy: ụ đất có bao cát, cửa hầm tối
        pygame.draw.ellipse(screen, OUTLINE, (cx - 170, ground - 92, 340, 130))
        pygame.draw.ellipse(screen, (118, 92, 60), (cx - 166, ground - 88, 332, 122))
        for i in range(9):
            bx = cx - 140 + i * 32
            by = ground - 70 - int(14 * math.sin(i / 8 * math.pi))
            pygame.draw.ellipse(screen, OUTLINE, (bx - 2, by - 2, 34, 20))
            pygame.draw.ellipse(screen, (176, 152, 104), (bx, by, 30, 16))
        pygame.draw.rect(screen, OUTLINE, (cx - 34, ground - 40, 68, 46))
        pygame.draw.rect(screen, (34, 26, 22), (cx - 30, ground - 36, 60, 42))
        top, bottom = ground - 290, ground - 80
        draw_pole(screen, cx, top, bottom)
        rise = min(1.0, max(0.0, (k - 0.08) / 0.42))
        fy = bottom - 90 - (bottom - 90 - top) * rise
        draw_flag(screen, cx + 2, fy, 150, 96, self.time, "QUYẾT CHIẾN QUYẾT THẮNG")
        if rise >= 1.0 and not self.raised:
            self.raised = True
            self.app.audio.play("thang")
        bob = 10 * abs(math.sin(self.time * 6)) if rise >= 1.0 else 0
        for i, x in enumerate((300, 380, 460, 820, 900, 980)):
            self._person(screen, "BoDoi", x, ground + 48, "up" if rise < 1 else "down", bob if i % 2 == 0 else bob * 0.6)
        if rise >= 1.0:
            self._cheer(screen, k)

    def _e_gionevo(self, screen, k):
        screen.fill(theme.LACQUER)
        page = pygame.Rect(120, 60, 600, 470)
        ui.paper_panel(screen, page)
        fonts.text(screen, "HIỆP ĐỊNH GIƠNEVƠ", fonts.font("black", 30), theme.LACQUER_RED, (page.centerx, page.y + 30), "midtop")
        fonts.text(screen, "về đình chỉ chiến sự ở Việt Nam", fonts.font("serif", 20), theme.INK, (page.centerx, page.y + 74), "midtop")
        shown = int(min(1.0, k / 0.6) * 9)
        for i in range(shown):
            w = page.w - 120 - (i % 3) * 40
            pygame.draw.rect(screen, theme.PAPER_3, (page.x + 60, page.y + 130 + i * 30, w, 8))
        if k > 0.6:
            stamp = art.stamp("Hoà bình", 120)
            screen.blit(stamp, stamp.get_rect(center=(page.right - 110, page.bottom - 90)))
        # dải đất nước từ Bắc xuống Nam, đường đứt ở vĩ tuyến 17
        strip = pygame.Rect(860, 60, 130, 470)
        pygame.draw.rect(screen, OUTLINE, strip.inflate(8, 8))
        pygame.draw.rect(screen, (196, 176, 120), strip)
        line_y = strip.y + int(strip.h * 0.45)
        fonts.text(screen, "Miền Bắc", fonts.font("bold", 18), theme.INK, (strip.centerx, strip.y + 80), "center")
        fonts.text(screen, "Miền Nam", fonts.font("bold", 18), theme.INK, (strip.centerx, strip.bottom - 80), "center")
        if k > 0.3:
            for x in range(strip.x - 40, strip.right + 40, 18):
                pygame.draw.line(screen, theme.RED_BRIGHT, (x, line_y), (x + 10, line_y), 4)
            ui.tag(screen, "Vĩ tuyến 17: giới tuyến quân sự tạm thời", (strip.centerx, line_y + 14), theme.LACQUER, theme.GOLD_LIGHT, 14,
                   "midtop")
            ui.tag(screen, "Hẹn tổng tuyển cử: tháng 7/1956", (strip.centerx, line_y - 14), theme.LACQUER_RED, theme.GOLD_LIGHT, 14,
                   "midbottom")

    def _street(self) -> pygame.Surface:
        """Một dãy phố Hà Nội: nhà ống mái ngói, cửa chớp, vỉa hè hai bên, mặt đường ở giữa. Vẽ một lần."""
        if "street" in _cache:
            return _cache["street"]
        s = pygame.Surface((W, CAPTION.y))
        for y in range(0, 200, 4):  # trời thu
            v = y / 200
            pygame.draw.rect(s, (int(150 + 70 * v), int(196 + 30 * v), int(232 - 10 * v)), (0, y, W, 4))
        base = 330
        x = 0
        for i in range(30):
            w, wall, floors = HOUSES[i % len(HOUSES)]
            top = base - floors * 62 - 10
            pygame.draw.rect(s, OUTLINE, (x, top - 2, w, base - top + 2))
            pygame.draw.rect(s, wall, (x + 2, top, w - 4, base - top))
            pygame.draw.polygon(s, OUTLINE, ((x - 4, top + 4), (x + 14, top - 26), (x + w - 14, top - 26), (x + w + 4, top + 4)))
            pygame.draw.polygon(s, (150, 62, 40), ((x - 1, top + 2), (x + 16, top - 23), (x + w - 16, top - 23), (x + w + 1, top + 2)))
            for f in range(floors):
                fy = base - (f + 1) * 62
                for wx in (x + w // 4, x + w * 3 // 4):
                    if f == 0 and wx < x + w // 2:  # tầng trệt: cửa hàng mở ra phố
                        pygame.draw.rect(s, OUTLINE, (x + 10, fy + 12, w // 2 - 4, 50))
                        pygame.draw.rect(s, (70, 48, 36), (x + 13, fy + 15, w // 2 - 10, 47))
                        continue
                    pygame.draw.rect(s, OUTLINE, (wx - 15, fy + 12, 30, 38))
                    pygame.draw.rect(s, (72, 116, 84), (wx - 13, fy + 14, 12, 34))
                    pygame.draw.rect(s, (72, 116, 84), (wx + 1, fy + 14, 12, 34))
                if f > 0:  # ban công
                    pygame.draw.rect(s, OUTLINE, (x + 6, fy + 52, w - 12, 8))
                    pygame.draw.rect(s, (200, 196, 186), (x + 8, fy + 53, w - 16, 5))
            x += w
            if x > W:
                break
        pygame.draw.rect(s, (182, 170, 150), (0, base, W, ROAD - base))  # vỉa hè
        for xx in range(0, W, 48):
            pygame.draw.line(s, (160, 148, 128), (xx, base), (xx, ROAD), 1)
        pygame.draw.rect(s, OUTLINE, (0, ROAD - 3, W, 4))
        pygame.draw.rect(s, (112, 106, 100), (0, ROAD, W, 100))  # mặt đường
        pygame.draw.rect(s, OUTLINE, (0, ROAD + 99, W, 4))
        pygame.draw.rect(s, (182, 170, 150), (0, ROAD + 102, W, CAPTION.y - ROAD - 102))
        _cache["street"] = s
        return s

    def _e_hanoi(self, screen, k):
        screen.blit(self._street(), (0, 0))
        x = 0
        for i in range(30):  # cờ treo trước cửa từng nhà
            w, _wall, floors = HOUSES[i % len(HOUSES)]
            if floors > 1:
                fy = 330 - 2 * 62
                draw_pole(screen, x + w // 2 - 20, fy + 4, fy + 52, 2)
                draw_flag(screen, x + w // 2 - 18, fy + 6, 42, 28, self.time + i, amp=2.0)
            x += w
            if x > W:
                break
        for i in range(11):  # dân trên vỉa hè phía trong phất cờ
            x = 70 + i * 118
            self._person(screen, CROWD[i % len(CROWD)], x, ROAD - 6, "down", 4 * abs(math.sin(self.time * 5 + i)))
            self._hand_flag(screen, x, ROAD - 6, i * 0.7)
        # đoàn quân đi từ trái sang phải, người đi đầu cầm cờ lớn
        lead = -120 + (W + 520) * min(1.0, k / 0.85)
        for row in range(2):
            for col in range(7):
                x = lead - 70 - col * 72
                if -40 < x < W + 40:
                    self._walker(screen, "BoDoi", x, ROAD + 58 + row * 28)
        draw_pole(screen, lead + 8, ROAD - 60, ROAD + 64, 3)
        draw_flag(screen, lead + 10, ROAD - 58, 96, 62, self.time)
        self._walker(screen, "BoDoi", lead, ROAD + 70)
        for i in range(11):  # dân trên vỉa hè phía ngoài, quay lưng lại
            x = 130 + i * 118
            self._person(screen, CROWD[(i + 3) % len(CROWD)], x, CAPTION.y - 2, "up", 4 * abs(math.sin(self.time * 5 + i * 1.3)))
            self._hand_flag(screen, x, CAPTION.y - 2, i * 1.1 + 2)
        if k > 0.3:
            self._cheer(screen, 0.6)

    def _e_cotco(self, screen, k):
        for y in range(0, 566, 4):  # trời chiều
            v = y / 566
            pygame.draw.rect(screen, (int(120 + 110 * v), int(170 + 40 * v), int(214 - 40 * v)), (0, y, W, 4))
        cx, ground = 640, 520
        pygame.draw.rect(screen, (196, 180, 150), (0, 500, W, CAPTION.y - 500))  # sân
        pygame.draw.rect(screen, OUTLINE, (0, 498, W, 3))
        stone, stone_d, stone_l = (150, 120, 92), (104, 82, 62), (182, 152, 118)
        for i, (w, h) in enumerate(((380, 32), (300, 32), (220, 32))):  # ba tầng đế vuông
            r = pygame.Rect(0, 0, w, h)
            r.midbottom = (cx, ground - i * h)
            pygame.draw.rect(screen, OUTLINE, r.inflate(6, 6))
            pygame.draw.rect(screen, stone, r)
            pygame.draw.rect(screen, stone_l, (r.x, r.y, r.w, 5))
            pygame.draw.rect(screen, stone_d, (r.x, r.bottom - 5, r.w, 5))
        body = pygame.Rect(0, 0, 84, 150)  # thân tháp tám cạnh: hai dải tối hai bên cho ra mặt nghiêng
        body.midbottom = (cx, ground - 96)
        pygame.draw.rect(screen, OUTLINE, body.inflate(6, 6))
        pygame.draw.rect(screen, stone, body)
        pygame.draw.rect(screen, stone_d, (body.x, body.y, 16, body.h))
        pygame.draw.rect(screen, stone_d, (body.right - 16, body.y, 16, body.h))
        for yy in range(body.y + 20, body.bottom - 10, 34):
            pygame.draw.rect(screen, (40, 30, 26), (cx - 5, yy, 10, 14))
        lamp = pygame.Rect(0, 0, 66, 34)  # vọng canh trên đỉnh
        lamp.midbottom = (cx, body.y)
        pygame.draw.rect(screen, OUTLINE, lamp.inflate(6, 6))
        pygame.draw.rect(screen, stone_l, lamp)
        for wx in range(lamp.x + 8, lamp.right - 6, 14):
            pygame.draw.rect(screen, (40, 30, 26), (wx, lamp.y + 10, 7, 14))
        top, bottom = lamp.y - 130, lamp.y
        draw_pole(screen, cx, top, bottom, 5)
        rise = min(1.0, max(0.0, (k - 0.05) / 0.45))
        fy = bottom - 72 - (bottom - 72 - top) * rise
        draw_flag(screen, cx + 3, fy, 108, 72, self.time)
        if rise >= 1.0 and not self.raised:
            self.raised = True
            self.app.audio.play("thang")
        for i in range(14):  # bộ đội và người dân đứng dưới sân
            x = 60 + i * 88
            who = "BoDoi" if i % 3 != 1 else CROWD[i % len(CROWD)]
            self._person(screen, who, x, 560, "up", 3 * abs(math.sin(self.time * 4 + i)) if rise >= 1 else 0)
            if who != "BoDoi" and rise >= 1:
                self._hand_flag(screen, x, 560, i)

    def _e_1975(self, screen, k):
        for y in range(0, 566, 4):
            v = y / 566
            pygame.draw.rect(screen, (int(60 + 60 * v), int(14 + 10 * v), int(12 + 8 * v)), (0, y, W, 4))
        draw_pole(screen, 350, 58, CAPTION.y - 6, 6)
        draw_flag(screen, 354, 60, 520, 330, self.time, amp=7)
        if k > 0.25:
            fonts.text(screen, "30 · 4 · 1975", fonts.font("black", 54), theme.GOLD_LIGHT, (W // 2 + 4, 448), "center", shadow=(60, 20, 14))
        if k > 0.5:
            fonts.text(screen, "Đất nước thống nhất, Bắc Nam sum họp một nhà", fonts.font("serif", 24), theme.PAPER, (W // 2, 502), "center",
                       shadow=(24, 16, 14))

    def _e_you(self, screen, k):
        st = self.state
        screen.fill(theme.LACQUER)
        hero = outfit.hero_cast(st.gear, 8).walk["down"][0]
        screen.blit(hero, hero.get_rect(midbottom=(250, 470)))
        draw_flag(screen, 330, 160, 120, 80, self.time)
        draw_pole(screen, 328, 154, 470, 4)
        panel = pygame.Rect(520, 60, 700, 470)
        ui.paper_panel(screen, panel)
        fonts.text(screen, "Hành trình của bạn", fonts.font("serif", 30), theme.LACQUER_RED, (panel.x + 30, panel.y + 24))
        total_relics = sum(len(st.levels[x]["relics"]) for x in st.order)
        rows = (
            ("Di tích đã đóng dấu", f"{len(st.stamps)}/{total_relics}"),
            ("Điểm học sử", f"{st.total_points}"),
            ("Câu hỏi đã trả lời đúng", f"{len(st.solved)}"),
            ("Cấp, cảnh giới", f"cấp {st.level} · {st.realm_name()}"),
            ("Sức mạnh", f"{st.power_rating()}"),
            ("Trang sổ bóng giặc đã mở", f"{len(st.bestiary)}/{len(rpg.MOBS)}"),
            ("Vùng luyện đã tới", f"{len(st.field_log)}/{len(st.fields)}"),
        )
        for i, (label, value) in enumerate(rows):
            if k * 9 < i:
                break
            y = panel.y + 90 + i * 50
            fonts.text(screen, label, fonts.font("semi", 20), theme.INK, (panel.x + 34, y))
            fonts.text(screen, value, fonts.font("bold", 22), theme.LACQUER_RED, (panel.right - 34, y), "topright")
            pygame.draw.line(screen, theme.PAPER_3, (panel.x + 30, y + 38), (panel.right - 30, y + 38), 1)

    # ----- vẽ chung -----
    def _source_line(self, cites) -> str:
        names = []
        for c in cites or ():
            book = self.books.get(self.cites.get(c, {}).get("source", ""), {}).get("title")
            if book and book not in names:
                names.append(book)
        return "Nguồn: " + "; ".join(names) if names else ""

    def draw(self, screen):
        title, text, dur, method, bg, cites = BEATS[self.i]
        k = min(1.0, self.t / dur)
        screen.fill(theme.LACQUER)
        if bg:
            screen.blit(diorama.scene(bg), (0, 0))
        getattr(self, method)(screen, k)
        if title:
            if self.last and self.then is None:  # xem lại từ màn hình tựa đề: không còn lời dặn phía sau
                text = "Cảm ơn bạn đã đi hết chặng đường giữ nước. Bấm phím cách để quay lại."
            ui.lacquer_panel(screen, CAPTION, 246)
            fonts.text(screen, title, fonts.font("bold", 26), theme.GOLD_LIGHT, (CAPTION.x + 30, CAPTION.y + 16))
            fonts.paragraph(screen, text, fonts.font("serif", 19), theme.PAPER, CAPTION.x + 30, CAPTION.y + 56, CAPTION.w - 60, gap=2)
            src = self._source_line(cites)
            if src:  # nguồn nằm trên khung lời dẫn, không đè lên tiêu đề
                ui.tag(screen, src[:170], (CAPTION.right - 6, CAPTION.y - 6), theme.LACQUER, theme.PAPER_3, 12, "bottomright")
        n = len(BEATS)
        x = W // 2 - n * 11
        for i in range(n):
            color = theme.GOLD_LIGHT if i == self.i else theme.GOLD_DARK if i < self.i else theme.LACQUER_2
            pygame.draw.rect(screen, OUTLINE, (x + i * 22 - 2, 18, 18, 14))
            pygame.draw.rect(screen, color, (x + i * 22, 20, 14, 10))
        if self.t < FADE:
            self.shade.set_alpha(int(255 * (1 - self.t / FADE)))
            screen.blit(self.shade, (0, 0))
