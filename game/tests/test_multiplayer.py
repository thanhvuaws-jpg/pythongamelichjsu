"""Chơi nhiều người, phía game: nối thẳng tới bộ điều phối thật của máy chủ (chạy trong tiến trình, lưu trong bộ nhớ).

Kiểm tra trọn giao thức hai đầu: thấy nhau trên map, mời tổ đội, chia kinh nghiệm khi đánh quái, nói nhanh, bảng trạng
thái khi bấm vào người khác, lời mời ở góc trên phải, và thách đấu thật giữa hai máy trên cùng võ đài.
"""

# isort: skip_file
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pygame
import pytest
from test_playthrough import Bot, press_key, win_fight  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import net, outfit, platform_io, theme
from core.sprites import TILE
from scenes.fight import FIELD, FightScene
from scenes.playercard import PlayerCard
from scenes.pvp import PvpScene
from scenes.shop import ShopScene
from scenes.social import SocialScene
from scenes.world import WorldScene

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.world.hub import Hub, MemoryStore  # noqa: E402

PIO_WRITE = platform_io.write_save  # hàm thật, trước khi các fixture thay bằng hàm không ghi gì


class HubPipe:
    """Thay cho window.SKNet của trang chơi: gửi thẳng vào bộ điều phối, nhận tin vào hàng đợi."""

    def __init__(self, hub: Hub, uid: str, name: str):
        self.hub, self.uid = hub, uid
        self.inbox: list[str] = []
        asyncio.run(hub.connect(uid, name, self._recv))

    async def _recv(self, msg):
        self.inbox.append(json.dumps(msg))

    def send(self, raw: str):
        asyncio.run(self.hub.handle(self.uid, json.loads(raw)))

    def take(self) -> str:
        out = "[" + ",".join(self.inbox) + "]"
        self.inbox = []
        return out

    def status(self) -> str:
        return "on"


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    b = Bot()
    yield b
    net.use(net.Net(None))  # trả lại chế độ chơi một mình cho các test khác


class Ticking:
    """Đồng hồ giả: mỗi lần hỏi giờ thì trôi 60 ms, để bộ điều phối không coi tin của test là gửi dồn dập."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        self.now += 0.06
        return self.now


def setup(bot):
    hub = Hub(MemoryStore(), Ticking())
    me = net.Net(HubPipe(hub, "a", "An"))
    other = net.Net(HubPipe(hub, "b", "Bình"))
    net.use(me)
    bot.state.reset()
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    return hub, me, other, ws


def walk_other(other, ws, dx=TILE, gear=None):
    other.send({"t": "pos", "map": ws.level_id, "x": ws.x + dx, "y": ws.y, "f": "left", "m": False, "lv": 7,
                "gear": gear or {"giap": "giap_vay", "mu": "non_la", "vu_khi": "giao_dai"},
                "combat": {"hp": 260, "dmg": 1.6, "spd": 1.1, "skills": {"phong_lao": 1}}})


def test_solo_when_there_is_no_server(bot):
    net.use(net.Net(None))
    bot.state.reset()
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick(3)
    assert ws.mp.hud_tag() is None and not ws.mp.avatars
    press_key(bot, pygame.K_p)
    assert isinstance(bot.scenes.top, SocialScene), "Không có máy chủ vẫn mở được bảng, chỉ báo đang chơi một mình"
    bot.tick(2)


def test_players_see_each_other_dressed_as_they_are(bot):
    hub, me, other, ws = setup(bot)
    walk_other(other, ws)
    bot.tick(8)
    assert hub.people["a"].map == "man1", "Game gửi vị trí của mình lên"
    assert "b" in ws.mp.avatars
    av = ws.mp.avatars["b"]
    assert av.gear["mu"] == "non_la"
    items = ws.mp.items(int(ws.cam_x), int(ws.cam_y))
    assert any(it[2] is outfit.hero_cast(av.gear).walk["left"][0] for it in items), "Người khác hiện đúng bộ đồ của họ"
    assert "1 người cùng map" in ws.mp.hud_tag()


def test_party_invite_shared_exp_and_phrases(bot):
    hub, me, other, ws = setup(bot)
    walk_other(other, ws)
    bot.tick(6)
    other.invite("party", "a")
    bot.tick(2)
    assert me.invites and me.invites[0]["kind"] == "party"
    press_key(bot, pygame.K_p)
    social = bot.scenes.top
    assert isinstance(social, SocialScene)
    bot.tick(2)
    bot.press(social.group, "Đồng ý")
    bot.tick(2)
    assert me.party and {m["id"] for m in me.party["members"]} == {"a", "b"}
    press_key(bot, pygame.K_ESCAPE)
    # bạn hạ quái đứng gần: mình được chia một nửa
    exp0 = bot.state.exp + 1000 * bot.state.level
    walk_other(other, ws)
    other.send({"t": "kill", "mob": "Lính Tống", "exp": 40, "tiem": 12})
    bot.tick(2)
    assert bot.state.exp + 1000 * bot.state.level > exp0 and bot.state.tiem_nang >= 6
    # mình hạ quái: bạn nhận phần
    m = next(m for m in ws.mobs.mobs if m.kind == "mob")
    ws.mobs._fought(m, {"win": True})
    other.poll()
    assert any(e.get("t") == "share" for e in other.events)
    # nói nhanh
    other.send({"t": "say", "k": 1})
    bot.tick(2)
    assert ws.mp.bubbles["b"][0] == net.PHRASES[1]


def _click_avatar(bot, ws, uid):
    av = ws.mp.avatars[uid]
    bot.click((av.x - ws.cam_x, av.y - TILE / 2 - ws.cam_y))


def _both(bot, bot2, n=1):
    for _ in range(n):
        bot2.tick()
        bot.tick()


def _left_click(bot, pos):
    bot.tick(1, pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
    bot.scenes.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))


def test_clicking_a_player_opens_their_card(bot):
    hub, me, other, ws = setup(bot)
    walk_other(other, ws, gear={"giap": "giap_dong", "vu_khi": "dai_dao"})
    bot.tick(6)
    _click_avatar(bot, ws, "b")
    card = bot.scenes.top
    assert isinstance(card, PlayerCard) and card.peer["name"] == "Bình", "Bấm vào người chơi thì hiện bảng trạng thái của họ"
    assert card.peer["gear"]["vu_khi"] == "dai_dao"
    assert {b.label for b in card.group.buttons} >= {"Mời vào tổ đội", "Kết đồng minh", "Thách đấu"}
    bot.tick(3)
    bot.press(card.group, "Kết đồng minh")
    assert bot.scenes.top is ws
    other.poll()
    assert other.invites and other.invites[-1]["kind"] == "ally" and other.invites[-1]["from"] == "a"
    _click_avatar(bot, ws, "b")
    press_key(bot, pygame.K_ESCAPE)
    assert bot.scenes.top is ws


def test_invites_show_top_right_and_are_answered_by_mouse(bot):
    hub, me, other, ws = setup(bot)
    walk_other(other, ws)
    bot.tick(4)
    other.invite("party", "a")
    bot.tick(2)
    cards = ws.mp.invite_cards()
    assert len(cards) == 1 and cards[0][1].right == theme.WIDTH - 12, "Lời mời hiện ở góc trên bên phải"
    assert ws.mp.invites_bottom() > cards[0][1].bottom, "Khung chat thế giới dịch xuống dưới thẻ lời mời"
    ok = next(b for b in ws.mp.invite_btns if b.label == "Đồng ý")
    bot.click(ok.rect.center)
    bot.tick(2)
    assert me.party and {m["id"] for m in me.party["members"]} == {"a", "b"}
    assert not ws.path, "Bấm vào thẻ lời mời không làm nhân vật đi tới đó"
    assert not ws.mp.invite_cards()
    other.invite("ally", "a")
    bot.tick(2)
    no = next(b for b in ws.mp.invite_btns if b.label == "Từ chối")
    bot.click(no.rect.center)
    other.poll()
    assert not me.invites and not me.allies


def test_world_stays_live_while_a_panel_is_open(bot):
    hub, me, other, ws = setup(bot)
    walk_other(other, ws)
    bot.tick(4)
    press_key(bot, pygame.K_b)
    assert isinstance(bot.scenes.top, ShopScene)
    seen = hub.people["a"].seen
    walk_other(other, ws, dx=TILE * 3)
    bot.tick(15)
    assert hub.people["a"].seen > seen, "Đang mở túi đồ vẫn gửi vị trí, người khác không thấy mình biến mất"
    assert next(p for p in me.peers if p["id"] == "b")["x"] == round(ws.x + TILE * 3), "Danh sách người cùng map vẫn mới"
    other.invite("party", "a")
    bot.tick(2)
    assert me.invites and any("mời bạn vào tổ đội" in t["msg"] for t in bot.toasts.items), "Lời mời tới khi đang mở bảng vẫn được báo"


def test_duel_brings_both_real_players_to_the_arena(bot):
    hub, me, other, ws = setup(bot)
    walk_other(other, ws, gear={"giap": "giap_dong", "vu_khi": "dai_dao"})
    bot.tick(6)
    _click_avatar(bot, ws, "b")
    bot.press(bot.scenes.top.group, "Thách đấu")
    other.poll()
    inv = next(i for i in other.invites if i["kind"] == "duel")
    press_key(bot, pygame.K_b)  # đang xem túi đồ thì bạn nhận lời: vẫn vào trận ngay
    bag = bot.scenes.top
    other.answer(inv, True)
    bot.tick(2)
    duel = bot.scenes.top
    assert isinstance(duel, PvpScene) and duel.side == 0 and bot.scenes.stack[-2] is bag
    ghost = duel.ghost
    assert ghost.weapon == "dai_dao" and ghost.cast is outfit.hero_cast({"giap": "giap_dong", "vu_khi": "dai_dao"}, 4)
    assert ghost.max_hp == 260 and duel.player.x < ghost.x, "Người mời đứng bên trái"
    # máy của người kia: cảnh võ đài của chính họ, nối cùng bộ điều phối
    bot2 = Bot()
    bot2.state.reset()
    other.poll()
    start = next(e for e in other.events if e.get("t") == "pvp_start")
    theirs = PvpScene(bot2, start)
    theirs.net = other
    bot2.scenes.reset(theirs)
    assert theirs.side == 1 and theirs.room == duel.room and theirs.player.x > theirs.ghost.x
    duel.intro = theirs.intro = 0
    # người kia đi tới sát mình: trên máy mình cái bóng đi theo, không có bot nào điều khiển
    theirs.player.x, theirs.player.y = duel.player.x + 50, duel.player.y
    _both(bot, bot2, 12)
    assert abs(ghost.x - (duel.player.x + 50)) < 4 and abs(ghost.y - duel.player.y) < 4
    assert abs(theirs.ghost.x - duel.player.x) < 4
    # động tác của cái bóng chỉ để nhìn, không tự trừ máu của mình
    hp = duel.player.hp
    duel._replay({"k": "atk", "a": 0})
    duel._replay({"k": "cast", "sid": "xoay_kiem"})
    assert duel.player.hp == hp
    # chuột trái chém: máy kia tự trừ máu
    duel.player.attack_cd = 0
    _left_click(bot, (FIELD.centerx, FIELD.centery))
    bot2.tick()
    assert theirs.player.hp < theirs.player.max_hp, "Đòn trúng cái bóng được báo sang, máy bị đánh tự trừ máu"
    # đang né thì đòn báo sang không tính
    hp2 = theirs.player.hp
    _both(bot, bot2, 15)
    duel.player.attack_cd = 0
    duel.ghost.dodge_t = 0.0
    _left_click(bot, (FIELD.centerx, FIELD.centery))
    theirs.player.dodge_t = 0.2
    bot2.tick()
    assert theirs.player.hp == hp2, "Né kịp thì không mất máu"
    # Shift để né: máy kia thấy cái bóng của mình lướt đi
    _both(bot, bot2, 15)
    press_key(bot, pygame.K_LSHIFT)
    assert duel.player.dodge_t > 0
    bot.tick()
    bot2.tick()
    assert theirs.ghost.dodge_t > 0
    # thuốc không dùng được khi thách đấu
    potions = bot.state.potions
    press_key(bot, pygame.K_q)
    assert bot.state.potions == potions
    # hạ gục: máy chủ phân xử, cả hai cùng nhận kết quả
    _both(bot, bot2, 30)
    theirs.player.hp = 1.0
    duel.player.attack_cd = 0
    duel.ghost.dodge_t = 0.0
    _left_click(bot, (FIELD.centerx, FIELD.centery))
    _both(bot, bot2, 3)
    assert theirs.player.dead and duel.result and duel.result["win"] and theirs.result and not theirs.result["win"]
    assert duel.result_text()[0] == "CHIẾN THẮNG" and theirs.result_text()[0] == "THUA TRẬN"
    assert hub.store.duels == [("a", "b", True, "man1"), ("b", "a", False, "man1")]
    bot.press(duel.group, "Tiếp tục")
    assert bot.scenes.top is bag, "Đánh xong quay về đúng chỗ cũ"
    assert bot.state.duels_won == 1 and ws.mp.fight is None


def test_quitting_a_duel_gives_the_other_player_the_win(bot):
    hub, me, other, ws = setup(bot)
    walk_other(other, ws)
    bot.tick(4)
    me.invite("duel", "b")
    other.poll()
    other.answer(next(i for i in other.invites if i["kind"] == "duel"), True)
    bot.tick(2)
    duel = bot.scenes.top
    assert isinstance(duel, PvpScene)
    duel.group.buttons[0].click()  # Rút lui
    assert bot.scenes.top is ws
    other.poll()
    assert other.duel[-1]["t"] == "pvp_over" and other.duel[-1]["win"] and other.duel[-1]["why"] == "quit"
    assert hub.store.duels[0] == ("a", "b", False, "man1") and bot.state.duels_won == 0


def test_fight_controls_left_click_attacks_and_shift_dodges(bot):
    bot.state.reset()
    fight = FightScene(bot, [{"name": "Bù nhìn", "char": "Villager", "hp": 500}], "Thử")
    bot.scenes.reset(fight)
    fight.intro = 0
    p = fight.player
    _left_click(bot, (FIELD.centerx, FIELD.centery))
    assert p.attack_cd > 0, "Chuột trái trên sân là chém"
    press_key(bot, pygame.K_k)
    assert p.dodge_t <= 0, "K không còn là né"
    press_key(bot, pygame.K_LSHIFT)
    assert p.dodge_t > 0, "Shift để né"
    bot.tick(30)
    x = p.x
    bot.scenes.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(FIELD.right - 20, int(p.y)), button=3))
    bot.tick(10)
    assert p.x > x, "Giữ chuột phải để đi theo con trỏ"
    bot.scenes.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(FIELD.right - 20, int(p.y)), button=3))
    assert not fight.mouse_down



def test_messages_to_the_page_are_pure_ascii(monkeypatch):
    sent, saved = [], []

    class Pipe:
        def send(self, raw):
            sent.append(raw)

        def status(self):
            return "on"

    net.Net(Pipe()).send({"t": "pos", "realm": "Tân binh"})
    assert sent[0].isascii() and json.loads(sent[0])["realm"] == "Tân binh", "Chữ có dấu phải qua được cầu nối sang JavaScript"

    class Storage:
        @staticmethod
        def setItem(_key, value):
            saved.append(value)

    class Window:
        localStorage = Storage

    import core.platform_io as pio

    monkeypatch.setattr(pio, "IS_WEB", True)
    monkeypatch.setattr(pio, "_window", lambda: Window)
    monkeypatch.setattr(pio, "write_save", PIO_WRITE)
    pio.write_save({"ten": "Đường Lâm"})
    assert saved and saved[0].isascii() and json.loads(saved[0])["ten"] == "Đường Lâm"


class FakeChat:
    """Thay cho window.SKChat của trang chơi: ghi lại lần mở ô chat, trả các tin người chơi vừa gõ."""

    def __init__(self):
        self.opened: list[str] = []
        self.out: list[dict] = []

    def open(self, ch):
        self.opened.append(ch)

    def take(self):
        out, self.out = self.out, []
        return out


def test_chat_map_is_free_and_world_costs_quan(bot):
    from core import rpg

    hub = Hub(MemoryStore(), Ticking())
    chat = FakeChat()
    me = net.Net(HubPipe(hub, "a", "An"), chat)
    other = net.Net(HubPipe(hub, "b", "Bình"))
    net.use(me)
    st = bot.state
    st.reset()
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    walk_other(other, ws)
    bot.tick(4)
    press_key(bot, pygame.K_l)
    assert chat.opened == ["map"], "Bấm L mở ô gõ chat của trang chơi"
    st.quan = rpg.WORLD_CHAT_COST + 5
    chat.out = [{"ch": "map", "text": "  Chào   bạn  "}]
    bot.tick(3)
    other.poll()
    assert other.chat[-1]["ch"] == "map" and other.chat[-1]["text"] == "Chào bạn" and other.chat[-1]["name"] == "An"
    assert st.quan == rpg.WORLD_CHAT_COST + 5, "Chat với người cùng map không mất gì"
    assert ws.mp.bubbles.get("me"), "Lời chat hiện trên đầu người nói"
    chat.out = [{"ch": "world", "text": "Ai cùng đánh Đông Khê không?"}]
    bot.tick(3)
    other.poll()
    assert other.chat[-1]["ch"] == "world" and st.quan == 5, "Chat thế giới trừ quan"
    assert any(c["ch"] == "world" and c["mine"] for c in me.chat)
    ws.mp.world_at = -1e9
    chat.out = [{"ch": "world", "text": "Thêm một tin nữa"}]
    bot.tick(3)
    other.poll()
    assert st.quan == 5 and other.chat[-1]["text"] != "Thêm một tin nữa", "Thiếu quan thì không gửi được"


def test_chat_without_the_web_page_only_shows_a_notice(bot):
    net.use(net.Net(None))
    bot.state.reset()
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    press_key(bot, pygame.K_l)
    assert bot.scenes.top is ws and not ws.mp.send_chat("map", "xin chào")


def test_others_see_me_fighting_a_mob_while_the_fight_screen_is_open(bot):
    hub, me, other, ws = setup(bot)
    walk_other(other, ws)
    bot.tick(4)
    mob = next(m for m in ws.mobs.mobs if m.kind == "mob" and not m.data.get("water"))
    ws.x, ws.y = mob.x, mob.y + TILE * 0.5
    bot.tick()
    press_key(bot, pygame.K_f)
    fight = bot.scenes.top
    assert isinstance(fight, FightScene) and fight.background is not None
    bot.tick(12)  # trận che map nhưng vẫn gửi vị trí, kèm đang đánh ai
    assert hub.people["a"].fight and hub.people["a"].fight["name"] == mob.data["name"]
    walk_other(other, ws)
    other.poll()
    seen = next(p for p in other.peers if p["id"] == "a")
    assert seen["fight"]["name"] == mob.data["name"] and abs(seen["fight"]["x"] - mob.x) <= 1
    win_fight(bot, fight)
    assert ws.mp.fight is None
    bot.tick(6)
    assert hub.people["a"].fight is None, "Đánh xong thì thôi báo"


def test_i_see_another_player_swinging_at_a_mob(bot):
    hub, me, other, ws = setup(bot)
    other.send({"t": "pos", "map": ws.level_id, "x": ws.x + TILE, "y": ws.y, "f": "left", "m": False, "lv": 7,
                "gear": {"vu_khi": "giao_dai"}, "fight": {"name": "Lính Tống", "x": ws.x + TILE * 2, "y": ws.y}})
    bot.tick(8)
    av = ws.mp.avatars["b"]
    assert av.data["fight"]["name"] == "Lính Tống" and av.facing == "right"
    bot.tick(10)  # vẽ cảnh vung vũ khí và dòng "đang đánh"

