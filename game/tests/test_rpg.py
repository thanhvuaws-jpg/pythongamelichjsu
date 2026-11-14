"""Kiểm thử lối chơi nhập vai: cấp, tiềm năng, cảnh giới, đồ, quái trên map, kẻ canh mật thư, thách đấu, chiến mã, báo cáo."""

# isort: skip_file
from __future__ import annotations

import random

import pygame
import pytest
from test_playthrough import Bot, play_story, press_key, win_fight  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import chienma, platform_io, progression, rpg
from core.sprites import ROOT, TILE
from scenes.fight import STATIC_CASTS, FightScene
from scenes.mobs import _reachable
from scenes.shop import ShopScene
from scenes.skills import SkillsScene
from scenes.story import StoryScene
from scenes.world import WorldScene

UI = ROOT / "ui"


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    return Bot()


def world(bot, level="man1"):
    bot.state.reset()
    ws = WorldScene(bot, level, "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    return ws


# ----- dữ liệu -----
def test_every_item_and_skill_has_an_icon():
    for iid in rpg.ITEMS:
        assert (UI / f"item_{iid}.png").exists(), iid
    for sid in progression.SKILLS:
        assert (UI / f"sk_{sid}.png").exists(), sid
    assert set(rpg.SLOT_NAMES) >= {i["slot"] for i in rpg.ITEMS.values()}
    assert {"giay", "gang"} <= {i["slot"] for i in rpg.ITEMS.values()}, "Phải có giày và găng"


def test_mobs_match_the_era_of_each_zone(bot):
    st = bot.state
    relics = {r["id"]: lid for lid in st.order for r in st.levels[lid]["relics"]}
    assert set(rpg.ZONE_MOBS) == set(relics), "Di tích nào cũng có quái, không có vùng lạ"
    era = {"man1": ("nam_han", "tong", "nguyen"), "man2": ("minh",), "man3": ("don_bot", "lo_cot")}
    for rid, mobs in rpg.ZONE_MOBS.items():
        for mid in mobs:
            assert any(k in mid for k in era[relics[rid]]), (rid, mid)
            m = rpg.MOBS[mid]
            assert m["char"] in STATIC_CASTS or (ROOT / "char" / m["char"]).exists()
            assert m["chief_char"] in STATIC_CASTS or (ROOT / "char" / m["chief_char"]).exists()
    # 1945 – 1954: không có quái là người
    for rid, lid in relics.items():
        if lid == "man3":
            assert all(rpg.MOBS[m].get("object") for m in rpg.ZONE_MOBS[rid])
    assert rpg.BOSSES["man3"].get("object")
    # Bạch Đằng 938 là quân Nam Hán, không phải quân Nguyên
    assert all("nam_han" in m for m in rpg.ZONE_MOBS["r_trang_kenh"])


# ----- cấp, tiềm năng, cảnh giới -----
def test_levels_are_capped_until_breakthrough(bot):
    st = bot.state
    st.reset()
    msgs = st.gain(exp=rpg.exp_need(1) + 5, tiem=20, quan=7)
    assert st.level == 2 and st.tiem_nang == 20 and st.quan == 7 and msgs
    st.gain(exp=10 ** 6)
    assert st.level == st.level_cap() == 10, "Tân binh dừng ở cấp 10"
    assert not st.can_break(), "Chưa đủ tinh hoa thì chưa đột phá được"
    st.memory_seen.update({f"d{i}" for i in range(4)})
    st.doc_done.update({"a", "b"})
    assert st.essence() == 8 and st.can_break()
    hp = st.max_hp()
    assert st.breakthrough() and st.realm_name() == "Sử sinh" and st.level_cap() == 20
    assert st.max_hp() > hp, "Đột phá thì chỉ số nhân thêm"


def test_gear_changes_stats_and_saves(bot):
    st = bot.state
    st.reset()
    assert st.gear == {"vu_khi": "gay_tre", "giap": "ao_vai", "mu": "khan_chit"} and st.potions == 2
    assert st.buy("ung_da") == "Cần cấp 12."
    st.quan = 50
    assert st.buy("giay_vai") == "Cần cấp 6."
    st.level = 6
    assert "thiếu" in st.buy("giay_vai")
    st.quan = 500
    speed = st.speed_mult()
    assert st.buy("giay_vai") is None and st.gear["giay"] == "giay_vai" and st.quan == 380
    assert st.speed_mult() == pytest.approx(speed + 0.06)
    assert st.buy("giay_vai") == "Đã có món này rồi."
    assert st.buy("thuoc_nam") is None and st.potions == 3
    st.equip("giay_vai")
    assert "giay" not in st.gear, "Bấm lần nữa thì cởi ra"
    st.equip("giay_vai")
    saved = st.to_dict()
    st.reset()
    st.from_dict(saved)
    assert st.gear["giay"] == "giay_vai" and st.level == 6 and st.potions == 3


def test_old_save_gets_rewards_for_stamped_relics(bot):
    st = bot.state
    st.reset()
    old = st.to_dict()
    old.pop("rpg")
    old["stamps"] = ["r_duong_lam", "r_trang_kenh"]
    st.from_dict(old)
    assert sorted(st.reports) == ["r_duong_lam", "r_trang_kenh"] and "gay_tre" in st.inventory
    done = st.report()
    assert len(done) == 2 and st.quan == 2 * rpg.RELIC_QUAN and not st.reports


# ----- quái trên map -----
@pytest.mark.parametrize("level", ["man1", "man2", "man3"])
def test_mobs_stand_where_the_player_can_walk(bot, level):
    ws = world(bot, level)
    reach = _reachable(ws.world)
    camps = [m for m in ws.mobs.mobs if m.kind == "mob"]
    assert len(camps) >= len(ws.relics) * 2, "Mỗi di tích phải có một toán quái"
    for m in ws.mobs.mobs:
        assert (int(m.x // TILE), int(m.y // TILE)) in reach, (m.data["name"], m.x, m.y)
    guards = [m for m in ws.mobs.mobs if m.kind != "mob"]
    assert sum(m.kind == "boss" for m in guards) == 1, "Mỗi màn đúng một trùm"
    assert all(m.scroll is not None and m.scroll.kind == "scroll" for m in guards)


def test_fight_a_mob_on_the_map(bot):
    ws = world(bot)
    st = bot.state
    m = next(m for m in ws.mobs.mobs if m.kind == "mob")
    ws.x, ws.y = m.x, m.y + TILE * 0.5
    bot.tick()
    assert ws.mobs.nearest() is m
    press_key(bot, pygame.K_f)
    fight = bot.scenes.top
    assert isinstance(fight, FightScene) and fight.foes[0].char == m.data["char"]
    win_fight(bot, fight)
    assert bot.scenes.top is ws and st.mobs_killed == 1 and st.exp > 0 and st.tiem_nang > 0 and st.quan > 0
    assert not m.alive and not ws.mobs.visible(m)
    bot.tick(int(rpg.RESPAWN / (1 / 30)) + 2)
    assert m.alive, "Quái mọc lại sau một lúc"


def test_losing_sends_player_home_and_weakens_the_guard(bot):
    ws = world(bot)
    st = bot.state
    guard = next(m for m in ws.mobs.mobs if m.kind == "guard")
    ws.mobs._fought(guard, {"win": False})
    assert st.boss_tries[guard.key] == 1
    assert (ws.x - ws.mentor.x) ** 2 + (ws.y - ws.mentor.y - TILE) ** 2 < 4
    full = rpg.fight_spec(guard.data, False)
    weak = rpg.fight_spec(guard.data, False, st.boss_ease(guard.key))
    assert weak["hp"] < full["hp"] and weak["power"] < full["power"]
    st.boss_tries[guard.key] = 99
    assert st.boss_ease(guard.key) == pytest.approx(0.45), "Trùm yếu đi có giới hạn"


def test_reward_shrinks_on_weak_mobs():
    mob = rpg.MOBS["linh_nam_han"]
    full = rpg.mob_reward(mob, 1, random.Random(1))
    low = rpg.mob_reward(mob, 20, random.Random(1))
    assert low[0] < full[0] and low[1] < full[1]


# ----- thách đấu -----
def test_challenger_can_be_refused_or_accepted(bot):
    ws = world(bot)
    st = bot.state
    st.level = 4
    random.seed(3)
    ws.mobs.duel_t = 0.01
    bot.tick(2)
    d = ws.mobs.duel
    assert d and d["state"] == "come"
    d["actor"].x, d["actor"].y = ws.x + 20, ws.y
    bot.tick()
    assert d["state"] == "ask"
    press_key(bot, pygame.K_n)
    assert d["state"] == "leave" and bot.scenes.top is ws
    bot.tick(120)
    assert ws.mobs.duel is None
    ws.mobs.duel_t = 0.01
    bot.tick(2)
    d = ws.mobs.duel
    d["actor"].x, d["actor"].y = ws.x + 20, ws.y
    bot.tick()
    press_key(bot, pygame.K_y)
    win_fight(bot, bot.scenes.top)
    assert st.duels_won == 1 and st.quan > 0


def test_walking_away_counts_as_fleeing(bot):
    ws = world(bot)
    bot.state.level = 3
    ws.mobs._start_duel()
    d = ws.mobs.duel
    d["state"] = "ask"
    d["actor"].x, d["actor"].y = ws.x + TILE * 6, ws.y
    bot.tick()
    assert d["state"] == "leave"


# ----- chiến mã -----
def test_summon_war_horse(bot):
    ws = world(bot)
    press_key(bot, pygame.K_h)
    assert ws.mode == "walk", "Chưa đủ cấp thì chưa gọi được chiến mã"
    bot.state.level = rpg.HORSE_LEVEL
    press_key(bot, pygame.K_h)
    assert ws.mode == "horse" and ws.horse_imgs is chienma.views()
    x = ws.x
    ws._move(1, 0, 0.1)
    assert ws.x - x > 0
    press_key(bot, pygame.K_h)
    assert ws.mode == "walk" and ws.horse_imgs is ws.plain_horse


# ----- lò rèn, túi đồ, tu luyện -----
def test_smith_shop_and_bag(bot):
    ws = world(bot)
    st = bot.state
    smith = next(a for a in ws.actors if a.kind == "smith")
    assert not ws.map.blocked(int(smith.x // TILE), int(smith.y // TILE))
    st.quan = 100
    st.level = 3
    ws.x, ws.y = smith.x, smith.y + TILE * 0.6
    ws.interact(smith)
    shop = bot.scenes.top
    assert isinstance(shop, ShopScene) and shop.shop
    bot.press(shop.group, "Mua (60)")
    assert st.gear["vu_khi"] == "dao_sat" and st.quan == 40
    bot.press(shop.group, "Túi đồ")
    bag = bot.scenes.top
    assert isinstance(bag, ShopScene) and not bag.shop
    assert not [b for b in bag.group.buttons if b.label.startswith("Mua")], "Túi đồ không bán"
    bot.press(bag.group, "Mặc vào")
    assert st.gear["vu_khi"] == "gay_tre"
    press_key(bot, pygame.K_b)
    assert bot.scenes.top is ws


def test_skills_page_breakthrough_button(bot):
    st = bot.state
    st.reset()
    st.gain(exp=10 ** 6)
    st.memory_seen.update({f"d{i}" for i in range(8)})
    sc = SkillsScene(bot)
    bot.scenes.reset(sc)
    bot.tick()
    bot.press(sc.group, "Đột phá")
    assert st.realm == 1


def test_potion_heals_during_fight(bot):
    ws = world(bot)
    fight = FightScene(bot, [{"name": "Bù nhìn", "char": "Villager3", "hp": 30, "power": 0.1, "speed": 80}], "Thử", backdrop=bot.screen)
    bot.scenes.push(fight)
    fight.intro = 0
    fight.player.hp = 10
    potions = bot.state.potions
    press_key(bot, pygame.K_q)
    assert fight.player.hp > 10 and bot.state.potions == potions - 1
    assert ws is not None


# ----- báo cáo già làng -----
def test_report_to_the_elder(bot):
    ws = world(bot)
    st = bot.state
    relic = ws.relics[0]
    st.finish_relic(relic)
    assert st.reports == [relic["id"]] and "báo cáo" in ws._current()[0]
    ws.x, ws.y = ws.mentor.x, ws.mentor.y + TILE * 0.6
    ws.interact(ws.mentor)
    assert isinstance(bot.scenes.top, StoryScene)
    play_story(bot)
    assert not st.reports and st.quan == rpg.RELIC_QUAN and st.tiem_nang == rpg.RELIC_TIEM
    assert bot.scenes.top is ws


def test_memories_give_essence_but_the_intro_does_not(bot):
    st = bot.state
    st.reset()
    bot.scenes.reset(StoryScene(bot, st.sources["intro"]))
    play_story(bot)
    assert st.essence() == 0, "Lời dẫn đầu game không phải hồi ức của di tích"
    memory = next(d for d in st.index["dialogues"].values() if any(n.get("memory") for n in d["nodes"]))
    bot.scenes.reset(StoryScene(bot, memory))
    play_story(bot)
    assert st.essence() == rpg.ESSENCE["memory"] and memory["id"] in st.memory_seen
