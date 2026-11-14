"""Dựng thế giới cho từng màn từ mô tả trong content/worlds.json: sông, đường, làng, thành, đền, trại quân..."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from core import buildings, sprites
from core.sprites import TILE
from core.tilemap import BRIDGE, PADDY, PATH, RICE, WATER, TileMap

# Tên vật thể -> (tileset, cột, hàng, rộng, cao, số hàng chắn đường tính từ dưới lên)
CATALOG = {
    "tree": ("nature", 0, 0, 2, 2, 1), "pine": ("nature", 2, 0, 2, 2, 1), "old_tree": ("nature", 6, 0, 2, 2, 1),
    "thin_tree": ("nature", 6, 8, 2, 2, 1), "grove": ("nature", 4, 2, 4, 3, 1), "pines": ("nature", 0, 2, 4, 3, 1),
    "banyan": ("nature", 3, 18, 3, 3, 1), "bamboo": ("nature", 11, 8, 1, 3, 1), "stump": ("nature", 0, 8, 2, 2, 1),
    "rock": ("nature", 15, 10, 2, 2, 1), "rock_big": ("nature", 17, 10, 4, 3, 2), "rock_tall": ("nature", 21, 10, 2, 3, 2),
    "gray": ("nature", 15, 14, 2, 2, 1), "gray_big": ("nature", 17, 14, 4, 3, 2), "gray_tall": ("nature", 21, 14, 2, 3, 2),
    "house": ("house", 0, 0, 3, 3, 2), "house2": ("house", 8, 0, 4, 3, 2), "house3": ("house", 4, 0, 4, 3, 2),
    "temple": ("house", 12, 0, 3, 3, 2), "hut": ("house", 3, 8, 3, 2, 1), "hut2": ("house", 0, 8, 3, 2, 1),
    "gate": ("house", 0, 5, 3, 2, 0), "statue": ("house", 1, 15, 2, 3, 1), "statue2": ("house", 3, 15, 2, 2, 1),
    "banner_r": ("house", 23, 20, 1, 2, 1), "banner_y": ("house", 28, 20, 1, 2, 1), "banner_g": ("house", 25, 20, 1, 2, 1),
    "arch": ("house", 29, 20, 3, 3, 0), "wall": ("house", 12, 9, 1, 1, 1), "wall_v": ("house", 11, 8, 1, 1, 1),
    "fence": ("house", 12, 5, 1, 1, 1), "fence_v": ("house", 11, 4, 1, 1, 1),
    "tent": ("camp", 4, 0, 3, 3, 2), "tent2": ("camp", 7, 0, 3, 3, 2), "tent3": ("camp", 10, 0, 3, 3, 2),
    "fire": ("camp", 10, 5, 2, 2, 1), "pot_stand": ("camp", 8, 3, 2, 2, 1), "table": ("camp", 0, 7, 3, 1, 1), "barrels": ("camp", 4, 5, 2, 2, 1),
    "sign": ("nature", 5, 8, 1, 1, 1), "well": ("element", 6, 1, 1, 1, 1), "pot": ("element", 4, 0, 1, 1, 1),
    "crate": ("element", 0, 0, 1, 1, 1), "scarecrow": ("element", 15, 0, 1, 1, 1), "stele": ("element", 4, 2, 1, 1, 0),
    "boat": ("boat", 0, 0, 5, 2, 0), "cellar": ("element", 8, 11, 1, 1, 0), "ruin": ("aband", 12, 7, 4, 4, 2),
    # công trình Việt vẽ riêng trong core/buildings.py
    "dinh": ("custom", 0, 0, 4, 3, 2), "nha_san": ("custom", 0, 0, 4, 3, 1), "cung_dien": ("custom", 0, 0, 5, 4, 2),
    "cong_thanh": ("custom", 0, 0, 5, 4, 2), "tuong_thanh": ("custom", 0, 0, 1, 2, 1), "tuong_thanh_doc": ("custom", 0, 0, 1, 1, 1),
    "luy_dat": ("custom", 0, 0, 1, 2, 1), "luy_dat_doc": ("custom", 0, 0, 1, 1, 1), "thap_canh": ("custom", 0, 0, 2, 4, 1),
    "nha_pho": ("custom", 0, 0, 3, 3, 2),
}


def prop_image(name: str, scale: int = sprites.SCALE) -> pygame.Surface:
    """Ảnh một vật thể: công trình Việt vẽ riêng nếu có, còn lại cắt từ tileset của gói asset."""
    if name in buildings.DRAW:
        return buildings.image(name, scale)
    sheet, c, r, w, h, _ = CATALOG[name]
    return sprites.region(sheet, c, r, w, h, scale)
BUSHES = [("nature", c, 10) for c in range(8)]
FLOWERS = [("nature", c, 11) for c in (0, 1, 2, 3, 6)]
SPOTS = ((-4, 1), (4, 1), (-3, -2), (3, -2), (-2, 3), (2, 3), (0, -3), (-5, -1), (5, -1))
TREE_SETS = {
    "song": ("tree", "tree", "thin_tree", "bamboo", "bamboo", "old_tree", "grove"),
    "rung": ("pine", "pine", "bamboo", "bamboo", "tree", "pines", "gray", "rock"),
    "bac": ("pine", "pines", "bamboo", "bamboo", "bamboo", "tree", "grove", "gray"),
}
BORDER = 3
CHARRED = (110, 92, 84)
ARENA_RX, ARENA_RY = 5, 3


@dataclass
class Prop:
    img: pygame.Surface
    x: int
    y: int
    sort: int


@dataclass
class Anim:
    frames: list
    x: int
    y: int
    sort: int
    fps: float = 6.0


@dataclass
class Zone:
    relic_id: str
    cx: int
    cy: int
    theme: str
    spots: list = field(default_factory=list)


class World:
    def __init__(self, level_id: str, spec: dict):
        self.level_id = level_id
        self.w, self.h = spec["size"]
        self.map = TileMap(self.w, self.h)
        self.props: dict[tuple[int, int], list[Prop]] = {}
        self.anims: list[Anim] = []
        self.ripples: list[tuple[int, int]] = []
        self.zones: dict[str, Zone] = {}
        self.spawn = tuple(spec["spawn"])
        self.portal = tuple(spec["portal"])
        self.mentor = tuple(spec["mentor"])
        self.npcs = spec.get("npcs", [])
        self.arena = tuple(spec["arena"]) if spec.get("arena") else None
        self.annex = spec.get("annex")  # vùng mở rộng: nơi phục dựng tư liệu
        self.px_w, self.px_h = self.w * TILE, self.h * TILE
        self.minimap: pygame.Surface | None = None
        self.on_water: list[tuple] = []  # thuyền, cọc: dùng để kiểm thử chúng không nằm trên bờ, trên cầu

    def add_prop(self, prop: Prop) -> None:
        self.props.setdefault((prop.x // (TILE * 8), prop.sort // (TILE * 8)), []).append(prop)

    def visible_props(self, cam_x: float, cam_y: float, sw: int, sh: int):
        """Vật thể trong khung nhìn, tính dư để vật cao ở hàng dưới màn hình vẫn được vẽ."""
        b = TILE * 8
        out = []
        for gy in range(int((cam_y - TILE) // b), int((cam_y + sh + TILE * 4) // b) + 1):
            for gx in range(int((cam_x - TILE * 5) // b), int((cam_x + sw) // b) + 1):
                out.extend(self.props.get((gx, gy), ()))
        return out

    def build_minimap(self) -> pygame.Surface:
        if self.minimap is None:
            s = pygame.Surface((self.w, self.h))
            colors = {0: (132, 164, 74), PATH: (176, 126, 84), WATER: (92, 170, 200), BRIDGE: (214, 150, 86), RICE: (226, 192, 104), PADDY: (96, 170, 84)}
            for y in range(self.h):
                for x in range(self.w):
                    i = y * self.w + x
                    c = colors.get(self.map.ground[i], (132, 164, 74))
                    if self.map.solid[i]:
                        c = (82, 112, 62)
                    s.set_at((x, y), c)
            self.minimap = pygame.transform.scale(s, (self.w * 2, self.h * 2))
        return self.minimap


class Builder:
    def __init__(self, level_id: str, spec: dict):
        self.world = World(level_id, spec)
        self.map = self.world.map
        self.rng = random.Random(level_id)
        self.reserved = bytearray(self.map.w * self.map.h)
        self.spec = spec
        self.last_prop: Prop | None = None
        for i in range(len(self.map.variant)):
            self.map.variant[i] = self.rng.randrange(255)

    # ----- nét vẽ địa hình -----
    def _reserve(self, x, y):
        if 0 <= x < self.map.w and 0 <= y < self.map.h:
            self.reserved[y * self.map.w + x] = 1

    def _free(self, x, y, w=1, h=1):
        for j in range(y, y + h):
            for i in range(x, x + w):
                if not (0 <= i < self.map.w and 0 <= j < self.map.h):
                    return False
                if self.reserved[j * self.map.w + i] or self.map.get(i, j) in (WATER, BRIDGE, PATH):
                    return False
        return True

    def stroke(self, pts, terrain, width):
        """Vẽ đường gấp khúc có độ rộng, dùng cho sông và đường đi."""
        for (x0, y0), (x1, y1) in zip(pts, pts[1:], strict=False):
            steps = max(abs(x1 - x0), abs(y1 - y0), 1)
            for s in range(steps + 1):
                cx, cy = x0 + (x1 - x0) * s / steps, y0 + (y1 - y0) * s / steps
                for j in range(-width // 2 + 1, width // 2 + 1):
                    for i in range(-width // 2 + 1, width // 2 + 1):
                        x, y = round(cx) + i, round(cy) + j
                        cur = self.map.get(x, y)
                        if cur == -1:
                            continue
                        if terrain == PATH:
                            self.map.set(x, y, BRIDGE if cur in (WATER, BRIDGE) else PATH)
                            self._reserve(x, y)
                        else:
                            self.map.set(x, y, terrain)

    def blob(self, cx, cy, rx, ry, terrain):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / max(rx, 1)) ** 2 + ((y - cy) / max(ry, 1)) ** 2 <= 1.0:
                    self.map.set(x, y, terrain)
                    if terrain == PATH:
                        self._reserve(x, y)

    def rect(self, x0, y0, w, h, terrain):
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                self.map.set(x, y, terrain)

    # ----- đặt vật thể -----
    def put(self, name, tx, ty, force=False) -> bool:
        _sheet, _c, _r, w, h, solid = CATALOG[name]
        if not force and not self._free(tx, ty, w, h):
            return False
        img = prop_image(name)
        self.last_prop = Prop(img, tx * TILE, ty * TILE, (ty + h) * TILE)
        self.world.add_prop(self.last_prop)
        for j in range(ty + h - solid, ty + h):
            for i in range(tx, tx + w):
                self.map.set_solid(i, j)
        for j in range(ty, ty + h):
            for i in range(tx, tx + w):
                self._reserve(i, j)
        return True

    def flag(self, tx, ty, color="red"):
        frames = sprites.strip(f"fx/flag_{color}.png", 4)
        self.world.anims.append(Anim(frames, tx * TILE, ty * TILE - TILE // 2, (ty + 1) * TILE, 7))
        self.map.set_solid(tx, ty)
        self._reserve(tx, ty)

    def flame(self, tx, ty):
        frames = sprites.strip("fx/flame.png", 8)
        self.world.anims.append(Anim(frames, tx * TILE - TILE // 4, ty * TILE - TILE, (ty + 1) * TILE, 10))

    def flat(self, tx, ty, piece):
        if self._free(tx, ty):
            self.map.flat[(tx, ty)] = sprites.region(*piece)

    def wall_ring(self, cx, cy, rx, ry, h="wall", v="wall_v"):
        """Vòng tường tự chừa cổng ở những chỗ có đường đi qua."""
        for x in range(cx - rx, cx + rx + 1):
            self.put(h, x, cy - ry)
            self.put(h, x, cy + ry)
        for y in range(cy - ry + 1, cy + ry):
            self.put(v, cx - rx, y)
            self.put(v, cx + rx, y)

    def rice(self, x0, y0, w, h):
        """Ruộng mạ xanh chia thành thửa."""
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                if self._free(x, y):
                    self.map.set(x, y, PADDY)
                    self._reserve(x, y)

    # ----- phần khám phá thêm -----
    def _link(self, tile):
        """Mở lối mòn từ một điểm tới con đường gần nhất, để nơi nào đặt trên map cũng đi tới được."""
        m = self.map
        for avoid_water in (True, False):
            came = {tuple(tile): None}
            queue, head, goal = [tuple(tile)], 0, None
            while head < len(queue) and goal is None:
                cur = queue[head]
                head += 1
                if m.get(*cur) in (PATH, BRIDGE):
                    goal = cur
                    break
                x, y = cur
                for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if nxt in came or m.blocked_solid(*nxt) or not (BORDER <= nxt[0] < m.w - BORDER and BORDER <= nxt[1] < m.h - BORDER):
                        continue
                    if avoid_water and m.get(*nxt) == WATER:
                        continue
                    came[nxt] = cur
                    queue.append(nxt)
            if goal is not None:
                cur = came[goal]
                while cur is not None:
                    m.set(*cur, BRIDGE if m.get(*cur) == WATER else PATH)
                    self._reserve(*cur)
                    cur = came[cur]
                return
        raise AssertionError(f"Không mở được lối tới {tile}")

    def _hamlets(self, limit: int):
        """Xóm nhỏ ở những khoảng đất trống xa di tích: vài nếp nhà quanh sân đất, ruộng lúa có bù nhìn, giếng, bờ tre,
        và lối mòn nối ra đường cái. Cho map đỡ trống, có dáng làng quê mà không chắn đường tới nơi nào."""
        m, rng, world = self.map, self.rng, self.world
        keep = [(z.cx, z.cy) for z in world.zones.values()] + [tuple(world.spawn), tuple(world.mentor), tuple(world.portal)]
        annex = self.spec.get("annex")
        if annex:
            keep.append(tuple(annex["at"]))
        spots = []
        for y in range(BORDER + 6, m.h - BORDER - 7, 3):
            for x in range(BORDER + 9, m.w - BORDER - 10, 3):
                if any((x - cx) ** 2 + (y - cy) ** 2 < 16 ** 2 for cx, cy in keep):
                    continue
                if self._free(x - 9, y - 6, 19, 12):
                    spots.append((x, y))
        rng.shuffle(spots)
        made: list[tuple[int, int]] = []
        for x, y in spots:
            if len(made) >= limit:
                break
            if any(abs(x - px) < 24 and abs(y - py) < 16 for px, py in made):
                continue
            if not self._free(x - 9, y - 6, 19, 12):
                continue
            self.blob(x, y + 1, 4, 1, PATH)  # sân đất trước nhà
            self.put("house", x - 1, y - 4)
            self.put(rng.choice(("hut", "hut2")), x - 6, y - 3)
            self.put(rng.choice(("hut", "hut2")), x + 3, y - 3)
            self.put("well", x + 4, y + 1)
            self.put(rng.choice(("pot", "crate")), x - 5, y + 1)
            self.rice(x - 8, y + 3, 7, 2)
            self.rice(x + 1, y + 3, 7, 2)
            self.put("scarecrow", x - 5, y + 3, True)
            for bx, by in ((x - 9, y - 5), (x + 7, y - 5), (x - 9, y - 1)):
                self.put("bamboo", bx, by)
            self._link((x, y + 1))
            made.append((x, y))

    def _arena_area(self, cx, cy):
        """Sân võ đài: nền đất nện, hàng rào chừa cổng ở chỗ con đường đi vào, cờ và hình nhân tập võ."""
        for y in range(cy - ARENA_RY, cy + ARENA_RY + 1):
            for x in range(cx - ARENA_RX, cx + ARENA_RX + 1):
                self.map.set(x, y, PATH)
                self._reserve(x, y)
        self.wall_ring(cx, cy, ARENA_RX + 1, ARENA_RY + 1, "fence", "fence_v")
        self.flag(cx - ARENA_RX, cy - ARENA_RY)
        self.flag(cx + ARENA_RX, cy - ARENA_RY, "yellow")
        self.put("scarecrow", cx - 3, cy + 1, True)
        self.put("scarecrow", cx + 3, cy + 1, True)

    def _burned(self, cx, cy):
        """Làng vừa bị đốt: nhà ám khói, lửa còn cháy, khói bốc lên."""
        self.blob(cx, cy, 5, 2, PATH)
        for name, dx, dy in (("house", -8, -6), ("ruin", 1, -7), ("hut", -10, 1), ("house3", 5, -1)):
            if self.put(name, cx + dx, cy + dy):
                prop = self.last_prop
                prop.img = prop.img.copy()
                prop.img.fill(CHARRED, special_flags=pygame.BLEND_RGB_MULT)
        smoke = sprites.strip("fx/smoke.png", 6, 3)
        for dx, dy in ((-7, -4), (3, -4), (-9, 2), (7, 1)):
            self.flame(cx + dx, cy + dy)
            self.flame(cx + dx + 1, cy + dy)
            self.world.anims.append(Anim(smoke, (cx + dx) * TILE, (cy + dy - 2) * TILE, (cy + dy + 3) * TILE, 4))
        # Giữ một khoảng trống quanh làng để cây rừng không mọc đè lên nhà cháy
        for y in range(cy - 8, cy + 5):
            for x in range(cx - 11, cx + 11):
                self._reserve(x, y)

    def _extras(self):
        extra = self.spec.get("extra", {})
        if self.world.arena:
            self._arena_area(*self.world.arena)
        for name, x, y in extra.get("buildings", ()):
            self.put(name, x, y, True)
        for tile in extra.get("open", ()):
            self._reserve(*tile)
        for tile in extra.get("links", ()):
            self._reserve(*tile)
            self._link(tile)
        for cx, cy in extra.get("burned", ()):
            self._burned(cx, cy)
        for key in ("horse",):
            if self.spec.get(key):
                self._reserve(*self.spec[key])
                self._link(self.spec[key])

    def _mills(self):
        """Cối xay nước: tìm chỗ bờ sông gần vị trí đã định, phía trên là nước."""
        frames = sprites.strip("fx/watermill.png", 3)
        for tx, ty in self.spec.get("mills", ()):
            spots = sorted(((tx + dx, ty + dy) for dx in range(-6, 7) for dy in range(-6, 7)), key=lambda t: abs(t[0] - tx) + abs(t[1] - ty))
            for x, y in spots:
                if self._free(x, y, 3, 1) and self.map.get(x, y - 1) == WATER and self.map.get(x + 1, y - 1) == WATER:
                    self.world.anims.append(Anim(frames, x * TILE - 4, (y - 1) * TILE - TILE // 3, y * TILE, 5))
                    for i in range(x, x + 2):
                        self.map.set_solid(i, y)
                    for i in range(x, x + 3):
                        self._reserve(i, y)
                    break

    # ----- các kiểu khu vực -----
    def _theme_lang(self, cx, cy):
        self.put("gate", cx - 1, cy + 6)
        self.put("banyan", cx + 7, cy - 3)
        self.put("house", cx - 10, cy - 7)
        self.put("house2", cx - 3, cy - 9)
        self.put("house", cx + 3, cy - 8)
        self.put("hut", cx - 11, cy + 2)
        self.put("well", cx - 7, cy + 3)
        self.put("pot", cx + 7, cy + 2)
        self.put("crate", cx + 8, cy + 2)
        self.rice(cx + 7, cy + 4, 6, 3)
        self.put("scarecrow", cx + 9, cy + 5, True)

    # ----- vùng mở rộng (Req: map rộng hơn, nơi phục dựng tư liệu) -----
    def _theme_van_mieu(self, cx, cy):
        """Văn Miếu – Quốc Tử Giám: điện thờ, cổng, hai dãy bia đá, hồ nhỏ, cây cổ thụ. Bia tiến sĩ là của các đời sau."""
        self.put("temple", cx - 1, cy - 9)
        self.put("gate", cx - 1, cy + 5)
        for dx in (-8, -6, 6, 8):
            for dy in (-4, -1):
                self.put("stele", cx + dx, cy + dy)
        self.blob(cx, cy - 5, 2, 1, WATER)
        for name, dx, dy in (("old_tree", -12, -8), ("old_tree", 10, -8), ("tree", -12, 2), ("tree", 11, 2), ("banner_r", -3, -7), ("banner_r", 3, -7)):
            self.put(name, cx + dx, cy + dy)

    def _theme_con_son(self, cx, cy):
        """Côn Sơn: chùa trên sườn núi, rừng thông, suối nhỏ chảy qua, bia đá."""
        self.put("temple", cx - 1, cy - 9)
        self.put("rock_big", cx - 13, cy - 9)
        self.put("rock_tall", cx + 9, cy - 10)
        self.stroke([(cx + 12, cy - 8), (cx + 8, cy - 1), (cx + 11, cy + 8)], WATER, 2)
        for dx, dy in ((-9, -3), (-10, 3), (-6, 6), (4, 6), (-3, -6), (3, -6)):
            self.put("pine", cx + dx, cy + dy)
        self.put("stele", cx + 4, cy - 4)
        for dx, dy in ((-12, 0), (-13, 5), (6, -7)):
            self.put("bamboo", cx + dx, cy + dy)

    def _theme_atk(self, cx, cy):
        """An toàn khu Định Hoá: nhà sàn lẫn trong rừng tre, lá cờ, bàn họp."""
        self.put("nha_san", cx - 10, cy - 8)
        self.put("nha_san", cx + 5, cy - 9)
        self.put("hut", cx + 7, cy + 4)
        self.flag(cx, cy - 5)
        self.put("table", cx - 5, cy + 5)
        for dx, dy in ((-12, -3), (-11, 2), (11, -3), (-2, -9), (2, 7), (-8, 7)):
            self.put("bamboo", cx + dx, cy + dy)
        self.put("pines", cx - 15, cy - 11)
        self.put("old_tree", cx + 10, cy - 11)

    def _open_water(self, x, y, w=1, h=1) -> bool:
        """Toàn bộ vùng là nước và chưa có gì đậu: không phải cầu, không phải bờ."""
        for j in range(y, y + h):
            for i in range(x, x + w):
                if self.map.get(i, j) != WATER or self.reserved[j * self.map.w + i]:
                    return False
        return True

    def _boat(self, tx, ty) -> bool:
        """Thuyền chỉ đậu trên nước; vướng cầu hay bờ thì dời sang chỗ trống gần nhất, không có thì bỏ."""
        sheet, c, r, w, h, _ = CATALOG["boat"]
        for dx, dy in ((0, 0), (0, 2), (0, -2), (-2, 0), (2, 0), (0, 4), (0, -4), (-2, 3), (2, 3), (-2, -3), (2, -3), (0, 6), (0, -6)):
            x, y = tx + dx, ty + dy
            if self._open_water(x, y, w, h):
                self.world.add_prop(Prop(sprites.region(sheet, c, r, w, h), x * TILE, y * TILE, (y + h) * TILE))
                self.world.on_water.append(("boat", x, y, w, h))
                for j in range(y, y + h):
                    for i in range(x, x + w):
                        self._reserve(i, j)
                return True
        return False

    def _stakes(self, x, y0, n):
        """Cọc gỗ đầu bịt sắt nhô khỏi mặt nước, chỉ cắm ở ô nước có nước hai bên để không lấn lên bờ, lên cầu."""
        img = stake_sprite()
        for i in range(n):
            if self.rng.random() >= 0.65:
                continue
            tx, ty = x + self.rng.randint(0, 1), y0 + i
            if self._open_water(tx - 1, ty, 3, 1):
                self.world.add_prop(Prop(img, tx * TILE, ty * TILE, (ty + 1) * TILE))
                self.world.on_water.append(("stake", tx, ty, 1, 1))
                self._reserve(tx, ty)

    def _theme_thanh(self, cx, cy):
        """Thành Cổ Loa: luỹ đất đắp vòng quanh, đền ở giữa."""
        self.wall_ring(cx, cy, 12, 9, "luy_dat", "luy_dat_doc")
        self.put("temple", cx - 1, cy - 8)
        self.put("banner_r", cx - 4, cy - 7)
        self.put("banner_r", cx + 3, cy - 7)
        self.put("house3", cx - 11, cy - 7)
        self.put("house2", cx + 7, cy - 7)
        # giá binh khí thay tượng ôm quả cầu của gói asset (vật kỳ ảo, không có trong thành cổ)
        self.put("pot_stand", cx - 10, cy + 4)
        self.put("pot_stand", cx + 8, cy + 4)
        self.flag(cx - 7, cy + 5)
        self.flag(cx + 6, cy + 5)

    def _theme_den(self, cx, cy):
        self.put("temple", cx - 1, cy - 8)
        self.put("banner_y", cx - 3, cy - 7)
        self.put("banner_y", cx + 2, cy - 7)
        self.put("statue", cx - 7, cy - 6)
        self.put("statue", cx + 6, cy - 6)
        self.put("pot", cx - 2, cy - 5)
        self.put("pot", cx + 2, cy - 5)
        self.put("gate", cx - 1, cy + 5)
        self.put("banyan", cx - 12, cy - 3)
        self.put("banyan", cx + 9, cy - 3)
        self.wall_ring(cx, cy, 14, 10, "fence", "fence_v")

    def _theme_trai(self, cx, cy):
        for name, dx, dy in (("tent", -11, -7), ("tent2", -3, -9), ("tent3", 6, -8), ("tent", 8, 3), ("tent2", -12, 3)):
            self.put(name, cx + dx, cy + dy)
        self.put("fire", cx + 7, cy - 3)
        self.flame(cx + 7, cy - 2)
        self.put("pot_stand", cx - 8, cy - 2)
        self.put("barrels", cx + 3, cy + 5)
        self.put("table", cx - 6, cy + 5)
        self.flag(cx - 5, cy - 5)
        self.flag(cx + 5, cy - 5, "yellow")
        self.put("thap_canh", cx - 15, cy - 9)
        self.put("thap_canh", cx + 13, cy - 9)

    def _theme_lam(self, cx, cy):
        self.put("nha_san", cx - 9, cy - 8)
        self.put("hut2", cx + 3, cy - 8)
        for dx, dy in ((-12, -3), (-11, 1), (10, -4), (11, 0), (-6, 6), (6, 6), (-14, 4), (13, 4)):
            self.put("bamboo", cx + dx, cy + dy)
        self.put("rock_big", cx - 16, cy - 9)
        self.put("rock_tall", cx + 11, cy - 9)
        self.flag(cx - 6, cy - 3)
        self.flag(cx + 6, cy - 3)
        self.put("fire", cx - 1, cy + 5)
        self.flame(cx - 1, cy + 6)

    def _theme_dong(self, cx, cy):
        self.rice(cx - 15, cy - 8, 8, 6)
        self.rice(cx + 8, cy - 8, 8, 6)
        self.rice(cx - 15, cy + 3, 8, 6)
        self.rice(cx + 8, cy + 3, 8, 6)
        self.put("scarecrow", cx - 11, cy - 5, True)
        self.put("scarecrow", cx + 12, cy + 6, True)
        self.put("hut", cx - 2, cy - 9)
        self.flag(cx - 6, cy - 4)
        self.flag(cx + 6, cy + 4, "yellow")

    def _theme_ai(self, cx, cy):
        for dx, name in ((-16, "gray_big"), (-11, "gray_tall"), (-8, "gray_big"), (-3, "gray_tall"), (0, "gray_big"), (5, "gray_tall"), (8, "gray_big"), (13, "gray_tall")):
            self.put(name, cx + dx, cy - 9)
            self.put(name, cx + dx + 1, cy + 6)
        self.put("tent", cx - 12, cy - 5)
        self.put("tent2", cx + 9, cy - 5)
        self.put("thap_canh", cx - 3, cy - 6)
        self.flag(cx - 6, cy - 5)
        self.flag(cx + 6, cy + 5, "yellow")

    def _theme_cay_da(self, cx, cy):
        self.put("banyan", cx - 1, cy - 9)
        self.put("dinh", cx + 4, cy - 8)
        self.put("nha_san", cx - 10, cy - 8)
        self.flag(cx - 4, cy - 3)
        for dx, dy in ((-10, 0), (-11, 3), (10, 0), (11, 3), (-7, 5), (7, 5)):
            self.put("bamboo", cx + dx, cy + dy)

    def _theme_quang_truong(self, cx, cy):
        self.blob(cx, cy, 11, 7, PATH)
        self.put("nha_pho", cx - 1, cy - 11)
        self.put("nha_pho", cx - 10, cy - 11)
        self.put("nha_pho", cx + 7, cy - 11)
        for dx in (-8, -4, 4, 8):
            self.flag(cx + dx, cy - 7)
        for dx, dy in ((-14, -2), (-14, 3), (13, -2), (13, 3)):
            self.put("tree", cx + dx, cy + dy)

    def _theme_doi(self, cx, cy):
        for name, dx, dy in (("tent", -9, -8), ("tent3", 4, -9)):
            self.put(name, cx + dx, cy + dy)
        self.put("gray_big", cx - 16, cy - 2)
        self.put("gray_big", cx + 12, cy - 2)
        self.flag(cx, cy - 6)
        self.put("barrels", cx + 7, cy + 3)

    def _theme_deo(self, cx, cy):
        """Đèo núi trên đường số 4: vách đá hai bên con đường quanh co, thùng hàng đổ bên vệ đường; không có trại, không cờ."""
        for name, dx, dy in (("gray_tall", -14, -8), ("gray_big", -9, -10), ("rock_tall", 8, -10), ("gray_tall", 13, -7),
                             ("gray_big", -15, 4), ("rock_big", 11, 5), ("pines", -4, -12), ("pines", 4, 8)):
            self.put(name, cx + dx, cy + dy)
        self.put("crate", cx + 5, cy + 3)
        self.put("barrels", cx - 7, cy + 3)

    def _theme_don(self, cx, cy):
        """Cụm cứ điểm trên đồi: hàng rào bao quanh (tự chừa lối ở chỗ đường đi qua), đá, thùng, hòm đạn; không cờ, không trại."""
        self.wall_ring(cx, cy, 11, 8, "fence", "fence_v")
        for name, dx, dy in (("gray_big", -9, -6), ("gray_tall", 7, -7), ("barrels", -8, 3), ("crate", 6, 4), ("crate", 7, 4),
                             ("gray", 3, -6)):
            self.put(name, cx + dx, cy + dy)

    def _theme_dien_bien(self, cx, cy):
        self.blob(cx, cy, 16, 11, RICE)
        self.blob(cx, cy, 7, 5, PATH)
        for a in range(0, 360, 24):
            r = math.radians(a)
            name = self.rng.choice(("gray_big", "gray_tall", "pines", "pine"))
            self.put(name, cx + int(math.cos(r) * 22) - 2, cy + int(math.sin(r) * 15) - 2)
        for i in range(-12, 13, 2):  # đường hào siết vòng vây
            self.map.set(cx + i, cy - 8, PATH)
            self.map.set(cx + i + 1, cy - 8, PATH)
            self.map.set(cx + i, cy + 8, PATH)
            self.map.set(cx + i + 1, cy + 8, PATH)
        self.put("tent", cx - 12, cy - 6)
        self.put("tent2", cx + 8, cy - 6)
        self.put("nha_san", cx - 19, cy + 3)
        self.put("barrels", cx + 7, cy + 3)
        self.flag(cx, cy - 6)
        self.flame(cx - 11, cy + 6)
        self.flame(cx + 12, cy + 5)

    # ----- ghép cả bản đồ -----
    def build(self, relics: list[dict]) -> World:
        spec = self.spec
        world = self.world
        for lake in spec.get("lakes", []):
            self.blob(*lake, WATER)
        for river in spec.get("rivers", []):
            self.stroke(river["pts"], WATER, river.get("w", 4))
        ids = {r["id"] for r in relics}
        zones = spec["zones"]
        assert set(zones) == ids, f"Thiếu khu vực cho di tích: {ids ^ set(zones)}"
        pre_water = {"ben", "coc", "dao", "ho"}
        for z in zones.values():  # các khu có sông, hồ riêng phải vẽ trước khi vẽ đường
            if z["theme"] in pre_water:
                cx, cy = z["at"]
                if z["theme"] == "ben":
                    self.rect(cx + 8, cy - 14, 9, 28, WATER)
                elif z["theme"] == "coc":
                    self.rect(cx + 7, cy - 13, 11, 27, WATER)
                elif z["theme"] == "dao":
                    self.blob(cx, cy, 15, 12, WATER)
                    self.blob(cx, cy, 10, 8, 0)
                elif z["theme"] == "ho":
                    self.blob(cx, cy - 11, 11, 6, WATER)
        for pts in spec["roads"]:
            self.stroke(pts, PATH, 2)
        for rid, z in zones.items():
            cx, cy = z["at"]
            self.blob(cx, cy, 5, 3, PATH)
            world.zones[rid] = Zone(rid, cx, cy, z["theme"], [(cx + dx, cy + dy) for dx, dy in SPOTS])
            self._reserve_spots(cx, cy)
        for tile in (world.spawn, world.mentor, world.portal):
            self.blob(tile[0], tile[1], 3, 2, PATH)
        for npc in world.npcs:
            self._reserve(*npc["at"])
        annex = spec.get("annex")
        if annex:
            ax, ay = annex["at"]
            self.blob(ax, ay, 5, 3, PATH)
            self._reserve_spots(ax, ay)
            self._reserve(*annex["keeper"])
        self._extras()
        themes = {
            "lang": self._theme_lang, "thanh": self._theme_thanh, "den": self._theme_den, "trai": self._theme_trai,
            "lam": self._theme_lam, "dong": self._theme_dong, "ai": self._theme_ai, "cay_da": self._theme_cay_da,
            "quang_truong": self._theme_quang_truong, "doi": self._theme_doi, "deo": self._theme_deo, "don": self._theme_don, "dien_bien": self._theme_dien_bien,
            "van_mieu": self._theme_van_mieu, "con_son": self._theme_con_son, "atk": self._theme_atk,
        }
        for z in zones.values():
            cx, cy = z["at"]
            if z["theme"] in themes:
                themes[z["theme"]](cx, cy)
        if annex and annex["theme"] in themes:
            themes[annex["theme"]](*annex["at"])
        self._finish_water_themes(zones)
        self._mills()
        self._portal_area()
        self._hamlets(spec.get("hamlets", 4))
        self._scatter(spec.get("trees", "song"), spec.get("forest", 0.55))
        self._border()
        self._settle_spots()
        self._collect_ripples()
        return world

    def _settle_spots(self):
        """Sông, nhà, cây có thể đè lên điểm nhiệm vụ: dời về ô đi được gần tâm khu vực nhất, không trùng nhau."""
        m = self.map
        for zone in self.world.zones.values():
            used = {(zone.cx, zone.cy)}
            queue, seen, head = [(zone.cx, zone.cy)], {(zone.cx, zone.cy)}, 0
            open_tiles = []
            while head < len(queue) and len(open_tiles) < 60:
                x, y = queue[head]
                head += 1
                open_tiles.append((x, y))
                for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if nxt not in seen and not m.blocked(*nxt):
                        seen.add(nxt)
                        queue.append(nxt)
            walkable = set(open_tiles)
            fixed = []
            for spot in zone.spots:
                if spot not in walkable or spot in used:
                    # lấy ô xa tâm một chút để các vật thể không dồn sát người giữ ký ức
                    spot = next(t for t in reversed(open_tiles) if t not in used)
                used.add(spot)
                fixed.append(spot)
            zone.spots = fixed

    def _reserve_spots(self, cx, cy):
        for dx, dy in SPOTS:
            self._reserve(cx + dx, cy + dy)

    def _finish_water_themes(self, zones):
        """Khu có nước: chỉ đặt vật thể, sông hồ đã vẽ từ trước nên không đè lên đường."""
        for z in zones.values():
            cx, cy = z["at"]
            theme = z["theme"]
            if theme == "ben":
                rx = cx + 8
                self.rect(rx - 2, cy, 6, 2, BRIDGE)  # cầu tàu
                for i in range(rx - 2, rx + 4):
                    self._reserve(i, cy)
                    self._reserve(i, cy + 1)
                for name, dx, dy in (("hut2", -9, -8), ("hut", -2, -9), ("barrels", -8, 3), ("crate", -6, 4)):
                    self.put(name, cx + dx, cy + dy)
                self.flag(cx + 6, cy - 3)
                self._boat(rx + 2, cy - 8)
                self._boat(rx + 3, cy + 6)
                if z.get("stakes"):  # cọc gỗ là dấu riêng của trận Bạch Đằng: chỉ cắm ở bến nào khai báo rõ
                    self._stakes(rx + 5, cy - 12, 24)
            elif theme == "coc":
                rx = cx + 7
                for k in (1, 4, 7):
                    self._stakes(rx + k, cy - 12, 25)
                self._boat(rx + 3, cy - 7)
                for name, dx, dy in (("hut", -10, -7), ("banyan", -3, -10), ("barrels", -8, 3)):
                    self.put(name, cx + dx, cy + dy)
                self.flag(cx + 5, cy - 4)
                self.flag(cx + 5, cy + 4)
            elif theme == "dao":
                for name, dx, dy in (("hut2", -5, -7), ("gray_big", 3, -8), ("gray", -9, 1), ("barrels", 7, 2)):
                    self.put(name, cx + dx, cy + dy)
                self._boat(cx + 10, cy - 10)
                self._boat(cx - 14, cy + 7)
            elif theme == "ho":
                # gò giữa hồ chỉ có cây cỏ: Tháp Rùa xây cuối thế kỷ XIX, chưa có ở thời Lê Lợi nên không vẽ công trình nào
                self.blob(cx, cy - 12, 2, 1, 0)
                for dx in (-1, 0, 1):
                    self.flat(cx + dx, cy - 12, BUSHES[dx % len(BUSHES)])
                for name, dx, dy in (("temple", 9, -3), ("banyan", -12, -3), ("banyan", -8, 5), ("banner_r", 8, -5)):
                    self.put(name, cx + dx, cy + dy)
                self.put("cong_thanh", cx - 3, cy - 24)
                for dx in list(range(-14, -3)) + list(range(2, 13)):
                    self.put("tuong_thanh", cx + dx, cy - 22)
                self.flag(cx + 7, cy + 3)

    def _portal_area(self):
        px, py = self.world.portal
        for dx in (-3, 3):
            self.put("banner_g", px + dx, py - 3)
        for dx, dy in ((-3, 1), (3, 1)):
            self.flag(px + dx, py + dy, "yellow")
        back = self.spec.get("back")
        if back:
            self.blob(back[0], back[1], 3, 2, PATH)
        mx, my = self.world.mentor
        self.put("banyan", mx - 2, my - 5)
        self.put("sign", mx + 2, my + 1)

    def _scatter(self, tree_set, density):
        """Rừng theo từng đám: vài tâm rừng có mật độ cao, xen kẽ cây lẻ, bụi cỏ và hoa."""
        rng, m = self.rng, self.map
        names = TREE_SETS[tree_set]
        groves = [(rng.randrange(m.w), rng.randrange(m.h), rng.randint(6, 13)) for _ in range(m.w * m.h // 260)]
        for y in range(BORDER, m.h - BORDER, 2):
            for x in range(BORDER, m.w - BORDER, 2):
                near = any((x - g[0]) ** 2 + (y - g[1]) ** 2 < g[2] ** 2 for g in groves)
                chance = density if near else 0.08
                jx, jy = x + rng.randint(0, 1), y + rng.randint(0, 1)
                if rng.random() < chance:
                    self.put(rng.choice(names), jx, jy)
                elif rng.random() < 0.16:
                    self.flat(jx, jy, rng.choice(BUSHES))
                elif rng.random() < 0.06:
                    self.flat(jx, jy, rng.choice(FLOWERS))

    def _border(self):
        m, names = self.map, ("pine", "tree", "pine", "bamboo", "pine")
        for x in range(0, m.w, 2):
            for y in (-1, m.h - 2):
                self.put(self.rng.choice(names[:3]), x, y, True)
        for y in range(1, m.h - 2, 2):
            for x in (-1, m.w - 2):
                self.put(self.rng.choice(names[:3]), x, y, True)
        for x in range(m.w):
            for y in (0, 1, m.h - 1):
                m.set_solid(x, y)
        for y in range(m.h):
            for x in (0, m.w - 1):
                m.set_solid(x, y)

    def _collect_ripples(self):
        m = self.map
        tiles = [(x, y) for y in range(m.h) for x in range(m.w) if m.get(x, y) == WATER]
        self.rng.shuffle(tiles)
        self.world.ripples = tiles[: max(12, len(tiles) // 12)]


_stake: pygame.Surface | None = None


def stake_sprite() -> pygame.Surface:
    """Cọc gỗ đầu bịt sắt vẽ ở 16 px rồi phóng to, cùng độ nét với tile."""
    global _stake
    if _stake is None:
        low = pygame.Surface((16, 16), pygame.SRCALPHA)
        for x, h in ((2, 10), (7, 13), (12, 9)):
            pygame.draw.polygon(low, (58, 38, 26), [(x - 1, 15), (x + 2, 15), (x + 2, 16 - h + 3), (x, 16 - h + 3)])
            pygame.draw.polygon(low, (150, 156, 164), [(x, 16 - h + 3), (x + 2, 16 - h + 3), (x + 2, 16 - h)])
            pygame.draw.line(low, (28, 18, 14), (x - 1, 15), (x, 16 - h + 3))
        _stake = sprites.scaled(low)
    return _stake


def door_of(building: dict) -> tuple[int, int]:
    """Ô đứng ngay trước cửa của một công trình."""
    _, _, _, w, h, _ = CATALOG[building["name"]]
    x, y = building["at"]
    return (x + w // 2, y + h)


def build_world(level_id: str, spec: dict, relics: list[dict]) -> World:
    return Builder(level_id, spec).build(relics)
