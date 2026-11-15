"""Điều khiển cảm ứng dùng chung: cần điều khiển ảo để đi, và nút nhận được ngón thứ hai.

Một cú chạm trên điện thoại đến game bằng hai đường: sự kiện ngón (FINGERDOWN, FINGERMOTION, FINGERUP, toạ độ 0..1, mỗi
ngón một mã) và "chuột giả" (MOUSEBUTTONDOWN... có touch=True) chỉ cho ngón chạm đầu tiên. Muốn vừa giữ cần đi bằng ngón
cái trái vừa bấm CHÉM bằng ngón cái phải thì cần và nút phải nghe sự kiện ngón; chuột giả của chính những cú chạm ấy thì
nuốt đi cho khỏi tính hai lần (và để màn chơi không tưởng là bấm lên bản đồ mà đi tới đó).

Máy nào không gửi sự kiện ngón (SceneManager.fingers còn False) thì cần và nút chạy bằng chuột như thường.
"""

from __future__ import annotations

import math

import pygame

from core import theme

FINGER_EVENTS = (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP)
MOUSE_EVENTS = (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP)


def finger_pos(event) -> tuple[float, float]:
    """Toạ độ ngón (0..1 theo khung game) đổi ra toạ độ màn hình game."""
    return event.x * theme.WIDTH, event.y * theme.HEIGHT


def is_touch_mouse(event) -> bool:
    """Chuột giả sinh ra từ một cú chạm."""
    return bool(getattr(event, "touch", False))


class Stick:
    """Cần điều khiển ảo: đặt ngón vào vòng tròn rồi kéo về hướng muốn đi, kéo càng xa càng nhanh, nhấc tay là dừng."""

    DEAD = 0.2  # rung tay quanh tâm thì không đi

    def __init__(self, center: tuple[float, float], radius: float = 66, grab: float = 1.4):
        self.cx, self.cy = center
        self.r = radius
        self.grab = radius * grab  # chạm lệch ra ngoài vòng một chút vẫn bắt được
        self.owner = None  # mã ngón đang giữ cần, "mouse" khi chạy bằng chuột
        self.knob = (0.0, 0.0)
        self._gesture = False  # đang nuốt chuột giả của một cú chạm bắt đầu trên cần

    @property
    def active(self) -> bool:
        return self.owner is not None

    def vector(self) -> tuple[float, float]:
        """Hướng và độ mạnh, mỗi trục từ -1 tới 1; (0, 0) khi không giữ cần."""
        dx, dy = self.knob[0] / self.r, self.knob[1] / self.r
        m = math.hypot(dx, dy)
        if not self.active or m < self.DEAD:
            return 0.0, 0.0
        k = min(1.0, (m - self.DEAD) / (1 - self.DEAD)) / m  # bỏ vùng chết rồi kéo dãn lại cho mượt
        return dx * k, dy * k

    def contains(self, pos) -> bool:
        return (pos[0] - self.cx) ** 2 + (pos[1] - self.cy) ** 2 <= self.grab ** 2

    def release(self):
        """Thả cần. Không xoá dấu cú chạm: chuột giả của ngón vừa nhấc còn tới sau, vẫn phải nuốt đi."""
        self.owner = None
        self.knob = (0.0, 0.0)

    def reset(self):
        """Quay lại màn chơi sau một cảnh khác: quên hết cú chạm cũ."""
        self.release()
        self._gesture = False

    def _aim(self, pos):
        dx, dy = pos[0] - self.cx, pos[1] - self.cy
        d = math.hypot(dx, dy)
        if d > self.r:
            dx, dy = dx / d * self.r, dy / d * self.r
        self.knob = (dx, dy)

    def handle(self, event, fingers: bool) -> bool:
        """True nếu sự kiện thuộc về cần (màn chơi đừng xử lý tiếp)."""
        t = event.type
        if t == pygame.FINGERDOWN:
            pos = finger_pos(event)
            if self.owner is None and self.contains(pos):
                self.owner = event.finger_id
                self._aim(pos)
                return True
            return False
        if t in (pygame.FINGERMOTION, pygame.FINGERUP):
            if self.owner is None or self.owner != event.finger_id:
                return False
            if t == pygame.FINGERUP:
                self.release()
            else:
                self._aim(finger_pos(event))
            return True
        if t == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.contains(event.pos):
            self._gesture = True
            if not (fingers and is_touch_mouse(event)) and self.owner is None:
                self.owner = "mouse"
                self._aim(event.pos)
            return True
        if not self._gesture or t not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
            return False
        if t == pygame.MOUSEMOTION and self.owner == "mouse":
            self._aim(event.pos)
        elif t == pygame.MOUSEBUTTONUP:
            self._gesture = False
            if self.owner == "mouse":
                self.release()
        return True

    def draw(self, screen):
        base = _base(round(self.r))
        screen.blit(base, base.get_rect(center=(self.cx, self.cy)))
        knob = _knob(round(self.r * 0.46), self.active)
        screen.blit(knob, knob.get_rect(center=(self.cx + self.knob[0], self.cy + self.knob[1])))


class FingerButtons:
    """Cho các nút (ui.Button) nhận ngón chạm, kể cả ngón thứ hai: đặt ngón lên nút, nhấc lên ngay trên nút đó là bấm."""

    def __init__(self):
        self.down: dict[int, object] = {}
        self._gesture = False

    def handle(self, event, buttons: list, fingers: bool) -> bool:
        t = event.type
        if t == pygame.FINGERDOWN:
            pos = finger_pos(event)
            for b in buttons:
                if b.enabled and b.rect.collidepoint(pos):
                    self.down[event.finger_id] = b
                    b._press = True
                    return True
            return False
        if t == pygame.FINGERUP and event.finger_id in self.down:
            b = self.down.pop(event.finger_id)
            b._press = False
            if b in buttons and b.rect.collidepoint(finger_pos(event)):
                b.click()
            return True
        if t == pygame.FINGERMOTION:
            return event.finger_id in self.down
        if not (fingers and is_touch_mouse(event)):
            return False
        # chuột giả của cú chạm đã xử lý bằng sự kiện ngón: nuốt đi nếu cú chạm bắt đầu trên một nút
        if t == pygame.MOUSEBUTTONDOWN and any(b.rect.collidepoint(event.pos) for b in buttons):
            self._gesture = True
            return True
        if self._gesture and t in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
            if t == pygame.MOUSEBUTTONUP:
                self._gesture = False
            return True
        return False


_cache: dict[tuple, pygame.Surface] = {}


def _base(r: int) -> pygame.Surface:
    key = ("base", r)
    if key not in _cache:
        s = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        c = r + 4
        pygame.draw.circle(s, (20, 12, 10, 120), (c, c), r)
        pygame.draw.circle(s, (243, 212, 140, 150), (c, c), r, 3)
        for ang in (0, 90, 180, 270):  # bốn mũi tên nhỏ chỉ hướng
            a = math.radians(ang)
            tip = (c + math.cos(a) * (r - 10), c + math.sin(a) * (r - 10))
            side = [(c + math.cos(a) * (r - 22) + math.cos(a + math.pi / 2) * 8, c + math.sin(a) * (r - 22) + math.sin(a + math.pi / 2) * 8),
                    (c + math.cos(a) * (r - 22) - math.cos(a + math.pi / 2) * 8, c + math.sin(a) * (r - 22) - math.sin(a + math.pi / 2) * 8)]
            pygame.draw.polygon(s, (243, 212, 140, 160), [tip, *side])
        _cache[key] = s
    return _cache[key]


def _knob(r: int, active: bool) -> pygame.Surface:
    key = ("knob", r, active)
    if key not in _cache:
        s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        c = r + 2
        pygame.draw.circle(s, (24, 16, 14, 200), (c, c), r + 2)
        pygame.draw.circle(s, (243, 212, 140, 235 if active else 170), (c, c), r)
        pygame.draw.circle(s, (217, 167, 72, 255), (c, c), r, 3)
        _cache[key] = s
    return _cache[key]
