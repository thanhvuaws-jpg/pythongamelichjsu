"""Thời tiết vẽ đè lên map: mưa, lá rơi, sương. Số hạt ít và ảnh dựng sẵn để vẫn nhẹ trên WebAssembly."""

from __future__ import annotations

import math
import random

import pygame

from core import sprites, theme

W, H = theme.WIDTH, theme.HEIGHT
RAIN_DROPS = 70
LEAVES = 12
CLOUDS = 3
LEAF_FRAMES = 6
CLOUD_SCALE = 7
CLOUD_ALPHA = 46
_cloud: pygame.Surface | None = None


def _cloud_image() -> pygame.Surface:
    global _cloud
    if _cloud is None:
        img = sprites.image("fx/clouds.png")
        _cloud = pygame.transform.scale(img, (img.get_width() * CLOUD_SCALE, img.get_height() * CLOUD_SCALE))
        _cloud.set_alpha(CLOUD_ALPHA)
    return _cloud


class Weather:
    def __init__(self):
        self.kind: str | None = None
        self.t = 0.0
        self.parts: list[list[float]] = []
        self.frames: list[pygame.Surface] = []

    def set(self, kind: str | None) -> None:
        if kind == "none":
            kind = None
        if kind == self.kind:
            return
        self.kind = kind
        if kind == "rain":
            self.parts = [[random.uniform(0, W), random.uniform(0, H)] for _ in range(RAIN_DROPS)]
        elif kind in ("leaf", "leaf_pink"):
            name = "fx/leaf.png" if kind == "leaf" else "fx/leaf_pink.png"
            self.frames = sprites.strip(name, LEAF_FRAMES, 3)
            self.parts = [[random.uniform(0, W), random.uniform(0, H), random.uniform(40, 80), random.uniform(0, 6)] for _ in range(LEAVES)]
        elif kind == "fog":
            self.parts = [[random.uniform(-200, W), random.uniform(60, H - 300), random.uniform(10, 24)] for _ in range(CLOUDS)]
        else:
            self.parts = []

    def update(self, dt: float) -> None:
        self.t += dt
        if self.kind == "rain":
            for p in self.parts:
                p[0] -= 150 * dt
                p[1] += 720 * dt
                if p[1] > H:
                    p[0], p[1] = random.uniform(0, W + 150), -16.0
        elif self.kind in ("leaf", "leaf_pink"):
            for p in self.parts:
                p[1] += p[2] * dt
                p[0] += math.sin(self.t * 1.3 + p[3]) * 50 * dt
                if p[1] > H:
                    p[0], p[1] = random.uniform(0, W), -12.0
        elif self.kind == "fog":
            cloud = _cloud_image()
            for p in self.parts:
                p[0] += p[2] * dt
                if p[0] > W:
                    p[0], p[1] = float(-cloud.get_width()), random.uniform(60, H - 300)

    def draw(self, screen: pygame.Surface) -> None:
        if self.kind == "rain":
            for x, y in self.parts:
                pygame.draw.line(screen, (176, 200, 216), (x, y), (x - 4, y + 16), 1)
        elif self.kind in ("leaf", "leaf_pink"):
            for x, y, _speed, phase in self.parts:
                screen.blit(self.frames[int(self.t * 5 + phase) % LEAF_FRAMES], (x, y))
        elif self.kind == "fog":
            cloud = _cloud_image()
            for x, y, _speed in self.parts:
                screen.blit(cloud, (x, y))
