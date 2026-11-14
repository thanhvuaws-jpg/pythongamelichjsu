"""Kiểm thử ngoại hình theo đồ, vũ khí có hoạt ảnh, quái vẽ riêng (kỵ binh, xe tăng, ụ súng) và vùng luyện."""

# isort: skip_file
from __future__ import annotations

import math

import pygame
import pytest
from test_playthrough import Bot, play_question, play_story, press_key, win_fight  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import mobart, outfit, platform_io, rpg, weapons
from core.sprites import ROOT, TILE
from core.tilemap import WATER
from scenes.field import FieldScene
from scenes.fight import REACH, FightScene
from scenes.mobs import _reachable
from scenes.world import WorldScene

DUMMY = {"name": "Bù nhìn", "char": "Villager3", "hp": 500, "power": 0.0, "speed": 0, "aggro": 0.0}


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    return Bot()


def _pixels(img):
    return [tuple(img.get_at((x, y))) for y in range(img.get_height()) for x in range(img.get_width())]


# ----- ngoại hình theo đồ -----
def test_clothes_change_the_look(bot):
    plain = outfit.hero_cast({}, 1)
    looks = [outfit.hero_cast({"giap": a, "mu": m}, 1).walk["down"][0] for a, m in
             (("ao_vai", "khan_chit"), ("giap_vay", "mu_sat"), ("giap_bong", "non_la"), ("giap_dong", "mu_da"))]
    seen = {tuple(_pixels(img)) for img in looks}
    assert len(seen) == 4, "Mỗi bộ đồ phải trông khác nhau"
    assert tuple(_pixels(plain.walk["down"][0])) not in seen
    boots = outfit.hero_cast({"giap": "ao_vai", "giay": "ung_da", "gang": "gang_sat"}, 1).walk["down"][0]
    assert _pixels(boots) != _pixels(looks[0]), "Giày và găng cũng phải hiện lên"
    assert outfit.hero_cast({"giap": "ao_vai"}, 4) is outfit.hero_cast({"giap": "ao_vai", "vu_khi": "dao_sat"}, 4), "Vũ khí vẽ riêng"


def test_world_and_fight_use_the_outfit(bot):
    st = bot.state
    st.reset()
    st.gear = {"giap": "giap_vay", "mu": "non_la", "vu_khi": "giao_dai"}
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick()
    assert ws.player_cast is outfit.hero_cast(st.gear)
    items = ws._player_items()
    assert len(items) == 2, "Người chơi cầm vũ khí đang trang bị"
    st.gear["mu"] = "mu_sat"
    ws.on_resume(None)
    assert ws.player_cast is outfit.hero_cast(st.gear), "Thay đồ xong quay lại map thì ngoại hình đổi ngay"
    fight = FightScene(bot, [DUMMY], "Thử", backdrop=bot.screen)
    assert fight.player.cast is outfit.hero_cast(st.gear, 4) and fight.player.weapon == "giao_dai"


# ----- vũ khí -----
def test_every_weapon_has_art_and_a_way_to_strike(bot):
    for iid, item in rpg.ITEMS.items():
        if item["slot"] != "vu_khi":
            continue
        assert weapons.image(iid, 4) is not None, iid
        held = weapons.held_sprite(iid, "right", 4)
        assert held and held[0].get_width() > 0
        moves = {weapons.style(iid)["move"]}
        assert moves <= {"swing", "thrust", "cleave", "shoot"}
    for path in set(weapons.ART.values()) - {None}:
        assert (ROOT / path).exists(), path
    a0, _ = weapons.swing("kiem_thep", "right", 0.0)
    a1, _ = weapons.swing("kiem_thep", "right", 1.0)
    assert a0 > a1 + 150, "Chém là vung một vòng cung"
    _, push = weapons.swing("giao_dai", "right", 0.5)
    assert push > 0.3, "Giáo đâm tới"


def _duel(bot, weapon, foe_dx):
    st = bot.state
    st.reset()
    st.gear = {"vu_khi": weapon} if weapon else {}
    fight = FightScene(bot, [DUMMY], "Thử", backdrop=bot.screen)
    bot.scenes.reset(fight)
    fight.intro = 0
    fight._bot = lambda f, dt: None  # bù nhìn đứng yên, không né
    foe = fight.foes[0]
    foe.x, foe.y = fight.player.x + foe_dx, fight.player.y
    return fight, foe


def test_bows_and_crossbows_shoot_real_arrows(bot):
    fight, foe = _duel(bot, "no_go", 400)
    fight.attack(fight.player)
    assert len(fight.shots) == 1, "Nỏ bắn ra mũi tên"
    for _ in range(30):
        bot.tick()
    assert foe.hp < foe.max_hp, "Mũi tên bay tới trúng đối thủ ở xa"


def test_long_weapons_reach_further(bot):
    gap = REACH * 1.2
    fight, foe = _duel(bot, None, gap)
    fight.attack(fight.player)
    assert foe.hp == foe.max_hp, "Tay không thì không với tới"
    fight, foe = _duel(bot, "giao_dai", gap)
    fight.attack(fight.player)
    assert foe.hp < foe.max_hp, "Giáo dài với tới"
    fight, foe = _duel(bot, "dai_dao", gap)
    fight.attack(fight.player)
    assert foe.hp < foe.max_hp and fight.fx.shake_power > 0, "Đại đao quét rộng, rung màn hình"


def test_weapon_animation_draws_every_phase(bot):
    fight, _foe = _duel(bot, "bao_kiem", 60)
    fight.attack(fight.player)
    for _ in range(10):
        bot.tick()  # vẽ cả lúc đang vung lẫn lúc cầm


# ----- quái vẽ riêng -----
@pytest.mark.parametrize("char", sorted(mobart.FACTORIES))
def test_drawn_mobs_have_every_frame(bot, char):
    c = mobart.cast(char, 4)
    for d in ("down", "up", "left", "right"):
        assert len(c.walk[d]) == 4 and c.attack[d].get_width() > 0
    assert c.dead.get_width() > 0
    fight = FightScene(bot, [dict(DUMMY, char=char)], "Thử", backdrop=bot.screen)
    bot.scenes.reset(fight)
    bot.tick(3)
    assert fight.foes[0].anchored == (char not in ("KyBinhMongCo", "TuongKyMongCo", "KyBinhMinh", "TuongKyMinh")), "Cỗ máy, thuyền, công sự không bị đẩy lùi"


def test_no_human_mobs_in_1945_1954():
    for fid, f in rpg_fields().items():
        if f["parent"] == "man3":
            mobs = {m for camp in f["camps"].values() for m in camp}
            assert all(rpg.MOBS[m].get("object") for m in mobs), fid
            assert rpg.ELITES[fid].get("object")


def rpg_fields():
    import json
    from core.state import CONTENT_DIR

    return json.loads((CONTENT_DIR / "fields.json").read_text(encoding="utf-8"))


# ----- vùng luyện -----
def _done_all(st):
    for lid in st.order:
        for q in st.engine(lid).quests:
            for o in q["objectives"]:
                st.progress.completed_objectives.add(o["id"])


@pytest.mark.parametrize("fid", sorted(rpg_fields()))
def test_field_map_is_playable(bot, fid):
    st = bot.state
    st.reset()
    f = st.fields[fid]
    assert f["requires"] in st.index["relics"], "Vùng luyện phải gắn với một di tích có thật trong game"
    for line in f["elder"]["lines"][:-1]:
        for c in line.get("cite", []):
            assert c in st.sources["citations"], c
    fs = FieldScene(bot, fid)
    bot.scenes.reset(fs)
    bot.tick(2)
    reach = _reachable(fs.world)
    for m in fs.mobs.mobs:
        tile = (int(m.x // TILE), int(m.y // TILE))
        if m.data.get("water"):  # thuyền, tàu neo ngoài bờ một ô: đứng ở mép bờ là với tới
            assert fs.map.get(*tile) == WATER, (fid, m.data["name"])
            assert any((tile[0] + 2 * dx, tile[1] + 2 * dy) in reach for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))), (fid, m.data["name"])
        else:
            assert tile in reach, (fid, m.data["name"])
    assert len(fs.mobs.mobs) == sum(len(c) for c in fs.field["camps"].values()) + 1, "Trại nào cũng đủ quân"
    assert sum(m.kind == "elite" for m in fs.mobs.mobs) == 1
    assert len(fs.mobs.mobs) >= 8
    for a in fs.actors:
        assert (int(a.x // TILE), int(a.y // TILE)) in reach or a.kind == "portal", (fid, a.kind)


def test_gate_opens_after_learning_then_field_then_back(bot):
    st = bot.state
    st.reset()
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    gate = next(a for a in ws.actors if a.kind == "fieldgate")
    assert (int(gate.x // TILE), int(gate.y // TILE)) in _reachable(ws.world)
    ws.x, ws.y = gate.x, gate.y + TILE * 0.6
    ws.interact(gate)
    assert ws.warp is None and ws.bubble, "Chưa học xong di tích thì đường chưa mở"
    _done_all(st)
    ws.interact(gate)
    for _ in range(60):
        bot.tick()
    fs = bot.scenes.top
    assert isinstance(fs, FieldScene) and fs.field_id == gate.data["id"]
    # nghe chuyện, trả lời câu hỏi
    fs.x, fs.y = fs.mentor.x, fs.mentor.y + TILE * 0.6
    fs.interact(fs.mentor)
    play_story(bot)
    play_question(bot, fs.field["elder"]["question"])
    assert bot.scenes.top is fs and fs.log().get("talk") and st.quan >= rpg.FIELD_TALK_REWARD[2]
    # hạ kẻ mạnh nhất vùng: thưởng, rồi một lúc lại xuất hiện
    elite = fs._elite()
    fs.x, fs.y = elite.x, elite.y + TILE * 0.5
    press_key(bot, pygame.K_f)
    win_fight(bot, bot.scenes.top)
    assert fs.log()["elite"] == 1 and not elite.alive
    bot.tick(int(rpg.ELITE_RESPAWN * 30) + 2)
    assert elite.alive
    # về cổng: trở lại map chính đúng chỗ biển chỉ đường
    fs.x, fs.y = fs.portal.x, fs.portal.y - 10
    for _ in range(60):
        bot.tick()
    back = bot.scenes.top
    assert isinstance(back, WorldScene) and not isinstance(back, FieldScene) and back.level_id == "man1"
    assert math.hypot(back.x - gate.x, back.y - gate.y) < TILE * 2


def test_every_mob_teaches_a_line_of_history(bot):
    st = bot.state
    assert set(rpg.MOB_FACTS) == set(rpg.MOBS), "Loại quái nào cũng có một dòng sử"
    for mid, (text, cite) in rpg.MOB_FACTS.items():
        assert text and cite in st.sources["citations"], mid
    st.reset()
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick()
    m = next(m for m in ws.mobs.mobs if m.kind == "mob")
    ws.mobs._fought(m, {"win": True})
    assert m.id in st.bestiary
    saved = st.to_dict()
    st.reset()
    st.from_dict(saved)
    assert m.id in st.bestiary


def test_bestiary_lists_every_mob_and_opens_pages(bot):
    from scenes.bestiary import ORDER, BestiaryScene

    assert sorted(mid for _e, mid in ORDER) == sorted(rpg.MOBS), "Sổ có đủ mọi loại quái, mỗi loại một trang"
    st = bot.state
    st.reset()
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick()
    press_key(bot, pygame.K_g)
    sc = bot.scenes.top
    assert isinstance(sc, BestiaryScene)
    bot.tick(2)
    st.bestiary.update(rpg.MOBS)
    bot.tick(2)  # vẽ được cả khi mọi trang đã mở
    press_key(bot, pygame.K_g)
    assert bot.scenes.top is ws


def test_boats_can_be_fought_from_the_shore(bot):
    st = bot.state
    st.reset()
    fs = FieldScene(bot, "f_chuong_duong")
    bot.scenes.reset(fs)
    bot.tick(2)
    boat = next(m for m in fs.mobs.mobs if m.data.get("water"))
    reach = _reachable(fs.world)
    tx, ty = int(boat.x // TILE), int(boat.y // TILE)
    shore = next((tx + 2 * dx, ty + 2 * dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (tx + 2 * dx, ty + 2 * dy) in reach)
    fs.x, fs.y = shore[0] * TILE + TILE / 2, shore[1] * TILE + TILE - 8
    bot.tick()
    assert fs.mobs.nearest() is boat, "Đứng ở mép bờ là đánh được thuyền neo ngoài sông"
    press_key(bot, pygame.K_f)
    assert isinstance(bot.scenes.top, FightScene) and bot.scenes.top.foes[0].anchored


def test_no_bach_dang_stakes_outside_bach_dang(bot):
    """Cọc gỗ trên sông là dấu riêng của trận Bạch Đằng, các vùng luyện khác không được có."""
    for fid in bot.state.fields:
        fs = FieldScene(bot, fid)
        assert not [w for w in fs.world.on_water if w[0] == "stake"], fid
