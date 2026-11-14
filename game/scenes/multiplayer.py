"""Người chơi khác trên map: gửi vị trí của mình, vẽ người khác mặc đúng đồ của họ, chia kinh nghiệm trong tổ đội,
nói nhanh bằng câu có sẵn, chat gõ tự do (kênh map miễn phí, kênh thế giới tốn quan), lời mời hiện ở góc trên phải để
bấm Đồng ý hay Từ chối, và đưa cả hai người tới võ đài khi lời thách đấu được nhận (xem scenes/pvp.py).

Kết nối vẫn chạy khi đang mở túi đồ, bảng bạn chơi, hội thoại...: SceneManager gọi `pump` mỗi khung hình, nên người khác
vẫn thấy mình, danh sách người cùng map vẫn mới và lời thách đấu được nhận ở đâu cũng vào trận ngay.
"""

from __future__ import annotations

import math

import pygame
from core import chienma, fonts, net, outfit, rpg, theme, ui, weapons
from core.sprites import TILE

from scenes.pvp import PvpScene

SEND_EVERY = 0.12  # gửi vị trí khoảng tám lần mỗi giây
FULL_EVERY = 2.0  # đồ và chỉ số chiến đấu gửi thưa hơn
SAY_TIME = 3.5
LERP = 10.0
PARTY_COL, ALLY_COL, OTHER_COL = (150, 230, 160), (243, 212, 140), (230, 230, 236)
CHAT_BUBBLE = 6.0  # lời chat hiện trên đầu người nói bấy nhiêu giây
WORLD_SHOW, MAP_SHOW = 45.0, 30.0  # tin thế giới, tin map còn hiện trong khung bấy nhiêu giây
WORLD_BOX = pygame.Rect(theme.WIDTH - 12 - 440, 64, 440, 0)  # khung chat thế giới, ngay dưới nút ba gạch ở góc trên phải
MAP_BOX = pygame.Rect(12, 0, 410, 0)  # khung chat map, ngay trên khung cấp độ ở góc dưới trái
BUBBLE_CHARS = 42
INVITE_TTL = 60.0  # máy chủ giữ lời mời bấy nhiêu giây
INVITE_BOX = pygame.Rect(theme.WIDTH - 12 - 400, 64, 400, 112)  # thẻ lời mời đầu tiên, ngay dưới nút ba gạch
INVITE_GAP = 8
INVITE_SHOW = 3
INVITE_TITLE = {"party": "MỜI VÀO TỔ ĐỘI", "ally": "KẾT ĐỒNG MINH", "duel": "THÁCH ĐẤU"}
INVITE_TEXT = {"party": "mời bạn vào tổ đội cùng đánh quái", "ally": "muốn kết đồng minh với bạn",
               "duel": "thách đấu bạn trên võ đài"}
INVITE_WHAT = {"party": "vào tổ đội", "ally": "kết đồng minh", "duel": "thách đấu"}


class Avatar:
    def __init__(self, p: dict):
        self.id = p["id"]
        self.x, self.y = float(p["x"]), float(p["y"])
        self.frame = 0.0
        self.set(p)

    def set(self, p: dict):
        self.data = p
        self.tx, self.ty = float(p["x"]), float(p["y"])
        self.facing = p.get("f", "down")
        self.moving = bool(p.get("m"))
        self.mode = p.get("mode", "walk")
        self.gear = p.get("gear") or {}


class Multiplayer:
    def __init__(self, ws):
        self.ws = ws
        self.app = ws.app
        self.state = ws.state
        self.net = net.get()
        self.send_t = 0.0
        self.full_t = 0.0
        self.avatars: dict[str, Avatar] = {}
        self.bubbles: dict[str, tuple[str, float]] = {}
        self.t = 0.0
        self.world_at = -1e9  # lúc gửi tin thế giới gần nhất
        self.fight: dict | None = None  # đang đánh ai: gửi kèm vị trí để người cùng map thấy
        self.invite_btns: list[ui.Button] = []
        self._invite_sig: tuple = ()
        self.app.scenes.pump = self.pump  # giữ kết nối khi cảnh khác che map

    # ----- gửi đi -----
    def combat(self) -> dict:
        st = self.state
        return {"hp": round(st.max_hp()), "dmg": round(st.damage_mult(), 3), "spd": round(st.speed_mult(), 3), "cd": round(st.cd_mult(), 3),
                "skills": {s: st.skill_levels.get(s, 1) for s in st.equipped_skills()}}

    def _send_pos(self, full: bool):
        ws, st = self.ws, self.state
        msg = {"t": "pos", "map": ws.level_id, "x": round(ws.x), "y": round(ws.y), "f": ws.facing, "m": ws.moving, "mode": ws.mode,
               "lv": st.level, "realm": st.realm_name(), "pow": st.power_rating()}
        if self.fight:
            msg["fight"] = self.fight
        if full:
            msg["gear"] = st.gear
            msg["combat"] = self.combat()
        self.net.send(msg)

    # ----- đang đánh: người cùng map thấy mình vung vũ khí -----
    def begin_fight(self, scene, name: str, x: float, y: float):
        """Vào trận với quái trên map: trận che mất map nên trận gọi `background` mỗi khung hình để vẫn gửi vị trí, kèm
        đang đánh ai, ở đâu. Không có hàm này thì người khác chỉ thấy mình đứng yên rồi biến mất."""
        self.fight = {"name": str(name)[:40], "x": round(x), "y": round(y)}
        scene.background = self.background
        self.send_t = 0.0

    def end_fight(self):
        self.fight = None
        self.send_t = 0.0

    def background(self, dt: float):
        if not self.net.available:
            return
        self.net.poll()
        self.send_t -= dt
        if self.send_t <= 0:
            self.send_t = SEND_EVERY * 2
            self._send_pos(False)

    def pump(self, dt: float):
        """Chạy mỗi khung hình dù cảnh nào ở trên cùng. Khi map bị che (túi đồ, bảng bạn chơi, hội thoại, câu hỏi...) vẫn
        nhận tin, vẫn gửi vị trí để người khác không thấy mình biến mất, và lời thách đấu được nhận thì vào trận ngay."""
        scenes = self.app.scenes
        if not self.net.available or scenes.top is self.ws or self.ws not in scenes.stack:
            return
        self.t += dt
        self.net.poll()
        if getattr(scenes.top, "background", None) is None:  # trận đánh tự gửi vị trí qua `background`
            self.send_t -= dt
            if self.send_t <= 0:
                self.send_t = SEND_EVERY * 2
                self._send_pos(False)
        self._age_invites(dt)
        self._handle_events()

    def mob_down(self, key: str):
        """Mình vừa hạ một con quái: người cùng map cũng thấy nó ngã."""
        self.net.send({"t": "mob_kill", "mob": key})

    def kill(self, mob_name: str, exp: int, tiem: int):
        """Vừa hạ quái: báo để đồng đội đứng gần được chia phần."""
        if self.net.party:
            self.net.send({"t": "kill", "mob": mob_name, "exp": exp, "tiem": tiem})

    def say(self, k: int):
        self.net.send({"t": "say", "k": k})

    # ----- chat gõ tự do -----
    def open_chat(self, ch: str = "map"):
        """Mở ô gõ chat của trang chơi; chơi trên máy (không qua trang web) thì báo không có chat."""
        if not self.net.open_chat(ch):
            self.app.toast("Chat chỉ dùng được khi chơi trên trang web đã đăng nhập.", theme.PAPER, 3.0)

    def send_chat(self, ch: str, text: str) -> bool:
        """Gửi một tin chat. Kênh thế giới trừ quan trong bản lưu trước khi gửi; thiếu quan hoặc gửi dồn thì không gửi."""
        st = self.state
        text = " ".join(str(text).split())[:net.CHAT_LEN]
        if ch not in net.CHANNELS or not text:
            return False
        if not self.net.online:
            self.app.toast("Chưa vào được thế giới chung nên chưa gửi được tin.", theme.PAPER, 3.0)
            return False
        if ch == "world":
            if self.t - self.world_at < rpg.WORLD_CHAT_GAP:
                self.app.toast("Kênh thế giới: chờ vài giây giữa hai tin.", theme.PAPER, 2.5)
                return False
            if st.quan < rpg.WORLD_CHAT_COST:
                self.app.toast(f"Chat thế giới tốn {rpg.WORLD_CHAT_COST} quan mỗi tin, bạn đang có {st.quan} quan.", theme.RED_BRIGHT, 3.5)
                return False
            st.quan -= rpg.WORLD_CHAT_COST
            st.save()
            self.world_at = self.t
            self.app.toast(f"Đã gửi lên kênh thế giới: -{rpg.WORLD_CHAT_COST} quan", theme.GOLD_LIGHT, 2.0)
        self.net.send({"t": "chat", "ch": ch, "text": text})
        return True

    # ----- nhận về -----
    def update(self, dt: float):
        self.t += dt
        for req in self.net.take_chat():
            self.send_chat(str(req.get("ch", "")), str(req.get("text", "")))
        if not self.net.available:
            return
        self.net.poll()
        for c in self.net.chat:
            c["age"] += dt
        self.send_t -= dt
        self.full_t -= dt
        if self.send_t <= 0:
            self.send_t = SEND_EVERY
            full = self.full_t <= 0
            if full:
                self.full_t = FULL_EVERY
            self._send_pos(full)
        self._sync_avatars(dt)
        for key in list(self.bubbles):
            text, t = self.bubbles[key]
            if t - dt <= 0:
                del self.bubbles[key]
            else:
                self.bubbles[key] = (text, t - dt)
        self._age_invites(dt)
        self._handle_events()

    def _age_invites(self, dt: float):
        """Lời mời mới thì kêu một tiếng và báo; lời mời quá hạn ở máy chủ thì bỏ khỏi góc màn hình."""
        n = self.net
        for inv in n.invites:
            inv["age"] = inv.get("age", 0.0) + dt
            if not inv.get("seen"):
                inv["seen"] = True
                what = INVITE_WHAT.get(inv.get("kind"), "")
                self.app.toast(f"{inv.get('name', '')} mời bạn {what} (trả lời ở góc trên phải)", theme.JADE_LIGHT, 5.0)
                self.app.audio.play("nhan")
        n.invites = [i for i in n.invites if i["age"] < INVITE_TTL]
        sig = tuple((i.get("kind"), i.get("from"), id(i)) for i in n.invites[-INVITE_SHOW:])
        if sig != self._invite_sig:
            self._invite_sig = sig
            self._build_invites()

    def _sync_avatars(self, dt: float):
        here = {p["id"]: p for p in self.net.peers} if self.net.peers_map == self.ws.level_id else {}
        for uid in list(self.avatars):
            if uid not in here:
                del self.avatars[uid]
        for uid, p in here.items():
            a = self.avatars.get(uid)
            if a is None:
                self.avatars[uid] = Avatar(p)
            else:
                a.set(p)
        k = min(1.0, dt * LERP)
        for a in self.avatars.values():
            if math.hypot(a.tx - a.x, a.ty - a.y) > TILE * 6:  # dịch chuyển xa thì nhảy tới luôn
                a.x, a.y = a.tx, a.ty
            a.x += (a.tx - a.x) * k
            a.y += (a.ty - a.y) * k
            a.frame = a.frame + dt * 8 if a.moving else 0.0
            fight = a.data.get("fight")
            if isinstance(fight, dict):
                a.facing = self.ws._dir_to(a.x, a.y, float(fight.get("x", a.x)), float(fight.get("y", a.y)))
                a.swing = (getattr(a, "swing", 0.0) + dt) % 0.6

    def _handle_events(self):
        st = self.state
        events, self.net.events = self.net.events, []
        for e in events:
            kind = e.get("t")
            if kind == "say" and isinstance(e.get("k"), int) and 0 <= e["k"] < len(net.PHRASES):
                who = "me" if self.net.me and e.get("from") == self.net.me["id"] else e.get("from")
                self.bubbles[who] = (net.PHRASES[e["k"]], SAY_TIME)
            elif kind == "chat" and e.get("ch") == "map":
                who = "me" if self.net.me and e.get("from") == self.net.me["id"] else e.get("from")
                text = str(e.get("text", ""))
                self.bubbles[who] = (text if len(text) <= BUBBLE_CHARS else text[:BUBBLE_CHARS - 1] + "…", CHAT_BUBBLE)
            elif kind == "notice":
                self.app.toast(str(e.get("text", ""))[:120], theme.PAPER, 3.5)
            elif kind == "mob_down":
                self.ws.mobs.remote_kill(e.get("mob"))  # người khác (hay bot) trên map vừa hạ con quái này
            elif kind == "share":
                exp, tiem = int(e.get("exp", 0)), int(e.get("tiem", 0))
                st.gain(exp, tiem, 0)
                st.save()
                self.app.toast(f"Đồng đội {e.get('from', '')} hạ {e.get('mob', 'quái')}: +{exp} kinh nghiệm, +{tiem} tiềm năng", theme.JADE_LIGHT, 3.0)
            elif kind == "pvp_start" and isinstance(e.get("vs"), dict) and isinstance(e.get("room"), str):
                self._start_pvp(e)

    # ----- thách đấu thật: cả hai người cùng vào võ đài -----
    def _start_pvp(self, start: dict):
        """Lời thách đấu đã được nhận: mở võ đài ngay trên cảnh đang mở (túi đồ, bảng bạn chơi...). Đánh xong thì quay về
        đúng chỗ cũ, cảnh bên dưới không bị đóng ngang."""
        if isinstance(self.app.scenes.top, PvpScene):  # máy chủ không cho đấu hai trận một lúc; phòng khi tin đến trễ
            self.net.send({"t": "pvp_quit", "room": start["room"]})
            return
        ws, vs = self.ws, start["vs"]
        ws.path.clear()
        ws.auto = None
        before = self.fight
        scene = PvpScene(self.app, start, lambda r: self._pvp_done(vs, r, before))
        self.begin_fight(scene, f"{str(vs.get('name', ''))[:28]} (thách đấu)", ws.x, ws.y)
        self.app.scenes.push(scene)

    def _pvp_done(self, vs: dict, result, before: dict | None = None):
        self.fight = before  # đang đánh quái trên map mà bị gọi đi thách đấu thì quay về trận cũ
        self.send_t = 0.0
        st = self.state
        name = vs.get("name", "đối thủ")
        if not isinstance(result, dict) or result.get("quit"):
            self.app.toast(f"Bạn đã rút lui khỏi trận thách đấu với {name}.", theme.PAPER, 3.0)
            return
        if result.get("win"):
            exp = 30 + 6 * st.level
            st.duels_won += 1
            st.gain(exp, 10, 0)
            st.save()
            self.app.toast(f"Bạn thắng {name}! +{exp} kinh nghiệm, +10 tiềm năng", theme.GOLD_LIGHT, 3.5)
        elif result.get("draw"):
            self.app.toast(f"Trận với {name} không phân thắng bại. Hẹn đấu lại!", theme.PAPER, 3.0)
        else:
            self.app.toast(f"Bạn thua {name}. Hẹn đấu lại!", theme.PAPER, 3.0)

    # ----- lời mời ở góc trên phải -----
    def invite(self, kind: str, uid: str):
        if not self.net.online:
            self.app.toast("Chưa vào được thế giới chung nên chưa mời được.", theme.PAPER, 3.0)
            return
        self.net.invite(kind, uid)
        self.app.audio.play("click")

    def answer(self, inv: dict, ok: bool):
        self.net.answer(inv, ok)
        self.app.audio.play("nhan" if ok else "click")
        self._age_invites(0.0)

    def invite_cards(self) -> list[tuple[dict, pygame.Rect]]:
        """Thẻ lời mời ở góc trên phải, lời mời mới nhất ở trên cùng."""
        return [(inv, INVITE_BOX.move(0, i * (INVITE_BOX.h + INVITE_GAP)))
                for i, inv in enumerate(reversed(self.net.invites[-INVITE_SHOW:]))]

    def invites_bottom(self) -> int:
        cards = self.invite_cards()
        return cards[-1][1].bottom + INVITE_GAP if cards else INVITE_BOX.y

    def _build_invites(self):
        self.invite_btns = []
        for inv, card in self.invite_cards():
            ok = ui.Button((card.right - 12 - 214, card.bottom - 40, 104, 32), "Đồng ý", None, "jade", size=14)
            ok.on_click = lambda i=inv: self.answer(i, True)
            no = ui.Button((card.right - 12 - 104, card.bottom - 40, 104, 32), "Từ chối", None, "ghost", size=14)
            no.on_click = lambda i=inv: self.answer(i, False)
            self.invite_btns += [ok, no]

    def handle(self, event) -> bool:
        """Bấm vào thẻ lời mời: trả True nếu đã dùng sự kiện (màn chơi không đi tới chỗ vừa bấm)."""
        if event.type not in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            return False
        for b in list(self.invite_btns):
            if b.handle(event):
                return True
        return event.type != pygame.MOUSEMOTION and any(card.collidepoint(event.pos) for _inv, card in self.invite_cards())

    def draw_invites(self, screen):
        for inv, card in self.invite_cards():
            kind = inv.get("kind")
            ui.lacquer_panel(screen, card, 236)
            accent = theme.GOLD_LIGHT if kind == "duel" else theme.JADE_LIGHT
            fonts.text(screen, INVITE_TITLE.get(kind, "LỜI MỜI"), fonts.font("bold", 14), accent, (card.x + 14, card.y + 10))
            left = max(0, round(INVITE_TTL - inv.get("age", 0.0)))
            fonts.text(screen, f"còn {left} giây", fonts.font("ui", 12), theme.PAPER_3, (card.right - 14, card.y + 11), "topright")
            who = f"{inv.get('name', '')} · cấp {inv['lv']}" if inv.get("lv") else str(inv.get("name", ""))
            fonts.text(screen, who, fonts.font("bold", 15), theme.PAPER, (card.x + 14, card.y + 30))
            fonts.text(screen, INVITE_TEXT.get(kind, ""), fonts.font("ui", 13), theme.PAPER_3, (card.x + 14, card.y + 51))
        for b in self.invite_btns:
            b.draw(screen)

    # ----- vẽ -----
    def relation(self, a: Avatar) -> tuple[int, int, int]:
        if a.data.get("party"):
            return PARTY_COL
        if a.data.get("ally"):
            return ALLY_COL
        return OTHER_COL

    def items(self, cx, cy) -> list[tuple]:
        out = []
        for a in self.avatars.values():
            if not (-TILE * 2 < a.x - cx < theme.WIDTH + TILE * 2 and -TILE < a.y - cy < theme.HEIGHT + TILE * 3):
                continue
            cast = outfit.hero_cast(a.gear)
            img = cast.walk[a.facing][int(a.frame) % 4 if a.moving else 0]
            if isinstance(a.data.get("fight"), dict) and getattr(a, "swing", 0.0) < 0.25:
                img = cast.attack[a.facing]  # đang đánh quái: vung vũ khí
            px, py = a.x - TILE / 2, a.y - TILE + 8
            if a.mode == "horse":
                horse = chienma.views()[a.facing][int(a.frame) % 2]
                out.append((a.y, 2.2, horse, a.x - horse.get_width() / 2, a.y - horse.get_height() + 8))
                py -= 24
            if a.mode != "boat":
                out.append((a.y, 2.3, img, px, py))
                held = weapons.held_sprite(a.gear.get("vu_khi"), a.facing, 4)
                if held:
                    w, dx, dy, behind = held
                    out.append((a.y, 2.25 if behind else 2.35, w, px + TILE / 2 + dx, py + TILE + dy))
        return out

    def draw_labels(self, screen, cx, cy):
        f = fonts.font("bold", 13)
        for a in self.avatars.values():
            sx, sy = a.x - cx, a.y - cy - TILE - (24 if a.mode == "horse" else 0)
            if not (-80 < sx < theme.WIDTH + 80 and -80 < sy < theme.HEIGHT + 80):
                continue
            tag = " · tổ đội" if a.data.get("party") else (" · đồng minh" if a.data.get("ally") else "")
            fonts.text(screen, f"{a.data.get('name', '')} · cấp {a.data.get('lv', 1)}{tag}", f, self.relation(a), (sx, sy), "midbottom", shadow=(24, 16, 14))
            fight = a.data.get("fight")
            if isinstance(fight, dict) and fight.get("name"):
                ui.tag(screen, f"đang đánh {str(fight['name'])[:40]}", (sx, a.y - cy + 6), theme.LACQUER_RED, theme.GOLD_LIGHT, 12, "midtop")
            bubble = self.bubbles.get(a.id)
            if bubble:
                ui.tag(screen, bubble[0], (sx, sy - 18), theme.PAPER, theme.INK, 13, "midbottom")
        mine = self.bubbles.get("me")
        if mine:
            ui.tag(screen, mine[0], (self.ws.x - cx, self.ws.y - cy - TILE - 4), theme.PAPER, theme.INK, 13, "midbottom")

    def _chat_box(self, screen, rect: pygame.Rect, title: str, hint: str, lines: list[dict], accent, grow_up: bool):
        f, f_name = fonts.font("ui", 13), fonts.font("bold", 13)
        rows = []
        for c in lines:
            name = "Bạn" if c["mine"] else c["name"]
            rows.append((name, fonts.wrap(f"{name}: {c['text']}", f, rect.w - 24), c["mine"]))
        lh = f.get_linesize()
        h = 30 + sum(len(w) for _n, w, _m in rows) * lh + 8
        box = pygame.Rect(rect.x, rect.y - h if grow_up else rect.y, rect.w, h)
        ui.lacquer_panel(screen, box, 205)
        fonts.text(screen, title, fonts.font("bold", 13), accent, (box.x + 12, box.y + 8))
        fonts.text(screen, hint, fonts.font("ui", 12), theme.PAPER_3, (box.right - 12, box.y + 9), "topright")
        y = box.y + 28
        for name, wrapped, mine in rows:
            color = theme.JADE_LIGHT if mine else accent
            for i, line in enumerate(wrapped):
                if i == 0 and line.startswith(name + ":"):
                    fonts.text(screen, name + ":", f_name, color, (box.x + 12, y))
                    fonts.text(screen, line[len(name) + 1:], f, theme.PAPER, (box.x + 12 + f_name.size(name + ":")[0], y))
                else:
                    fonts.text(screen, line, f, theme.PAPER, (box.x + 12, y))
                y += lh

    def draw_chat(self, screen, map_bottom: int):
        """Khung chat thế giới ở góc trên phải (dưới nút ba gạch), khung chat map ở góc dưới trái; tin cũ tự ẩn."""
        world = [c for c in self.net.chat if c["ch"] == "world" and c["age"] < WORLD_SHOW][-5:]
        if world:
            box = WORLD_BOX.move(0, self.invites_bottom() - WORLD_BOX.y)  # nằm dưới các thẻ lời mời
            self._chat_box(screen, box, "THẾ GIỚI", f"L để chat · {rpg.WORLD_CHAT_COST} quan/tin", world, theme.GOLD_LIGHT, False)
        here = [c for c in self.net.chat if c["ch"] == "map" and c["age"] < MAP_SHOW][-4:]
        if here:
            self._chat_box(screen, MAP_BOX.move(0, map_bottom - 8), "CÙNG MAP", "L để chat · miễn phí", here, OTHER_COL, True)

    def hud_tag(self) -> str | None:
        if not self.net.available:
            return None
        n = len(self.avatars)
        inv = f" · {len(self.net.invites)} lời mời" if self.net.invites else ""
        return (f"Thế giới chung: {n} người cùng map{inv}" if self.net.online else self.net.status_text())

    def avatar_at(self, wx: float, wy: float) -> Avatar | None:
        """Người chơi khác ở chỗ vừa bấm (toạ độ trên map); hai người chồng lên nhau thì chọn người đứng trước."""
        best = None
        for a in self.avatars.values():
            lift = 24 if a.mode == "horse" else 0
            if abs(wx - a.x) <= TILE * 0.6 and a.y - TILE - 12 - lift <= wy <= a.y + 10 and (best is None or a.y > best.y):
                best = a
        return best

    def nearest(self, reach: float) -> Avatar | None:
        best, best_d = None, reach * reach
        for a in self.avatars.values():
            d = (a.x - self.ws.x) ** 2 + (a.y - self.ws.y) ** 2
            if d < best_d:
                best, best_d = a, d
        return best

