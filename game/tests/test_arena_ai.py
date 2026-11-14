"""Kiểm thử võ đài nâng cấp: chiêu mới của bot có báo trước và trúng đúng chỗ, bot khôn biết né đạn và tránh chông."""

# isort: skip_file
from __future__ import annotations

import math
import random

import pygame
import pytest
from test_playthrough import Bot  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import platform_io, progression
from scenes.arena import ArenaScene
from scenes.fight import DODGE_CD, RAIN_DELAY, FightScene


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    b = Bot()
    b.state.reset()
    yield b


def fight(bot, skills, smart=0.5, style="melee", hp=400, ai=True):
    spec = {"name": "Thử", "char": "Knight", "hp": hp, "power": 1.0, "speed": 200, "skills": skills, "aggro": 0.0, "smart": smart, "style": style}
    sc = FightScene(bot, [spec], "Thử chiêu")
    bot.scenes.reset(sc)
    sc.intro = 0
    sc.player.max_hp = sc.player.hp = 500
    if not ai:
        sc._bot = lambda f, dt: None  # thử riêng từng chiêu: bot đứng yên, không tự đánh thêm
    return sc, sc.foes[0]


def run(sc, seconds, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        sc.update(dt)


def test_every_bot_skill_is_castable_and_listed(bot):
    for sid in progression.BOT_SKILLS:
        sc, foe = fight(bot, [sid])
        foe.x, foe.y = sc.player.x + 250, sc.player.y
        foe.aim = (sc.player.x, sc.player.y)
        assert sc.cast(foe, sid), sid
        run(sc, 2.0)
        assert foe.cds[sid] > 0
    ex = bot.state.extras["arena"]
    assert len(ex) >= 9
    for b in ex:
        assert all(progression.skill_info(s) for s in b.get("skills", [])), b["id"]
    assert sum(1 for b in ex if set(b.get("skills", [])) & set(progression.BOT_SKILLS)) >= 6


def test_arrow_rain_marks_then_hits_only_who_stays(bot):
    sc, foe = fight(bot, ["mua_ten"], ai=False)
    p = sc.player
    foe.x = p.x + 300
    sc._sk_mua_ten(foe, p, 1.0, 1)
    assert len(sc.zones) == 3, "Phải có vòng báo trước"
    z = sc.zones[0]
    p.x, p.y = z["x"], z["y"]
    hp = p.hp
    run(sc, RAIN_DELAY * 0.5)
    assert p.hp == hp, "Chưa tới lúc tên rơi"
    run(sc, RAIN_DELAY)
    assert p.hp < hp and not sc.zones


def test_shockwave_is_dodged_with_iframes(bot):
    sc, foe = fight(bot, ["chan_dia"], ai=False)
    p = sc.player
    foe.x, foe.y = p.x + 200, p.y
    sc._sk_chan_dia(foe, p, 1.0, 1)
    hp = p.hp
    run(sc, 0.8)
    assert p.hp < hp, "Đứng yên thì trúng sóng"
    sc2, foe2 = fight(bot, ["chan_dia"], ai=False)
    p2 = sc2.player
    foe2.x, foe2.y = p2.x + 200, p2.y
    sc2._sk_chan_dia(foe2, p2, 1.0, 1)
    hp2 = p2.hp
    for _ in range(30):
        w = sc2.waves[0] if sc2.waves else None
        if w and math.hypot(p2.x - w["x"], p2.y - w["y"]) - w["r"] < 60 and p2.dodge_cd <= 0:
            sc2.dodge(p2, w["x"] - p2.x, w["y"] - p2.y)  # lướt xuyên qua sóng về phía tâm
        sc2.update(1 / 30)
    assert p2.hp == hp2, "Lướt xuyên qua sóng đúng lúc thì không mất máu"


def test_charge_follows_the_telegraphed_line(bot):
    sc, foe = fight(bot, ["xung_phong"])
    p = sc.player
    foe.x, foe.y = p.x + 320, p.y
    foe.aim = (p.x, p.y)
    hp = p.hp
    sc._sk_xung_phong(foe, p, 1.0, 1)
    run(sc, 0.6)
    assert p.hp < hp and foe.x < p.x + 120


def test_smoke_reappears_behind_and_strikes(bot):
    sc, foe = fight(bot, ["khoi_mu"])
    p = sc.player
    foe.x, foe.y = p.x + 200, p.y
    hp = p.hp
    sc._sk_khoi_mu(foe, p, 1.0, 1)
    assert foe.x < p.x, "Hiện ra sau lưng"
    run(sc, 1.0)
    assert p.hp < hp


def test_combo_hits_three_times(bot):
    sc, foe = fight(bot, ["lien_hoan"])
    p = sc.player
    foe.x, foe.y = p.x + 60, p.y
    hits = []
    real = sc._hurt
    sc._hurt = lambda t, a, s=None, k=0.0: (hits.append(a), real(t, a, s, k))
    sc._sk_lien_hoan(foe, p, 1.0, 1)
    run(sc, 1.0)
    assert len(hits) >= 3


def test_smart_bot_dodges_incoming_lance_more_than_dumb_bot(bot):
    def dodges(smart):
        random.seed(3)
        count = 0
        for _ in range(12):
            sc, foe = fight(bot, [], smart=smart)
            p = sc.player
            foe.x, foe.y = p.x + 330, p.y
            sc._sk_phong_lao(p, foe, 1.0, 1)
            for _ in range(15):
                sc.update(1 / 30)
            count += foe.dodge_cd > DODGE_CD - 1.0
        return count

    assert dodges(0.95) > dodges(0.05)


def test_bot_steps_around_caltrops(bot):
    sc, foe = fight(bot, [], smart=0.8)
    p = sc.player
    foe.x, foe.y = p.x + 260, p.y
    for k in range(3):
        sc.traps.append({"x": p.x + 160, "y": p.y - 30 + k * 30, "team": 0, "src": p, "dmg": 10, "t": 1.0})
    hp = foe.hp
    run(sc, 3.0)
    assert foe.hp == hp or foe.slow_t == 0, "Bot khôn phải đi vòng qua chông"


@pytest.mark.parametrize("bot_id", ["b_vo_su", "b_thich_khach", "b_tho_san", "b_xa_thu", "b_do_vat", "b_cao_thu"])
def test_full_fights_run_without_errors(bot, bot_id):
    spec = next(b for b in bot.state.extras["arena"] if b["id"] == bot_id)
    random.seed(bot_id)
    arena = ArenaScene(bot)
    bot.scenes.reset(arena)
    arena._fight(spec)
    sc = bot.scenes.top
    assert isinstance(sc, FightScene)
    for _ in range(int(25 * 30)):
        sc.update(1 / 30)
        if sc.result:
            break
    sc.draw(bot.screen)
    assert sc.foes[0].smart == spec["smart"] and sc.foes[0].style == spec["style"]
    bot.tick(2)
