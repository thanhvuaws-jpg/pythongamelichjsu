"""Lò rèn và túi đồ: mua vũ khí, áo, mũ, giày, găng, cần câu, thuốc nam bằng tiền quan rồi mặc vào để mạnh lên.

Mở lò rèn bằng cách nói chuyện với thợ rèn gần chỗ xuất phát; túi đồ (phím B) thì mở ở đâu cũng được nhưng chỉ để thay đồ.
"""

from __future__ import annotations

import pygame
from core import fonts, outfit, rpg, sprites, theme, ui, weapons
from core.scene import Scene

W, H = theme.WIDTH, theme.HEIGHT
LEFT = pygame.Rect(30, 112, 400, 590)
RIGHT = pygame.Rect(444, 112, 806, 590)
TABS = tuple(rpg.SLOT_NAMES)
ROW_H = 58
LIST_Y = RIGHT.y + 62


class ShopScene(Scene):
    def __init__(self, app, shop: bool = True, smith: str = "Thợ rèn"):
        super().__init__(app)
        self.shop, self.smith = shop, smith
        self.tab = TABS[0]
        self.group = ui.ButtonGroup()
        self.note = ""
        self.t = 0.0
        self._build()

    def _items(self) -> list[str]:
        st = self.state
        items = [i for i, it in rpg.ITEMS.items() if it["slot"] == self.tab]
        if self.shop:
            return [i for i in items if not rpg.ITEMS[i].get("craft")]  # cá tươi, cá nướng: tự làm ra, không bán
        return [i for i in items if i in st.inventory or self._count(i) > 0]

    def _count(self, iid: str) -> int:
        st = self.state
        return {"thuoc_nam": st.potions, "ca_tuoi": st.fish_count(), "ca_nuong": st.grilled}.get(iid, 0)

    def _build(self):
        st = self.state
        self.group.clear()
        self.group.add(ui.Button((W - 150, 14, 136, 40), "Đóng", lambda: self.app.scenes.pop(), "ghost", size=15))
        if self.shop:
            self.group.add(ui.Button((W - 300, 14, 140, 40), "Túi đồ (B)", self._to_bag, "ghost", size=14))
        else:
            self.group.add(ui.Button((W - 330, 14, 170, 40), "Sổ bóng giặc (G)", self._to_bestiary, "ghost", size=14))
        x = RIGHT.x + 14
        w = (RIGHT.w - 28 - 8 * (len(TABS) - 1)) // len(TABS)
        for slot in TABS:
            b = ui.Button((x, RIGHT.y + 12, w, 38), rpg.SLOT_NAMES[slot], None, "gold" if slot == self.tab else "ghost", True, 14)
            b.on_click = lambda s=slot: self._set_tab(s)
            self.group.add(b)
            x += w + 8
        y = LIST_Y
        for iid in self._items():
            item = rpg.ITEMS[iid]
            bx = RIGHT.right - 128
            if item["slot"] == "dung":
                if self.shop:
                    ok = st.quan >= item["price"]
                    b = ui.Button((bx, y + 9, 114, 40), f"Mua ({item['price']})", None, "gold" if ok else "ghost", ok, 13)
                    b.on_click = lambda i=iid: self._buy(i)
                    self.group.add(b)
            elif iid in st.inventory:
                worn = st.gear.get(item["slot"]) == iid
                on, off = ("Đang mang", "Mang theo") if item["slot"] == "cong_cu" else ("Đang mặc", "Mặc vào")
                b = ui.Button((bx, y + 9, 114, 40), on if worn else off, None, "jade" if worn else "primary", True, 13)
                b.on_click = lambda i=iid: self._equip(i)
                self.group.add(b)
            elif self.shop:
                ok = st.level >= item["level"] and st.quan >= item["price"]
                b = ui.Button((bx, y + 9, 114, 40), f"Mua ({item['price']})", None, "gold" if ok else "ghost", ok, 13)
                b.on_click = lambda i=iid: self._buy(i)
                self.group.add(b)
            y += ROW_H

    def _set_tab(self, slot):
        self.tab = slot
        self.app.audio.play("click")
        self._build()

    def _to_bag(self):
        self.app.scenes.replace(ShopScene(self.app, shop=False))

    def _to_bestiary(self):
        from scenes.bestiary import BestiaryScene

        self.app.scenes.replace(BestiaryScene(self.app))

    def _buy(self, iid):
        why = self.state.buy(iid)
        if why:
            self.note = why
            self.app.audio.play("sai")
        else:
            self.note = f"Đã mua {rpg.ITEMS[iid]['name']}."
            self.app.audio.play("nhan")
        self._build()

    def _equip(self, iid):
        self.state.equip(iid)
        self.app.audio.play("click")
        self._build()

    def handle(self, event):
        self.group.handle(event)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_b):
                self.app.scenes.pop()
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                i = TABS.index(self.tab) + (1 if event.key == pygame.K_RIGHT else -1)
                self._set_tab(TABS[i % len(TABS)])

    def update(self, dt):
        self.t += dt

    def draw(self, screen):
        st = self.state
        screen.fill(theme.LACQUER)
        title = f"LÒ RÈN · {self.smith}" if self.shop else "TÚI ĐỒ"
        fonts.text(screen, title, fonts.font("serif", 28), theme.GOLD_LIGHT, (30, 16))
        r = ui.tag(screen, f"{st.quan} quan", (30, 62), theme.LACQUER_RED, theme.GOLD_LIGHT, 17)
        r = ui.tag(screen, f"Thuốc nam: {st.potions}", (r.right + 12, 62), theme.LACQUER_2, theme.GOLD_LIGHT, 17)
        if st.grilled or st.fish_count():
            r = ui.tag(screen, f"Cá nướng: {st.grilled} · cá tươi: {st.fish_count()}", (r.right + 12, 62), theme.LACQUER_2,
                       theme.GOLD_LIGHT, 17)
        ui.tag(screen, f"Cấp {st.level}", (r.right + 12, 62), theme.LACQUER_2, theme.GOLD_LIGHT, 17)
        tip = "Quan có khi đánh quái, thắng thách đấu, trả lời đúng, về báo cáo già làng." if self.shop else "Đến lò rèn để mua thêm đồ."
        fonts.text(screen, self.note or tip, fonts.font("semi", 14), theme.PAPER_3, (W - 320, 70), "topright")
        ui.paper_panel(screen, LEFT, shadow=False)
        ui.paper_panel(screen, RIGHT, shadow=False)
        self._draw_hero(screen)
        self._draw_list(screen)
        self.group.draw(screen)

    def _draw_hero(self, screen):
        st = self.state
        x = LEFT.x + 20
        fonts.text(screen, "Đang mặc", fonts.font("bold", 18), theme.INK, (x, LEFT.y + 14))
        img = outfit.hero_cast(st.gear, 6).walk["down"][0]
        rect = img.get_rect(midtop=(LEFT.right - 80, LEFT.y + 40))
        screen.blit(img, rect)
        weapons.blit(screen, st.gear.get("vu_khi"), 6, weapons.hand_at("down", rect.midbottom, 6), weapons.held("down")[0])
        y = LEFT.y + 48
        for slot, name in rpg.SLOT_NAMES.items():
            if slot == "dung":
                continue
            iid = st.gear.get(slot)
            box = pygame.Rect(x, y, 52, 52)
            ui.alpha_rect(screen, box, (120, 70, 40, 40), 6)
            pygame.draw.rect(screen, theme.GOLD_DARK, box, 2, 6)
            if iid:
                screen.blit(sprites.icon(rpg.item_icon(iid), 2), (x + 2, y + 2))
            fonts.text(screen, name, fonts.font("semi", 12), theme.INK_SOFT, (x + 62, y + 4))
            fonts.text(screen, rpg.ITEMS[iid]["name"] if iid else "Trống", fonts.font("bold", 15), theme.INK if iid else theme.INK_FAINT, (x + 62, y + 22))
            y += 62
        y += 8
        f = fonts.font("semi", 14)
        rows = (f"Máu tối đa: {round(st.max_hp())}", f"Sát thương: x{st.damage_mult():.2f}", f"Tốc độ: x{st.speed_mult():.2f}",
                f"Hồi kỹ năng: x{st.cd_mult():.2f}")
        for i, line in enumerate(rows):
            fonts.text(screen, line, f, theme.INK, (x + (i % 2) * 180, y + (i // 2) * 22))
        fonts.text(screen, f"Sức mạnh: {st.power_rating()}", fonts.font("bold", 17), theme.LACQUER_RED, (x, y + 52))

    def _draw_list(self, screen):
        st = self.state
        x = RIGHT.x + 18
        y = LIST_Y
        items = self._items()
        if not items:
            fonts.text(screen, "Chưa có món nào ở mục này.", fonts.font("italic", 16), theme.INK_SOFT, (x, y + 10))
        for iid in items:
            item = rpg.ITEMS[iid]
            screen.blit(sprites.icon(rpg.item_icon(iid), 2), (x, y + 4))
            locked = st.level < item["level"] and iid not in st.inventory
            col = theme.INK_FAINT if locked else theme.INK
            name = item["name"] if item["slot"] != "dung" or self.shop else f"{item['name']} × {self._count(iid)}"
            r = fonts.text(screen, name, fonts.font("bold", 15), col, (x + 60, y + 2))
            req = f"cấp {item['level']}"
            fonts.text(screen, req, fonts.font("semi", 12), theme.LACQUER_RED if locked else theme.JADE, (r.right + 10, y + 5))
            fonts.text(screen, rpg.item_text(item), fonts.font("semi", 12), theme.LACQUER_RED, (x + 60, y + 21))
            fonts.paragraph(screen, item["desc"], fonts.font("ui", 12), theme.INK_SOFT, x + 60, y + 37, RIGHT.w - 230, gap=0)
            y += ROW_H
            pygame.draw.line(screen, theme.PAPER_3, (x, y - 3), (RIGHT.right - 18, y - 3))
