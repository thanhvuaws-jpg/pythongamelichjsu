"""Bot chơi hết game không cần màn hình: qua mọi scene, mọi trận đánh, ghi nhận lỗi và số điểm cuối.

Chạy: .venv/Scripts/python -m pytest game/tests -q
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "game")]

import pygame  # noqa: E402
import pytest  # noqa: E402
from core import platform_io, scene, theme, ui  # noqa: E402
from core.audio import Audio  # noqa: E402
from core.sprites import TILE  # noqa: E402
from core.state import GameState  # noqa: E402
from scenes import battle as battle_mod  # noqa: E402
from scenes.atlas import AtlasScene  # noqa: E402
from scenes.battle import AmbushBattle, SiegeBattle, TideBattle  # noqa: E402
from scenes.ending import EndingScene  # noqa: E402
from scenes.fight import FightScene  # noqa: E402
from scenes.notebook import NotebookScene  # noqa: E402
from scenes.profile import ProfileScene  # noqa: E402
from scenes.question import FragmentScene, QuestionScene  # noqa: E402
from scenes.review import ReviewScene  # noqa: E402
from scenes.story import StoryScene  # noqa: E402
from scenes.timeline import LevelSummaryScene, TimelineScene  # noqa: E402
from scenes.title import TitleScene  # noqa: E402
from scenes.world import PauseScene, WorldScene  # noqa: E402

DT = 1 / 30


class Bot:
    """Thay thế App trong main.py, không có vòng lặp thật."""

    def __init__(self):
        self.screen = pygame.display.set_mode((theme.WIDTH, theme.HEIGHT))
        self.state = GameState()
        self.state.reset()
        self.audio = Audio()
        self.audio.enabled = False
        self.toasts = ui.Toasts()
        self.scenes = scene.SceneManager()

    def toast(self, message, color=theme.GOLD, seconds=3.0):
        self.toasts.add(message, color, seconds)

    def go_title(self):
        self.scenes.reset(TitleScene(self))

    def tick(self, n=1, event=None):
        for _ in range(n):
            if event is not None:
                self.scenes.handle(event)
                event = None
            self.scenes.update(DT)
            self.toasts.update(DT)
            self.scenes.draw(self.screen)
            self.toasts.draw(self.screen)

    def click(self, pos):
        pos = (int(pos[0]), int(pos[1]))
        self.scenes.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
        self.scenes.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
        self.scenes.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))
        self.tick()

    def press(self, group, label):
        """Bấm nút theo nhãn, báo lỗi nếu nút không tồn tại hoặc đang tắt."""
        for b in group.buttons:
            if label in b.label:
                assert b.enabled, f"Nút '{label}' đang tắt"
                self.click(b.rect.center)
                return
        raise AssertionError(f"Không thấy nút '{label}' trong {[b.label for b in group.buttons]}")


@pytest.fixture(scope="module")
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None  # không ghi đè file lưu thật khi kiểm thử
    platform_io.load_save = lambda: None
    yield Bot()
    pygame.quit()


def play_question(bot, q):
    sc = bot.scenes.top
    assert isinstance(sc, QuestionScene)
    bot.tick(2)
    kind = q["kind"]
    if kind in ("single", "multi"):
        wanted = q["correct_answer"] if kind == "multi" else [q["correct_answer"]]
        for rect, o in list(sc.opt_rects):
            if o["id"] in wanted:
                bot.click(rect.center)
        if kind == "multi":
            bot.press(sc.group, "Trả lời")
    elif kind == "order":
        sc.order = [next(i for i in q["items"] if i["id"] == x) for x in q["correct_answer"]]
        bot.press(sc.group, "Trả lời")
    elif kind == "match":
        lefts, rights = sc._match_rects()
        for left, right in q["correct_answer"].items():
            bot.click(lefts[left].center)
            bot.click(rights[right].center)
        bot.press(sc.group, "Trả lời")
    else:
        c = q["correct_answer"]
        sc.marker = (c["lat"], c["lon"])
        sc._bottom_buttons()
        bot.tick(2)
        bot.press(sc.group, "Trả lời")
    assert sc.result and sc.result["correct"], f"Câu {q['id']} chấm sai"
    bot.tick(2)
    bot.press(sc.group, "Tiếp tục")


def play_story(bot):
    """Đọc từng đoạn, mở cả các chủ đề hỏi thêm nếu có."""
    sc = bot.scenes.top
    assert isinstance(sc, StoryScene)
    guard = 0
    while bot.scenes.top is sc:
        guard += 1
        assert guard < 300, "Câu chuyện không kết thúc"
        bot.tick(1)
        if sc.node.get("topics"):
            sc.chars = sc._text_len()
            bot.tick(1)
            bot.press(sc.topic_buttons, sc.node.get("exit", "Đi tiếp"))
            continue
        bot.click((640, 300))  # hiện hết chữ
        bot.click((640, 300))  # sang đoạn sau


def play_tide(bot, sc, perfect=True):
    bot.press(sc.group, "Vào trận")
    assert sc.stage == "plant"
    plan = {0: [3], 1: [0, 3], 2: [0, 3], 3: [3]}
    for lane, cols in plan.items():
        for col in cols:
            bot.click(sc._cell(lane, col).center)
    assert len(sc.stakes) == battle_mod.BUDGET
    bot.press(sc.group, "chờ triều lên")
    assert sc.stage == "flood"
    guard = 0
    while not sc.ready:
        bot.tick()
        guard += 1
        assert guard < 900, "Thuyền địch không vào vị trí"
    bot.press(sc.group, "giả thua")
    assert sc.stage == "lure"
    guard = 0
    while sc.tide > (0.55 if perfect else 0.9):
        bot.tick()
        guard += 1
        assert guard < 900
    bot.press(sc.group, "PHẢN CÔNG")
    assert sc.stage == "strike"
    guard = 0
    while sc.stage != "result":
        bot.tick()
        guard += 1
        assert guard < 1500, "Trận Bạch Đằng không kết thúc"
    if perfect:
        assert sc.stars == 3, f"Đánh tối ưu phải đạt 3 sao, được {sc.stars}: {sc.report}"
        assert sc.impaled == sum(battle_mod.LANE_BOATS), "Đủ cọc và đúng lúc thì mọi thuyền phải vỡ trên cọc"


def play_ambush(bot, sc):
    bot.press(sc.group, "Vào trận")
    for sid in ("ma_yen", "rung", "lay"):
        sp = next(s for s in battle_mod.SPOTS if s["id"] == sid)
        bot.click((sp["x"], sp["y"]))
    bot.press(sc.group, "nhử địch")
    guard = 0
    while sc.leader["x"] > 550:
        bot.tick()
        guard += 1
        assert guard < 900
    bot.press(sc.group, "PHỤC BINH")
    guard = 0
    while sc.stage != "result":
        bot.tick()
        guard += 1
        assert guard < 900, "Trận Chi Lăng không kết thúc"
    assert sc.stars == 3, sc.report


def play_siege(bot, sc):
    bot.press(sc.group, "Vào trận")
    bot.press(sc.group, "Đánh nhanh")
    assert sc.mistakes == 1 and sc.stage == "choose"
    bot.press(sc.group, "Đánh chắc")
    assert sc.stage == "haul"
    guard = 0
    while sc.stage == "haul":
        guard += 1
        assert guard < 4000, "Không kéo xong pháo"
        bot.tick()
        if abs(sc.mark - 0.5) <= battle_mod.SWEET * 0.5:
            bot.press(sc.group, "DÔ TA")
    assert sc.misses == 0
    bad = battle_mod.NODES["muong_thanh"]
    bot.click((battle_mod.BOARD.x + bad[1], battle_mod.BOARD.y + bad[2]))
    assert sc.mistakes == 2 and sc.note, "Đánh sai đợt phải bị nhắc"
    bot.tick(1)
    for ph in battle_mod.PHASES:
        for nid in ph["targets"]:
            n = battle_mod.NODES[nid]
            bot.click((battle_mod.BOARD.x + n[1], battle_mod.BOARD.y + n[2]))
            guard = 0
            while sc.busy > 0:
                bot.tick()
                guard += 1
                assert guard < 200
            assert nid in sc.taken
    guard = 0
    while sc.stage != "result":
        bot.tick()
        guard += 1
        assert guard < 300
    assert sc.stars == 2, sc.report  # 2 lần sai có chủ ý


def play_battle(bot):
    sc = bot.scenes.top
    bot.tick(2)
    if isinstance(sc, TideBattle):
        play_tide(bot, sc)
    elif isinstance(sc, AmbushBattle):
        play_ambush(bot, sc)
    elif isinstance(sc, SiegeBattle):
        play_siege(bot, sc)
    else:
        raise AssertionError(f"Không phải trận đánh: {sc}")
    bot.tick(5)
    bot.press(sc.group, "Tiếp tục")


def walk_near(bot, ws, actor):
    """Đặt nhân vật ngay cạnh mục tiêu rồi cho một khung hình chạy, tương đương việc đã đi bộ tới."""
    ws.x, ws.y = actor.x, actor.y + TILE * 0.6
    ws.path.clear()
    ws._snap_camera()


def press_key(bot, key):
    bot.scenes.handle(pygame.event.Event(pygame.KEYDOWN, key=key, unicode="", mod=0, scancode=0))
    bot.tick()


def win_fight(bot, fight):
    """Cho một trận đánh trên map kết thúc thắng: qua phần đếm ngược, hạ hết đối thủ, bấm Tiếp tục."""
    assert isinstance(fight, FightScene)
    fight.intro = 0
    for f in fight.foes:
        f.hp = 0.0
        f.dead = True
    bot.tick()
    assert fight.result and fight.result["win"]
    fight._finish()
    bot.tick()


def beat_guard(bot, ws, scroll):
    """Mật thư cuối của di tích có kẻ canh: phải đi tới, bấm F, thắng trận mới nhặt được."""
    guard = ws.mobs.guard_of(scroll)
    if guard is None:
        return
    assert ws.mobs.visible(guard), "Kẻ canh phải hiện ra khi mật thư là việc hiện tại"
    ws.x, ws.y = scroll.x, scroll.y
    bot.tick()
    assert bot.scenes.top is ws, "Còn kẻ canh thì chưa nhặt được mật thư"
    ws.x, ws.y = guard.x, guard.y + TILE * 0.5
    press_key(bot, pygame.K_f)
    win_fight(bot, bot.scenes.top)
    assert bot.scenes.top is ws and guard.key in bot.state.bosses_beaten


def play_relic(bot, ws, relic):
    """Làm từng bước của một di tích bằng cách đi tới đúng vật thể rồi bấm phím tương tác."""
    st = bot.state
    zone = ws.world.zones[relic["id"]]
    ws.x, ws.y = (zone.cx + 0.5) * TILE, (zone.cy + 3) * TILE
    bot.tick(2)
    assert ws._objectives(relic)[0]["id"] in st.progress.completed_objectives, "Bước vào khu vực phải tính là đã đến"
    guard = 0
    while ws._next_obj(relic):
        guard += 1
        assert guard < 40
        obj = ws._next_obj(relic)
        if obj["kind"] == "dialogue":
            actor = next(a for a in ws.actors if a.kind == "keeper" and a.relic is relic)
        else:
            actor = next(a for a in ws.actors if a.objective is not None and a.objective["id"] == obj["id"])
        walk_near(bot, ws, actor)
        assert ws._visible(actor) and ws._is_current(actor) or obj["kind"] == "dialogue"
        if actor.kind == "scroll":
            beat_guard(bot, ws, actor)
            ws.x, ws.y = actor.x, actor.y
            bot.tick()  # mảnh ghép tự nhặt khi đi qua
        else:
            assert ws.nearest() is not None
            ws.interact(actor)
            bot.tick()
        top = bot.scenes.top
        assert top is not ws, f"Không mở được bước {obj}"
        if obj["kind"] == "dialogue":
            play_story(bot)
        elif obj["kind"] == "answer":
            play_question(bot, st.index["questions"][obj["target_id"]])
        elif obj["kind"] == "collect":
            assert isinstance(top, FragmentScene)
            bot.tick(30)
            bot.press(ui.ButtonGroup([top.btn]), "Cất vào Sổ tay")
        else:
            play_battle(bot)
        assert bot.scenes.top is ws
    assert st.relic_done(relic["id"])
    assert relic["id"] in st.stamps, "Xong di tích phải được đóng dấu"
    assert relic["id"] in st.reports, "Xong di tích thì phải về báo cáo già làng"
    if relic.get("artifact"):
        assert relic["artifact"] in st.owned_artifacts
    bot.tick(10)
    keeper = next(a for a in ws.actors if a.kind == "keeper" and a.relic is relic)
    walk_near(bot, ws, keeper)
    ws.interact(keeper)
    bot.tick()
    if relic.get("extra_talk"):
        talk = bot.scenes.top
        assert isinstance(talk, StoryScene), "Quay lại di tích phải trò chuyện thêm được"
        talk.chars = talk._text_len()
        bot.tick(2)
        for b in list(talk.topic_buttons.buttons):
            if b.enabled and b.data:
                bot.click(b.rect.center)
                guard = 0
                while not talk.node.get("topics"):
                    guard += 1
                    assert guard < 40
                    bot.click((640, 300))
                    bot.click((640, 300))
                talk.chars = talk._text_len()
                bot.tick(2)
                break
        bot.press(talk.topic_buttons, talk.node.get("exit", "Đi tiếp"))
        assert bot.scenes.top is ws


def play_timeline(bot, sc, level_id):
    bot.tick(2)
    # Thử một lần đặt sai để kiểm tra gợi ý nhân quả: thẻ muộn nhất đặt trước thẻ sớm nhất
    ordered = sorted(sc.events, key=lambda e: sc.dates[e["id"]].sort_key())
    first, last = ordered[0]["id"], ordered[-1]["id"]
    sc._drop(last, 0)
    sc._drop(first, 1)  # thẻ sớm nhất đặt sau thẻ muộn nhất là sai
    assert sc.mistakes == 1, "Đặt sai thứ tự phải bị tính lỗi"
    assert first not in sc.placed and "Chưa đúng" in sc.hint
    for e in ordered:
        eid = e["id"]
        if eid in sc.placed:
            continue
        rects = sc._tray_rects()
        idx = next(
            (i for i in range(len(sc.placed) + 1)
             if battle_ok(sc, eid, i)),
            None,
        )
        assert idx is not None, f"Không có vị trí đúng cho {eid}"
        # Mô phỏng kéo thả thật khi có thể
        pos = rects[eid].center
        bot.scenes.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
        assert sc.drag == eid
        bot.tick()
        sc.drag = None
        sc._drop(eid, idx)
        bot.tick()
    assert sc.done and not sc.tray
    bot.tick(10)
    bot.press(sc.group, "Hoàn tất")
    assert level_id in bot.state.progress.completed_levels, "Xong dòng thời gian phải hoàn thành màn"
    summary = bot.scenes.top
    assert isinstance(summary, LevelSummaryScene), "Hoàn thành màn phải có màn tổng kết"
    bot.tick(3)
    bot.press(summary.group, "Ôn tập")
    assert isinstance(bot.scenes.top, ReviewScene)
    bot.tick(2)
    bot.scenes.pop()
    assert bot.scenes.top is summary
    bot.press(summary.group, "Về bản đồ")


def battle_ok(sc, eid, index):
    from shared.timeline_rules import is_valid_placement

    return is_valid_placement([sc.dates[e] for e in sc.placed], sc.dates[eid], index)


def test_full_playthrough(bot):
    bot.go_title()
    bot.tick(3)
    assert isinstance(bot.scenes.top, TitleScene)
    bot.state.tutorial_seen = True  # trailer có test riêng trong test_guide.py
    bot.press(bot.scenes.top.group, "Bắt đầu hành trình")
    assert isinstance(bot.scenes.top, StoryScene)  # lời dẫn lần đầu
    play_story(bot)
    ws = bot.scenes.top
    assert isinstance(ws, WorldScene), "Xong lời dẫn phải vào thẳng map"
    st = bot.state
    assert ws.level_id == "man1" and not st.level_unlocked("man2")
    for i, lid in enumerate(st.order):
        ws = bot.scenes.top
        assert isinstance(ws, WorldScene) and ws.level_id == lid
        bot.tick(3)
        # chưa xong màn thì cổng phải đóng
        ws.x, ws.y = ws.portal.x, ws.portal.y - 10
        bot.tick(2)
        assert bot.scenes.top is ws and ws.warp is None, "Cổng phải khoá khi chưa xong màn"
        # giữ ký ức ở di tích chưa mở không cho làm tiếp
        locked = next((r for r in ws.relics if not ws._unlocked(r)), None)
        if locked:
            keeper = next(a for a in ws.actors if a.kind == "keeper" and a.relic is locked)
            walk_near(bot, ws, keeper)
            ws.interact(keeper)
            assert bot.scenes.top is ws and ws.bubble, "Di tích chưa mở chỉ được nhắc đường"
        for relic in sorted(st.levels[lid]["relics"], key=lambda r: bool(r.get("optional"))):
            assert ws._unlocked(relic), f"{relic['id']} chưa mở"
            play_relic(bot, ws, relic)
            assert bot.scenes.top is ws
        assert st.timeline_ready(lid)
        walk_near(bot, ws, ws.mentor)
        quan_before = st.quan
        ws.interact(ws.mentor)
        assert isinstance(bot.scenes.top, StoryScene), "Có di tích chưa báo cáo thì già làng nghe báo cáo trước"
        play_story(bot)
        assert not st.reports and st.quan > quan_before, "Báo cáo xong phải nhận thưởng"
        assert isinstance(bot.scenes.top, TimelineScene), "Cụ Đồ Sử phải mở dòng thời gian khi đủ di tích"
        play_timeline(bot, bot.scenes.top, lid)
        assert bot.scenes.top is ws
        assert ws._portal_open(), "Xong màn thì cổng mở"
        # đi vào cổng: dịch chuyển sang map sau, hoặc lời kết ở màn cuối
        ws.x, ws.y = ws.portal.x, ws.portal.y - 10
        guard = 0
        while bot.scenes.top is ws:
            bot.tick()
            guard += 1
            assert guard < 90, "Cổng không dịch chuyển"
        if i + 1 < len(st.order):
            nxt = bot.scenes.top
            assert isinstance(nxt, WorldScene) and nxt.level_id == st.order[i + 1]
            assert st.level_unlocked(nxt.level_id)
            assert nxt.back_portal is not None
    assert isinstance(bot.scenes.top, EndingScene), "Qua cổng cuối thì có đoạn kết cờ bay"
    assert st.finished
    press_key(bot, pygame.K_ESCAPE)
    assert isinstance(bot.scenes.top, StoryScene), "Sau đoạn kết là lời dặn của Cụ Đồ Sử"
    assert st.progress.points > 0
    assert len(st.stamps) == sum(len(st.levels[x]["relics"]) for x in st.order)
    assert "man:man3" in st.badges
    main = [q["id"] for lid in st.order for q in st.levels[lid]["questions"]]
    assert not [q for q in main if q not in st.solved], "Còn câu hỏi chưa được trả lời"


def test_portal_back_and_movement(bot):
    """Đi bằng bàn phím bị tường chắn, bấm chuột tự tìm đường, cổng quay về đúng màn trước."""
    st = bot.state
    ws = WorldScene(bot, "man2", "spawn")
    bot.scenes.reset(ws)
    bot.tick(3)
    x0 = ws.x
    ws._move(1, 0, 0.1)
    assert ws.x != x0, "Đường trống phải đi được"
    assert not ws._hit(ws.x, ws.y)
    # bấm chuột vào một ô xa: nhân vật tự đi và không bao giờ vào ô bị chắn
    wx, wy = ws.x + TILE * 6, ws.y
    bot.click((wx - ws.cam_x, wy - ws.cam_y))
    assert ws.path, "Bấm chuột phải có đường đi"
    for _ in range(120):
        bot.tick()
        assert not ws._hit(ws.x, ws.y), "Nhân vật không được đi vào vật cản"
    assert not ws.path
    # đi vào nước bằng phím phải bị chặn
    river = next((x, y) for y in range(ws.map.h) for x in range(ws.map.w) if ws.map.blocked(x, y) and ws.map.get(x, y) == 2)
    assert ws._hit((river[0] + 0.5) * TILE, (river[1] + 0.5) * TILE)
    # cổng quay về
    ws.x, ws.y = ws.back_portal.x, ws.back_portal.y - 10
    guard = 0
    while bot.scenes.top is ws:
        bot.tick()
        guard += 1
        assert guard < 90
    back = bot.scenes.top
    assert isinstance(back, WorldScene) and back.level_id == "man1"
    assert (back.x - back.portal.x) ** 2 + (back.y - back.portal.y) ** 2 > 48 ** 2, "Quay về không được rơi ngay vào cổng"
    # bản đồ Việt Nam: đi nhanh tới di tích đã mở
    back._atlas()
    atlas = bot.scenes.top
    assert isinstance(atlas, AtlasScene)
    bot.tick(2)
    relic = back.relics[0]
    atlas._select(relic)
    bot.tick()
    bot.press(atlas.info_group, "Đi nhanh")
    assert bot.scenes.top is back
    zone = back.world.zones[relic["id"]]
    assert abs(back.x - (zone.cx + 0.5) * TILE) < TILE
    # tạm dừng
    press_key(bot, pygame.K_ESCAPE)
    assert isinstance(bot.scenes.top, PauseScene)
    bot.tick(2)
    press_key(bot, pygame.K_ESCAPE)
    assert bot.scenes.top is back
    st.current_level = "man1"


@pytest.mark.parametrize("level", ["man1", "man2", "man3"])
def test_map_is_sane(bot, level):
    """Thuyền, cọc phải nằm trên nước; mọi nơi cần đến và mọi NPC phải đi tới được."""
    from core.tilemap import WATER
    from scenes.world import get_world

    world = get_world(bot.state, level)
    m = world.map
    for kind, x, y, w, h in world.on_water:
        for j in range(y, y + h):
            for i in range(x, x + w):
                assert m.get(i, j) == WATER, f"{kind} tại ({x},{y}) không nằm trên nước"
    if level == "man1":
        kinds = {item[0] for item in world.on_water}
        assert kinds == {"boat", "stake"}, "Màn 1 phải có cả thuyền và cọc trên sông"
    start = world.spawn
    seen = {start}
    queue = [start]
    while queue:
        x, y = queue.pop()
        for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nxt not in seen and not m.blocked(*nxt):
                seen.add(nxt)
                queue.append(nxt)
    must = [("mentor", world.mentor), ("portal", (world.portal[0], world.portal[1] + 1))]
    for rid, z in world.zones.items():
        must.append((rid, (z.cx, z.cy)))
        must.extend((f"{rid}/{i}", spot) for i, spot in enumerate(z.spots))
    must.extend((f"npc {n['char']}", tuple(n["at"])) for n in world.npcs)
    bad = [(name, tile) for name, tile in must if tuple(tile) not in seen]
    assert not bad, f"Không đi tới được: {bad}"


def _tide_until_strike(bot, stakes, tide=0.55):
    sc = battle_mod.make_battle(bot, bot.state.index["battles"]["b_bach_dang_938"])
    bot.scenes.reset(sc)
    bot.tick(2)
    bot.press(sc.group, "Vào trận")
    for lane, cols in stakes.items():
        for col in cols:
            bot.click(sc._cell(lane, col).center)
    bot.press(sc.group, "chờ triều lên")
    while not sc.ready:
        bot.tick()
    bot.press(sc.group, "giả thua")
    while sc.tide > tide:
        bot.tick()
    bot.press(sc.group, "PHẢN CÔNG")
    return sc


def test_tide_ebb_reveals_stakes_and_boats_crash(bot):
    """Triều rút làm cọc lộ dần; thuyền đâm cọc thì mắc lại, cọc vẽ đè lên thân và có cảnh chậm."""
    sc = _tide_until_strike(bot, {0: [3], 1: [0, 3], 2: [0, 3], 3: [3]})
    start = sc._ebb()
    assert sc.panic > 0 and all(b["state"] == "run" for b in sc.boats), "Địch phải khựng lại trước khi quay đầu"
    x = [b["x"] for b in sc.boats]
    bot.tick(10)
    assert [b["x"] for b in sc.boats] == x, "Lúc hoảng loạn thuyền chưa chạy"
    assert sc._ebb() > start, "Triều phải rút dần làm lộ cọc"
    guard = 0
    while not any(b["state"] == "stuck" for b in sc.boats):
        bot.tick()
        guard += 1
        assert guard < 300, "Không có thuyền nào đâm vào cọc"
    hit = next(b for b in sc.boats if b["state"] == "stuck")
    assert sc._ebb() > 0.5, "Lúc va chạm cọc phải đã lộ rõ"
    assert sc.slow > 0, "Cú va chạm đầu tiên phải có cảnh chậm"
    assert hit["x"] >= hit["doom"] - battle_mod.BOW and hit["x"] < hit["doom"]
    assert not all(c["alive"] for c in hit["crew"]), "Đâm cọc phải có người ngã"
    assert sc.fx.items, "Phải có mảnh gỗ, bọt nước văng ra"
    guard = 0
    while sc.stage != "result":
        bot.tick()
        guard += 1
        assert guard < 2500
    assert sc.impaled == sum(battle_mod.LANE_BOATS) and sc.stars == 3


def test_tide_skills_stop_escaping_boats(bot):
    """Ít cọc thì có thuyền thoát; cả ba kỹ năng đều phải chặn được hoặc gây hại, có hồi chiêu."""
    sc = _tide_until_strike(bot, {1: [0], 2: [0], 0: [0], 3: [0]})
    total = sum(battle_mod.LANE_BOATS)
    assert sc.impaled < total, "Ít cọc thì không thể phá hết thuyền bằng cọc"
    while sc.panic > 0:
        bot.tick()
    by_id = {k["id"]: k for k in battle_mod.SKILLS}
    # tên lửa đốt thuyền đang thoát
    press_key(bot, by_id["lua"]["key"])
    assert sc.cds["lua"] > 0 and sc.fx.shots, "Tên lửa phải bay và vào hồi chiêu"
    cd = sc.cds["lua"]
    press_key(bot, by_id["lua"]["key"])
    assert sc.cds["lua"] <= cd, "Đang hồi chiêu thì không bắn lại được"
    for _ in range(40):
        bot.tick()
    assert any(b["burn"] is not None for b in sc.boats) or sc.burned >= 1, "Trúng tên lửa thì thuyền phải cháy"
    # phóng lao giết lính trên boong
    alive = sum(c["alive"] for b in sc.boats for c in b["crew"])
    press_key(bot, by_id["lao"]["key"])
    assert sc.cds["lao"] > 0
    for _ in range(30):
        bot.tick()
    assert sum(c["alive"] for b in sc.boats for c in b["crew"]) < alive, "Phóng lao phải hạ được lính"
    # xung phong nhảy sang thuyền địch rồi quay về
    press_key(bot, by_id["xung"]["key"])
    assert sc.jumpers, "Xung phong phải có lính nhảy sang"
    guard = 0
    while sc.stage != "result":
        bot.tick()
        guard += 1
        assert guard < 2500
    assert not sc.jumpers
    assert sc.burned >= 1 and sc.broken > sc.impaled
    assert sc.broken <= total
    assert any("bị đốt" in line for line in sc.report)


@pytest.mark.parametrize("level", ["man1", "man2", "man3"])
def test_each_step_has_exactly_one_thing_to_walk_to(bot, level):
    """Mỗi câu hỏi, mảnh ghép, trận đánh ứng với đúng một vật thể; không có vật thể nào thừa (như cờ trận giả)."""
    ws = WorldScene(bot, level, "spawn")
    kinds = {"answer": "quiz", "collect": "scroll", "battle": "war"}
    for relic in ws.relics:
        wanted = sorted(o["id"] for o in ws._objectives(relic) if o["kind"] in kinds)
        got = sorted(a.objective["id"] for a in ws.actors if a.relic is relic and a.objective is not None)
        assert got == wanted, f"{relic['id']}: thừa hoặc thiếu vật thể"
        for a in ws.actors:
            if a.relic is relic and a.objective is not None:
                assert a.kind == kinds[a.objective["kind"]], f"{a.objective['id']} sai loại vật thể"


def test_mixer_plays_music_at_its_own_quality():
    """Bộ trộn phải khớp với file nhạc, nếu không nhạc bị hạ chất lượng ngay lúc phát và nghe rè."""
    from core import audio

    assert audio.MIXER_RATE >= 44100 and audio.MIXER_CHANNELS == 2
    assert audio.MIXER_BUFFER >= 1024, "Bộ đệm nhỏ thì trên web dễ kêu lách tách khi khung hình chậm"
    main_py = (ROOT / "game" / "main.py").read_text(encoding="utf-8")
    assert "audio.MIXER_RATE" in main_py, "main.py phải dùng đúng cấu hình này"


def test_audio_files_are_web_safe():
    """pygbag từ chối đóng gói WAV khi build web; âm thanh khai báo trong code phải có file thật."""
    from core import audio

    root = ROOT / "game" / "assets"
    assert not list(root.rglob("*.wav")), "Không được để file WAV: build web sẽ hỏng"
    for name, file in audio._FILES.items():
        assert (audio.SFX_DIR / f"{file}.ogg").exists(), f"Thiếu file âm thanh cho {name}"
    for track in ("title", "road", "temple", "sad", "fight"):
        assert (audio.MUSIC_DIR / f"{track}.ogg").exists()
    pygame.mixer.init()
    for file in audio._FILES.values():
        assert pygame.mixer.Sound(str(audio.SFX_DIR / f"{file}.ogg")).get_length() > 0


@pytest.mark.parametrize("dialogue", ["d_bd_3", "d_bc_2"])
def test_memory_replays_the_real_battle(bot, dialogue):
    """Hồi ức Bạch Đằng phải diễn đúng trình tự: nhử, triều rút lộ cọc, đâm cọc, tàn trận."""
    from core import cinematic

    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    s = StoryScene(bot, bot.state.index["dialogues"][dialogue])
    bot.scenes.push(s)
    assert [n["cine"] for n in s.queue if n.get("cine")] == list(cinematic.BEATS), "Thiếu nhịp diễn lại"
    cine = s.cine
    assert cine and cine.beat == "lure" and s.memory and s.opaque
    assert cine.tide == 1.0 and cine._ebb() == 0, "Lúc nhử triều phải lên che kín cọc"
    x0 = [b["x"] for b in cine.boats]
    a0 = [a["x"] for a in cine.allies]
    bot.tick(30)
    assert all(b["x"] < x for b, x in zip(cine.boats, x0, strict=True)), "Thuyền địch phải đuổi theo"
    assert all(a["x"] < x for a, x in zip(cine.allies, a0, strict=True)), "Thuyền ta phải giả thua chạy về"
    s.chars = 9999
    bot.click((640, 300))
    assert cine.beat == "ebb"
    before = cine._ebb()
    bot.tick(60)
    assert cine._ebb() > before, "Triều phải rút làm lộ cọc"
    s.chars = 9999
    bot.click((640, 300))
    assert cine.beat == "crash" and not s.ambient.duels
    assert all(b["doom"] is None or b["doom"] > b["bait"] for b in cine.boats), "Cọc phải nằm trên đường thuyền chạy ra biển"
    guard = 0
    while not any(b["state"] == "stuck" for b in cine.boats):
        bot.tick()
        guard += 1
        assert guard < 200, "Không có thuyền nào đâm cọc"
    for _ in range(300):
        bot.tick()
    assert any(b["state"] in ("stuck", "wreck") for b in cine.boats)
    assert any(b["doom"] is None for b in cine.boats), "Phải có thuyền thoát như sử chép"
    assert not s.ambient.duels, "Không được có lính đứng đánh nhau trên mặt nước"
    s.chars = 9999
    bot.click((640, 300))
    assert cine.beat == "after" and not any(b["state"] == "run" for b in cine.boats)
    bot.tick(10)
    s.chars = 9999
    bot.click((640, 300))
    assert s.cine is None, "Sang đoạn thường thì dừng cảnh diễn lại"
    bot.scenes.reset(ws)


def test_no_soldiers_on_water_in_memories(bot):
    """Lính trong hồi ức chỉ đứng trên dải đất của từng cảnh."""
    from core import diorama, fx

    ambient = fx.Ambient(fx.Fx("day_du", old=True))
    ambient.ground = diorama.GROUND["bach_dang"]
    ambient.set(["clash"])
    for _ in range(600):
        ambient.update(1 / 30)
        for d in ambient.duels:
            assert ambient.ground[0] <= d.y <= ambient.ground[1]
    ambient.ground = diorama.GROUND["van_don"]
    ambient.duels.clear()
    for _ in range(300):
        ambient.update(1 / 30)
    assert not ambient.duels, "Cảnh toàn nước thì không có lính đứng"


def test_keeper_can_retell_the_memory(bot):
    """Xong di tích có thể nhờ người giữ ký ức kể lại, và vẫn thấy cảnh diễn lại."""
    st = bot.state
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    relic = next(r for r in ws.relics if r["id"] == "r_trang_kenh")
    saved = set(st.progress.completed_objectives)
    st.progress.completed_objectives.update(o["id"] for q in ws.relics[:2] for o in ws._objectives(q))
    keeper = next(a for a in ws.actors if a.kind == "keeper" and a.relic is relic)
    walk_near(bot, ws, keeper)
    ws.interact(keeper)
    talk = bot.scenes.top
    assert isinstance(talk, StoryScene)
    talk.chars = talk._text_len()
    bot.tick(2)
    btn = next(b for b in talk.topic_buttons.buttons if b.data and b.data.get("replay") == "d_bd_3")
    bot.click(btn.rect.center)
    assert talk.cine and talk.cine.beat == "lure", "Kể lại phải chạy đúng cảnh diễn lại"
    bot.tick(5)
    st.progress.completed_objectives.clear()
    st.progress.completed_objectives.update(saved)
    bot.scenes.reset(ws)


def test_side_screens(bot):
    """Sau khi chơi xong: sổ tay, hộ chiếu, ôn tập, cài đặt đều phải vẽ được mọi tab."""
    bot.go_title()
    nb = NotebookScene(bot)
    bot.scenes.push(nb)
    for i in range(5):
        nb._switch(i)
        assert nb.rows
        for row in nb.rows[:25]:
            if row["open"]:
                nb.selected = row
                bot.tick()
    nb._switch(0)
    for ch in "ngo quyen":
        bot.scenes.handle(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=ch, mod=0, scancode=0))
    assert any("Ngô Quyền" in r["title"] for r in nb.rows), "Tìm không dấu phải ra Ngô Quyền"
    bot.scenes.pop()
    pf = ProfileScene(bot)
    bot.scenes.push(pf)
    for i in range(4):
        pf._switch(i)
        bot.tick(2)
    pf._switch(3)
    bot.press(pf.settings_group, "Giảm nhẹ")
    assert bot.state.settings["violence"] == "nhe"
    bot.press(pf.settings_group, "Đầy đủ")
    bot.scenes.pop()
    # đẩy mọi câu vào hạn ôn rồi ôn hết
    st = bot.state
    for q in list(st.solved)[:6]:
        st._schedule(q, None, False, 2)
        st.review[q]["due"] = "2000-01-01T00:00:00+00:00"
    rv = ReviewScene(bot)
    bot.scenes.push(rv)
    assert rv.total >= 1
    bot.tick(2)
    bot.press(rv.group, "Bắt đầu ôn tập")
    guard = 0
    while isinstance(bot.scenes.top, QuestionScene):
        guard += 1
        assert guard < 20
        play_question(bot, bot.scenes.top.q)
    assert rv.finished and "chuyen_can" in st.badges
    bot.tick(2)
    bot.scenes.pop()


def test_wrong_answers_then_give_up(bot):
    """Sai 3 lần: hiện đáp án, không có điểm, vẫn đi tiếp được và vào danh sách ôn tập."""
    st = bot.state
    q = {"id": "q_tam", "kind": "single", "difficulty": 1, "prompt": "?", "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}], "correct_answer": "a", "explanation": "x"}
    st.index["questions"]["q_tam"] = q
    before = st.progress.points
    sc = QuestionScene(bot, q)
    bot.scenes.push(sc)
    wrong = next(r for r, o in sc.opt_rects if o["id"] == "b")
    for attempt in range(3):
        bot.click(wrong.center)
        assert not sc.result["correct"]
        if attempt < 2:
            bot.press(sc.group, "Thử lại")
    assert sc.result["final"]
    bot.press(sc.group, "Tiếp tục")
    assert st.progress.points == before
    assert "q_tam" in st.review
    del st.index["questions"]["q_tam"]
    st.review.pop("q_tam")


def test_violence_setting_changes_fx(bot):
    from core import fx

    gentle, full = fx.Fx("nhe"), fx.Fx("day_du")
    gentle.blood(0, 0, 20)
    full.blood(0, 0, 20)
    red = lambda c: c[0] > 100 and c[1] < 50  # noqa: E731
    assert any(red(p.color) for p in full.items)
    assert not any(red(p.color) for p in gentle.items)
