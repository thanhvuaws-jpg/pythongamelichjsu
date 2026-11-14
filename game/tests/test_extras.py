"""Kiểm thử phần chơi thêm: điểm kỹ năng, chỉ số, võ đài, giao tranh, điều tra, nhiệm vụ phụ, ngựa, thuyền, thời tiết."""

# isort: skip_file
from __future__ import annotations

import pygame
import pytest
from test_playthrough import Bot, play_question, play_story, press_key  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import platform_io, progression
from core.sprites import TILE
from core.tilemap import BRIDGE, WATER
from core.weather import Weather
from scenes.arena import ArenaScene
from scenes.case import DESK, CaseScene
from scenes.fight import FightScene
from scenes.question import QuestionScene
from scenes.skills import SkillsScene
from scenes.story import StoryScene
from scenes.world import PauseScene, WorldScene, get_world

WEAK = {"name": "Bù nhìn", "char": "Villager3", "hp": 30, "power": 0.1, "speed": 80, "aggro": 0.1}
STRONG = {"name": "Võ sư", "char": "Master", "hp": 900, "power": 3.0, "speed": 260, "aggro": 0.9}


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    b = Bot()
    yield b


def world(bot, level="man1"):
    bot.state.reset()
    ws = WorldScene(bot, level, "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    return ws


def stand_at(ws, actor):
    ws.mode = "walk"
    ws.x, ws.y = actor.x, actor.y + TILE * 0.6
    ws.path.clear()
    ws._snap_camera()


def find(ws, kind, key=None):
    return next(a for a in ws.actors if a.kind == kind and (key is None or (a.data and a.data.get("id") == key)))


def finish_relic(st, relic_id):
    """Coi như đã xong một di tích để mở các nội dung phía sau."""
    for quest in st.engine(st.level_of[relic_id]).quests:
        if quest["id"] == relic_id:
            for obj in quest["objectives"]:
                st.progress.completed_objectives.add(obj["id"])
    st.stamps.add(relic_id)


# ----- điểm kỹ năng, chỉ số -----
def test_points_come_from_progress_and_old_saves_work(bot):
    st = bot.state
    st.reset()
    assert st.skill_points_earned() == 0
    st.first_try.update({"a", "b"})
    st.stamps.add("r_duong_lam")
    st.progress.completed_levels.add("man1")
    st.arena_wins.add("b_trai_lang")
    st.discovered.add("d_lang_ngo")
    want = 2 * progression.SP_FIRST_TRY + progression.SP_RELIC + progression.SP_LEVEL + progression.SP_ARENA + progression.SP_DISCOVERY
    assert st.skill_points_earned() == want
    # Bản lưu từ trước khi có kỹ năng vẫn đọc được và đủ điểm
    st.reset()
    st.from_dict({"first_try": ["a"], "stamps": ["r_duong_lam"], "points": 50})
    assert st.skill_points_left() == progression.SP_FIRST_TRY + progression.SP_RELIC
    assert st.stat_levels == {} and st.equipped == []


def test_spending_points_is_limited_and_saved(bot):
    st = bot.state
    st.reset()
    assert not st.upgrade_stat("suc"), "Không có tiềm năng thì không tăng được"
    st.tiem_nang = 15
    assert st.upgrade_stat("suc") and st.stat_levels["suc"] == 1 and st.tiem_nang == 0
    assert not st.upgrade_stat("suc"), "Bậc 2 tốn 30 tiềm năng"
    st.first_try.update({f"q{i}" for i in range(3)})
    assert st.skill_points_left() == 3, "Tăng chỉ số không tốn điểm kỹ năng"
    assert not st.upgrade_skill("phong_lao"), "Chưa đủ câu trả lời đúng thì chưa học được"
    st.solved.update({"q0", "q1", "q2"})
    assert st.upgrade_skill("phong_lao") and st.equipped == ["phong_lao"]
    assert st.upgrade_skill("phong_lao"), "Cấp 2 tốn 2 điểm"
    assert st.skill_points_left() == 0
    assert not st.upgrade_skill("phong_lao")
    saved = st.to_dict()
    st.reset()
    st.from_dict(saved)
    assert st.skill_levels == {"phong_lao": 2} and st.stat_levels == {"suc": 1} and st.equipped == ["phong_lao"]


def test_gave_up_questions_do_not_count_as_correct(bot):
    st = bot.state
    st.reset()
    q = next(iter(st.index["questions"].values()))
    st.give_up(q)
    assert q["id"] in st.solved
    assert st.need_progress(("answers", 1)) == 0


def test_stats_change_real_numbers(bot):
    st = bot.state
    st.reset()
    st.gear.clear()  # bỏ đồ khởi đầu để đo đúng phần chỉ số
    assert st.max_hp() == progression.BASE_HP and st.damage_mult() == 1.0 and st.speed_mult() == 1.0 and st.cd_mult() == 1.0
    st.stat_levels.update({"suc": 5, "the": 5, "nhanh": 5, "tri": 5})
    assert st.max_hp() == progression.BASE_HP + 60
    assert st.damage_mult() == pytest.approx(1.4)
    assert st.speed_mult() == pytest.approx(1.2)
    assert st.cd_mult() == pytest.approx(0.8)


def test_speed_stat_makes_walking_faster(bot):
    ws = world(bot)
    bot.state.gear.clear()
    x0, y0 = ws.x, ws.y
    ws._move(1, 0, 0.1)
    slow = ws.x - x0
    ws.x, ws.y = x0, y0
    bot.state.stat_levels["nhanh"] = 5
    ws._move(1, 0, 0.1)
    assert ws.x - x0 == pytest.approx(slow * 1.2)


def test_intelligence_shortens_battle_cooldown(bot):
    from scenes import battle as battle_mod

    bot.state.reset()
    bot.state.stat_levels["tri"] = 5
    sc = battle_mod.make_battle(bot, bot.state.index["battles"]["b_bach_dang_938"])
    bot.scenes.reset(sc)
    assert bot.state.cd_mult() == pytest.approx(0.8)


def test_skill_page_buttons(bot):
    st = bot.state
    st.reset()
    st.first_try.update({f"q{i}" for i in range(6)})
    st.tiem_nang = 200
    sc = SkillsScene(bot)
    bot.scenes.reset(sc)
    bot.tick(2)
    plus = [b for b in sc.group.buttons if b.label == "+"]
    assert len(plus) == len(progression.STATS) and all(b.enabled for b in plus)
    bot.click(plus[0].rect.center)
    assert st.stat_levels["suc"] == 1
    st.solved.update({"q0", "q1", "q2"})
    sc._build()
    bot.press(sc.group, "Học (1)")
    assert st.skill_levels["phong_lao"] == 1
    bot.press(sc.group, "Đang dùng")
    assert st.equipped == []
    bot.press(sc.group, "Trang bị")
    assert st.equipped == ["phong_lao"]


# ----- đối kháng -----
def fight(bot, foes, buff=1.0):
    holder = ArenaScene(bot)
    bot.scenes.reset(holder)
    sc = FightScene(bot, foes, "Thử sức", "vo_dai", buff)
    bot.scenes.push(sc)
    for _ in range(90):
        bot.tick()
    assert sc.intro <= 0
    return sc


def test_player_can_win_a_fight(bot):
    bot.state.reset()
    sc = fight(bot, [WEAK])
    for _ in range(600):
        if sc.result:
            break
        foe = sc.foes[0]
        sc.player.x, sc.player.y = foe.x - 60, foe.y
        sc.attack(sc.player)
        bot.tick()
    assert sc.result == {"win": True}
    bot.press(sc.group, "Tiếp tục")
    assert isinstance(bot.scenes.top, ArenaScene)


def test_player_loses_if_idle_against_a_strong_bot(bot):
    bot.state.reset()
    sc = fight(bot, [STRONG])
    for _ in range(1800):
        if sc.result:
            break
        bot.tick()
    assert sc.result == {"win": False}


def test_every_skill_works_for_player_and_bot(bot):
    st = bot.state
    st.reset()
    for sid in progression.SKILLS:
        st.skill_levels[sid] = 2
    st.equipped = list(progression.SKILLS)[:4]
    spec = dict(WEAK, hp=5000, power=1.0, skills=list(progression.SKILLS), level=3, aggro=1.0)
    sc = fight(bot, [spec])
    foe = sc.foes[0]
    for sid in progression.SKILLS:
        sc.player.skills[sid] = 2
        sc.player.cds[sid] = 0.0
        sc.player.x, sc.player.y = foe.x - 120, foe.y
        assert sc.cast(sc.player, sid), f"Không dùng được {sid}"
        assert sc.player.cds[sid] > 0
        foe.cds[sid] = 0.0
        assert sc.cast(foe, sid), f"Bot không dùng được {sid}"
        bot.tick(4)
    bot.tick(60)
    assert not any(tr is None for tr in sc.traps)


def test_dodge_and_shield_reduce_damage(bot):
    bot.state.reset()
    sc = fight(bot, [dict(WEAK, hp=500)])
    p = sc.player
    hp = p.hp
    p.dodge_t = 0.2
    sc._hurt(p, 50)
    assert p.hp == hp, "Đang né thì không mất máu"
    p.dodge_t = 0.0
    p.shield_t = 1.0
    sc._hurt(p, 40)
    assert p.hp == pytest.approx(hp - 10)


def test_arrow_keys_and_space_do_not_press_retreat(bot):
    bot.state.reset()
    sc = fight(bot, [dict(WEAK, hp=500)])
    press_key(bot, pygame.K_RIGHT)
    press_key(bot, pygame.K_SPACE)
    assert bot.scenes.top is sc


def test_arena_gives_one_point_for_first_win_only(bot):
    st = bot.state
    st.reset()
    sc = ArenaScene(bot)
    bot.scenes.reset(sc)
    bot.tick(2)
    locked = st.extras["arena"][1]
    assert not st.arena_unlocked(locked)
    assert "Cần đóng dấu" in st.arena_need_text(locked)
    bot.press(sc.group, "Thách đấu")
    assert isinstance(bot.scenes.top, FightScene)
    bot.scenes.pop({"win": True})
    assert st.arena_wins == {"b_trai_lang"} and st.skill_points_earned() == progression.SP_ARENA
    bot.press(sc.group, "Đấu lại")
    bot.scenes.pop({"win": True})
    assert st.skill_points_earned() == progression.SP_ARENA
    assert any("sắp có" in b.label and not b.enabled for b in sc.group.buttons), "Đấu với người phải hiện là sắp có"


def test_arena_warmup_question_gives_buff(bot):
    st = bot.state
    st.reset()
    q = next(iter(st.index["questions"].values()))
    st.solved.add(q["id"])
    sc = ArenaScene(bot)
    bot.scenes.reset(sc)
    bot.tick(2)
    q_pick = sc._quiz_pool()[0]
    bot.press(sc.group, "Ôn bài")
    assert isinstance(bot.scenes.top, QuestionScene)
    bot.scenes.pop(True)
    assert sc.buff > 1.0
    assert q_pick
    bot.press(sc.group, "Thách đấu")
    fighter = bot.scenes.top
    assert fighter.player.power == pytest.approx(st.damage_mult() * sc.buff)


# ----- khám phá -----
def test_all_extras_are_reachable(bot):
    bot.state.reset()
    for level in bot.state.order:
        ws = WorldScene(bot, level, "spawn")
        world_ = get_world(bot.state, level)
        m = world_.map
        start = world_.spawn
        seen = {start}
        queue = [start]
        while queue:
            x, y = queue.pop()
            for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if nxt not in seen and not m.blocked(*nxt):
                    seen.add(nxt)
                    queue.append(nxt)
        water = set()
        for a in ws.actors:
            if a.kind == "pier":
                tile = ws._nearest_tile(a.x, a.y, 4, lambda x, y, g=m: g.get(x, y) == WATER)
                assert tile, f"{level}: bến không sát nước"
                water.add(tile)
        queue = list(water)
        while queue:
            x, y = queue.pop()
            for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if nxt not in water and m.get(*nxt) in (WATER, BRIDGE):
                    water.add(nxt)
                    queue.append(nxt)
        for a in ws.actors:
            if a.kind not in ("discovery", "case", "giver", "gather", "depot", "skirmish", "arena", "horse", "pier"):
                continue
            tile = (int(a.x // TILE), int(a.y // TILE))
            if a.kind == "discovery" and a.data.get("water"):
                assert tile in water, f"{level}: {a.name} không chèo thuyền tới được"
            else:
                near = [(tile[0] + dx, tile[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
                assert any(t in seen for t in near), f"{level}: không đi tới được {a.kind} {a.name} {tile}"


def test_extra_questions_are_in_the_review_book(bot):
    st = bot.state
    for kind in ("discoveries", "cases", "sides"):
        for item in st.extras[kind]:
            qid = item["question"]["id"]
            assert st.index["questions"][qid] is item["question"]
            assert st.level_of[qid] == item["level"]


def test_discovery_story_then_question_then_reward(bot):
    ws = world(bot)
    a = find(ws, "discovery", "d_lang_ngo")
    stand_at(ws, a)
    ws.interact(a)
    assert isinstance(bot.scenes.top, StoryScene)
    play_story(bot)
    assert isinstance(bot.scenes.top, QuestionScene)
    play_question(bot, a.data["question"])
    assert bot.scenes.top is ws
    st = bot.state
    assert "d_lang_ngo" in st.discovered
    assert st.skill_points_earned() == progression.SP_DISCOVERY + progression.SP_FIRST_TRY
    ws.interact(a)
    assert ws.bubble and bot.scenes.top is ws, "Lần sau chỉ nhắc lại, không hỏi lại"


def test_ho_guom_legend_has_turtle_not_dragon(bot):
    from core.cinematic import TurtleMemory

    ws = world(bot, "man2")
    a = find(ws, "discovery", "d_long_quan")
    ws.interact(a)
    story = bot.scenes.top
    assert isinstance(story, StoryScene) and isinstance(story.cine, TurtleMemory)
    bot.tick(30)
    story.cine.set_beat("turtle")
    bot.tick(90)
    assert story.cine._turtle_depth() == 0.0, "Rùa phải nổi lên giữa cảnh"
    story.cine.t = 20.0
    bot.tick(2)
    assert story.cine._turtle_depth() == 1.0, "Cuối cảnh rùa ngậm gươm lặn xuống"
    assert "rùa vàng" in " ".join(line["text"].lower() for line in a.data["lines"])
    assert "rồng" not in " ".join(line["text"].lower() for line in a.data["lines"])
    assert any(line.get("fiction") for line in a.data["lines"])
    assert a.data.get("legend"), "Truyền thuyết phải được ghi nhãn"


def test_case_is_locked_until_relic_done_then_can_be_solved(bot):
    ws = world(bot)
    st = bot.state
    a = find(ws, "case", "c_co_loa")
    stand_at(ws, a)
    ws.interact(a)
    assert bot.scenes.top is ws and ws.bubble, "Chưa xong di tích thì cửa còn đóng"
    finish_relic(st, "r_co_loa")
    ws.interact(a)
    sc = bot.scenes.top
    assert isinstance(sc, CaseScene)
    bot.tick(3)
    for i in range(len(sc.clues)):
        sc._read(i)
        play_story(bot)
    assert sc._all_found()
    sc.x, sc.y = sc._tile_px(*DESK)
    near = sc._near()
    assert near[0] in ("desk", "clue")
    sc._use(("desk", 0))
    assert isinstance(bot.scenes.top, QuestionScene)
    play_question(bot, a.data["question"])
    assert "c_co_loa" in st.case_done
    press_key(bot, pygame.K_ESCAPE)
    assert bot.scenes.top is ws


def test_case_room_has_no_clue_inside_a_wall(bot):
    for case in bot.state.extras["cases"]:
        sc = CaseScene(bot, case)
        for c in case["clues"]:
            assert tuple(c["at"]) not in sc.solid, f"{case['id']}: manh mối nằm trong tường"
        assert DESK not in sc.solid, f"{case['id']}: chỗ đứng ghép manh mối bị chắn"
        assert not sc._blocked(sc.x, sc.y), f"{case['id']}: cửa vào bị chắn"
        bot.scenes.reset(sc)
        bot.tick(2)


def test_gather_quest_flow(bot):
    ws = world(bot)
    st = bot.state
    giver = find(ws, "giver", "s_go_coc")
    items = [a for a in ws.actors if a.kind == "gather"]
    assert not any(ws._visible(a) for a in items), "Chưa nhận việc thì chưa có đồ để nhặt"
    stand_at(ws, giver)
    ws.interact(giver)
    play_story(bot)
    assert "s_go_coc" in st.side_state
    for a in items:
        ws.x, ws.y = a.x, a.y
        ws.explore.update(0.03)
    assert len(st.side_state["s_go_coc"]["got"]) == giver.data["count"]
    assert "5/5" in ws.explore.tracker()
    stand_at(ws, giver)
    ws.interact(giver)
    play_question(bot, giver.data["question"])
    assert "s_go_coc" in st.side_done and bot.scenes.top is ws


def test_carry_quest_slows_you_and_needs_trips(bot):
    ws = world(bot, "man3")
    st = bot.state
    giver = find(ws, "giver", "s_gui_gao")
    depot = next(a for a in ws.actors if a.kind == "depot")
    ws.interact(giver)
    play_story(bot)
    normal = ws._speed()
    for trip in range(giver.data["count"]):
        ws.interact(depot)
        assert ws.explore.carrying and ws._speed() < normal
        assert not ws._visible(depot), "Đang gùi thì không lấy thêm được"
        ws.interact(giver)
        assert not ws.explore.carrying
        if trip < giver.data["count"] - 1:
            assert bot.scenes.top is ws
    play_question(bot, giver.data["question"])
    assert "s_gui_gao" in st.side_done


def test_skirmish_needs_relic_and_gives_points_on_win(bot):
    ws = world(bot)
    st = bot.state
    a = find(ws, "skirmish", "sk_sat_that")
    assert not ws._visible(a)
    finish_relic(st, "r_den_tran")
    assert ws._visible(a)
    ws.interact(a)
    play_story(bot)
    assert isinstance(bot.scenes.top, FightScene)
    assert len(bot.scenes.top.foes) == 2
    bot.scenes.pop({"win": False})
    assert "sk_sat_that" not in st.skirmish_done
    ws.interact(a)
    play_story(bot)
    bot.scenes.pop({"win": True})
    assert "sk_sat_that" in st.skirmish_done
    assert not ws._visible(a)


def test_no_melee_skirmish_in_man3(bot):
    assert not [k for k in bot.state.extras["skirmishes"] if k["level"] == "man3"], "Màn 3 giữ giọng trân trọng, không đánh giáp lá cà"


# ----- đi lại -----
def test_horse_is_faster_and_can_be_left_anywhere(bot):
    ws = world(bot)
    horse = find(ws, "horse")
    walk = ws._speed()
    stand_at(ws, horse)
    press_key(bot, pygame.K_r)
    assert ws.mode == "horse" and ws._speed() > walk and not ws._visible(horse)
    ws.x += TILE
    ws.y = horse.y
    bot.tick()
    press_key(bot, pygame.K_r)
    assert ws.mode == "walk" and ws._visible(horse) and horse.x == ws.x


def test_boat_stays_on_water_and_lands_on_shore(bot):
    ws = world(bot)
    pier = find(ws, "pier")
    ws.x, ws.y = pier.x, pier.y
    assert not ws._hit(ws.x, ws.y), "Bến phải đứng được"
    ws.interact(pier)
    assert ws.mode == "boat"
    assert ws.map.get(int(ws.x // TILE), int(ws.y // TILE)) == WATER
    for _ in range(600):
        ws._move(-1, 0, 1 / 30)
    assert ws.map.get(int(ws.x // TILE), int(ws.y // TILE)) in (WATER, BRIDGE), "Thuyền không được lên cạn"
    ws._save_pos()
    saved = bot.state.player_pos["man1"]
    assert not ws.map.blocked(int(saved[0] // TILE), int(saved[1] // TILE)), "Lưu khi đang chèo phải là chỗ trên bờ"
    ws._disembark()
    assert ws.mode == "walk"
    assert not ws._hit(ws.x, ws.y)


def test_horse_and_boat_turn_in_all_four_directions(bot):
    ws = world(bot)
    pier = find(ws, "pier")
    ws.x, ws.y = pier.x, pier.y
    ws.interact(pier)
    boat = ws.boat_imgs
    assert boat["up"].get_height() > boat["up"].get_width(), "Đi dọc thì thuyền phải quay dọc"
    assert boat["down"].get_height() > boat["down"].get_width()
    assert boat["left"].get_width() > boat["left"].get_height()
    for facing, want in (("up", boat["up"]), ("down", boat["down"]), ("left", boat["left"]), ("right", boat["right"])):
        ws.facing = facing
        assert ws._player_items()[0][2] is want
    ws._disembark()
    horse = find(ws, "horse")
    ws.mount(horse)
    seen = set()
    for facing in ("up", "down", "left", "right"):
        ws.facing = facing
        items = sorted(ws._player_items(), key=lambda it: it[1])
        img = next(it[2] for it in items if it[2] is ws.horse_imgs[facing][0])
        seen.add(pygame.image.tobytes(img, "RGBA"))
    assert len(seen) == 4, "Mỗi hướng phải có một hình riêng"


def test_arrow_key_on_map_does_not_trigger_hud_button(bot):
    ws = world(bot)
    press_key(bot, pygame.K_DOWN)
    press_key(bot, pygame.K_SPACE)
    assert bot.scenes.top is ws
    press_key(bot, pygame.K_k)
    assert isinstance(bot.scenes.top, SkillsScene)
    press_key(bot, pygame.K_ESCAPE)
    press_key(bot, pygame.K_ESCAPE)
    assert isinstance(bot.scenes.top, PauseScene)


def test_arena_door_opens_from_map(bot):
    ws = world(bot)
    a = find(ws, "arena")
    stand_at(ws, a)
    assert ws.nearest() is a
    ws.interact(a)
    assert isinstance(bot.scenes.top, ArenaScene)


def test_weather_kinds_and_critters_run(bot):
    w = Weather()
    screen = pygame.Surface((1280, 720))
    for kind in ("rain", "leaf", "leaf_pink", "fog", "none", None):
        w.set(kind)
        for _ in range(5):
            w.update(0.1)
            w.draw(screen)
    for level in bot.state.order:
        ws = world(bot, level)
        assert ws.critters, f"{level}: chưa có thú"
        bot.tick(30)
        for c in ws.critters:
            assert not ws.map.blocked(int(c.x // TILE), int(c.y // TILE)), f"{c.kind} đi vào chỗ chắn"
