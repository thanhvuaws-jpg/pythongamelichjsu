"""Thành phần giao diện: khung giấy, khung sơn mài, nút bấm, nhãn, thông báo nổi."""

from __future__ import annotations

import math
from collections.abc import Callable

import pygame

from core import fonts, theme

_alpha_cache: dict[tuple, pygame.Surface] = {}
_ALPHA_CACHE_MAX = 300


def alpha_rect(surface, rect, color, radius=0):
    """Hình chữ nhật có độ trong suốt (pygame.draw không tự trộn alpha).

    Tạo surface mỗi khung hình rất tốn trên WebAssembly nên lưu lại theo kích thước và màu.
    """
    rect = pygame.Rect(rect)
    key = (rect.size, tuple(color), radius)
    lop = _alpha_cache.get(key)
    if lop is None:
        if len(_alpha_cache) >= _ALPHA_CACHE_MAX:
            _alpha_cache.clear()
        lop = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(lop, color, lop.get_rect(), border_radius=radius)
        _alpha_cache[key] = lop
    surface.blit(lop, rect)


def veil(surface, color=(10, 6, 4, 150)):
    """Phủ tối cả màn hình. Alpha theo surface nhanh hơn nhiều so với alpha theo từng điểm ảnh."""
    key = ("veil", surface.get_size(), tuple(color))
    lop = _alpha_cache.get(key)
    if lop is None:
        lop = pygame.Surface(surface.get_size())
        lop.fill(color[:3])
        lop.set_alpha(color[3])
        _alpha_cache[key] = lop
    surface.blit(lop, (0, 0))


OUTLINE = (24, 16, 14)
_PANEL_STYLES = {
    # (viền ngoài sáng, viền ngoài tối, đường trong, nền trong)
    "dark": ((232, 150, 66), (176, 94, 40), (70, 42, 30), (46, 36, 40)),
    "paper": ((232, 150, 66), (176, 94, 40), (120, 76, 44), (240, 222, 182)),
}


def _pixel_box(w: int, h: int, style: str, alpha: int = 255) -> pygame.Surface:
    """Khung bo góc vuông theo nét 3 px, cùng độ phóng với tile để giao diện ăn nhập với map."""
    key = ("box", w, h, style, alpha)
    box = _alpha_cache.get(key)
    if box is not None:
        return box
    light, dark, line, fill = _PANEL_STYLES[style]
    box = pygame.Surface((w, h), pygame.SRCALPHA)
    u = 3
    pygame.draw.rect(box, OUTLINE, (u, 0, w - 2 * u, h))
    pygame.draw.rect(box, OUTLINE, (0, u, w, h - 2 * u))
    pygame.draw.rect(box, light, (u, u, w - 2 * u, h - 2 * u))
    pygame.draw.rect(box, dark, (u, h - 3 * u, w - 2 * u, 2 * u))
    pygame.draw.rect(box, dark, (w - 2 * u, u, u, h - 2 * u))
    pygame.draw.rect(box, line, (3 * u, 3 * u, w - 6 * u, h - 6 * u))
    pygame.draw.rect(box, (*fill, alpha), (4 * u, 4 * u, w - 8 * u, h - 8 * u))
    _alpha_cache[key] = box
    return box


def paper_panel(surface, rect, shadow=True):
    """Khung giấy - dùng cho nội dung đọc."""
    rect = pygame.Rect(rect)
    if shadow:
        alpha_rect(surface, rect.move(0, 6), (0, 0, 0, 80))
    surface.blit(_pixel_box(rect.w, rect.h, "paper"), rect)


def lacquer_panel(surface, rect, alpha=236):
    """Khung tối - dùng cho thanh công cụ, hộp thoại."""
    rect = pygame.Rect(rect)
    surface.blit(_pixel_box(rect.w, rect.h, "dark", alpha), rect)


def tag(surface, label, pos, bg=theme.LACQUER_RED, fg=theme.GOLD_LIGHT, size=13, anchor="topleft"):
    """Nhãn nhỏ dạng ấn son, ví dụ 'Lời dẫn hư cấu', 'HỒI ỨC'."""
    f = fonts.font("semi", size)
    w, h = f.size(fonts.nfc(label))
    rect = pygame.Rect(0, 0, w + 16, h + 6)
    setattr(rect, anchor, pos)
    pygame.draw.rect(surface, OUTLINE, rect.inflate(4, 4))
    pygame.draw.rect(surface, bg, rect)
    fonts.text(surface, label, f, fg, rect.center, "center")
    return rect


def progress_bar(surface, rect, ratio, fill=theme.GOLD, back=theme.LACQUER_2, border=theme.GOLD_DARK):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, back, rect, border_radius=rect.height // 2)
    if ratio > 0:
        w = max(rect.height, int(rect.width * min(1.0, ratio)))
        pygame.draw.rect(surface, fill, (rect.x, rect.y, w, rect.height), border_radius=rect.height // 2)
    pygame.draw.rect(surface, border, rect, 1, border_radius=rect.height // 2)


_button_cache: dict[tuple, pygame.Surface] = {}
_BUTTON_CACHE_MAX = 400


class Button:
    """Nút bấm dùng được bằng chuột, chạm và bàn phím (khi được focus)."""

    STYLES = {
        "primary": (theme.LACQUER_RED, theme.RED, theme.GOLD_LIGHT, theme.GOLD),
        "gold": (theme.GOLD, theme.GOLD_LIGHT, theme.INK, theme.GOLD_DARK),
        "ghost": (theme.LACQUER_2, (70, 44, 34), theme.PAPER, theme.GOLD_DARK),
        "paper": (theme.PAPER_2, theme.PAPER, theme.INK, theme.GOLD_DARK),
        "jade": (theme.JADE, (60, 150, 118), theme.WHITE, theme.JADE_LIGHT),
    }

    def __init__(
        self,
        rect,
        label: str,
        on_click: Callable[[], None] | None = None,
        style: str = "primary",
        enabled: bool = True,
        size: int = 19,
        data=None,
    ):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.style = style
        self.enabled = enabled
        self.size = size
        self.hover = False
        self.focus = False
        self.data = data
        self._press = False

    def handle(self, event) -> bool:
        """Trả True nếu nút vừa được bấm."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._press = True
                self.hover = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            pressed, self._press = self._press, False
            if pressed and self.rect.collidepoint(event.pos):
                self.click()
                return True
        elif event.type == pygame.KEYDOWN and self.focus and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.click()
            return True
        return False

    def click(self):
        if self.on_click:
            self.on_click()

    def draw(self, surface):
        active = (self.hover or self.focus) and self.enabled
        press = 3 if self._press else 0
        key = (self.rect.size, self.label, self.style, self.enabled, active, press, self.size)
        img = _button_cache.get(key)
        if img is None:
            if len(_button_cache) >= _BUTTON_CACHE_MAX:
                _button_cache.clear()
            img = self._render(active, press)
            _button_cache[key] = img
        surface.blit(img, self.rect)

    def _render(self, active: bool, press: int) -> pygame.Surface:
        """Vẽ nút lên ảnh riêng, cao hơn nút 3 px để chứa phần bóng phía dưới."""
        base, hot, fg, _ = self.STYLES[self.style]
        rect = self.rect
        if not self.enabled:
            base, hot, fg = (84, 74, 68), (84, 74, 68), (178, 168, 156)
        body = hot if active else base
        shade = tuple(int(c * 0.68) for c in body)
        lit = tuple(min(255, int(c * 1.22) + 8) for c in body)
        u = 3
        out = pygame.Surface((rect.w, rect.h + u), pygame.SRCALPHA)
        r = pygame.Rect(0, press, rect.w, rect.h)
        pygame.draw.rect(out, OUTLINE, (r.x + u, r.y, r.w - 2 * u, r.h + (u - press)))
        pygame.draw.rect(out, OUTLINE, (r.x, r.y + u, r.w, r.h - 2 * u + (u - press)))
        pygame.draw.rect(out, shade, (r.x + u, r.y + u, r.w - 2 * u, r.h - 2 * u + (u - press)))
        pygame.draw.rect(out, body, (r.x + u, r.y + u, r.w - 2 * u, r.h - 3 * u))
        pygame.draw.rect(out, lit, (r.x + u, r.y + u, r.w - 2 * u, u))
        if active:
            pygame.draw.rect(out, theme.GOLD_LIGHT, (r.x + u, r.y + u, r.w - 2 * u, r.h - 2 * u + (u - press)), u)
        f = fonts.font("semi", self.size)
        lines = fonts.wrap(self.label, f, rect.width - 20)
        h = f.get_linesize()
        y = r.centery - (len(lines) * h) / 2
        for line in lines:
            fonts.text(out, line, f, fg, (r.centerx, y), "midtop")
            y += h
        return out


class ButtonGroup:
    """Quản lý một nhóm nút: bàn phím Tab/mũi tên chuyển focus, Enter để bấm."""

    def __init__(self, buttons: list[Button] | None = None):
        self.buttons = buttons or []
        self.index = -1

    def add(self, button: Button) -> Button:
        self.buttons.append(button)
        return button

    def clear(self):
        self.buttons.clear()
        self.index = -1

    def _move(self, step: int):
        usable = [i for i, b in enumerate(self.buttons) if b.enabled]
        if not usable:
            return
        if self.index in usable:
            pos = (usable.index(self.index) + step) % len(usable)
        else:
            pos = 0
        for b in self.buttons:
            b.focus = False
        self.index = usable[pos]
        self.buttons[self.index].focus = True

    def handle(self, event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_TAB, pygame.K_DOWN, pygame.K_RIGHT):
                self._move(1)
                return True
            if event.key in (pygame.K_UP, pygame.K_LEFT):
                self._move(-1)
                return True
        # Duyệt bản sao: on_click có thể thay đổi danh sách nút
        for b in list(self.buttons):
            if b.handle(event):
                return True
        return False

    def draw(self, surface):
        for b in self.buttons:
            b.draw(surface)


class Toasts:
    """Thông báo nổi góc trên: hoàn thành mục tiêu, nhận thưởng..."""

    def __init__(self):
        self.items: list[dict] = []

    def add(self, message: str, color=theme.GOLD, seconds: float = 3.0):
        self.items.append({"msg": message, "color": color, "t": seconds, "total": seconds})
        self.items = self.items[-4:]

    def update(self, dt: float):
        for it in self.items:
            it["t"] -= dt
        self.items = [it for it in self.items if it["t"] > 0]

    def draw(self, surface):
        f = fonts.font("semi", 17)
        y = 14
        for it in self.items:
            lines = fonts.wrap(it["msg"], f, 440)
            h = len(lines) * f.get_linesize() + 16
            w = max(f.size(line)[0] for line in lines) + 38
            rect = pygame.Rect(theme.WIDTH // 2 - w // 2, y, w, h)
            lacquer_panel(surface, rect)
            pygame.draw.circle(surface, it["color"], (rect.x + 16, rect.centery), 5)
            ty = rect.y + 8
            for line in lines:
                fonts.text(surface, line, f, theme.WHITE, (rect.x + 28, ty))
                ty += f.get_linesize()
            y += h + 8


def pulse(t: float, speed: float = 3.0) -> float:
    """Giá trị dao động 0..1 để tạo nhịp nhấp nháy."""
    return (math.sin(t * speed) + 1) / 2


def fancy_menu(surface, buttons, slide: dict, icons: dict) -> None:
    """Menu kiểu sơn mài: thanh vàng bên trái, biểu tượng, trượt nhẹ và viền sáng khi rê chuột hoặc chọn bằng phím."""
    from core import sprites  # nhập muộn: sprites nạp ảnh, ui dùng được cả khi chưa có cửa sổ

    for i, b in enumerate(buttons):
        r = b.rect.move(slide.get(i, 0.0), 0)
        lit = (b.hover or b.focus) and b.enabled
        gold = b.style == "gold"
        base = theme.GOLD if gold else (theme.LACQUER_RED if b.style == "primary" else theme.LACQUER_2)
        alpha_rect(surface, r.move(0, 4), (0, 0, 0, 90), 8)
        pygame.draw.rect(surface, base, r, border_radius=8)
        if lit:
            pygame.draw.rect(surface, theme.GOLD_LIGHT, r, 3, border_radius=8)
        pygame.draw.rect(surface, theme.GOLD_LIGHT if lit else theme.GOLD_DARK, (r.x, r.y + 8, 5, r.h - 16), border_radius=3)
        icon = icons.get(b.label)
        if icon:
            img = sprites.icon(icon, 2)
            surface.blit(img, img.get_rect(midleft=(r.x + 18, r.centery)))
        ink = theme.INK if gold else theme.GOLD_LIGHT
        fonts.text(surface, b.label, fonts.font("black" if gold else "bold", 21 if gold else 17), ink, (r.x + (70 if icon else 22), r.centery), "midleft")


def ease_slide(buttons, slide: dict, dt: float, amount: float = 14.0) -> None:
    """Cho nút đang được rê chuột hay chọn trượt ra một chút, mượt theo thời gian."""
    for i, b in enumerate(buttons):
        want = amount if (b.hover or b.focus) and b.enabled else 0.0
        cur = slide.get(i, 0.0)
        slide[i] = cur + (want - cur) * min(1.0, dt * 12)
