"""Trailer hướng dẫn: tự chạy gần ba phút, diễn từng việc người mới cần biết bằng chính hình trong game.

Đi theo đúng thứ tự người mới gặp: vòng chơi, màn hình, các nhân vật, học một di tích từ đầu tới cuối, đánh nhau, lên cấp,
tu luyện, cảnh giới, lò rèn, vùng luyện, sổ bóng giặc, câu cá, chơi cùng bạn bè và chat.

Hiện một lần khi bắt đầu ván mới, xem lại được từ màn hình tựa đề và menu tạm dừng. Phím cách để sang đoạn sau, Esc để bỏ
qua. Công cụ tools/make_trailer_video.py cũng dùng đúng scene này để xuất video cho trang giới thiệu.
"""

from __future__ import annotations

import math

import pygame
from core import art, diorama, fleet, fonts, fx, outfit, rpg, sprites, theme, ui
from core.cinematic import TideMemory
from core.scene import Scene
from core.worldgen import CATALOG

from scenes.fishing import _flames, _hearth, _skewer
from scenes.honor import board_sprite

W, H = theme.WIDTH, theme.HEIGHT
CAPTION = pygame.Rect(40, 566, 1200, 132)
FADE = 0.3
ROAD_Y = 530
CROSS_X = 672
PLAYER = "SamuraiBlue"
OUTLINE = (24, 16, 14)
# (tiêu đề, lời dẫn, số giây, hàm vẽ, cảnh nền)
BEATS = (
    ("", "", 3.5, "_b_open", None),
    ("Vòng chơi của Sử Ký Điều Tra", "Học sử là con đường chính: mỗi di tích cho điểm, điểm kỹ năng và tinh hoa. Đánh quái giúp "
     "lên cấp, nhưng chỉ tới giới hạn của cảnh giới; muốn mạnh hơn nữa thì phải học tiếp.", 9.0, "_b_loop", None),
    ("Đi lại", "Dùng các phím W, A, S, D hoặc phím mũi tên. Bấm chuột vào đâu, nhân vật tự đi tới đó.", 5.0, "_b_walk", "huong_dan"),
    ("Màn hình chơi", "Góc trái trên: việc cần làm. Góc trái dưới: cấp, tiền quan, thuốc. Góc phải dưới: bản đồ nhỏ. Mọi bảng "
     "khác nằm trong nút ba gạch ở góc phải trên, có ghi phím tắt.", 8.0, "_b_menu", "huong_dan"),
    ("Luôn biết việc cần làm", "Khung ở góc trái ghi việc cần làm ngay. Mũi tên đỏ ở mép màn hình chỉ đường tới nơi đó.", 5.5, "_b_track", "huong_dan"),
    ("Những người bạn sẽ gặp", "Mỗi người giữ một việc. Đến gần, thấy chữ E hiện dưới chân họ thì bấm E để nói chuyện.", 9.0, "_b_npcs", None),
    ("Nghe người giữ ký ức kể chuyện", "Thấy dấu chấm than thì đến gần rồi bấm E. Mỗi di tích bắt đầu từ một câu chuyện.", 6.0, "_b_talk", "huong_dan"),
    ("Trả lời để đi tiếp", "Đúng ngay lần đầu được nhiều điểm nhất. Sai thì đọc lời giải, câu đó sẽ quay lại khi ôn tập.", 6.0, "_b_ask", "huong_dan"),
    ("Nhặt mảnh ghép tư liệu", "Đi qua tờ giấy đang phát sáng là nhặt được. Tư liệu được cất vào Sổ tay, mở bằng phím N.", 5.0, "_b_scroll", "huong_dan"),
    ("Mảnh cuối có kẻ canh", "Mảnh ghép cuối của mỗi di tích có bóng giặc canh giữ. Đứng gần bấm F để đánh, thắng rồi mới nhặt "
     "được. Cuối mỗi màn còn một trùm.", 7.0, "_b_guard", "huong_dan"),
    ("Cờ đỏ là trận đánh", "Mỗi trận diễn theo cách đánh của trận thật, như cắm cọc rồi chờ con nước ở sông Bạch Đằng.", 7.0, "_b_battle", None),
    ("Đóng dấu, rồi về báo cáo già làng", "Xong các bước, di tích được đóng dấu vào Hộ chiếu. Về báo cáo Cụ Đồ Sử để nhận thưởng và việc tiếp theo.", 5.5, "_b_stamp", "den_tran"),
    ("Dựng dòng thời gian, rồi qua cổng", "Đủ dấu thì về gặp Cụ Đồ Sử xếp lại các sự kiện. Cổng dịch chuyển mở, bước vào là sang giai đoạn mới.", 7.0, "_b_gate", "huong_dan"),
    ("Đánh nhau thế nào", "Trong trận: W, A, S, D để đi, bấm chuột trái để chém, Shift để né, phím 1 đến 4 để tung chiêu. "
     "Q uống thuốc nam, E ăn cá nướng.", 8.0, "_b_fight", "vo_dai"),
    ("Lên cấp, tiềm năng, tiền quan", "Hạ quái được kinh nghiệm, tiềm năng, tiền quan, đôi khi rơi thuốc nam. Tên quái màu xanh là "
     "dễ, vàng là ngang sức, đỏ là mạnh hơn bạn. Quái hạ xong một lúc lại mọc lại.", 8.0, "_b_grow", "huong_dan"),
    ("Tu luyện (phím K)", "Tiềm năng dùng để tăng sức đánh, thể lực, nhanh nhẹn, trí tuệ. Chiêu thức học bằng điểm kỹ năng, mà "
     "điểm kỹ năng chỉ có khi học sử.", 7.5, "_b_arena", "vo_dai"),
    ("Cảnh giới và đột phá", "Mỗi cảnh giới chặn cấp tối đa. Muốn đột phá phải đủ tinh hoa: nghe hồi ức, khám phá được 1; ghép "
     "xong tư liệu, phá xong vụ điều tra được 2.", 8.5, "_b_realm", None),
    ("Lò rèn và túi đồ", "Thợ rèn đứng ngay chỗ xuất phát, bán vũ khí, áo, mũ, giày, găng và cần câu. Mặc vào là nhân vật đổi "
     "dáng. Bấm B để mở túi đồ.", 7.5, "_b_shop", "huong_dan"),
    ("Vùng luyện", "Học xong một di tích thì biển VÙNG LUYỆN gần đó mở đường. Nghe người kể chuyện, trả lời một câu, rồi luyện "
     "với quân giặc đúng thời. Mỗi vùng có một kẻ mạnh nhất.", 8.0, "_b_field", "huong_dan"),
    ("Sổ bóng giặc (phím G)", "Hạ mỗi loại quân lần đầu thì mở một trang: đội quân đó là ai, sử chép gì, có ghi nguồn.", 6.5, "_b_bestiary", None),
    ("Câu cá, nướng cá", "Mua cần câu tre, đứng sát mép nước bấm C. Phao chìm, hiện dấu chấm than thì bấm C kéo lên. Nướng ở "
     "bếp lửa, vào trận bấm E ăn cho lại sức.", 8.0, "_b_fish", "huong_dan"),
    ("Còn nhiều thứ để khám phá", "Không bắt buộc, nhưng có thêm chuyện để nghe, thêm tinh hoa và điểm kỹ năng.", 6.0, "_b_extras", "huong_dan"),
    ("Chơi cùng bạn bè", "Bấm vào người chơi khác để mời tổ đội (chia kinh nghiệm), kết đồng minh hay thách đấu thật trên võ đài. "
     f"Bấm L để chat: cùng map miễn phí, kênh thế giới {rpg.WORLD_CHAT_COST} quan một tin. Bảng vàng ghi 20 người giỏi nhất.", 9.0,
     "_b_social", "huong_dan"),
    ("Lạc đường thì bấm J", "Bảng Lộ trình cho biết bạn đang ở đâu và cần làm gì tiếp theo.", 5.0, "_b_end", "huong_dan"),
)
EXTRAS = (
    ("ui/emote_question.png", "Dấu hỏi trên map", "chuyện lạ chờ khám phá"),
    ("ui/book.png", "Cửa có dấu chấm than", "vào trong để điều tra"),
    ("horse", "Ngựa và chiến mã", "R cưỡi ngựa có sẵn, H gọi chiến mã (từ cấp 3)"),
    ("boat", "Bến thuyền", "chèo ra sông tìm bãi cọc cũ"),
)
CARDS = ((938, "Ngô Quyền thắng ở Bạch Đằng"), (1077, "Phòng tuyến Như Nguyệt"), (1288, "Bãi cọc Yên Giang"))


class TrailerScene(Scene):
    def __init__(self, app, recording: bool = False):
        super().__init__(app)
        self.recording = recording  # xuất video thì không vẽ nút bấm
        self.i = 0
        self.t = 0.0
        self.time = 0.0
        self.fx = fx.Fx(self.state.settings["violence"])
        self.cast = outfit.hero_cast({"giap": "ao_vai", "mu": "khan_chit"})
        self.cine: TideMemory | None = None
        self.shade = pygame.Surface((W, H))
        self.shade.fill(theme.LACQUER)
        self.next_hit = 0.0
        self.foe_hp = 1.0
        self.group = ui.ButtonGroup()
        self.skip = self.group.add(ui.Button((W - 150, 12, 136, 40), "Bỏ qua", self._done, "ghost", size=15))
        self.go = ui.Button((W // 2 - 130, 470, 260, 56), "Vào chơi", self._done, "gold", size=20)
        self.app.audio.music("road")

    # ----- điều khiển -----
    def _done(self):
        self.app.scenes.pop(None)

    def _goto(self, i):
        self.i = max(0, min(len(BEATS) - 1, i))
        self.t = 0.0
        self.fx = fx.Fx(self.state.settings["violence"])
        self.next_hit = 0.0
        self.foe_hp = 1.0
        if BEATS[self.i][3] == "_b_battle":
            self.cine = TideMemory(self.fx, self.app.audio)
            self.cine.set_beat("crash")
        else:
            self.cine = None

    @property
    def last(self) -> bool:
        return self.i == len(BEATS) - 1

    def handle(self, event):
        if self.last and self.go.handle(event):
            return
        if event.type != pygame.KEYDOWN and self.group.handle(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._done()
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_RIGHT):
                if self.last:
                    self._done()
                else:
                    self._goto(self.i + 1)
            elif event.key == pygame.K_LEFT:
                self._goto(self.i - 1)

    def update(self, dt):
        self.t += dt
        self.time += dt
        self.fx.update(dt)
        if self.cine:
            self.cine.update(dt)
        if self.t >= BEATS[self.i][2] and not self.last:
            self._goto(self.i + 1)

    # ----- tiện ích vẽ -----
    @staticmethod
    def _along(points, k):
        """Vị trí trên đường gấp khúc ứng với tỉ lệ k, kèm hướng đi và có đang đi hay không."""
        lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:], strict=False)]
        left = max(0.0, min(1.0, k)) * sum(lengths)
        for (a, b), length in zip(zip(points, points[1:], strict=False), lengths, strict=False):
            if left <= length:
                f = left / max(1.0, length)
                dx, dy = b[0] - a[0], b[1] - a[1]
                facing = ("right" if dx > 0 else "left") if abs(dx) > abs(dy) else ("down" if dy > 0 else "up")
                return a[0] + dx * f, a[1] + dy * f, facing, k < 1.0
            left -= length
        return points[-1][0], points[-1][1], "down", False

    def _person(self, screen, cast, x, y, facing="down", moving=False):
        img = cast.walk[facing][int(self.time * 8) % 4 if moving else 0]
        screen.blit(img, img.get_rect(midbottom=(x, y)))

    def _player(self, screen, points, k, end_facing="right"):
        x, y, facing, moving = self._along(points, k)
        self._person(screen, self.cast, x, y, facing if moving else end_facing, moving)
        return x, y

    @staticmethod
    def _key(screen, label, x, y, on=False, w=46):
        rect = pygame.Rect(x, y + (3 if on else 0), w, 44)
        pygame.draw.rect(screen, OUTLINE, rect.inflate(6, 6))
        pygame.draw.rect(screen, theme.GOLD if on else theme.PAPER_2, rect)
        if not on:
            pygame.draw.rect(screen, theme.PAPER_3, (rect.x, rect.bottom - 5, rect.w, 5))
        fonts.text(screen, label, fonts.font("bold", 20), theme.INK, rect.center, "center")

    def _mark(self, screen, name, x, y):
        img = sprites.icon(name)
        screen.blit(img, img.get_rect(midbottom=(x, y + 4 * math.sin(self.time * 5))))

    # ----- từng đoạn -----
    def _b_open(self, screen, k):
        screen.fill(theme.LACQUER)
        drum = art.drum(520, theme.GOLD_DARK)
        screen.blit(drum, drum.get_rect(center=(W // 2, H // 2)))
        fonts.text(screen, "SỬ KÝ ĐIỀU TRA", fonts.font("black", 72), theme.GOLD_LIGHT, (W // 2, H // 2 - 50), "center", shadow=(60, 20, 14))
        fonts.text(screen, "Người mới cần làm gì? Xem gần ba phút là nắm hết cách chơi.", fonts.font("serif", 24), theme.PAPER,
                   (W // 2, H // 2 + 30), "center", shadow=(24, 16, 14))
        fonts.text(screen, "Phím cách: sang đoạn sau  ·  mũi tên trái: xem lại  ·  Esc: bỏ qua", fonts.font("ui", 16), theme.PAPER_3,
                   (W // 2, H // 2 + 72), "center")

    def _b_walk(self, screen, k):
        _x, _y = self._player(screen, ((180, ROAD_Y), (CROSS_X, ROAD_Y), (CROSS_X, 250)), k / 0.9, "up")
        going_up = k > 0.56
        x0, y0 = 980, 300
        self._key(screen, "W", x0 + 56, y0, going_up and k < 0.9)
        self._key(screen, "A", x0, y0 + 56)
        self._key(screen, "S", x0 + 56, y0 + 56)
        self._key(screen, "D", x0 + 112, y0 + 56, not going_up)

    def _b_track(self, screen, k):
        self._player(screen, ((280, ROAD_Y), (880, ROAD_Y)), k / 0.95)
        box = pygame.Rect(12, 10, 440, 104)
        ui.lacquer_panel(screen, box, 244)
        fonts.text(screen, "Những khúc sông giữ nước", fonts.font("serif", 18), theme.GOLD_LIGHT, (28, 20))
        fonts.text(screen, "938 – 1288", fonts.font("ui", 13), theme.PAPER_3, (28, 44))
        ui.progress_bar(screen, (28, 64, 408, 7), 0.05)
        fonts.text(screen, "Đi tới Đường Lâm", fonts.font("semi", 14), theme.PAPER, (28, 78))
        if int(self.time * 3) % 2 == 0:
            pygame.draw.rect(screen, theme.GOLD_LIGHT, box.inflate(8, 8), 3)
        bob = 8 * ui.pulse(self.time, 5)
        ax, ay = W - 70 + bob, ROAD_Y - 60
        points = [(ax + 28, ay), (ax - 18, ay - 22), (ax - 18, ay + 22)]
        pygame.draw.polygon(screen, theme.RED_BRIGHT, points)
        pygame.draw.polygon(screen, theme.WHITE, points, 3)

    def _b_talk(self, screen, k):
        keeper = sprites.cast("OldWoman")
        kx = 800
        arrived = k >= 0.45
        self._person(screen, keeper, kx, ROAD_Y, "left" if arrived else "down")
        self._player(screen, ((260, ROAD_Y), (kx - 70, ROAD_Y)), k / 0.45)
        if not arrived:
            self._mark(screen, "ui/emote_alert.png", kx, ROAD_Y - 66)
            return
        pressed = k > 0.55
        if not pressed:
            ui.tag(screen, "E  Nói chuyện", (kx, ROAD_Y + 6), theme.LACQUER, theme.GOLD_LIGHT, 13, "midtop")
        self._key(screen, "E", 980, 330, pressed)
        if pressed:
            box = pygame.Rect(kx - 300, ROAD_Y - 190, 400, 92)
            ui.paper_panel(screen, box)
            fonts.paragraph(screen, "Cháu ngồi xuống đây, bà kể cho nghe chuyện đất này ngày xưa.", fonts.font("semi", 16), theme.INK, box.x + 20, box.y + 18, box.w - 40, gap=2)

    def _b_ask(self, screen, k):
        rect = pygame.Rect(190, 60, 900, 470)
        ui.paper_panel(screen, rect)
        ui.tag(screen, "Chọn một đáp án", (rect.x + 34, rect.y + 24))
        fonts.paragraph(screen, "Ai đã đánh tan quân Nam Hán trên sông Bạch Đằng năm 938?", fonts.font("semi", 23), theme.INK, rect.x + 34, rect.y + 62, rect.w - 68)
        answered = k > 0.42
        y = rect.y + 112
        for i, label in enumerate(("Ngô Quyền", "Lê Lợi", "Trần Hưng Đạo")):
            row = pygame.Rect(rect.x + 34, y, rect.w - 68, 54)
            bg, line = theme.PAPER_2, theme.PAPER_3
            if answered and i == 0:
                bg, line = (178, 218, 186), theme.JADE
            pygame.draw.rect(screen, bg, row, border_radius=6)
            pygame.draw.rect(screen, line, row, 2, border_radius=6)
            pygame.draw.circle(screen, theme.LACQUER_RED, (row.x + 28, row.centery), 15)
            fonts.text(screen, i + 1, fonts.font("bold", 16), theme.GOLD_LIGHT, (row.x + 28, row.centery), "center")
            fonts.text(screen, label, fonts.font("ui", 19), theme.INK, (row.x + 58, row.centery), "midleft")
            y += 64
        if answered:
            box = pygame.Rect(rect.x + 24, rect.bottom - 150, rect.w - 48, 134)
            ui.lacquer_panel(screen, box, 250)
            fonts.text(screen, "Chính xác!  +10 điểm", fonts.font("bold", 19), theme.JADE_LIGHT, (box.x + 22, box.y + 16))
            fonts.paragraph(screen, "Năm 938, Ngô Quyền dùng cọc gỗ và con nước đánh tan thuỷ quân Nam Hán.", fonts.font("ui", 17), theme.PAPER, box.x + 22, box.y + 46, box.w - 44, gap=2)
            fonts.text(screen, "Nguồn: Đại Việt sử ký toàn thư", fonts.font("italic", 13), theme.PAPER_3, (box.x + 22, box.bottom - 32))

    def _b_scroll(self, screen, k):
        sx = 780
        got = k > 0.5
        if not got:
            bob = 4 * math.sin(self.time * 4)
            scroll = sprites.icon("ui/scroll.png")
            screen.blit(scroll, scroll.get_rect(midbottom=(sx, ROAD_Y + bob)))
            spirit = sprites.strip("fx/spirit.png", 5, 2)[int(self.time * 9) % 5]
            screen.blit(spirit, spirit.get_rect(center=(sx, ROAD_Y - 26)))
        self._player(screen, ((300, ROAD_Y), (sx, ROAD_Y)), k / 0.5)
        if got:
            box = pygame.Rect(W // 2 - 280, 120, 560, 240)
            ui.paper_panel(screen, box)
            ui.tag(screen, "Mảnh ghép tư liệu", (box.x + 28, box.y + 22))
            fonts.paragraph(screen, "Những tờ sử cũ bị thất lạc, bạn nhặt lại từng tờ.", fonts.font("serif", 24), theme.INK, box.x + 28, box.y + 62, box.w - 56, gap=4)
            fonts.text(screen, "Đã cất vào Sổ tay", fonts.font("semi", 15), theme.INK_SOFT, (box.x + 28, box.bottom - 42))
            self._key(screen, "N", box.right - 74, box.bottom - 62, True)

    def _b_battle(self, screen, k):
        offset = self.fx.offset()
        self.cine.draw(screen, offset)
        self.fx.draw(screen)
        flag = sprites.strip("fx/flag_red.png", 4)[int(self.time * 7) % 4]
        screen.blit(flag, (32, 24))

    def _b_stamp(self, screen, k):
        page = pygame.Rect(W // 2 - 310, 58, 620, 490)
        ui.paper_panel(screen, page)
        fonts.text(screen, "Hộ chiếu di sản", fonts.font("serif", 24), theme.INK, (page.centerx, page.y + 22), "midtop")
        rel = min(1.0, self.t / 0.35)
        size = int(320 - 130 * rel)
        stamp = art.stamp("Đường Lâm", 190)
        img = pygame.transform.smoothscale(stamp, (size, size)) if size != 190 else stamp
        screen.blit(img, img.get_rect(center=(page.centerx, page.y + 170)))
        if k > 0.45:
            ui.tag(screen, "Mở khoá địa danh: Cửa sông Bạch Đằng", (page.centerx, page.y + 296), theme.LACQUER, theme.GOLD_LIGHT, 16, "midtop")
        x = page.centerx - 231
        for i, label in enumerate(("Đường Lâm", "Bạch Đằng", "Cổ Loa", "Như Nguyệt")):
            mini = art.stamp(label, 96, active=i == 0)
            screen.blit(mini, (x + i * 116, page.bottom - 122))

    def _b_gate(self, screen, k):
        if k < 0.52:
            part = k / 0.52
            self._person(screen, sprites.cast("Master"), 250, ROAD_Y)
            self._mark(screen, "ui/emote_alert.png", 250, ROAD_Y - 66)
            for i, (year, label) in enumerate(CARDS):
                appear = min(1.0, max(0.0, part * 3 - i))
                rect = pygame.Rect(420 + i * 270, int(330 - (1 - appear) * 260), 250, 120)
                ui.paper_panel(screen, rect)
                fonts.text(screen, year, fonts.font("black", 30), theme.LACQUER_RED, (rect.x + 20, rect.y + 16))
                fonts.paragraph(screen, label, fonts.font("semi", 15), theme.INK, rect.x + 20, rect.y + 58, rect.w - 40, gap=1)
            pygame.draw.line(screen, theme.GOLD, (420, 300), (420 + int(790 * part), 300), 5)
            return
        part = (k - 0.52) / 0.48
        arch = sprites.region("house", 29, 20, 3, 3)
        gate_x, gate_y = 760, ROAD_Y - 10
        screen.blit(arch, arch.get_rect(midbottom=(gate_x, gate_y + 16)))
        swirl = sprites.strip("fx/portal.png", 6)[int(self.time * 10) % 6]
        screen.blit(swirl, swirl.get_rect(center=(gate_x, gate_y - 64)))
        self._player(screen, ((300, ROAD_Y), (gate_x, gate_y)), part / 0.7, "up")
        if part > 0.7:
            flash = (part - 0.7) / 0.3
            self.shade.fill((255, 250, 230))
            self.shade.set_alpha(int(255 * flash * flash))
            screen.blit(self.shade, (0, 0))
            self.shade.fill(theme.LACQUER)

    def _b_arena(self, screen, k):
        hero = self.cast
        foe = sprites.cast("FighterRed")
        px, fx_ = 620, 860
        y = 470
        if self.t >= self.next_hit:
            self.next_hit = self.t + 0.55
            self.foe_hp = max(0.2, self.foe_hp - 0.08)
            self.fx.play("fx/curved.png", 4, fx_ - 30, y - 34, 18, False, 3)
            self.fx.blood(fx_, y - 34, 8)
        swinging = (self.next_hit - self.t) > 0.35
        img = hero.attack["right"] if swinging else hero.walk["right"][0]
        screen.blit(img, img.get_rect(midbottom=(px + 110 if swinging else px, y)))
        self._person(screen, foe, fx_, y, "left")
        ui.progress_bar(screen, (fx_ - 40, y - 78, 80, 8), self.foe_hp, (214, 70, 60))
        self.fx.draw(screen)
        panel = pygame.Rect(60, 120, 400, 360)
        ui.lacquer_panel(screen, panel, 244)
        fonts.text(screen, "Điểm kỹ năng còn: 5", fonts.font("bold", 19), theme.GOLD_LIGHT, (panel.x + 28, panel.y + 26))
        rows = (("sk_suc", "Sức đánh"), ("sk_nhanh", "Nhanh nhẹn"), ("sk_phong_lao", "Phóng lao"), ("sk_ten_lua", "Tên lửa"))
        yy = panel.y + 66
        for i, (icon, label) in enumerate(rows):
            if k * 5 < i:
                break
            screen.blit(sprites.icon(f"ui/{icon}.png", 2), (panel.x + 28, yy))
            fonts.text(screen, label, fonts.font("semi", 17), theme.PAPER, (panel.x + 90, yy + 12))
            yy += 66
        self._key(screen, "K", panel.right - 74, panel.y + 18, int(self.time * 2) % 2 == 0)

    def _b_extras(self, screen, k):
        horse = sprites.strip("animal/horse.png", 2)[int(self.time * 5) % 2]
        boat = fleet.boat_sprite(120)
        for i, (icon, title, sub) in enumerate(EXTRAS):
            appear = min(1.0, max(0.0, k * 5 - i))
            if appear <= 0:
                continue
            rect = pygame.Rect(90 + (i % 2) * 560, int(90 + (i // 2) * 220 + (1 - appear) * 40), 540, 196)
            ui.paper_panel(screen, rect)
            img = horse if icon == "horse" else boat if icon == "boat" else sprites.icon(icon)
            screen.blit(img, img.get_rect(center=(rect.x + 100, rect.centery)))
            fonts.text(screen, title, fonts.font("bold", 22), theme.INK, (rect.x + 190, rect.centery - 34))
            fonts.paragraph(screen, sub, fonts.font("ui", 17), theme.INK_SOFT, rect.x + 190, rect.centery + 2, rect.w - 220, gap=2)

    def _b_end(self, screen, k):
        rect = pygame.Rect(170, 90, 940, 330)
        ui.lacquer_panel(screen, rect, 244)
        fonts.text(screen, "Lộ trình của bạn", fonts.font("bold", 24), theme.GOLD_LIGHT, (rect.x + 34, rect.y + 26))
        self._key(screen, "J", rect.right - 86, rect.y + 22, int(self.time * 2) % 2 == 0)
        x0, y = rect.x + 70, rect.y + 150
        gap = 132
        pygame.draw.line(screen, theme.GOLD_DARK, (x0, y), (x0 + gap * 6, y), 6)
        for i in range(7):
            cx = x0 + i * gap
            if i < 2:
                pygame.draw.circle(screen, theme.LACQUER_RED, (cx, y), 26)
                pygame.draw.lines(screen, theme.WHITE, False, [(cx - 12, y), (cx - 3, y + 10), (cx + 13, y - 10)], 5)
            elif i == 2:
                r = 26 + int(5 * ui.pulse(self.time, 5))
                pygame.draw.circle(screen, theme.GOLD_LIGHT, (cx, y), r)
                fonts.text(screen, i + 1, fonts.font("bold", 20), theme.INK, (cx, y), "center")
            else:
                pygame.draw.circle(screen, theme.GRAY, (cx, y), 24)
                fonts.text(screen, i + 1, fonts.font("bold", 18), theme.PAPER, (cx, y), "center")
        fonts.text(screen, "Đang làm", fonts.font("semi", 16), theme.GOLD_LIGHT, (x0 + gap * 2, y + 44), "midtop")
        fonts.text(screen, "Việc cần làm ngay: nghe bà cụ bán nước kể chuyện", fonts.font("serif", 20), theme.PAPER, (rect.centerx, rect.bottom - 56), "midtop")
        if not self.recording:
            self.go.draw(screen)

    # ----- các đoạn thêm: vòng chơi, màn hình, nhân vật -----
    def _card(self, screen, rect, title, sub, img=None, appear=1.0, dark=False):
        rect = pygame.Rect(rect.x, int(rect.y + (1 - appear) * 30), rect.w, rect.h)
        if dark:
            ui.lacquer_panel(screen, rect, 240)
        else:
            ui.paper_panel(screen, rect)
        x = rect.x + 18
        if img is not None:
            screen.blit(img, img.get_rect(midleft=(rect.x + 14, rect.centery)))
            x = rect.x + 28 + img.get_width()
        fonts.text(screen, title, fonts.font("bold", 18), theme.GOLD_LIGHT if dark else theme.INK, (x, rect.y + 16))
        fonts.paragraph(screen, sub, fonts.font("ui", 14), theme.PAPER if dark else theme.INK_SOFT, x, rect.y + 44, rect.right - x - 14, gap=1)

    @staticmethod
    def _arrow(screen, a, b, color=theme.GOLD, width=5):
        pygame.draw.line(screen, color, a, b, width)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        tip = [b, (b[0] - 18 * math.cos(ang - 0.45), b[1] - 18 * math.sin(ang - 0.45)),
               (b[0] - 18 * math.cos(ang + 0.45), b[1] - 18 * math.sin(ang + 0.45))]
        pygame.draw.polygon(screen, color, tip)

    def _b_loop(self, screen, k):
        screen.fill(theme.LACQUER)
        cx = W // 2
        nodes = (
            ((cx, 92), "Học sử", "Nghe kể, trả lời, nhặt tư liệu, vào trận ở mỗi di tích", "ui/book.png"),
            ((cx + 380, 300), "Phần thưởng của việc học", "Điểm xếp hạng, điểm kỹ năng, tinh hoa", "ui/gem.png"),
            ((cx, 500), "Mạnh lên", "Học chiêu, đột phá cảnh giới để mở cấp cao hơn", "ui/sk_suc.png"),
            ((cx - 380, 300), "Đánh quái, vùng luyện", "Kinh nghiệm, tiềm năng, tiền quan, sắm đồ", "ui/sword.png"),
        )
        for i in range(4):
            if k * 5 > i + 1:
                a, b = nodes[i][0], nodes[(i + 1) % 4][0]
                mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                start = (a[0] + (mid[0] - a[0]) * 0.55, a[1] + (mid[1] - a[1]) * 0.55)
                end = (b[0] + (mid[0] - b[0]) * 0.55, b[1] + (mid[1] - b[1]) * 0.55)
                self._arrow(screen, start, end)
        for i, (pos, title, sub, icon) in enumerate(nodes):
            appear = min(1.0, max(0.0, k * 5 - i))
            if appear <= 0:
                continue
            rect = pygame.Rect(0, 0, 340, 96)
            rect.center = pos
            self._card(screen, rect, title, sub, sprites.icon(icon), appear, dark=i != 0)
        if k > 0.85:
            fonts.text(screen, "Học càng nhiều, càng mạnh: vòng này lặp lại suốt ba màn.", fonts.font("serif", 20), theme.GOLD_LIGHT,
                       (cx, 400), "center")

    def _hamburger(self, screen, rect, open_):
        ui.lacquer_panel(screen, rect, 250)
        c = rect.center
        if open_:
            for d in (-1, 1):
                pygame.draw.line(screen, theme.GOLD_LIGHT, (c[0] - 9, c[1] - 9 * d), (c[0] + 9, c[1] + 9 * d), 4)
        else:
            for dy in (-8, 0, 8):
                pygame.draw.rect(screen, theme.PAPER, (c[0] - 12, c[1] + dy - 2, 24, 4), border_radius=2)

    def _b_menu(self, screen, k):
        f = fonts.font("semi", 14)
        tracker = pygame.Rect(12, 10, 440, 104)
        ui.lacquer_panel(screen, tracker, 244)
        fonts.text(screen, "Những khúc sông giữ nước", fonts.font("serif", 18), theme.GOLD_LIGHT, (28, 20))
        fonts.text(screen, "Đi tới Đường Lâm", f, theme.PAPER, (28, 78))
        rpgbox = pygame.Rect(12, 420, 410, 92)
        ui.lacquer_panel(screen, rpgbox, 244)
        fonts.text(screen, "Cấp 3 · Tân binh", fonts.font("serif", 18), theme.PAPER, (26, 430))
        ui.progress_bar(screen, (26, 458, 382, 8), 0.4, theme.JADE_LIGHT)
        fonts.text(screen, "Tiềm năng 12  ·  45 quan  ·  Tinh hoa 1  ·  Thuốc 2", f, theme.PAPER, (26, 482))
        mini = pygame.Rect(W - 250, 420, 236, 92)
        ui.lacquer_panel(screen, mini.inflate(16, 16), 240)
        pygame.draw.rect(screen, (120, 160, 90), mini)
        pygame.draw.line(screen, (106, 158, 176), (mini.x + 150, mini.y), (mini.x + 170, mini.bottom), 8)
        pygame.draw.rect(screen, theme.RED_BRIGHT, (mini.x + 60, mini.y + 50, 6, 6))
        opened = k > 0.45
        toggle = pygame.Rect(W - 64, 10, 52, 44)
        self._hamburger(screen, toggle, opened)
        labels = (("Góc trái trên: việc cần làm", tracker), ("Cấp, kinh nghiệm, tiềm năng, tiền", rpgbox), ("Bản đồ nhỏ", mini))
        for i, (text, rect) in enumerate(labels):
            if k * 4 > i:
                ui.tag(screen, text, (rect.centerx, rect.bottom + 8), theme.GOLD, theme.INK, 14, "midtop")
        if not opened:
            if int(self.time * 3) % 2 == 0:
                pygame.draw.rect(screen, theme.GOLD_LIGHT, toggle.inflate(8, 8), 3)
            return
        items = (("Lộ trình", "J"), ("Kỹ năng", "K"), ("Tư liệu", "T"), ("Sổ tay", "N"), ("Bản đồ", "M"), ("Túi đồ", "B"),
                 ("Sổ bóng giặc", "G"), ("Bạn chơi", "P"), ("Chat", "L"), ("Tạm dừng", "Esc"))
        shown = max(1, int(min(1.0, (k - 0.45) / 0.3) * len(items)))
        panel = pygame.Rect(W - 220, 62, 208, 12 + 32 * shown)
        ui.lacquer_panel(screen, panel, 244)
        for i, (label, key) in enumerate(items[:shown]):
            row = pygame.Rect(panel.x + 6, panel.y + 6 + i * 32, panel.w - 12, 28)
            pygame.draw.rect(screen, theme.LACQUER_2, row)
            fonts.text(screen, label, f, theme.PAPER, (row.x + 12, row.centery), "midleft")
            fonts.text(screen, key, fonts.font("ui", 12), theme.PAPER_3, (row.right - 10, row.centery), "midright")

    def _b_npcs(self, screen, k):
        screen.fill(theme.LACQUER)
        fonts.text(screen, "Ai làm gì?", fonts.font("serif", 26), theme.GOLD_LIGHT, (W // 2, 22), "midtop")
        people = (
            ("Master", "Cụ Đồ Sử", "Giao việc, nhận báo cáo, dựng dòng thời gian, mở cổng sang màn sau"),
            ("OldWoman", "Người giữ ký ức", "Đứng ở mỗi di tích, kể câu chuyện mở đầu"),
            ("stele", "Bia đá, người trong vùng", "Đặt câu hỏi về di tích"),
            ("Villager", "Thợ rèn", "Bán vũ khí, áo, mũ, giày, găng, cần câu"),
            ("OldMan", "Người kể chuyện vùng luyện", "Kể trận đánh thật, hỏi một câu, thưởng tiền quan"),
            ("OldMan3", "Người câu cá", "Kể chuyện sông nước, bán cần câu tre"),
            ("Villager3", "Người đi đường", "Vài câu chuyện, mẹo chơi"),
            ("FighterRed", "Võ sư, người thách đấu", "Đấu tập ở võ đài; trên đường có người mời đấu, bấm Y hoặc N"),
        )
        for i, (who, name, sub) in enumerate(people):
            appear = min(1.0, max(0.0, k * 9 - i))
            if appear <= 0:
                continue
            rect = pygame.Rect(40 + (i % 4) * 302, 80 + (i // 4) * 232, 290, 216)
            rect.y += int((1 - appear) * 30)
            ui.paper_panel(screen, rect)
            if who == "stele":
                img = sprites.region(*CATALOG["stele"][:3])
            else:
                img = sprites.cast(who).walk["down"][int(self.time * 4) % 4 if who == "Villager3" else 0]
            img = pygame.transform.scale(img, (img.get_width() * 3 // 2, img.get_height() * 3 // 2))
            screen.blit(img, img.get_rect(midtop=(rect.centerx, rect.y + 12)))
            fonts.text(screen, name, fonts.font("bold", 17), theme.INK, (rect.centerx, rect.y + 116), "midtop")
            fonts.paragraph(screen, sub, fonts.font("ui", 14), theme.INK_SOFT, rect.x + 16, rect.y + 144, rect.w - 32, gap=1)

    # ----- các đoạn thêm: kẻ canh, đánh nhau, lên cấp, cảnh giới -----
    def _b_guard(self, screen, k):
        sx, gx = 860, 780
        guard = sprites.cast("LinhTong")
        beaten = k > 0.62
        if not beaten:
            scroll = sprites.icon("ui/scroll.png")
            screen.blit(scroll, scroll.get_rect(midbottom=(sx, ROAD_Y + 4 * math.sin(self.time * 4))))
            if k > 0.4 and self.t >= self.next_hit:
                self.next_hit = self.t + 0.4
                self.fx.play("fx/curved.png", 4, gx - 10, ROAD_Y - 34, 18, False, 3)
            self._person(screen, guard, gx, ROAD_Y, "left")
            fonts.text(screen, "Đầu mục quân Nam Hán · cấp 4", fonts.font("bold", 14), (240, 110, 90), (gx, ROAD_Y - 74), "midbottom",
                       shadow=(24, 16, 14))
        else:
            dead = guard.dead
            screen.blit(dead, dead.get_rect(midbottom=(gx, ROAD_Y)))
        self.fx.draw(screen)
        px, _py = self._player(screen, ((260, ROAD_Y), (gx - 80 if not beaten else sx, ROAD_Y)), k / (0.35 if not beaten else 0.85))
        if 0.35 < k <= 0.62:
            self._key(screen, "F", 980, 300, True)
        if beaten:
            ui.tag(screen, "Đã nhặt mật thư" if k > 0.85 else "Kẻ canh đã bị hạ", (sx, ROAD_Y - 90), theme.JADE, theme.WHITE, 15, "midbottom")

    def _b_fight(self, screen, k):
        hero = outfit.hero_cast({"giap": "ao_vai", "mu": "khan_chit"}, 6)
        foe = sprites.cast("LinhNguyen", 6)
        y = 470
        stage = min(4, int(k * 5))
        px = 560 - (60 if stage == 1 else 0)
        swinging = stage in (0, 2) and (self.t % 0.6) < 0.25
        img = hero.attack["right"] if swinging else hero.walk["right"][int(self.time * 8) % 4 if stage == 1 else 0]
        screen.blit(img, img.get_rect(midbottom=(px + (50 if swinging else 0), y)))
        self._person(screen, foe, 760, y, "left")
        if self.t >= self.next_hit and stage in (0, 2):
            self.next_hit = self.t + 0.6
            self.fx.play("fx/curved.png", 4, 730, y - 34, 18, False, 3)
            self.foe_hp = max(0.25, self.foe_hp - 0.07)
        ui.progress_bar(screen, (710, y - 112, 100, 9), self.foe_hp, (214, 70, 60))
        ui.progress_bar(screen, (px - 50, y - 112, 100, 9), 0.55 if stage < 3 else 0.95, theme.JADE_LIGHT)
        if stage == 3:
            fonts.text(screen, "+40% máu", fonts.font("bold", 20), theme.JADE_LIGHT, (px, y - 130 - (self.t % 1) * 20), "midbottom",
                       shadow=(24, 16, 14))
        self.fx.draw(screen)
        panel = pygame.Rect(850, 70, 390, 420)
        ui.lacquer_panel(screen, panel, 244)
        rows = (("Chuột trái", "Chém (giữ để chém liền)"), ("Shift", "Né"), ("1–4", "Tung chiêu đã học"), ("Q", "Uống thuốc nam"),
                ("E", "Ăn cá nướng"))
        key_w = fonts.font("bold", 20).size(rows[0][0])[0] + 22
        for i, (key, text) in enumerate(rows):
            yy = panel.y + 22 + i * 78
            self._key(screen, key, panel.x + 22, yy, i == stage, w=max(46, fonts.font("bold", 20).size(key)[0] + 22))
            fonts.text(screen, text, fonts.font("semi", 17), theme.GOLD_LIGHT if i == stage else theme.PAPER,
                       (panel.x + 40 + key_w, yy + 12))

    def _b_grow(self, screen, k):
        mobs = (("LinhTong", "Lính Tống · cấp 5", (150, 220, 150), 300), ("LinhNguyen", "Lính Nguyên · cấp 8", (243, 212, 140), 640),
                ("LinhMinh", "Lính Minh · cấp 12", (240, 110, 90), 980))
        for i, (char, label, color, x) in enumerate(mobs):
            if k * 4 < i:
                continue
            self._person(screen, sprites.cast(char), x, 330, "down")
            ui.tag(screen, label, (x, 262), theme.LACQUER, color, 15, "midbottom")
            ui.tag(screen, ("dễ", "ngang sức", "mạnh hơn bạn")[i], (x, 340), theme.LACQUER, color, 14, "midtop")
        box = pygame.Rect(40, 400, 520, 120)
        ui.lacquer_panel(screen, box, 246)
        lvl = 4 if k > 0.75 else 3
        fonts.text(screen, f"Cấp {lvl} · Tân binh", fonts.font("serif", 20), theme.PAPER, (box.x + 18, box.y + 12))
        fill = min(1.0, k / 0.75) if k <= 0.75 else (k - 0.75) * 2
        ui.progress_bar(screen, (box.x + 18, box.y + 46, box.w - 36, 10), fill, theme.JADE_LIGHT)
        fonts.text(screen, "Tiềm năng · tiền quan · thuốc nam rơi ra", fonts.font("semi", 15), theme.PAPER_3, (box.x + 18, box.y + 70))
        if 0.3 < k < 0.95:
            rise = (self.t * 30) % 40
            ui.tag(screen, "+26 kinh nghiệm   +9 tiềm năng   +5 quan", (box.right + 260, box.y + 40 - rise), theme.LACQUER,
                   theme.GOLD_LIGHT, 17, "center")
        if k > 0.75:
            ui.tag(screen, "LÊN CẤP!", (box.right - 20, box.y - 10), theme.GOLD, theme.INK, 18, "bottomright")

    def _b_realm(self, screen, k):
        screen.fill(theme.LACQUER)
        fonts.text(screen, "Cảnh giới", fonts.font("serif", 26), theme.GOLD_LIGHT, (60, 30))
        steps = len(rpg.REALMS)
        for i, realm in enumerate(rpg.REALMS):
            rect = pygame.Rect(60 + i * 190, 390 - i * 70, 176, 90 + i * 70)
            reached = k * steps > i
            pygame.draw.rect(screen, theme.LACQUER_RED if reached else theme.LACQUER_2, rect)
            pygame.draw.rect(screen, theme.GOLD if reached else theme.GOLD_DARK, rect, 3)
            fonts.text(screen, realm["name"], fonts.font("bold", 18), theme.GOLD_LIGHT, (rect.centerx, rect.y + 12), "midtop")
            fonts.text(screen, f"tới cấp {realm['cap']}", fonts.font("semi", 15), theme.PAPER, (rect.centerx, rect.y + 38), "midtop")
            need = f"cần {realm['need']} tinh hoa" if realm["need"] else "lúc mới vào"
            fonts.text(screen, need, fonts.font("ui", 14), theme.PAPER_3, (rect.centerx, rect.y + 58), "midtop")
        at = min(steps - 1, int(k * steps))
        self._person(screen, self.cast, 60 + at * 190 + 88, 390 - at * 70 - 4, "down")
        panel = pygame.Rect(860, 100, 380, 380)
        ui.paper_panel(screen, panel)
        fonts.text(screen, "Tinh hoa có từ việc học", fonts.font("bold", 19), theme.INK, (panel.x + 20, panel.y + 18))
        rows = (("Nghe một hồi ức", rpg.ESSENCE["memory"]), ("Khám phá một chuyện lạ", rpg.ESSENCE["discovery"]),
                ("Ghép xong một tư liệu", rpg.ESSENCE["document"]), ("Phá xong một vụ điều tra", rpg.ESSENCE["case"]))
        for i, (text, n) in enumerate(rows):
            yy = panel.y + 66 + i * 58
            fonts.text(screen, f"+{n}", fonts.font("black", 26), theme.LACQUER_RED, (panel.x + 24, yy))
            fonts.text(screen, text, fonts.font("semi", 17), theme.INK, (panel.x + 80, yy + 6))
        fonts.paragraph(screen, "Đánh quái mãi cũng không đột phá được: phải học sử.", fonts.font("italic", 15), theme.INK_SOFT,
                        panel.x + 20, panel.bottom - 66, panel.w - 40)

    # ----- các đoạn thêm: lò rèn, vùng luyện, sổ bóng giặc, câu cá, chơi cùng bạn -----
    def _b_shop(self, screen, k):
        looks = ({"giap": "ao_vai", "mu": "khan_chit"}, {"giap": "giap_da", "mu": "non_la"}, {"giap": "giap_vay", "mu": "mu_sat"})
        look = looks[min(2, int(k * 3))]
        cast = outfit.hero_cast(look, 6)
        img = cast.walk["down"][0]
        screen.blit(img, img.get_rect(midbottom=(300, 480)))
        smith = sprites.cast("Villager")
        self._person(screen, smith, 470, 480, "left")
        fonts.text(screen, "LÒ RÈN", fonts.font("bold", 16), theme.GOLD_LIGHT, (470, 400), "midbottom", shadow=(24, 16, 14))
        panel = pygame.Rect(640, 60, 560, 440)
        ui.paper_panel(screen, panel)
        fonts.text(screen, "Lò rèn", fonts.font("serif", 24), theme.INK, (panel.x + 24, panel.y + 16))
        items = ("dao_sat", "giao_dai", "giap_da", "giap_vay", "non_la", "mu_sat", "giay_vai", "can_cau")
        for i, iid in enumerate(items):
            item = rpg.ITEMS[iid]
            row = pygame.Rect(panel.x + 20, panel.y + 60 + i * 46, panel.w - 40, 42)
            if int(k * len(items)) == i:
                pygame.draw.rect(screen, (232, 216, 182), row)
            icon = pygame.transform.smoothscale(sprites.icon(rpg.item_icon(iid)), (32, 32))
            screen.blit(icon, icon.get_rect(midleft=(row.x + 8, row.centery)))
            fonts.text(screen, item["name"], fonts.font("semi", 17), theme.INK, (row.x + 56, row.centery), "midleft")
            fonts.text(screen, f"cấp {item['level']} · {item['price']} quan", fonts.font("bold", 15), theme.LACQUER_RED,
                       (row.right - 8, row.centery), "midright")
        self._key(screen, "B", 260, 120, int(self.time * 2) % 2 == 0)
        fonts.text(screen, "túi đồ", fonts.font("semi", 16), theme.PAPER, (316, 132), shadow=(24, 16, 14))

    def _b_field(self, screen, k):
        sign = sprites.region(*CATALOG["sign"][:3])
        sx = 640
        screen.blit(sign, sign.get_rect(midbottom=(sx, ROAD_Y)))
        fonts.text(screen, "VÙNG LUYỆN", fonts.font("bold", 14), theme.GOLD_LIGHT, (sx, ROAD_Y - 84), "midbottom", shadow=(24, 16, 14))
        self._mark(screen, "ui/emote_alert.png" if k > 0.25 else "ui/emote_lock.png", sx, ROAD_Y - 64)
        self._player(screen, ((260, ROAD_Y), (sx - 60, ROAD_Y)), k / 0.4)
        if k < 0.25:
            ui.tag(screen, "Chưa học xong di tích: đường còn khoá", (sx, ROAD_Y + 6), theme.LACQUER, theme.PAPER, 14, "midtop")
        if k < 0.45:
            return
        panel = pygame.Rect(70, 60, 1140, 300)
        ui.lacquer_panel(screen, panel, 246)
        fonts.text(screen, f"{len(self.state.fields)} vùng luyện, mở dần theo bài học", fonts.font("bold", 22), theme.GOLD_LIGHT,
                   (panel.x + 26, panel.y + 18))
        names = [f["title"] for f in sorted(self.state.fields.values(), key=lambda f: (f["parent"], f["title"][-4:]))]
        shown = int(min(1.0, (k - 0.45) / 0.35) * len(names))
        for i, name in enumerate(names[:shown]):
            col, row = i % 3, i // 3
            fonts.text(screen, f"· {name}", fonts.font("semi", 18), theme.PAPER, (panel.x + 30 + col * 370, panel.y + 70 + row * 44))
        fonts.text(screen, "Người kể chuyện · câu hỏi có thưởng · các trại quân · kẻ mạnh nhất vùng hồi sinh sau ít phút",
                   fonts.font("ui", 16), theme.PAPER_3, (panel.x + 30, panel.bottom - 42))

    def _b_bestiary(self, screen, k):
        screen.fill(theme.LACQUER)
        fonts.text(screen, "SỔ BÓNG GIẶC", fonts.font("serif", 26), theme.GOLD_LIGHT, (60, 30))
        cards = (("LinhTong", "linh_tong"), ("LinhNguyen", "linh_nguyen"), ("LinhMinh", "linh_minh"))
        for i, (char, mid) in enumerate(cards):
            rect = pygame.Rect(60 + i * 400, 100, 370, 380)
            open_ = k * 3.2 > i + 0.6
            img = sprites.cast(char).walk["down"][0]
            img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            if open_:
                ui.paper_panel(screen, rect)
                screen.blit(img, img.get_rect(midtop=(rect.centerx, rect.y + 16)))
                fonts.text(screen, rpg.MOBS[mid]["name"], fonts.font("bold", 19), theme.INK, (rect.centerx, rect.y + 156), "midtop")
                fonts.text(screen, "Sử ghi", fonts.font("bold", 14), theme.LACQUER_RED, (rect.x + 20, rect.y + 192))
                fonts.paragraph(screen, rpg.MOB_FACTS[mid][0], fonts.font("ui", 15), theme.INK, rect.x + 20, rect.y + 214, rect.w - 40, gap=2)
            else:
                ui.lacquer_panel(screen, rect, 220)
                shadow = img.copy()
                shadow.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MIN)
                screen.blit(shadow, shadow.get_rect(midtop=(rect.centerx, rect.y + 16)))
                fonts.text(screen, "? ? ?", fonts.font("bold", 22), theme.PAPER_3, (rect.centerx, rect.y + 170), "midtop")
                fonts.text(screen, "Hạ một lần để mở trang", fonts.font("ui", 15), theme.PAPER_3, (rect.centerx, rect.y + 210), "midtop")

    def _b_fish(self, screen, k):
        pond = pygame.Rect(700, 330, 520, 230)
        pygame.draw.ellipse(screen, (64, 120, 150), pond.inflate(12, 12))
        pygame.draw.ellipse(screen, (96, 164, 196), pond)
        px, py = 660, 470
        self._person(screen, self.cast, px, py, "right")
        bob_x, bob_y = 900, 420 + (6 if 0.35 < k < 0.55 else 2 * math.sin(self.time * 3))
        if k < 0.6:
            pygame.draw.line(screen, (120, 80, 44), (px + 14, py - 40), (px + 90, py - 110), 4)
            pygame.draw.line(screen, (230, 230, 230), (px + 90, py - 110), (bob_x, bob_y), 1)
            pygame.draw.circle(screen, (214, 66, 44), (bob_x, int(bob_y)), 6)
            pygame.draw.circle(screen, theme.WHITE, (bob_x, int(bob_y) - 3), 3)
        if 0.35 < k < 0.55:
            self._mark(screen, "ui/emote_alert.png", px, py - 70)
            self._key(screen, "C", 520, 200, True)
        if k >= 0.55:
            fish = pygame.transform.scale(sprites.image("animal/fish_red.png").subsurface((0, 0, 16, 16)), (48, 48))
            t = min(1.0, (k - 0.55) / 0.12)
            fx_, fy_ = bob_x + (px - bob_x) * t, bob_y - 120 * math.sin(math.pi * t) + (py - 60 - bob_y) * t
            screen.blit(fish, fish.get_rect(center=(fx_, fy_)))
        hx = 400
        hearth = _hearth()
        screen.blit(hearth, hearth.get_rect(midbottom=(hx, py)))
        flame = _flames()[int(self.time * 10) % 8]
        screen.blit(flame, flame.get_rect(midbottom=(hx, py - 10)))
        screen.blit(_skewer(), _skewer().get_rect(midbottom=(hx + 54, py)))
        if k > 0.7:
            panel = pygame.Rect(60, 80, 420, 150)
            ui.lacquer_panel(screen, panel, 246)
            screen.blit(sprites.icon(rpg.item_icon("ca_nuong"), 2), (panel.x + 18, panel.y + 30))
            fonts.text(screen, "Cá nướng", fonts.font("bold", 20), theme.GOLD_LIGHT, (panel.x + 110, panel.y + 24))
            fonts.text(screen, f"Trong trận bấm E: hồi {round(rpg.GRILL_HEAL * 100)}% máu", fonts.font("semi", 16), theme.PAPER,
                       (panel.x + 110, panel.y + 60))
            self._key(screen, "E", panel.x + 110, panel.y + 92, int(self.time * 2) % 2 == 0)

    def _b_social(self, screen, k):
        board = pygame.transform.scale(board_sprite(), (198, 177))
        screen.blit(board, board.get_rect(midbottom=(250, 520)))
        fonts.text(screen, "TOP 20 NGƯỜI CHƠI", fonts.font("bold", 16), theme.GOLD_LIGHT, (250, 336), "midbottom", shadow=(24, 16, 14))
        friend = outfit.hero_cast({"giap": "giap_vay", "mu": "non_la"})
        self._person(screen, self.cast, 560, 470, "right")
        self._person(screen, friend, 660, 470, "left")
        fonts.text(screen, "Minh An · cấp 9 · tổ đội", fonts.font("bold", 13), (150, 230, 160), (660, 400), "midbottom", shadow=(24, 16, 14))
        if k > 0.2:
            ui.tag(screen, "Cùng đi Chi Lăng không?", (660, 382), theme.PAPER, theme.INK, 13, "midbottom")
        self._key(screen, "Chuột trái", 470, 150, k < 0.4, w=fonts.font("bold", 20).size("Chuột trái")[0] + 22)
        self._key(screen, "L", 620, 150, k >= 0.4)
        if k < 0.4:  # bấm vào bạn: bảng trạng thái, lời mời hiện ở góc trên phải màn chơi của người kia
            ui.tag(screen, "Bấm vào bạn mình", (660, 300), theme.GOLD, theme.INK, 14, "midbottom")
            card = pygame.Rect(W - 412, 64, 400, 112)
            ui.lacquer_panel(screen, card, 236)
            fonts.text(screen, "THÁCH ĐẤU", fonts.font("bold", 14), theme.GOLD_LIGHT, (card.x + 14, card.y + 10))
            fonts.text(screen, "Minh An · cấp 9", fonts.font("bold", 15), theme.PAPER, (card.x + 14, card.y + 30))
            fonts.text(screen, "thách đấu bạn trên võ đài", fonts.font("ui", 13), theme.PAPER_3, (card.x + 14, card.y + 51))
            ui.Button((card.right - 226, card.bottom - 40, 104, 32), "Đồng ý", None, "jade", size=14).draw(screen)
            ui.Button((card.right - 116, card.bottom - 40, 104, 32), "Từ chối", None, "ghost", size=14).draw(screen)
            ui.tag(screen, "Đồng ý là hai người cùng vào võ đài", (card.centerx, card.bottom + 8), theme.GOLD, theme.INK, 14, "midtop")
        if k > 0.4:
            box = pygame.Rect(W - 452, 64, 440, 118)
            ui.lacquer_panel(screen, box, 230)
            fonts.text(screen, "THẾ GIỚI", fonts.font("bold", 13), theme.GOLD_LIGHT, (box.x + 12, box.y + 8))
            fonts.text(screen, f"L để chat · {rpg.WORLD_CHAT_COST} quan/tin", fonts.font("ui", 12), theme.PAPER_3, (box.right - 12, box.y + 9),
                       "topright")
            lines = (("Gia Bảo", "Ai lập tổ đội đánh vùng Đông Khê không?"), ("Thu Hà", "Mình vừa đột phá lên Sử quan!"),
                     ("Bạn", "Cho mình vào với"))
            for i, (name, text) in enumerate(lines[:1 + int((k - 0.4) * 6)]):
                f_name = fonts.font("bold", 13)
                yy = box.y + 30 + i * 26
                fonts.text(screen, name + ":", f_name, theme.JADE_LIGHT if name == "Bạn" else theme.GOLD_LIGHT, (box.x + 12, yy))
                fonts.text(screen, text, fonts.font("ui", 13), theme.PAPER, (box.x + 18 + f_name.size(name + ":")[0], yy))
            ui.tag(screen, "Góc phải trên: chat thế giới", (box.centerx, box.bottom + 8), theme.GOLD, theme.INK, 14, "midtop")


    # ----- vẽ chung -----
    def draw(self, screen):
        title, text, _dur, method, bg = BEATS[self.i]
        k = min(1.0, self.t / BEATS[self.i][2])
        if bg:
            screen.blit(diorama.scene(bg), (0, 0))
        getattr(self, method)(screen, k)
        if title:
            ui.lacquer_panel(screen, CAPTION, 246)
            fonts.text(screen, title, fonts.font("bold", 26), theme.GOLD_LIGHT, (CAPTION.x + 30, CAPTION.y + 18))
            fonts.paragraph(screen, text, fonts.font("serif", 19), theme.PAPER, CAPTION.x + 30, CAPTION.y + 60, CAPTION.w - 60, gap=2)
        self._draw_pips(screen)
        if not self.recording:
            self.group.draw(screen)
        if self.t < FADE:
            self.shade.set_alpha(int(255 * (1 - self.t / FADE)))
            screen.blit(self.shade, (0, 0))

    def _draw_pips(self, screen):
        n = len(BEATS)
        x = W // 2 - n * 11
        for i in range(n):
            color = theme.GOLD_LIGHT if i == self.i else theme.GOLD_DARK if i < self.i else theme.LACQUER_2
            pygame.draw.rect(screen, OUTLINE, (x + i * 22 - 2, 18, 18, 14))
            pygame.draw.rect(screen, color, (x + i * 22, 20, 14, 10))
