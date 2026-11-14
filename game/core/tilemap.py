"""Bản đồ ô vuông: tự nối đường đi và bờ nước, vẽ theo từng mảng để nhẹ trên WebAssembly.

Tự nối theo cách ghép 4 góc: mỗi ô 16 px chia thành 4 phần 8 px, chọn từ khối 3x3 và ô "đảo nhỏ" của tileset
tuỳ theo các ô hàng xóm. Nhờ vậy chỉ cần vài ô gốc mà đủ mọi góc trong, góc ngoài.
"""

from __future__ import annotations

import pygame

from core import sprites
from core.sprites import SCALE, TILE, UNIT

GRASS, PATH, WATER, BRIDGE, RICE, SAND, PADDY = range(7)
# Mỗi mảng 8x8 ô: dựng rất nhanh nên không làm khựng khung hình, tốn cùng bộ nhớ với 9 mảng 16x16.
CHUNK = 8
MAX_CHUNKS = 36  # phải đủ chứa khung nhìn cộng một vòng dựng trước (tối đa 6x5 mảng)
PREFETCH_MARGIN = 1
HALF = UNIT // 2
# (tileset, cột khối 3x3, hàng khối 3x3, ô đảo nhỏ)
_AUTO = {PATH: ("floor", 0, 7, (6, 9)), WATER: ("water", 0, 6, (6, 8))}
_GRASS_TILES = ((0, 12), (0, 12), (0, 12), (0, 12), (0, 12), (0, 12), (1, 12), (2, 12), (3, 12), (4, 12))
_cache: dict[tuple, pygame.Surface] = {}


def _native(sheet: str, col: int, row: int) -> pygame.Surface:
    return sprites.image(f"tiles/{sheet}.png").subsurface((col * UNIT, row * UNIT, UNIT, UNIT))


def _auto_tile(terrain: int, mask: tuple[bool, ...]) -> pygame.Surface:
    """`mask` = (B, Đ, N, T, ĐB, ĐN, TN, TB): ô hàng xóm có cùng loại địa hình không."""
    key = (terrain, mask)
    out = _cache.get(key)
    if out is not None:
        return out
    sheet, c0, r0, island = _AUTO[terrain]
    n, e, s, w, ne, se, sw, nw = mask
    tile = pygame.Surface((UNIT, UNIT), pygame.SRCALPHA)
    # Mỗi phần: (vị trí trong ô, hàng xóm dọc, hàng xóm ngang, hàng xóm chéo, hướng trong khối 3x3)
    quads = ((0, 0, n, w, nw, -1, -1), (1, 0, n, e, ne, 1, -1), (0, 1, s, w, sw, -1, 1), (1, 1, s, e, se, 1, 1))
    for qx, qy, vert, horiz, diag, dx, dy in quads:
        if vert and horiz:
            if diag:
                col, row, sx, sy = c0 + 1, r0 + 1, qx, qy  # giữa khối
            else:
                col, row, sx, sy = island[0], island[1], 1 - qx, 1 - qy  # góc trong lấy từ ô đảo nhỏ
        else:
            col = c0 + 1 + (dx if not horiz else 0)
            row = r0 + 1 + (dy if not vert else 0)
            sx, sy = qx, qy
        src = _native(sheet, col, row).subsurface((sx * HALF, sy * HALF, HALF, HALF))
        tile.blit(src, (qx * HALF, qy * HALF))
    out = sprites.scaled(tile, SCALE)
    _cache[key] = out
    return out


class TileMap:
    """Lưới địa hình + lớp trang trí phẳng, vẽ thành từng mảng rồi lưu đệm."""

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.ground = bytearray(w * h)
        self.solid = bytearray(w * h)
        self.flat: dict[tuple[int, int], pygame.Surface] = {}
        self.variant = bytearray(w * h)
        self._chunks: dict[tuple[int, int], pygame.Surface] = {}
        self._ready_view: tuple[int, int, int, int] | None = None

    # ----- truy vấn -----
    def get(self, x: int, y: int) -> int:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.ground[y * self.w + x]
        return -1

    def set(self, x: int, y: int, terrain: int) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.ground[y * self.w + x] = terrain

    def blocked(self, x: int, y: int) -> bool:
        if not (0 <= x < self.w and 0 <= y < self.h):
            return True
        i = y * self.w + x
        return bool(self.solid[i]) or self.ground[i] == WATER

    def blocked_solid(self, x: int, y: int) -> bool:
        """Có vật chắn hoặc ngoài bản đồ; không tính nước, dùng khi mở lối đi mới."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return True
        return bool(self.solid[y * self.w + x])

    def set_solid(self, x: int, y: int, value: bool = True) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.solid[y * self.w + x] = 1 if value else 0

    # ----- vẽ ô -----
    def _same(self, terrain: int, x: int, y: int) -> bool:
        t = self.get(x, y)
        if t == -1:
            return True  # coi ngoài rìa bản đồ là cùng loại để khỏi hiện viền ở mép
        if terrain == WATER:
            return t in (WATER, BRIDGE)
        if terrain == PATH:
            return t in (PATH, BRIDGE)
        return t == terrain

    def _tile(self, x: int, y: int) -> pygame.Surface:
        t = self.get(x, y)
        if t == -1:
            return sprites.region("floor", 0, 12)  # mảng ảnh có thể chìa ra ngoài rìa bản đồ
        if t in _AUTO:
            same = self._same
            mask = (
                same(t, x, y - 1), same(t, x + 1, y), same(t, x, y + 1), same(t, x - 1, y),
                same(t, x + 1, y - 1), same(t, x + 1, y + 1), same(t, x - 1, y + 1), same(t, x - 1, y - 1),
            )
            return _auto_tile(t, mask)
        if t == BRIDGE:
            return sprites.region("water", 1, 13)
        if t == RICE:
            return sprites.region("element", 14, 5)
        if t == SAND:
            return sprites.region("floor", 0, 5)
        if t == PADDY:
            return sprites.region("nature", 7, 11)
        col, row = _GRASS_TILES[self.variant[y * self.w + x] % len(_GRASS_TILES)]
        return sprites.region("floor", col, row)

    def warm(self) -> None:
        """Tạo sẵn mọi kiểu ô mà map này dùng tới. Chạy lúc tải màn, tốn một lần rồi thôi."""
        for y in range(self.h):
            for x in range(self.w):
                self._tile(x, y)

    def _build_chunk(self, cx: int, cy: int) -> pygame.Surface:
        surf = pygame.Surface((CHUNK * TILE, CHUNK * TILE))
        grass = sprites.region("floor", 0, 12)
        for j in range(CHUNK):
            y = cy * CHUNK + j
            for i in range(CHUNK):
                x = cx * CHUNK + i
                pos = (i * TILE, j * TILE)
                if self.get(x, y) in (*_AUTO, PADDY):
                    surf.blit(grass, pos)  # lót nền cỏ dưới các ô có phần trong suốt
                surf.blit(self._tile(x, y), pos)
                deco = self.flat.get((x, y))
                if deco is not None:
                    surf.blit(deco, pos)
        return surf

    def draw(self, screen: pygame.Surface, cam_x: float, cam_y: float) -> None:
        sw, sh = screen.get_size()
        size = CHUNK * TILE
        x0, y0 = int(cam_x // size), int(cam_y // size)
        x1, y1 = int((cam_x + sw) // size), int((cam_y + sh) // size)
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                if not (0 <= cx * CHUNK < self.w and 0 <= cy * CHUNK < self.h):
                    continue
                screen.blit(self._chunk(cx, cy), (cx * size - cam_x, cy * size - cam_y))

    def _chunk(self, cx: int, cy: int) -> pygame.Surface:
        key = (cx, cy)
        chunk = self._chunks.get(key)
        if chunk is None:
            chunk = self._build_chunk(cx, cy)
            self._chunks[key] = chunk
            if len(self._chunks) > MAX_CHUNKS:
                # Bỏ mảng xa chỗ vừa dựng nhất, như vậy không bao giờ bỏ nhầm mảng đang nhìn thấy
                far = max(self._chunks, key=lambda k: (k[0] - cx) ** 2 + (k[1] - cy) ** 2)
                del self._chunks[far]
                self._ready_view = None
        return chunk

    def prefetch(self, cam_x: float, cam_y: float, sw: int, sh: int) -> bool:
        """Dựng trước tối đa một mảng ở ngay ngoài khung nhìn, để lúc camera tới nơi đã có sẵn.

        Trên web âm thanh chạy chung luồng với game: dựng nhiều mảng trong một khung hình làm khung đó dài ra và nhạc
        kêu "è è". Chia đều mỗi khung một mảng thì không khung nào bị khựng.
        """
        size = CHUNK * TILE
        x0, y0 = int(cam_x // size) - PREFETCH_MARGIN, int(cam_y // size) - PREFETCH_MARGIN
        x1, y1 = int((cam_x + sw) // size) + PREFETCH_MARGIN, int((cam_y + sh) // size) + PREFETCH_MARGIN
        view = (x0, y0, x1, y1)
        if view == self._ready_view:
            return False
        mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
        best, best_d = None, 1e9
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                if (cx, cy) in self._chunks or not (0 <= cx * CHUNK < self.w and 0 <= cy * CHUNK < self.h):
                    continue
                d = (cx - mid_x) ** 2 + (cy - mid_y) ** 2
                if d < best_d:
                    best, best_d = (cx, cy), d
        if best is None:
            self._ready_view = view
            return False
        self._chunk(*best)
        return True

    def forget(self) -> None:
        """Giải phóng bộ nhớ khi rời bản đồ."""
        self._chunks.clear()
        self._ready_view = None

    # ----- tìm đường cho bấm chuột, chạm màn hình -----
    def find_path(self, start: tuple[int, int], goal: tuple[int, int], limit: int = 6000) -> list[tuple[int, int]]:
        """BFS 4 hướng; ô đích bị chắn thì đi tới ô trống gần nhất đã thăm."""
        if start == goal:
            return []
        w = self.w
        prev = {start: None}
        queue = [start]
        head = 0
        best, best_d = start, abs(start[0] - goal[0]) + abs(start[1] - goal[1])
        while head < len(queue) and len(queue) < limit:
            cur = queue[head]
            head += 1
            d = abs(cur[0] - goal[0]) + abs(cur[1] - goal[1])
            if d < best_d:
                best, best_d = cur, d
            if cur == goal:
                best = cur
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (cur[0] + dx, cur[1] + dy)
                if nxt in prev or not (0 <= nxt[0] < w and 0 <= nxt[1] < self.h) or self.blocked(*nxt):
                    continue
                prev[nxt] = cur
                queue.append(nxt)
        path = []
        cur = best
        while cur is not None and cur != start:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path
