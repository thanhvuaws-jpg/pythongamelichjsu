"""Bảng Bạn chơi (phím P): người cùng map, tổ đội, đồng minh, lời mời đang chờ, lời nói nhanh.

Mời vào tổ đội để cùng đánh quái chia kinh nghiệm; kết đồng minh để luôn thấy nhau trong danh sách; thách đấu để hai
người cùng vào võ đài đánh thật (scenes/pvp.py). Bấm thẳng vào người chơi trên map cũng mời được (scenes/playercard.py).
Lời nói nhanh ở đây là các câu có sẵn; chat gõ tự do thì bấm L (xem scenes/multiplayer.py).
"""

from __future__ import annotations

import pygame
from core import fonts, net, theme, ui
from core.scene import Scene

W, H = theme.WIDTH, theme.HEIGHT
PEERS = pygame.Rect(30, 104, 620, 470)
PARTY = pygame.Rect(664, 104, 586, 150)
ALLIES = pygame.Rect(664, 266, 586, 150)
INVITES = pygame.Rect(664, 428, 586, 146)
SAY = pygame.Rect(30, 586, 1220, 118)
ROW = 46
INVITE_NAMES = {"party": "mời vào tổ đội", "ally": "mời kết đồng minh", "duel": "thách đấu"}


class SocialScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.net = net.get()
        self.group = ui.ButtonGroup()
        self.t = 0.0
        self._sig = None
        self._build()

    def _signature(self):
        n = self.net
        return (tuple((p["id"], p.get("party"), p.get("ally")) for p in n.peers[:9]), str(n.party), str(n.allies),
                tuple((i["kind"], i["from"]) for i in n.invites), n.online)

    def _build(self):
        n = self.net
        self._sig = self._signature()
        self.group.clear()
        self.group.add(ui.Button((W - 150, 14, 136, 40), "Đóng", lambda: self.app.scenes.pop(), "ghost", size=15))
        on = n.online
        y = PEERS.y + 46
        for p in n.peers[:9]:
            x = PEERS.right - 330
            for label, kind, show in (("Tổ đội", "party", not p.get("party")), ("Đồng minh", "ally", not p.get("ally")),
                                      ("Thách đấu", "duel", True)):
                if show:
                    b = ui.Button((x, y + 4, 100, 36), label, None, "primary" if kind != "duel" else "gold", on, 12)
                    b.on_click = lambda k=kind, u=p["id"]: self._invite(k, u)
                    self.group.add(b)
                x += 108
            y += ROW
        if n.party:
            self.group.add(ui.Button((PARTY.right - 130, PARTY.y + 10, 116, 34), "Rời đội", self._leave, "ghost", on, 12))
        y = ALLIES.y + 44
        for a in n.allies[:3]:
            b = ui.Button((ALLIES.right - 110, y, 96, 30), "Bỏ", None, "ghost", on, 12)
            b.on_click = lambda u=a["id"]: self._unally(u)
            self.group.add(b)
            y += 34
        y = INVITES.y + 44
        for inv in n.invites[:3]:
            ok = ui.Button((INVITES.right - 214, y, 96, 30), "Đồng ý", None, "jade", True, 12)
            ok.on_click = lambda i=inv: self._answer(i, True)
            no = ui.Button((INVITES.right - 110, y, 96, 30), "Từ chối", None, "ghost", True, 12)
            no.on_click = lambda i=inv: self._answer(i, False)
            self.group.add(ok)
            self.group.add(no)
            y += 34
        for i, text in enumerate(net.PHRASES):
            col, row = i % 6, i // 6
            b = ui.Button((SAY.x + 14 + col * 200, SAY.y + 40 + row * 38, 192, 32), text, None, "ghost", on, 12)
            b.on_click = lambda k=i: self._say(k)
            self.group.add(b)

    def map_name(self, mid: str) -> str:
        """Tên chặng hoặc tên vùng luyện thay cho mã map."""
        st = self.state
        if mid in st.levels:
            return st.levels[mid]["level"]["title"]
        if mid in st.fields:
            return st.fields[mid]["name"]
        return "nơi khác"

    def _invite(self, kind, uid):
        self.net.invite(kind, uid)
        self.app.audio.play("click")

    def _answer(self, inv, ok):
        self.net.answer(inv, ok)
        self.app.audio.play("nhan" if ok else "click")
        self._build()

    def _leave(self):
        self.net.send({"t": "party_leave"})
        self.app.audio.play("click")

    def _unally(self, uid):
        self.net.send({"t": "ally_remove", "id": uid})
        self.app.audio.play("click")

    def _say(self, k):
        self.net.send({"t": "say", "k": k})
        self.app.audio.play("click")
        self.app.scenes.pop()

    def handle(self, event):
        self.group.handle(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.app.scenes.pop()

    def update(self, dt):
        self.t += dt
        self.net.poll()
        if self._signature() != self._sig:
            self._build()

    def draw(self, screen):
        n = self.net
        screen.fill(theme.LACQUER)
        fonts.text(screen, "BẠN CHƠI", fonts.font("serif", 28), theme.GOLD_LIGHT, (30, 16))
        ui.tag(screen, n.status_text(), (190, 22), theme.JADE if n.online else theme.LACQUER_2, theme.WHITE, 15)
        fonts.text(screen, "Tổ đội cùng đánh quái được chia một nửa kinh nghiệm của nhau. Thách đấu: hai người cùng vào võ đài đánh thật.",
                   fonts.font("ui", 14), theme.PAPER_3, (30, 66))
        for rect in (PEERS, PARTY, ALLIES, INVITES, SAY):
            ui.paper_panel(screen, rect, shadow=False)
        self._draw_peers(screen)
        self._draw_party(screen)
        self._draw_allies(screen)
        self._draw_invites(screen)
        fonts.text(screen, "Nói nhanh (người cùng map đều thấy)", fonts.font("bold", 16), theme.INK, (SAY.x + 16, SAY.y + 12))
        self.group.draw(screen)

    def _draw_peers(self, screen):
        n = self.net
        fonts.text(screen, f"Người cùng map ({len(n.peers)})", fonts.font("bold", 17), theme.INK, (PEERS.x + 16, PEERS.y + 12))
        if not n.peers:
            msg = "Chưa có ai ở map này. Rủ bạn cùng lớp vào chơi nhé!" if n.online else "Khi có kết nối, người chơi khác sẽ hiện ở đây."
            fonts.text(screen, msg, fonts.font("italic", 15), theme.INK_SOFT, (PEERS.x + 16, PEERS.y + 52))
        y = PEERS.y + 46
        for p in n.peers[:9]:
            col = theme.JADE if p.get("party") else (theme.LACQUER_RED if p.get("ally") else theme.INK)
            fonts.text(screen, p.get("name", ""), fonts.font("bold", 15), col, (PEERS.x + 16, y + 4))
            fonts.text(screen, f"cấp {p.get('lv', 1)} · {p.get('realm', '')} · sức mạnh {p.get('pow', 0)}", fonts.font("ui", 12), theme.INK_SOFT,
                       (PEERS.x + 16, y + 24))
            y += ROW

    def _draw_party(self, screen):
        party = self.net.party
        fonts.text(screen, "Tổ đội", fonts.font("bold", 17), theme.INK, (PARTY.x + 16, PARTY.y + 12))
        if not party:
            fonts.text(screen, "Chưa có tổ đội. Mời người cùng map bằng nút Tổ đội.", fonts.font("ui", 14), theme.INK_SOFT, (PARTY.x + 16, PARTY.y + 48))
            return
        y = PARTY.y + 48
        for m in party.get("members", []):
            lead = " (đội trưởng)" if m.get("id") == party.get("leader") else ""
            dot = theme.JADE if m.get("online") else theme.INK_FAINT
            pygame.draw.circle(screen, dot, (PARTY.x + 22, y + 9), 5)
            fonts.text(screen, (m.get("name") or "Đang vắng") + lead, fonts.font("semi", 14), theme.INK, (PARTY.x + 34, y))
            y += 22

    def _draw_allies(self, screen):
        allies = self.net.allies
        fonts.text(screen, f"Đồng minh ({len(allies)})", fonts.font("bold", 17), theme.INK, (ALLIES.x + 16, ALLIES.y + 12))
        if not allies:
            fonts.text(screen, "Kết đồng minh để luôn biết bạn mình đang ở đâu.", fonts.font("ui", 14), theme.INK_SOFT, (ALLIES.x + 16, ALLIES.y + 48))
        y = ALLIES.y + 44
        for a in allies[:3]:
            where = f"đang ở {self.map_name(a.get('map'))}" if a.get("online") and a.get("map") else ("đang chơi" if a.get("online") else "vắng mặt")
            fonts.text(screen, f"{a.get('name') or '...'} · {where}", fonts.font("semi", 14), theme.INK, (ALLIES.x + 16, y + 6))
            y += 34

    def _draw_invites(self, screen):
        invites = self.net.invites
        fonts.text(screen, f"Lời mời ({len(invites)})", fonts.font("bold", 17), theme.INK, (INVITES.x + 16, INVITES.y + 12))
        y = INVITES.y + 44
        for inv in invites[:3]:
            fonts.text(screen, f"{inv.get('name', '')} {INVITE_NAMES.get(inv.get('kind'), '')}", fonts.font("semi", 14), theme.INK, (INVITES.x + 16, y + 6))
            y += 34
