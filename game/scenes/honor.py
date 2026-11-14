"""Bảng vàng ở map đầu: 20 người nhiều điểm học sử nhất và 20 người sức mạnh cao nhất trên máy chủ.

Game không gọi mạng trực tiếp: trang chơi lấy `/api/v1/game/honor` mỗi phút rồi ghi vào localStorage (khoá `HONOR_KEY`),
game chỉ việc đọc ra. Chơi trên máy (không đăng nhập) thì bảng trống và hiện sức mạnh của chính mình.
"""

from __future__ import annotations

import json

import pygame
from core import fonts, platform_io, sprites, theme, ui
from core.scene import Scene

W, H = theme.WIDTH, theme.HEIGHT
HONOR_KEY = "sukydieutra.honor"  # trùng với web/js/play.js
TOP = 20
MEDALS = ((236, 190, 70), (200, 204, 212), (205, 132, 72))  # vàng, bạc, đồng
OUTLINE = (24, 16, 14)
_board: pygame.Surface | None = None


def load() -> dict:
    """Dữ liệu bảng vàng trang chơi để lại; thiếu hoặc hỏng thì trả hai bảng rỗng."""
    try:
        raw = platform_io.read_key(HONOR_KEY)
        data = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        data = {}
    out = {}
    for key in ("points", "power"):
        rows = data.get(key) if isinstance(data, dict) else None
        out[key] = [r for r in rows if isinstance(r, dict) and r.get("name")][:TOP] if isinstance(rows, list) else []
    return out


def board_sprite() -> pygame.Surface:
    """Tấm bảng sơn son viền vàng trên hai cột gỗ, đặt ngoài map; vẽ một lần rồi giữ lại."""
    global _board
    if _board is None:
        s = pygame.Surface((132, 118), pygame.SRCALPHA)
        for x in (16, 108):  # hai cột gỗ
            pygame.draw.rect(s, OUTLINE, (x - 2, 40, 12, 78))
            pygame.draw.rect(s, (120, 80, 46), (x, 42, 8, 74))
            pygame.draw.line(s, (156, 108, 64), (x + 1, 42), (x + 1, 114), 2)
        pygame.draw.polygon(s, OUTLINE, [(2, 18), (66, 0), (130, 18), (130, 26), (2, 26)])  # mái che
        pygame.draw.polygon(s, (150, 40, 32), [(6, 20), (66, 4), (126, 20), (126, 23), (6, 23)])
        panel = pygame.Rect(8, 24, 116, 64)
        pygame.draw.rect(s, OUTLINE, panel.inflate(6, 6))
        pygame.draw.rect(s, theme.GOLD, panel.inflate(2, 2))
        pygame.draw.rect(s, theme.LACQUER_RED, panel)
        fonts.text(s, "BẢNG VÀNG", fonts.font("bold", 15), theme.GOLD_LIGHT, (panel.centerx, panel.y + 6), "midtop")
        for i, w in enumerate((70, 58, 64, 50)):  # các dòng tên nhỏ
            y = panel.y + 30 + i * 8
            pygame.draw.rect(s, theme.GOLD_DARK if i else theme.GOLD, (panel.centerx - w // 2, y, w, 3))
        _board = s
    return _board


class HonorScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.data = load()
        self.t = 0.0
        self.group = ui.ButtonGroup()
        self.group.add(ui.Button((W - 150, 14, 136, 40), "Đóng", lambda: self.app.scenes.pop(), "ghost", size=15))

    def handle(self, event):
        self.group.handle(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_e, pygame.K_SPACE):
            self.app.scenes.pop()

    def update(self, dt):
        self.t += dt

    def _column(self, screen, rect, title, sub, rows, unit, show_level):
        ui.paper_panel(screen, rect)
        fonts.text(screen, title, fonts.font("serif", 24), theme.LACQUER_RED, (rect.x + 24, rect.y + 16))
        fonts.text(screen, sub, fonts.font("ui", 13), theme.INK_SOFT, (rect.x + 24, rect.y + 50))
        if not rows:
            fonts.paragraph(screen, "Chưa có ai trên bảng. Bảng vàng lấy dữ liệu từ máy chủ, chỉ hiện khi chơi trên trang web "
                            "đã đăng nhập; trang tự cập nhật mỗi phút.", fonts.font("ui", 15), theme.INK_SOFT,
                            rect.x + 24, rect.y + 96, rect.w - 48, gap=3)
            return
        f_rank, f_name, f_val = fonts.font("bold", 15), fonts.font("semi", 15), fonts.font("bold", 15)
        row_h = (rect.h - 86) / TOP
        for i, r in enumerate(rows[:TOP]):
            y = rect.y + 78 + i * row_h
            line = pygame.Rect(rect.x + 14, int(y), rect.w - 28, int(row_h) - 2)
            if i % 2 == 0:
                pygame.draw.rect(screen, (232, 216, 182), line)
            rank = int(r.get("rank", i + 1))
            cx, cy = line.x + 20, line.centery
            if rank <= 3:
                pygame.draw.circle(screen, OUTLINE, (cx, cy), 11)
                pygame.draw.circle(screen, MEDALS[rank - 1], (cx, cy), 9)
            fonts.text(screen, rank, f_rank, theme.INK, (cx, cy), "center")
            name = str(r["name"])[:28]
            fonts.text(screen, name, f_name, theme.INK, (line.x + 44, cy), "midleft")
            value = f"{int(r.get('value', 0)):,}".replace(",", ".") + f" {unit}"
            if show_level and r.get("level"):
                value = f"cấp {int(r['level'])} · {value}"
            fonts.text(screen, value, f_val, theme.LACQUER_RED if rank <= 3 else theme.INK_SOFT, (line.right - 10, cy), "midright")

    def draw(self, screen):
        st = self.state
        screen.fill(theme.LACQUER)
        board = pygame.transform.scale(board_sprite(), (66, 59))
        screen.blit(board, (24, 8))
        fonts.text(screen, "BẢNG VÀNG", fonts.font("serif", 30), theme.GOLD_LIGHT, (104, 14))
        fonts.text(screen, "Hai mươi người đứng đầu toàn máy chủ. Học sử để có điểm, luyện tập và sắm đồ để tăng sức mạnh.",
                   fonts.font("ui", 14), theme.PAPER_3, (104, 52))
        left = pygame.Rect(30, 92, 600, H - 160)
        right = pygame.Rect(650, 92, 600, H - 160)
        self._column(screen, left, "Điểm học sử", "Cộng dồn từ mọi câu trả lời đúng, di tích, tư liệu", self.data["points"], "điểm", False)
        self._column(screen, right, "Sức mạnh", "Tính từ máu, sát thương, tốc độ: chỉ số, đồ, cảnh giới", self.data["power"], "", True)
        icon = sprites.icon("ui/stamp.png")
        screen.blit(icon, icon.get_rect(midleft=(30, H - 36)))
        mine = f"Của bạn: {st.total_points} điểm học sử · sức mạnh {st.power_rating()} · cấp {st.level} ({st.realm_name()})"
        fonts.text(screen, mine, fonts.font("semi", 16), theme.GOLD_LIGHT, (30 + icon.get_width() + 12, H - 36), "midleft")
        fonts.text(screen, "Esc hoặc E để đóng", fonts.font("ui", 13), theme.PAPER_3, (W - 30, H - 36), "midright")
        self.group.draw(screen)
