"""Đồ hoạ pixel art (Ninja Adventure, CC0): tile gốc 16 px, phóng to bằng số nguyên để giữ nét."""

from __future__ import annotations

from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent / "assets" / "pixel"
UNIT = 16
SCALE = 4
TILE = UNIT * SCALE
DIRS = ("down", "up", "left", "right")

# Vai trong nội dung -> nhân vật trong gói asset. Nhân vật lịch sử hiện đại dùng biểu tượng tư liệu, không vẽ mặt.
PORTRAITS = {
    "cu_do": "Master", "cu_tu": "Monk", "ba_cu": "OldWoman", "lai_do": "OldMan3", "cuu_binh": "OldMan",
    "tuong": "TuongDaiViet", "vua": "Noble", "quan_van": "Monk2", "nghia_si": "Villager3", "bo_lao": "Master",
    "nu_si": "Princess", "chien_si": "BoDoi", "giac": "NinjaGray",
    "giac_tong": "TuongTong", "giac_nguyen": "TuongNguyen", "giac_minh": "TuongMinh",
}

_images: dict[str, pygame.Surface] = {}
_cache: dict[tuple, object] = {}


def image(name: str) -> pygame.Surface:
    img = _images.get(name)
    if img is None:
        img = pygame.image.load(str(ROOT / name)).convert_alpha()
        _images[name] = img
    return img


def scaled(img: pygame.Surface, scale: int = SCALE) -> pygame.Surface:
    return pygame.transform.scale(img, (img.get_width() * scale, img.get_height() * scale))


def region(sheet: str, col: int, row: int, w: int = 1, h: int = 1, scale: int = SCALE) -> pygame.Surface:
    """Cắt một vùng tính theo ô 16 px từ tileset, đã phóng to."""
    key = (sheet, col, row, w, h, scale)
    out = _cache.get(key)
    if out is None:
        src = image(f"tiles/{sheet}.png").subsurface((col * UNIT, row * UNIT, w * UNIT, h * UNIT))
        out = scaled(src, scale)
        _cache[key] = out
    return out


def strip(name: str, count: int, scale: int = SCALE) -> list[pygame.Surface]:
    """Dải khung hình nằm ngang (hiệu ứng, cờ bay...)."""
    key = ("strip", name, count, scale)
    out = _cache.get(key)
    if out is None:
        src = image(name)
        fw, fh = src.get_width() // count, src.get_height()
        out = [scaled(src.subsurface((i * fw, 0, fw, fh)), scale) for i in range(count)]
        _cache[key] = out
    return out


def icon(name: str, scale: int = SCALE) -> pygame.Surface:
    key = ("icon", name, scale)
    out = _cache.get(key)
    if out is None:
        out = scaled(image(name), scale)
        _cache[key] = out
    return out


def sepia(img: pygame.Surface) -> pygame.Surface:
    """Bản màu nâu cũ dùng trong hồi ức. Giữ kênh alpha để nhân vật không bị viền."""
    out = pygame.transform.grayscale(img)
    out.fill((255, 226, 178, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return out


class Cast:
    """Khung hình một nhân vật: `walk[hướng][khung]`, `attack[hướng]`, `dead`, `face`."""

    def __init__(self, name: str, scale: int = SCALE, old: bool = False):
        fx = sepia if old else (lambda s: s)
        walk = image(f"char/{name}/walk.png")
        attack = image(f"char/{name}/attack.png")
        self.walk = {
            d: [fx(scaled(walk.subsurface((c * UNIT, r * UNIT, UNIT, UNIT)), scale)) for r in range(4)]
            for c, d in enumerate(DIRS)
        }
        self.attack = {d: fx(scaled(attack.subsurface((c * UNIT, 0, UNIT, UNIT)), scale)) for c, d in enumerate(DIRS)}
        self.dead = fx(scaled(image(f"char/{name}/dead.png"), scale))
        self.size = UNIT * scale


def cast(name: str, scale: int = SCALE, old: bool = False) -> Cast:
    key = ("cast", name, scale, old)
    out = _cache.get(key)
    if out is None:
        out = Cast(name, scale, old)
        _cache[key] = out
    return out


def portrait(kind: str, scale: int = 3) -> pygame.Surface:
    """Chân dung trong khung. `tu_lieu` và nhân vật lịch sử hiện đại hiện cuộn tư liệu thay vì khuôn mặt."""
    key = ("portrait", kind, scale)
    out = _cache.get(key)
    if out is None:
        box = scaled(image("ui/faceset_box.png"), scale)
        out = box.copy()
        name = PORTRAITS.get(kind)
        path = ROOT / "char" / str(name) / "face.png"
        if name and path.exists():
            face = scaled(image(f"char/{name}/face.png"), scale)
        else:
            face = scaled(image("ui/scroll.png"), scale * 2)
        out.blit(face, face.get_rect(center=out.get_rect().center))
        _cache[key] = out
    return out
