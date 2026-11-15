"""Scene và SceneManager dạng ngăn xếp: mở hội thoại, câu hỏi chồng lên bản đồ."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pygame

from core import platform_io
from core.theme import HEIGHT, WIDTH

FADE_TIME = 0.22


class Scene:
    """Một màn hình của game. Scene không trong suốt (opaque) thì che scene bên dưới."""

    opaque = True

    def __init__(self, app: Any):
        self.app = app

    @property
    def state(self):
        return self.app.state

    def on_enter(self) -> None: ...

    def on_resume(self, result: Any = None) -> None:
        """Gọi khi scene phía trên vừa đóng, `result` là giá trị scene đó trả về."""

    def handle(self, event: pygame.event.Event) -> None: ...

    def update(self, dt: float) -> None: ...

    def draw(self, screen: pygame.Surface) -> None: ...

    def backdrop(self, screen: pygame.Surface) -> None:
        """Lớp phủ tĩnh của scene trong suốt, được ghép sẵn cùng các scene bên dưới."""


class SceneManager:
    def __init__(self):
        self.stack: list[Scene] = []
        self._fade = 0.0
        self._fade_surf = pygame.Surface((WIDTH, HEIGHT))
        self._under = pygame.Surface((WIDTH, HEIGHT))
        self._under_owner: Scene | None = None
        # Hàm chạy mỗi khung hình dù cảnh nào đang ở trên cùng: giữ kết nối thế giới chung khi người chơi mở túi đồ,
        # bảng bạn chơi, hội thoại... (chỉ cảnh trên cùng được cập nhật nên không có hàm này thì mạng đứng im).
        self.pump: Callable[[float], None] | None = None
        # Đang chơi bằng cảm ứng: hiện nút chạm thay cho các phím (thuyền, ngựa, câu cá...). Hỏi trình duyệt lúc mở game,
        # rồi bật hẳn khi nhận được cú chạm đầu tiên.
        self.touch = platform_io.is_touch_device()

    @property
    def top(self) -> Scene | None:
        return self.stack[-1] if self.stack else None

    def push(self, scene: Scene) -> None:
        self.stack.append(scene)
        scene.on_enter()
        self._fade = FADE_TIME

    def replace(self, scene: Scene) -> None:
        if self.stack:
            self.stack.pop()
        self.push(scene)

    def reset(self, scene: Scene) -> None:
        self.stack.clear()
        self.push(scene)

    def pop(self, result: Any = None) -> None:
        if self.stack:
            self.stack.pop()
        if self.stack:
            self.stack[-1].on_resume(result)
            self._fade = FADE_TIME * 0.6

    def handle(self, event: pygame.event.Event) -> None:
        if event.type == pygame.FINGERDOWN or (event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "touch", False)):
            self.touch = True
        if self.top:
            self.top.handle(event)

    def update(self, dt: float) -> None:
        self._fade = max(0.0, self._fade - dt)
        if self.top:
            self.top.update(dt)
        if self.pump is not None:
            self.pump(dt)

    def draw(self, screen: pygame.Surface) -> None:
        # Vẽ từ scene không trong suốt gần nhất trở lên
        start = 0
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].opaque:
                start = i
                break
        top = self.stack[-1] if self.stack else None
        if top is not None and not top.opaque:
            # Chỉ scene trên cùng được cập nhật, nên phần bên dưới đứng yên: vẽ một lần rồi dùng lại
            if self._under_owner is not top:
                for scene in self.stack[start:-1]:
                    scene.draw(self._under)
                top.backdrop(self._under)
                self._under_owner = top
            screen.blit(self._under, (0, 0))
            top.draw(screen)
        elif top is not None:
            self._under_owner = None
            top.draw(screen)
        if self._fade > 0:
            self._fade_surf.set_alpha(int(255 * self._fade / FADE_TIME))
            screen.blit(self._fade_surf, (0, 0))
