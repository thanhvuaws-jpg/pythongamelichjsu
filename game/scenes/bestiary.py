"""Sổ bóng giặc: mỗi loại quái một trang, hạ được lần đầu thì mở ra dòng sử về đội quân đó kèm nguồn.

Biến việc đánh quái thành việc sưu tầm kiến thức: chưa hạ thì chỉ thấy bóng đen và gợi ý nơi gặp.
"""

from __future__ import annotations

import pygame
from core import fonts, mobart, rpg, sprites, theme, ui
from core.scene import Scene

from scenes.fight import STATIC_CASTS

W, H = theme.WIDTH, theme.HEIGHT
COLS, CARD_W, CARD_H = 6, 198, 196
TOP = 104
# Xếp theo thời: Nam Hán (thế kỷ X), Tống (thế kỷ XI), Mông Cổ (1258), Nguyên (1285 – 1288), Minh (1407 – 1427), 1945 – 1954
ERAS = (
    ("Thế kỷ X", ("linh_nam_han", "thuy_binh_nam_han")),
    ("Thế kỷ XI", ("linh_tong", "cung_thu_tong", "may_ban_da_tong")),
    ("Năm 1258", ("linh_mong_co", "cung_thu_mong_co", "ky_binh_mong_co")),
    ("1285 – 1288", ("linh_nguyen", "cung_thu_nguyen", "thuyen_chien_nguyen", "thuy_binh_nguyen", "thuyen_luong_nguyen")),
    ("1407 – 1427", ("linh_minh", "cung_thu_minh", "tran_thu_minh", "linh_giu_thanh_minh", "ky_binh_minh", "linh_khien_minh",
                     "thuyen_luong_minh")),
    ("1945 – 1954", ("don_bot", "lo_cot", "u_sung", "xe_tang", "tau_chien", "ca_no", "xe_van_tai", "xe_boc_thep", "u_phao")),
)
ORDER = [(era, mid) for era, mids in ERAS for mid in mids]
PER_PAGE = COLS * 3


def portrait(char: str) -> pygame.Surface:
    if char in STATIC_CASTS:
        return STATIC_CASTS[char](3).walk["down"][0]
    if mobart.has(char):
        return mobart.cast(char, 3).walk["down"][0]
    return sprites.cast(char, 4).walk["down"][0]


def _fit(text: str, font, width: int) -> str:
    """Cắt bớt cho vừa khung, thêm dấu ba chấm."""
    if font.size(text)[0] <= width:
        return text
    while text and font.size(text + "…")[0] > width:
        text = text[:-1]
    return text + "…"


def silhouette(img: pygame.Surface) -> pygame.Surface:
    return pygame.mask.from_surface(img).to_surface(setcolor=(104, 84, 68, 255), unsetcolor=(0, 0, 0, 0))


class BestiaryScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.group = ui.ButtonGroup()
        self.page = 0
        self.pages = (len(ORDER) + PER_PAGE - 1) // PER_PAGE
        self.group.add(ui.Button((W - 150, 14, 136, 40), "Đóng", lambda: self.app.scenes.pop(), "ghost", size=15))
        self.group.add(ui.Button((W - 470, 14, 150, 40), "◀ Trang trước", lambda: self.turn(-1), "ghost", size=14))
        self.group.add(ui.Button((W - 310, 14, 150, 40), "Trang sau ▶", lambda: self.turn(1), "ghost", size=14))
        self.t = 0.0
        self._imgs = {mid: portrait(rpg.MOBS[mid]["char"]) for _era, mid in ORDER}

    def turn(self, step: int):
        self.page = (self.page + step) % self.pages
        self.app.audio.play("click")

    def handle(self, event):
        self.group.handle(event)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_g):
                self.app.scenes.pop()
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.turn(1 if event.key == pygame.K_RIGHT else -1)

    def update(self, dt):
        self.t += dt

    def where(self, mid: str) -> str:
        """Gặp loại quái này ở đâu: di tích hoặc vùng luyện."""
        st = self.state
        for rid, mobs in rpg.ZONE_MOBS.items():
            if mid in mobs:
                return "quanh " + st.index["relics"][rid]["title"]
        for f in st.fields.values():
            if any(mid in camp for camp in f["camps"].values()):
                return "ở vùng luyện " + f["name"]
        return "trên đường"

    def draw(self, screen):
        st = self.state
        screen.fill(theme.LACQUER)
        fonts.text(screen, "SỔ BÓNG GIẶC", fonts.font("serif", 28), theme.GOLD_LIGHT, (30, 16))
        got = sum(mid in st.bestiary for _e, mid in ORDER)
        ui.tag(screen, f"Đã mở {got}/{len(ORDER)} trang", (270, 22), theme.LACQUER_RED, theme.GOLD_LIGHT, 17)
        fonts.text(screen, f"{self.page + 1}/{self.pages}", fonts.font("bold", 15), theme.PAPER_3, (W - 480, 34), "midright")
        fonts.text(screen, "Hạ mỗi loại quái một lần để mở một dòng sử về đội quân đó. Bóng giặc là phần trò chơi; dòng sử là chuyện thật, có nguồn.",
                   fonts.font("ui", 14), theme.PAPER_3, (30, 66))
        f_name, f_small, f_body = fonts.font("bold", 14), fonts.font("semi", 11), fonts.font("ui", 11)
        start = self.page * PER_PAGE
        for i, (era, mid) in enumerate(ORDER[start:start + PER_PAGE]):
            m = rpg.MOBS[mid]
            x = 30 + (i % COLS) * (CARD_W + 6)
            y = TOP + (i // COLS) * (CARD_H + 6)
            rect = pygame.Rect(x, y, CARD_W, CARD_H)
            known = mid in st.bestiary
            if known:
                ui.paper_panel(screen, rect, shadow=False)
            else:
                ui.lacquer_panel(screen, rect, 200)
            img = self._imgs[mid] if known else silhouette(self._imgs[mid])
            bob = 2 * pygame.math.Vector2(0, 1).rotate(self.t * 90 + i * 40).y if known else 0
            pic = img.get_rect(midbottom=(x + 48, y + 78 + bob))
            pic.clamp_ip(rect.inflate(-12, -12))
            screen.blit(img, pic)
            ink = theme.INK if known else theme.PAPER_3
            fonts.text(screen, era, f_small, theme.LACQUER_RED if known else theme.GOLD_DARK, (x + 92, y + 10))
            name_lines = fonts.wrap(m["name"], f_name, CARD_W - 98)
            for j, line in enumerate(name_lines[:2]):
                fonts.text(screen, line, f_name, ink, (x + 92, y + 26 + j * 16))
            fonts.text(screen, f"cấp {m['level']}", f_small, ink, (x + 92, y + 60))
            if known:
                fact, cite = rpg.MOB_FACTS[mid]
                fonts.paragraph(screen, fact, f_body, theme.INK_SOFT, x + 14, y + 86, CARD_W - 28, gap=0)
                src = st.sources["citations"].get(cite, {}).get("source", "")
                title = st.sources["sources"].get(src, {}).get("title", "")
                fonts.text(screen, _fit(f"Nguồn: {title}", f_small, CARD_W - 28), f_small, theme.JADE, (x + 14, rect.bottom - 22))
            else:
                fonts.paragraph(screen, f"Chưa mở. Gặp {self.where(mid)}.", f_body, theme.PAPER_3, x + 14, y + 92, CARD_W - 28, gap=0)
        self.group.draw(screen)
