"""Xuất bản đồ đi được của mọi map cho người chơi máy chạy trên máy chủ.

    .venv/Scripts/python tools/export_botmaps.py

Máy chủ không dựng được map (map dựng bằng pygame ở phía game) nên không tự tìm đường được. Công cụ này dựng từng map, từng
vùng luyện đúng như game dựng, rồi ghi ra `backend/app/world/botmaps.json`:

- ô đi được (đi bộ tới được từ chỗ xuất phát), nén thành dãy bit;
- chỗ làm nhiệm vụ (người giữ ký ức, bia đá, già làng), lò rèn, chỗ câu cá;
- các con quái thường (không phải kẻ canh, kẻ mạnh nhất vùng, trùm, thuyền) với tên riêng giống hệt ở phía game, để bot
  hạ con nào thì con đó cũng ngã trên máy người chơi;
- danh sách đồ theo cấp, cảnh giới, để bot mặc đồ hợp cấp.

Đổi bản đồ, đổi quái thì chạy lại; test `test_botmaps_are_up_to_date` báo khi file đã cũ.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "game"), str(ROOT / "game" / "tests")]

import pygame  # noqa: E402
from core import platform_io, rpg  # noqa: E402
from core.sprites import TILE  # noqa: E402
from scenes.field import FieldScene  # noqa: E402
from scenes.mobs import _reachable, mob_key  # noqa: E402
from scenes.world import WorldScene  # noqa: E402
from test_playthrough import Bot  # noqa: E402

OUT = ROOT / "backend" / "app" / "world" / "botmaps.json"


def pack(w: int, h: int, cells: set[tuple[int, int]]) -> str:
    """Ô đi được thành dãy bit (hàng nối hàng), mã base64 cho gọn."""
    bits = bytearray((w * h + 7) // 8)
    for x, y in cells:
        if 0 <= x < w and 0 <= y < h:
            i = y * w + x
            bits[i // 8] |= 1 << (i % 8)
    return base64.b64encode(bytes(bits)).decode("ascii")


def _tile(a) -> list[int]:
    return [int(a.x // TILE), int(a.y // TILE)]


def describe(scene, name: str) -> dict:
    world = scene.world
    reach = _reachable(world)
    points: dict[str, list] = {"quest": [], "mentor": [], "shop": [], "fish": []}
    kinds = {"keeper": "quest", "quiz": "quest", "mentor": "mentor", "smith": "shop", "fisher": "fish"}
    for a in scene.actors:
        if a.kind in kinds:
            points[kinds[a.kind]].append(_tile(a))
    mobs = [
        {"key": mob_key(m), "name": m.data["name"], "level": m.data["level"], "tx": int(m.home[0] // TILE), "ty": int(m.home[1] // TILE)}
        for m in scene.mobs.mobs
        if m.kind == "mob" and not m.data.get("water")
    ]
    return {
        "name": name,
        "w": scene.map.w,
        "h": scene.map.h,
        "walk": pack(scene.map.w, scene.map.h, reach),
        "spawn": list(world.spawn),
        "points": {k: sorted(v) for k, v in points.items()},
        "mobs": sorted(mobs, key=lambda m: m["key"]),
    }


def build() -> dict:
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    pygame.init()
    bot = Bot()
    st = bot.state
    maps = {}
    for lid in st.order:
        st.reset()
        ws = WorldScene(bot, lid, "spawn")
        maps[lid] = describe(ws, ws.level["title"])
    for fid, f in st.fields.items():
        st.reset()
        maps[fid] = describe(FieldScene(bot, fid), f"{f['name']} (vùng luyện)")
    items = {}
    for iid, it in rpg.ITEMS.items():
        if it["slot"] in ("vu_khi", "giap", "mu", "giay", "gang"):
            items.setdefault(it["slot"], []).append([it["level"], iid])
    return {
        "tile": TILE,
        "realms": [[r["cap"], r["name"]] for r in rpg.REALMS],
        "items": {k: sorted(v) for k, v in sorted(items.items())},
        "maps": maps,
    }


def main() -> None:
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    sizes = {k: len(v["mobs"]) for k, v in data["maps"].items()}
    print(f"Đã ghi {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB), số quái mỗi map: {sizes}")


if __name__ == "__main__":
    main()
