"""Bảng trạng thái của một người chơi khác: bấm vào người đó trên map là hiện, thay cho việc mở bảng Bạn chơi (P).

Có hình nhân vật mặc đúng đồ họ đang mặc, cấp, cảnh giới, lực chiến, đồ đang dùng, quan hệ với mình, và các nút Mời vào tổ
đội, Kết đồng minh, Thách đấu. Lời mời tới máy người kia hiện ở góc trên phải màn chơi của họ.
"""

from __future__ import annotations

import pygame
from core import fonts, outfit, rpg, sprites, theme, ui, weapons
from core.scene import Scene

W, H = theme.WIDTH, theme.HEIGHT
CARD = pygame.Rect(W // 2 - 330, 120, 660, 450)
FIGURE = pygame.Rect(CARD.x + 24, CARD.y + 24, 220, 280)
SCALE = 6
GEAR_SLOTS = ("vu_khi", "giap", "mu", "giay", "gang")


class PlayerCard(Scene):
    opaque = False

    def __init__(self, app, mp, uid: str):
        super().__init__(app)
        self.mp = mp
        self.net = mp.net
        self.uid = uid
        self.group = ui.ButtonGroup()
        self._sig = None
        self.peer = self._find() or {"id": uid, "name": ""}
        self._build()

    def _find(self) -> dict | None:
        """Bản mới nhất của người này trong danh sách người cùng map (vẫn được làm mới khi bảng đang mở)."""
        if self.net.peers_map == self.mp.ws.level_id:
            for p in self.net.peers:
                if p.get("id") == self.uid:
                    return p
        return None

    def _signature(self):
        p = self._find()
        return (p is not None, bool(p and p.get("party")), bool(p and p.get("ally")), self.net.online)

    def _build(self):
        self._sig = self._signature()
        here, party, ally, online = self._sig
        ok = here and online
        self.group.clear()
        x, y = CARD.x + 268, CARD.bottom - 64
        for label, kind, style, show in (("Mời vào tổ đội", "party", "primary", not party), ("Kết đồng minh", "ally", "primary", not ally),
                                         ("Thách đấu", "duel", "gold", True)):
            b = ui.Button((x, y, 122, 44), label if show else ("Đã cùng đội" if kind == "party" else "Đã là đồng minh"), None, style,
                          ok and show, 13)
            b.on_click = lambda k=kind: self._invite(k)
            self.group.add(b)
            x += 130
        self.group.add(ui.Button((CARD.right - 50, CARD.y + 12, 38, 34), "X", self._close, "ghost", size=14))

    def _invite(self, kind: str):
        self.mp.invite(kind, self.uid)
        self.app.scenes.pop()

    def _close(self):
        self.app.scenes.pop()

    def handle(self, event):
        if self.group.handle(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._close()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and not CARD.collidepoint(event.pos):
            self._close()  # bấm ra ngoài bảng thì đóng

    def update(self, dt):
        p = self._find()
        if p is not None:
            self.peer = p
        if self._signature() != self._sig:
            self._build()

    def backdrop(self, screen):
        ui.veil(screen, (10, 6, 4, 120))

    def draw(self, screen):
        p = self.peer
        ui.paper_panel(screen, CARD)
        here = self._sig[0]
        # hình nhân vật mặc đúng đồ, cầm đúng vũ khí
        ui.lacquer_panel(screen, FIGURE, 230)
        gear = p.get("gear") or {}
        img = outfit.hero_cast(gear, SCALE).walk["down"][0]
        rect = img.get_rect(midbottom=(0, 0))
        held = weapons.held_sprite(gear.get("vu_khi"), "down", SCALE)
        box = rect.union(held[0].get_rect(topleft=(held[1], held[2]))) if held else rect
        dx, dy = FIGURE.centerx - box.centerx, FIGURE.centery + 6 - box.centery  # người và vũ khí nằm giữa khung
        rect.move_ip(dx, dy)
        clip = screen.get_clip()
        screen.set_clip(FIGURE.inflate(-8, -8))
        pygame.draw.ellipse(screen, (30, 24, 20), (rect.centerx - rect.w * 0.36, rect.bottom - 10, rect.w * 0.72, 18))
        if held and held[3]:
            screen.blit(held[0], (held[1] + dx, held[2] + dy))
        screen.blit(img, rect)
        if held and not held[3]:
            screen.blit(held[0], (held[1] + dx, held[2] + dy))
        screen.set_clip(clip)
        # thông tin
        x = CARD.x + 268
        fonts.text(screen, str(p.get("name", "")) or "Người chơi", fonts.font("serif", 28), theme.INK, (x, CARD.y + 22))
        relation = "Cùng tổ đội" if p.get("party") else ("Đồng minh" if p.get("ally") else "Người chơi cùng map")
        ui.tag(screen, relation, (x, CARD.y + 66), theme.JADE if p.get("party") else (theme.LACQUER_RED if p.get("ally") else theme.LACQUER_2),
               theme.WHITE, 13)
        if not here:
            ui.tag(screen, "Đã rời map", (x + 190, CARD.y + 66), theme.INK_SOFT, theme.WHITE, 13)
        f, fb = fonts.font("ui", 15), fonts.font("bold", 15)
        rows = (("Cấp", str(p.get("lv", 1))), ("Cảnh giới", str(p.get("realm") or "—")), ("Lực chiến", f"{p.get('pow', 0):,}".replace(",", ".")))
        y = CARD.y + 104
        for label, value in rows:
            fonts.text(screen, label, f, theme.INK_SOFT, (x, y))
            fonts.text(screen, value, fb, theme.INK, (x + 110, y))
            y += 26
        fight = p.get("fight")
        if isinstance(fight, dict) and fight.get("name"):
            fonts.text(screen, f"Đang đánh {str(fight['name'])[:40]}", fonts.font("italic", 14), theme.LACQUER_RED, (x, y))
        y = CARD.y + 206
        fonts.text(screen, "Đồ đang dùng", fonts.font("bold", 14), theme.INK, (x, y))
        y += 24
        for i, slot in enumerate(GEAR_SLOTS):
            cx, cy = x + (i % 2) * 190, y + (i // 2) * 34
            item = gear.get(slot)
            name = rpg.ITEMS.get(item, {}).get("name") if item else None
            if name:
                try:
                    icon = sprites.icon(rpg.item_icon(item), 1)
                    screen.blit(icon, icon.get_rect(midleft=(cx, cy + 10)))
                except Exception:  # noqa: BLE001  thiếu hình món đồ thì chỉ ghi tên
                    pass
            fonts.text(screen, f"{rpg.SLOT_NAMES[slot]}: {name or 'trống'}", fonts.font("ui", 13), theme.INK if name else theme.INK_FAINT,
                       (cx + 30, cy + 2))
        fonts.text(screen, "Lời mời hiện ở góc trên phải màn chơi của họ, họ bấm Đồng ý là vào việc ngay.", fonts.font("italic", 13),
                   theme.INK_SOFT, (CARD.x + 24, CARD.bottom - 96))
        self.group.draw(screen)
