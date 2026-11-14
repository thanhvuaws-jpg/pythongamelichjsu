"""Vẽ lính và tướng nhà Tống, Nguyên, Minh trên nền nhân vật Villager của gói Ninja Adventure (CC0).

Gói asset chỉ có hiệp sĩ châu Âu nên trước đây quân phương Bắc trông lạc thời. Công cụ này giữ nguyên dáng và khung
chuyển động của Villager, chỉ vẽ đè mũ giáp và đổi màu áo theo những nét trang phục phổ biến, được ghi chép rộng rãi:

- Nguyên Mông: mũ sắt tròn viền lông, có hai tai che bằng lông, áo choàng dài cài vạt chéo (áo deel), đai da.
- Minh: mũ sắt hình bát có chóp nhọn và tua đỏ, áo bông dày màu đỏ của lính.
- Tống (dùng cả cho quân Nam Hán thế kỷ X): mũ sắt sẫm có che gáy, giáp vảy, đai đỏ.
- Đại Việt: khăn chít đầu, áo ngắn, thắt lưng vải, xà cạp quấn ống chân; tướng mặc giáp, đội mũ có tua.
- Nghĩa quân Lam Sơn: khăn đen, áo nâu, thắt lưng vải.
- Bộ đội thời chống Pháp: mũ lá có vành gài lá ngụy trang, quân phục màu xanh, thắt lưng.

Chạy: .venv/Scripts/python tools/make_soldiers.py   (ghi vào game/assets/pixel/char/<Tên>/)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "game"))
from core.outfit import BASE, DIRS, U, dress  # noqa: E402  phần vẽ trang phục dùng chung với ngoại hình người chơi

CHAR = ROOT / "game" / "assets" / "pixel" / "char"

DAI_VIET = {"head": "wrap", "rim": (0, 0, 0), "flaps": None, "top": None, "diagonal": False}
STYLES = {
    "LinhDaiViet": {**DAI_VIET, "helm": (84, 58, 42), "helm_light": (118, 84, 60), "rim_dark": (56, 38, 28),
                    "coat": (62, 72, 104), "coat_light": (92, 104, 138), "coat_dark": (44, 50, 76),
                    "trim": (176, 48, 40), "belt": (176, 48, 40), "pants": (70, 58, 50), "leggings": (214, 196, 156)},
    "LinhDaiViet2": {**DAI_VIET, "helm": (46, 40, 38), "helm_light": (78, 70, 66), "rim_dark": (26, 22, 22),
                     "coat": (128, 88, 56), "coat_light": (160, 116, 78), "coat_dark": (94, 62, 40),
                     "trim": (176, 48, 40), "belt": (176, 48, 40), "pants": (66, 56, 50), "leggings": (214, 196, 156)},
    "NghiaQuan": {**DAI_VIET, "helm": (40, 36, 34), "helm_light": (70, 64, 60), "rim_dark": (22, 20, 20),
                  "coat": (112, 76, 48), "coat_light": (142, 100, 66), "coat_dark": (82, 54, 34),
                  "trim": (66, 48, 34), "belt": (66, 48, 34), "pants": (82, 64, 50)},
    "TuongDaiViet": {
        "helm": (150, 44, 36), "helm_light": (190, 74, 60), "rim": (226, 180, 70), "rim_dark": (170, 126, 40),
        "flaps": "guard", "rim_style": "band", "top": "plume", "plume": (214, 44, 40), "knob": (226, 180, 70),
        "coat": (110, 64, 44), "coat_light": (226, 180, 70), "coat_dark": (78, 44, 30),
        "trim": (226, 180, 70), "belt": (226, 180, 70), "pants": (120, 40, 36), "diagonal": False, "scales": True,
    },
    "BoDoi": {
        "helm": (170, 158, 104), "helm_light": (204, 192, 136), "rim": (150, 138, 88), "rim_dark": (60, 104, 52),
        "flaps": None, "rim_style": "brim", "top": None, "leaves": True,
        "coat": (96, 112, 70), "coat_light": (126, 142, 92), "coat_dark": (70, 82, 50),
        "trim": (96, 112, 70), "belt": (66, 50, 36), "pants": (84, 98, 62), "diagonal": False,
    },
    "LinhNguyen": {
        "helm": (96, 90, 84), "helm_light": (134, 124, 112), "rim": (176, 132, 84), "rim_dark": (128, 92, 58),
        "flaps": "fur", "rim_style": "fur", "top": "knob", "coat": (62, 84, 120), "coat_light": (96, 122, 160), "coat_dark": (42, 58, 88),
        "trim": (196, 170, 120), "belt": (138, 96, 56), "pants": (64, 46, 36), "diagonal": True,
    },
    "TuongNguyen": {
        "helm": (110, 98, 84), "helm_light": (150, 136, 112), "rim": (186, 140, 86), "rim_dark": (132, 94, 58),
        "flaps": "fur", "rim_style": "fur", "top": "plume", "plume": (200, 44, 40), "knob": (232, 186, 70),
        "coat": (128, 46, 42), "coat_light": (164, 74, 62), "coat_dark": (90, 30, 28),
        "trim": (232, 186, 70), "belt": (232, 186, 70), "pants": (64, 46, 36), "diagonal": True,
    },
    "LinhMinh": {
        "helm": (128, 132, 140), "helm_light": (176, 180, 188), "rim": (88, 90, 98), "rim_dark": (66, 68, 76),
        "flaps": None, "rim_style": "brim", "ribs": True, "top": "tassel", "plume": (214, 44, 40), "knob": (88, 90, 98),
        "coat": (196, 48, 40), "coat_light": (228, 92, 74), "coat_dark": (140, 30, 28),
        "trim": (240, 200, 170), "belt": (44, 34, 30), "pants": (54, 48, 50), "diagonal": False,
    },
    "TuongMinh": {
        "helm": (150, 150, 156), "helm_light": (196, 196, 200), "rim": (226, 180, 70), "rim_dark": (170, 126, 40),
        "flaps": None, "rim_style": "brim", "ribs": True, "top": "tassel", "plume": (214, 44, 40), "knob": (226, 180, 70),
        "coat": (150, 30, 32), "coat_light": (190, 60, 56), "coat_dark": (104, 20, 22),
        "trim": (226, 180, 70), "belt": (226, 180, 70), "pants": (54, 48, 50), "diagonal": False,
    },
    "LinhTong": {
        "helm": (78, 84, 96), "helm_light": (118, 126, 140), "rim": (60, 64, 74), "rim_dark": (44, 48, 56),
        "flaps": "guard", "top": "finial", "knob": (60, 64, 74),
        "coat": (90, 98, 112), "coat_light": (140, 148, 162), "coat_dark": (62, 68, 80),
        "trim": (186, 48, 40), "belt": (186, 48, 40), "pants": (98, 62, 50), "diagonal": False, "scales": True,
    },
    "TuongTong": {
        "helm": (92, 96, 106), "helm_light": (140, 146, 158), "rim": (226, 180, 70), "rim_dark": (170, 126, 40),
        "flaps": "guard", "top": "tassel", "plume": (200, 44, 40), "knob": (226, 180, 70),
        "coat": (104, 110, 122), "coat_light": (160, 166, 178), "coat_dark": (72, 76, 88),
        "trim": (226, 180, 70), "belt": (226, 180, 70), "pants": (120, 40, 36), "diagonal": False, "scales": True,
    },
}


def make(name: str, st: dict) -> None:
    src = CHAR / BASE
    out = CHAR / name
    out.mkdir(parents=True, exist_ok=True)
    walk = pygame.image.load(str(src / "walk.png"))
    sheet = pygame.Surface(walk.get_size(), pygame.SRCALPHA)
    for c, d in enumerate(DIRS):
        for r in range(4):
            frame = walk.subsurface((c * U, r * U, U, U)).copy()
            sheet.blit(dress(frame, d, st), (c * U, r * U))
    pygame.image.save(sheet, str(out / "walk.png"))
    attack = pygame.image.load(str(src / "attack.png"))
    sheet = pygame.Surface(attack.get_size(), pygame.SRCALPHA)
    for c, d in enumerate(DIRS):
        frame = attack.subsurface((c * U, 0, U, U)).copy()
        sheet.blit(dress(frame, d, st), (c * U, 0))
    pygame.image.save(sheet, str(out / "attack.png"))
    dead = pygame.image.load(str(src / "dead.png"))
    pygame.image.save(dress(dead.copy(), "down", st, lying=True), str(out / "dead.png"))
    front = pygame.image.load(str(out / "walk.png")).subsurface((0, 0, U, U))
    face = pygame.Surface((38, 38), pygame.SRCALPHA)
    big = pygame.transform.scale(front, (U * 2, U * 2))
    face.blit(big, big.get_rect(midbottom=(19, 38)))
    pygame.image.save(face, str(out / "face.png"))


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    for name, st in STYLES.items():
        make(name, st)
        print("đã vẽ", name)


if __name__ == "__main__":
    main()
