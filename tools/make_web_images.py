"""Chụp ảnh trực tiếp từ game cho trang giới thiệu, nên ảnh luôn đúng với thứ người chơi thấy.

    .venv/Scripts/python tools/make_web_images.py

Ảnh map không có giao diện được thu về đúng độ phân giải gốc của pixel art (16 px một ô) cho file rất nhẹ, trang web phóng
to lại bằng `image-rendering: pixelated`. Ảnh có chữ giữ nguyên 1280x720.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "game"), str(ROOT / "game" / "tests")]

import pygame  # noqa: E402
from core import platform_io  # noqa: E402
from core.sprites import SCALE, TILE  # noqa: E402
from scenes import world as world_mod  # noqa: E402
from scenes.case import CaseScene  # noqa: E402
from scenes.fight import FightScene  # noqa: E402
from scenes.question import QuestionScene  # noqa: E402
from scenes.story import StoryScene  # noqa: E402
from scenes.world import WorldScene  # noqa: E402
from test_playthrough import Bot, _tide_until_strike  # noqa: E402

OUT = ROOT / "web" / "img"
# Tên ảnh -> (màn, cột, hàng, số ô ngang, số ô dọc)
MAPS = {
    "hero": ("man1", 14, 21, 40, 20),
    "era1": ("man1", 62, 40, 24, 12),
    "era2": ("man2", 44, 44, 24, 12),
    "era3": ("man3", 12, 4, 24, 12),
}
SHOT_W, SHOT_H = world_mod.W, world_mod.H


def map_image(bot, name: str, level: str, tx: int, ty: int, cols: int, rows: int) -> None:
    """Vẽ một vùng map đúng như trong game nhưng bỏ giao diện và nhân vật người chơi."""
    surface = pygame.Surface((cols * TILE, rows * TILE))
    world_mod.W, world_mod.H = surface.get_size()
    try:
        ws = WorldScene(bot, level, "spawn")
        bot.scenes.reset(ws)
        ws.t = 1.3
        ws.x, ws.y = -5000.0, -5000.0
        cx, cy = tx * TILE, ty * TILE
        ws.map.draw(surface, cx, cy)
        ws._draw_ripples(surface, cx, cy)
        ws._draw_entities(surface, cx, cy)
    finally:
        world_mod.W, world_mod.H = SHOT_W, SHOT_H
    small = pygame.transform.scale(surface, (cols * TILE // SCALE, rows * TILE // SCALE))
    pygame.image.save(small, OUT / f"{name}.png")


def shot(bot, name: str, ticks: int = 20) -> None:
    bot.tick(ticks)
    bot.scenes.draw(bot.screen)
    pygame.image.save(bot.screen, OUT / f"{name}.png")


def question_shot(bot) -> None:
    st = bot.state
    q = next(q for q in st.levels["man1"]["questions"] if q["kind"] == "single" and q["difficulty"] == 2)
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    ws.banner = None
    sc = QuestionScene(bot, q)
    bot.scenes.push(sc)
    bot.tick(2)
    # Chụp lúc đã trả lời để thấy cả lời giải và nguồn
    right = next(o for _rect, o in sc.opt_rects if o["id"] == q["correct_answer"])
    sc._choose(right)
    shot(bot, "question")


def memory_shot(bot) -> None:
    st = bot.state
    dialogue = next(d for d in st.index["dialogues"].values() if any(n.get("cine") == "crash" for n in d["nodes"]))
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    sc = StoryScene(bot, dialogue)
    bot.scenes.push(sc)
    while sc.node.get("cine") != "crash":
        sc._advance()
    shot(bot, "memory", 75)


def battle_shot(bot) -> None:
    _tide_until_strike(bot, {0: [0], 1: [0, 1], 2: [0, 1], 3: [0]})
    shot(bot, "battle", 70)


def arena_shot(bot) -> None:
    st = bot.state
    sc = FightScene(bot, [st.extras["arena"][2]], "Võ sinh áo đỏ", "vo_dai")
    bot.scenes.reset(sc)
    bot.tick(90)
    sc.player.x, sc.player.y = sc.foes[0].x - 170, sc.foes[0].y
    sc.cast(sc.player, "ten_lua")
    bot.tick(7)
    bot.scenes.draw(bot.screen)
    pygame.image.save(bot.screen, OUT / "arena.png")


def case_shot(bot) -> None:
    sc = CaseScene(bot, bot.state.extras["cases"][0])
    bot.scenes.reset(sc)
    shot(bot, "case")


# Nhân vật giới thiệu ở trang chủ: tên ảnh -> nhân vật trong game (hoặc vật thể trên map)
NPCS = {
    "cu_do": "Master", "giu_ky_uc": "OldWoman", "bia_da": "stele", "tho_ren": "Villager", "ke_chuyen": "OldMan",
    "cau_ca": "OldMan3", "di_duong": "Villager3", "vo_su": "FighterRed", "bang_vang": "honor",
}


def npc_images() -> None:
    """Ảnh từng nhân vật ở đúng cỡ gốc 16 px một ô; trang web phóng to lại bằng image-rendering: pixelated."""
    from core import sprites
    from core.worldgen import CATALOG
    from scenes.honor import board_sprite

    for name, who in NPCS.items():
        if who == "stele":
            img = sprites.region(*CATALOG["stele"][:3])
        elif who == "honor":
            img = board_sprite()
            img = pygame.transform.scale(img, (img.get_width() // 2, img.get_height() // 2))
            pygame.image.save(img, OUT / f"npc_{name}.png")
            continue
        else:
            img = sprites.cast(who).walk["down"][0]
        small = pygame.transform.scale(img, (img.get_width() // SCALE, img.get_height() // SCALE))
        pygame.image.save(small, OUT / f"npc_{name}.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if "--npc" in sys.argv:  # chỉ xuất ảnh nhân vật
        pygame.init()
        pygame.display.set_mode((1, 1))
        npc_images()
        print("Đã xuất ảnh nhân vật:", sorted(p.name for p in OUT.glob("npc_*.png")))
        return
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    pygame.init()
    bot = Bot()
    st = bot.state
    st.reset()
    for name, (level, tx, ty, cols, rows) in MAPS.items():
        map_image(bot, name, level, tx, ty, cols, rows)
    st.reset()
    st.first_try.update({f"q{i}" for i in range(14)})
    st.solved.update({f"q{i}" for i in range(12)})
    st.upgrade_stat("suc")
    st.upgrade_skill("phong_lao")
    st.upgrade_skill("ten_lua")
    question_shot(bot)
    memory_shot(bot)
    battle_shot(bot)
    arena_shot(bot)
    case_shot(bot)
    npc_images()
    sizes = {p.name: p.stat().st_size // 1024 for p in sorted(OUT.glob("*.png"))}
    print("Đã chụp (KB):", sizes)


if __name__ == "__main__":
    main()
