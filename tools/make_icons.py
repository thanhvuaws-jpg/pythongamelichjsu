"""Vẽ icon 24x24 cho kỹ năng mới và đồ trang bị (vũ khí, giáp, mũ, giày, găng, thuốc).

Cùng nét pixel với icon của gói Ninja Adventure. Ghi vào game/assets/pixel/ui/ (sk_<id>.png, item_<id>.png).
Chạy: .venv/Scripts/python tools/make_icons.py
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

UI = Path(__file__).resolve().parent.parent / "game" / "assets" / "pixel" / "ui"
OUT = (24, 18, 16)
WOOD, WOOD_D, WOOD_L = (150, 98, 56), (104, 64, 36), (190, 136, 84)
STEEL, STEEL_D, STEEL_L = (170, 176, 186), (110, 116, 128), (226, 232, 238)
BAMBOO, BAMBOO_D = (176, 170, 86), (124, 118, 56)
RED, GOLD = (196, 44, 38), (232, 186, 70)
CLOTH, CLOTH_D = (112, 80, 52), (82, 56, 36)
LEATHER, LEATHER_D = (150, 96, 58), (108, 66, 38)
BRONZE = (196, 140, 70)


def _line(s, c, a, b, w=1):
    pygame.draw.line(s, c, a, b, w)


def blade(s, length, width, col=STEEL, hilt=WOOD, guard=GOLD, curve=0):
    """Lưỡi dao, kiếm chéo từ góc dưới trái lên góc trên phải."""
    x0, y0 = 4, 19
    x1, y1 = x0 + length, y0 - length
    _line(s, OUT, (x0 - 1, y0 + 1), (x1, y1 - curve), width + 2)
    _line(s, col, (x0, y0), (x1 - 1, y1 + 1 - curve), width)
    _line(s, STEEL_L, (x0 + 4, y0 - 5), (x1 - 2, y1 + 2 - curve))
    pygame.draw.rect(s, OUT, (x0 - 1, y0 - 3, 6, 6))
    pygame.draw.rect(s, guard, (x0, y0 - 2, 4, 4))
    _line(s, OUT, (x0 - 3, y0 + 3), (x0, y0), 4)
    _line(s, hilt, (x0 - 3, y0 + 3), (x0, y0), 2)


def icons():
    def gay_tre(s):
        _line(s, OUT, (3, 21), (21, 3), 5)
        _line(s, BAMBOO, (3, 21), (21, 3), 3)
        for k in (7, 12, 17):
            _line(s, BAMBOO_D, (k - 1, 24 - k - 1), (k + 1, 24 - k + 1), 2)

    def dao_sat(s):
        blade(s, 13, 3, curve=2)

    def kiem_thep(s):
        blade(s, 15, 2)

    def bao_kiem(s):
        blade(s, 15, 3, STEEL_L, RED, GOLD)
        s.set_at((6, 15), RED)

    def ma_tau(s):
        blade(s, 12, 4, curve=3)

    def dai_dao(s):
        _line(s, OUT, (2, 22), (15, 9), 4)
        _line(s, WOOD, (2, 22), (15, 9), 2)
        pygame.draw.polygon(s, OUT, [(13, 7), (21, 1), (22, 6), (17, 12)])
        pygame.draw.polygon(s, STEEL, [(14, 7), (20, 2), (21, 6), (17, 11)])
        s.set_at((14, 10), RED)

    def giao_dai(s):
        _line(s, OUT, (2, 22), (18, 6), 4)
        _line(s, WOOD, (2, 22), (18, 6), 2)
        pygame.draw.polygon(s, OUT, [(16, 5), (22, 1), (20, 8)])
        pygame.draw.polygon(s, STEEL, [(17, 5), (21, 2), (19, 7)])
        _line(s, RED, (15, 9), (14, 12), 2)

    def no_go(s):
        _line(s, OUT, (4, 12), (20, 12), 4)  # thân nỏ
        _line(s, WOOD, (4, 12), (20, 12), 2)
        pygame.draw.arc(s, OUT, (12, 3, 10, 18), -1.57, 1.57, 3)  # cánh nỏ
        pygame.draw.arc(s, WOOD_D, (12, 3, 10, 18), -1.57, 1.57, 1)
        _line(s, (230, 220, 190), (17, 4), (17, 20))  # dây
        pygame.draw.rect(s, BRONZE, (8, 13, 3, 4))  # lẫy đồng

    def cung_sung(s):
        pygame.draw.arc(s, OUT, (5, 2, 14, 20), 1.57, 4.71, 3)
        pygame.draw.arc(s, WOOD_L, (5, 2, 14, 20), 1.57, 4.71, 1)
        _line(s, (230, 220, 190), (12, 2), (12, 21))
        _line(s, OUT, (8, 12), (22, 12), 2)
        pygame.draw.polygon(s, STEEL, [(20, 10), (23, 12), (20, 14)])

    def ao(colors, plates=False):
        main, dark = colors

        def draw(s):
            pygame.draw.polygon(s, OUT, [(4, 7), (9, 3), (15, 3), (20, 7), (18, 11), (17, 21), (7, 21), (6, 11)])
            pygame.draw.polygon(s, main, [(5, 7), (9, 4), (15, 4), (19, 7), (17, 10), (16, 20), (8, 20), (7, 10)])
            _line(s, dark, (12, 5), (12, 19))
            if plates:
                for y in range(8, 20, 3):
                    for x in range(8, 17, 3):
                        s.set_at((x, y), STEEL_L if main == STEEL else GOLD)
            _line(s, RED, (8, 14), (16, 14), 2)
        return draw

    def khan_chit(s):
        pygame.draw.ellipse(s, OUT, (4, 7, 16, 11))
        pygame.draw.ellipse(s, (60, 50, 44), (5, 8, 14, 9))
        for y in (10, 13):
            _line(s, (40, 32, 28), (6, y), (18, y))
        pygame.draw.polygon(s, (60, 50, 44), [(18, 12), (22, 16), (19, 17)])

    def non_la(s):
        pygame.draw.polygon(s, OUT, [(1, 17), (12, 4), (23, 17)])
        pygame.draw.polygon(s, (226, 208, 150), [(3, 16), (12, 5), (21, 16)])
        for k in range(6, 16, 3):
            _line(s, (186, 166, 110), (12 - (k - 4), k + 2), (12 + (k - 4), k + 2))
        _line(s, OUT, (1, 17), (23, 17), 2)

    def mu_da(s):
        pygame.draw.ellipse(s, OUT, (4, 5, 16, 14))
        pygame.draw.ellipse(s, LEATHER, (5, 6, 14, 12))
        _line(s, LEATHER_D, (4, 15), (20, 15), 3)

    def mu_sat(s):
        pygame.draw.ellipse(s, OUT, (4, 4, 16, 15))
        pygame.draw.ellipse(s, STEEL, (5, 5, 14, 13))
        _line(s, STEEL_D, (3, 15), (21, 15), 3)
        _line(s, OUT, (12, 1), (12, 5), 2)
        pygame.draw.rect(s, RED, (11, 0, 3, 2))

    def giay(main, dark, tall=False):
        def draw(s):
            top = 6 if tall else 11
            for x0 in (3, 13):
                pygame.draw.rect(s, OUT, (x0 - 1, top - 1, 8, 20 - top))
                pygame.draw.rect(s, main, (x0, top, 6, 18 - top))
                pygame.draw.rect(s, OUT, (x0 - 1, 17, 10, 4))
                pygame.draw.rect(s, dark, (x0, 18, 8, 2))
        return draw

    def dep_rom(s):
        for x0 in (3, 13):
            pygame.draw.ellipse(s, OUT, (x0 - 1, 6, 9, 16))
            pygame.draw.ellipse(s, (214, 186, 110), (x0, 7, 7, 14))
            _line(s, (150, 120, 70), (x0 + 1, 11), (x0 + 6, 11), 2)

    def gang(main, dark, studs=None):
        def draw(s):
            pygame.draw.polygon(s, OUT, [(6, 22), (6, 9), (8, 4), (17, 4), (19, 9), (19, 22)])
            pygame.draw.polygon(s, main, [(7, 21), (7, 9), (9, 5), (16, 5), (18, 9), (18, 21)])
            for x in (9, 12, 15):
                _line(s, dark, (x, 5), (x, 10))
            _line(s, dark, (7, 17), (18, 17), 2)
            if studs:
                for x in (9, 12, 15):
                    s.set_at((x, 13), studs)
        return draw

    # ----- câu cá -----
    def can_cau(s):
        _line(s, OUT, (2, 22), (20, 2), 4)
        _line(s, BAMBOO, (3, 21), (19, 3), 2)
        for x, y in ((7, 16), (12, 10), (16, 6)):  # đốt tre
            s.set_at((x, y), BAMBOO_D)
        _line(s, (232, 228, 214), (20, 3), (20, 15))  # dây câu
        pygame.draw.arc(s, OUT, (17, 14, 5, 6), 3.4, 6.3, 1)  # lưỡi câu
        s.set_at((21, 16), STEEL_D)

    def fish(body, dark, belly):
        def draw(s):
            pygame.draw.polygon(s, OUT, [(15, 12), (23, 5), (23, 19)])  # đuôi
            pygame.draw.polygon(s, dark, [(17, 12), (22, 7), (22, 17)])
            pygame.draw.ellipse(s, OUT, (1, 6, 18, 12))
            pygame.draw.ellipse(s, body, (2, 7, 16, 10))
            pygame.draw.ellipse(s, belly, (4, 12, 11, 4))
            s.set_at((5, 10), OUT)
            for x in (9, 12):
                s.set_at((x, 9), dark)
        return draw

    def ca_nuong(s):
        _line(s, OUT, (0, 22), (23, 2), 3)  # que tre xiên qua
        _line(s, BAMBOO, (1, 21), (22, 3), 1)
        fish((178, 104, 46), (116, 62, 26), (222, 160, 86))(s)
        for x in (8, 11, 14):  # vệt cháy than
            _line(s, (84, 44, 20), (x, 8), (x - 1, 15))

    def thuoc_nam(s):
        pygame.draw.ellipse(s, OUT, (5, 7, 14, 15))
        pygame.draw.ellipse(s, (150, 104, 60), (6, 8, 12, 13))
        pygame.draw.rect(s, OUT, (9, 3, 6, 6))
        pygame.draw.rect(s, (200, 170, 120), (10, 4, 4, 4))
        for x, y in ((10, 13), (13, 15), (11, 17)):
            s.set_at((x, y), (90, 150, 70))

    # ----- kỹ năng mới -----
    def sk_no_lien_chau(s):
        no_go(s)
        for k in range(3):
            _line(s, STEEL_L, (2, 3 + k * 4), (8, 3 + k * 4), 1)

    def sk_hoa_cong(s):
        for x, h, c in ((6, 14, (232, 120, 40)), (12, 19, (250, 196, 80)), (18, 13, (214, 70, 30))):
            pygame.draw.polygon(s, OUT, [(x - 4, 22), (x, 22 - h), (x + 4, 22)])
            pygame.draw.polygon(s, c, [(x - 3, 21), (x, 23 - h), (x + 3, 21)])

    def sk_hao_khi(s):
        pygame.draw.circle(s, OUT, (12, 12), 10)
        pygame.draw.circle(s, RED, (12, 12), 9)
        for a in range(0, 360, 45):
            import math
            r = math.radians(a)
            _line(s, GOLD, (12 + math.cos(r) * 3, 12 + math.sin(r) * 3), (12 + math.cos(r) * 8, 12 + math.sin(r) * 8), 2)

    def sk_phi_ma(s):
        pygame.draw.ellipse(s, OUT, (3, 9, 15, 9))
        pygame.draw.ellipse(s, (128, 70, 40), (4, 10, 13, 7))
        pygame.draw.polygon(s, OUT, [(15, 10), (19, 3), (23, 5), (19, 12)])
        pygame.draw.polygon(s, (128, 70, 40), [(16, 10), (19, 4), (22, 6), (19, 11)])
        for x in (5, 8, 13, 16):
            _line(s, OUT, (x, 16), (x, 22), 2)
        pygame.draw.rect(s, RED, (7, 8, 6, 3))

    return {
        "item_gay_tre": gay_tre, "item_dao_sat": dao_sat, "item_giao_dai": giao_dai, "item_no_go": no_go, "item_kiem_thep": kiem_thep,
        "item_cung_ten": cung_sung, "item_ma_tau": ma_tau, "item_dai_dao": dai_dao, "item_bao_kiem": bao_kiem,
        "item_ao_vai": ao((CLOTH, CLOTH_D)), "item_giap_da": ao((LEATHER, LEATHER_D)), "item_giap_bong": ao(((196, 60, 50), (140, 36, 30))),
        "item_giap_vay": ao((STEEL, STEEL_D), True), "item_giap_dong": ao((BRONZE, (150, 100, 46)), True),
        "item_khan_chit": khan_chit, "item_non_la": non_la, "item_mu_da": mu_da, "item_mu_sat": mu_sat,
        "item_dep_rom": dep_rom, "item_giay_vai": giay((70, 70, 90), (40, 40, 52)), "item_ung_da": giay(LEATHER, LEATHER_D, True),
        "item_bao_tay_vai": gang((200, 190, 160), (150, 140, 112)), "item_gang_da": gang(LEATHER, LEATHER_D),
        "item_gang_sat": gang(STEEL, STEEL_D, GOLD), "item_thuoc_nam": thuoc_nam,
        "item_can_cau": can_cau, "item_ca_tuoi": fish((150, 170, 180), (92, 110, 122), (220, 226, 226)), "item_ca_nuong": ca_nuong,
        "sk_no_lien_chau": sk_no_lien_chau, "sk_hoa_cong": sk_hoa_cong, "sk_hao_khi": sk_hao_khi, "sk_phi_ma": sk_phi_ma,
    }


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    for name, draw in icons().items():
        s = pygame.Surface((24, 24), pygame.SRCALPHA)
        if name.startswith("sk_"):
            # nền cam bo góc như icon kỹ năng sẵn có của gói Ninja Adventure
            pygame.draw.rect(s, (233, 133, 82), (0, 0, 24, 24), border_radius=2)
            for x, y in ((3, 3), (20, 4), (4, 20)):
                s.set_at((x, y), (253, 189, 115))
            inner = pygame.Surface((24, 24), pygame.SRCALPHA)
            draw(inner)
            s.blit(pygame.transform.scale(inner, (20, 20)), (2, 2))
        else:
            draw(s)
        pygame.image.save(s, str(UI / f"{name}.png"))
    print("icons:", len(icons()))


if __name__ == "__main__":
    main()
