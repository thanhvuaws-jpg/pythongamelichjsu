"""Lọc đúng các file cần dùng từ gói Ninja Adventure (CC0) vào game/assets/pixel/.

Gói gốc 110 MB, game chỉ cần vài MB nên web tải nhanh. Công cụ này chỉ chạy một lần khi đổi danh sách asset:

    python tools/pack_assets.py "<thư mục giải nén>/Ninja Adventure - Asset Pack"

Cần thư viện soundfile (pip install soundfile) để đổi WAV sang OGG, vì pygbag từ chối đóng gói WAV khi build web.

Nguồn: https://pixel-boy.itch.io/ninja-adventure-asset-pack (Pixel-Boy và AAA, CC0 1.0).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "game" / "assets" / "pixel"
TILES = "Backgrounds/Tilesets/"
# Nhân vật: người giữ ký ức, dân làng, lính hai phe
CAST = (
    "SamuraiBlue", "Master", "OldMan3", "OldWoman", "Monk", "Monk2", "OldMan", "Samurai", "SamuraiRed", "Knight",
    "GladiatorBlue", "Villager", "Villager3", "Villager4", "Woman", "Princess", "Boy", "CamouflageGreen", "Inspector", "Noble",
    "Hunter", "FighterRed", "FighterWhite", "NinjaGray",
)
FILES = {
    "tiles/floor.png": TILES + "TilesetFloor.png",
    "tiles/nature.png": TILES + "TilesetNature.png",
    "tiles/house.png": TILES + "TilesetHouse.png",
    "tiles/water.png": TILES + "TilesetWater.png",
    "tiles/element.png": TILES + "TilesetElement.png",
    "tiles/camp.png": TILES + "tileset_camp.png",
    "tiles/boat.png": "Backgrounds/Vehicles/Boat.png",
    "animal/fish_red.png": "Actor/Animal/Fish/SpriteSheetRed.png",
    "animal/fish_white.png": "Actor/Animal/Fish/SpriteSheetWhite.png",
    "animal/fish_yellow.png": "Actor/Animal/Fish/SpriteSheetYellow.png",
    "tiles/fishnet.png": "Backgrounds/Vehicles/FishNetFull.png",
    "fx/slash.png": "FX/Slash/SpriteSheetArc.png",
    "fx/flame.png": "FX/Elemental/Flam/SpriteSheet.png",
    "fx/explosion.png": "FX/Elemental/Explosion/SpriteSheet.png",
    "fx/smoke.png": "FX/Smoke/Smoke/SpriteSheet.png",
    "fx/portal.png": "FX/Magic/Circle/SpriteSheetSpark.png",
    "fx/spirit.png": "FX/Magic/Spirit/SpriteSheetBlue.png",
    "fx/ripple.png": "Backgrounds/Animated/Water Ripples/SpriteSheet16x16.png",
    "fx/cut.png": "FX/Attack/Cut/SpriteSheet.png",
    "fx/cutx.png": "FX/Attack/CutX/SpriteSheet.png",
    "fx/curved.png": "FX/Attack/SlashCurved/SpriteSheet.png",
    "fx/wood.png": "FX/Particle/Wood.png",
    "fx/arrow.png": "FX/Projectile/Arrow.png",
    "fx/fireball.png": "FX/Projectile/Fireball.png",
    "fx/lance.png": "Items/Weapons/Lance/Sprite.png",
    "ui/skill_fire.png": "Ui/Skill Icon/Spell/Fireball.png",
    "ui/skill_spear.png": "Ui/Skill Icon/Items & Weapon/Kunai.png",
    "ui/skill_cut.png": "Ui/Skill Icon/Spell/Cut.png",
    "sfx/slash.wav": "Audio/Sounds/Whoosh & Slash/Slash.wav",
    "sfx/sword.wav": "Audio/Sounds/Whoosh & Slash/Sword2.wav",
    "sfx/launch.wav": "Audio/Sounds/Whoosh & Slash/Launch.wav",
    "sfx/fire.wav": "Audio/Sounds/Elemental/Fireball.wav",
    "sfx/explosion.wav": "Audio/Sounds/Elemental/Explosion.wav",
    "sfx/impact.wav": "Audio/Sounds/Hit & Impact/Impact3.wav",
    "sfx/splash.wav": "Audio/Sounds/Elemental/Water1.wav",
    "fx/circle_slash.png": "FX/Attack/CircularSlash/SpriteSheet.png",
    "fx/shield.png": "FX/Magic/Shield/SpriteSheetYellow.png",
    "fx/boost.png": "FX/Magic/Boost/SpriteSheet.png",
    "fx/leaf.png": "FX/Particle/Leaf.png",
    "fx/leaf_pink.png": "FX/Particle/LeafPink.png",
    "fx/clouds.png": "FX/Particle/Clouds.png",
    "fx/watermill.png": "Backgrounds/Animated/WaterMill/Watermill_A_34x36.png",
    "fx/flower.png": "Backgrounds/Animated/Flower/SpriteSheet16x16.png",
    "ui/caltrop.png": "Items/Projectile/Caltrop.png",
    "ui/log.png": "Items/Resource/Branch.png",
    "ui/yam.png": "Items/Food/SeedLarge.png",
    "ui/rice_bag.png": "Items/Object/Bag.png",
    "ui/letter.png": "Items/Scroll/ScrollEmpty.png",
    "ui/book.png": "Items/Object/Book.png",
    "ui/gem.png": "Items/Resource/GemYellow.png",
    "ui/arrow_item.png": "Items/Weapons/Bow/Arrow.png",
    "ui/sword.png": "Items/Weapons/Sword/Sprite.png",
    "ui/coin.png": "Items/Treasure/GoldCoin.png",
    "ui/cup.png": "Items/Treasure/GoldCup.png",
    "ui/stamp.png": "Items/Other/Stamp.png",
    "tiles/int_floor.png": "Backgrounds/Tilesets/Interior/TilesetInteriorFloor.png",
    "tiles/int_wall.png": "Backgrounds/Tilesets/Interior/TilesetWallSimple.png",
    "tiles/aband.png": "Backgrounds/Tilesets/TilesetVillageAbandoned.png",
    "animal/chicken.png": "Actor/Animal/Chicken/SpriteSheetBrown.png",
    "animal/dog.png": "Actor/Animal/Dog/SpriteSheet.png",
    "animal/frog.png": "Actor/Animal/Frog/SpriteSheet.png",
    "animal/cow.png": "Actor/Animal/Cow/SpriteSheetWhiteSide.png",
    "animal/horse.png": "Actor/Animal/Horse/SpriteSheetBrownSide.png",
    "animal/horse_front.png": "Actor/Animal/Horse/SpriteSheetBrown.png",
    "sfx/voice1.wav": "Audio/Sounds/Voice/Voice1.wav",
    "sfx/voice2.wav": "Audio/Sounds/Voice/Voice2.wav",
    "sfx/voice3.wav": "Audio/Sounds/Voice/Voice3.wav",
    "sfx/voice4.wav": "Audio/Sounds/Voice/Voice4.wav",
    "sfx/step.wav": "Audio/Sounds/Elemental/Grass.wav",
    "sfx/hit.wav": "Audio/Sounds/Hit & Impact/Hit1.wav",
    "sfx/heal.wav": "Audio/Sounds/Magic & Skill/Heal.wav",
    "sfx/magic.wav": "Audio/Sounds/Magic & Skill/Magic1.wav",
    "sfx/coin.wav": "Audio/Sounds/Bonus/Coin.wav",
    "sfx/powerup.wav": "Audio/Sounds/Bonus/PowerUp1.wav",
    "sfx/move.wav": "Audio/Sounds/Menu/Move1.wav",
    "sfx/cancel.wav": "Audio/Sounds/Menu/Cancel.wav",
    "sfx/success.wav": "Audio/Jingles/Success1.wav",
    "sfx/levelup.wav": "Audio/Jingles/LevelUp1.wav",
    "sfx/rain.wav": "Audio/Sounds/Ambient/Rain.wav",
    "sfx/river.wav": "Audio/Sounds/Ambient/River.wav",
    "sfx/wind.wav": "Audio/Sounds/Ambient/Wind.wav",
    "ui/sk_phong_lao.png": "Ui/Skill Icon/Items & Weapon/Kunai.png",
    "ui/sk_ten_lua.png": "Ui/Skill Icon/Spell/Fireball.png",
    "ui/sk_dot_kich.png": "Ui/Skill Icon/Spell/Cut.png",
    "ui/sk_xoay_kiem.png": "Ui/Skill Icon/Spell/Counter.png",
    "ui/sk_the_thu.png": "Ui/Skill Icon/Items & Weapon/Guard.png",
    "ui/sk_hoi_khi.png": "Ui/Skill Icon/Spell/Heal.png",
    "ui/sk_chong_ngam.png": "Ui/Skill Icon/Spell/RockSpike.png",
    "ui/sk_suc.png": "Ui/Skill Icon/Spell/AttackUpgrade.png",
    "ui/sk_the.png": "Ui/Skill Icon/Items & Weapon/Armor.png",
    "ui/sk_nhanh.png": "Ui/Skill Icon/Items & Weapon/Boot.png",
    "ui/sk_tri.png": "Ui/Skill Icon/Items & Weapon/Scroll.png",
    "fx/flag_red.png": "Backgrounds/Animated/Flag/FlagRed16x16.png",
    "fx/flag_yellow.png": "Backgrounds/Animated/Flag/FlagYellow16x16.png",
    "ui/scroll.png": "Items/Scroll/Scroll.png",
    "ui/faceset_box.png": "Ui/Dialog/FacesetBox.png",
    "ui/emote_talk.png": "Ui/Emote/emote20.png",
    "ui/emote_alert.png": "Ui/Emote/emote22.png",
    "ui/emote_question.png": "Ui/Emote/emote25.png",
    "ui/emote_lock.png": "Ui/Emote/emote29.png",
    "music/title.ogg": "Audio/Musics/6 - Story (Short).ogg",
    "music/road.ogg": "Audio/Musics/23 - Road.ogg",
    "music/temple.ogg": "Audio/Musics/12 - Temple.ogg",
    "music/fight.ogg": "Audio/Musics/17 - Fight.ogg",
    "music/sad.ogg": "Audio/Musics/7 - Sad Theme.ogg",
    "LICENSE-CC0.txt": "LICENSE.txt",
    # vũ khí cầm tay, ngựa đen cho kỵ binh, hiệu ứng thêm (lấy từ bản đầy đủ của gói, cùng giấy phép CC0)
    "weapon/stick.png": "Items/Weapons/Stick/SpriteInHand.png",
    "weapon/katana.png": "Items/Weapons/Katana/SpriteInHand.png",
    "weapon/lance.png": "Items/Weapons/Lance/SpriteInHand.png",
    "weapon/lance2.png": "Items/Weapons/Lance2/SpriteInHand.png",
    "weapon/sword.png": "Items/Weapons/Sword/SpriteInHand.png",
    "weapon/sword2.png": "Items/Weapons/Sword2/SpriteInHand.png",
    "weapon/bigsword.png": "Items/Weapons/BigSword/SpriteInHand.png",
    "weapon/bow.png": "Items/Weapons/Bow/Sprite.png",
    "fx/canonball.png": "FX/Projectile/CanonBall.png",
    "fx/slash_double.png": "FX/Attack/SlashDoubleCurved/SpriteSheet.png",
    "fx/cut_double.png": "FX/Attack/CutDouble/SpriteSheet.png",
    "fx/spark.png": "FX/Particle/Spark.png",
    "fx/rock.png": "FX/Particle/Rock.png",
    "animal/horse_black.png": "Actor/Animal/Horse/SpriteSheetBlackSide.png",
    "animal/horse_black_front.png": "Actor/Animal/Horse/SpriteSheetBlack.png",
}
AMBIENT_LOOPS = ("rain", "river", "wind")
AMBIENT_SECONDS = 6
AMBIENT_FADE = 0.4
CREDIT = """Đồ hoạ, nhạc: Ninja Adventure Asset Pack của Pixel-Boy và AAA, giấy phép CC0 1.0 (không bắt buộc ghi công).
https://pixel-boy.itch.io/ninja-adventure-asset-pack
Đây là bản rút gọn do tools/pack_assets.py lọc ra, đặt lại tên cho gọn.

LinhTong, TuongTong, LinhNguyen, TuongNguyen, LinhMinh, TuongMinh: vẽ đè mũ giáp và trang phục lên nhân vật Villager
của Ninja Adventure (CC0) bằng tools/make_soldiers.py, để quân Tống, Nguyên, Minh không còn trông như hiệp sĩ châu Âu.

ui/item_*.png và ui/sk_no_lien_chau, sk_hoa_cong, sk_hao_khi, sk_phi_ma: tự vẽ bằng tools/make_icons.py.
"""


def _split_sheet(sheet: Path, out: Path) -> None:
    """Vài nhân vật chỉ có sprite sheet 4 cột x 2 hàng: tự tách thành file đi, đánh, ngã."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    import pygame

    pygame.display.init()
    pygame.display.set_mode((1, 1))
    img = pygame.image.load(str(sheet)).convert_alpha()
    out.mkdir(parents=True, exist_ok=True)
    walk = pygame.Surface((64, 64), pygame.SRCALPHA)
    for row, src_row in enumerate((0, 1, 0, 1)):
        walk.blit(img, (0, row * 16), (0, src_row * 16, 64, 16))
    pygame.image.save(walk, str(out / "walk.png"))
    pygame.image.save(img.subsurface((0, 0, 64, 16)), str(out / "attack.png"))
    pygame.image.save(img.subsurface((0, 0, 16, 16)), str(out / "dead.png"))


def _to_ogg(path: Path) -> None:
    import numpy as np
    import soundfile

    data, rate = soundfile.read(str(path))
    # Tiếng nền gốc rất dài: cắt vài giây rồi cho lặp để game tải nhanh. Cắt thẳng thì chỗ nối kêu "tách" mỗi vòng lặp,
    # nên trộn đoạn cuối vào đoạn đầu cho hai đầu khớp nhau.
    if path.stem in AMBIENT_LOOPS:
        fade = min(int(rate * AMBIENT_FADE), len(data) // 3)
        keep = min(rate * AMBIENT_SECONDS, len(data) - fade)
        ramp = np.linspace(0.0, 1.0, fade)
        if data.ndim > 1:
            ramp = ramp[:, None]
        loop = data[:keep].copy()
        loop[:fade] = data[:fade] * ramp + data[keep : keep + fade] * (1.0 - ramp)
        data = loop
    soundfile.write(str(path.with_suffix(".ogg")), data, rate, format="OGG", subtype="VORBIS")
    path.unlink()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows mặc định không in được tiếng Việt
    src = Path(sys.argv[1])
    if OUT.exists():
        shutil.rmtree(OUT)
    files = dict(FILES)
    for name in CAST:
        base = f"Actor/Character/{name}/"
        if not (src / (base + "SeparateAnim/Walk.png")).exists():
            _split_sheet(src / (base + "SpriteSheet.png"), OUT / "char" / name)
            files[f"char/{name}/face.png"] = base + "Faceset.png"
            continue
        files[f"char/{name}/walk.png"] = base + "SeparateAnim/Walk.png"
        files[f"char/{name}/attack.png"] = base + "SeparateAnim/Attack.png"
        files[f"char/{name}/dead.png"] = base + "SeparateAnim/Dead.png"
        if (src / (base + "Faceset.png")).exists():
            files[f"char/{name}/face.png"] = base + "Faceset.png"
    total = 0
    for out, rel in files.items():
        target = OUT / out
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src / rel, target)
        total += target.stat().st_size
    for wav in OUT.rglob("*.wav"):
        _to_ogg(wav)
    (OUT / "README.txt").write_text(CREDIT, encoding="utf-8")
    print(f"Đã chép {len(files)} file, {total / 1024 / 1024:.1f} MB vào {OUT}")
    # Lính Tống, Nguyên, Minh được vẽ từ nhân vật trong gói; thư mục vừa bị xoá nên vẽ lại
    import runpy

    runpy.run_path(str(Path(__file__).with_name("make_soldiers.py")), run_name="__main__")
    runpy.run_path(str(Path(__file__).with_name("make_icons.py")), run_name="__main__")


if __name__ == "__main__":
    main()
