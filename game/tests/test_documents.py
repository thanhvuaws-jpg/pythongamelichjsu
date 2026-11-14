"""Kiểm thử vùng mở rộng và cơ chế phục dựng tư liệu: mảnh đi tới được, nhặt đủ thì ghép, ghép đúng mới vào kho."""

# isort: skip_file
from __future__ import annotations

from collections import deque

import pygame
import pytest
from test_playthrough import Bot, play_question  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import platform_io, progression
from core.sprites import TILE
from scenes.archive import ArchiveScene
from scenes.question import QuestionScene
from scenes.world import WorldScene, get_world


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    b = Bot()
    b.state.reset()
    yield b


def reachable(world) -> set:
    m = world.map
    seen = {world.spawn}
    q = deque([world.spawn])
    while q:
        x, y = q.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in seen and not m.blocked(*n):
                seen.add(n)
                q.append(n)
    return seen


def test_documents_are_well_formed(bot):
    st = bot.state
    docs = st.documents()
    assert len(docs) == 8 and {d["level"] for d in docs} == {"man1", "man2", "man3"}
    for d in docs:
        q = d["question"]
        assert q["kind"] == "order" and len(q["items"]) == len(d["pieces"]) >= 4, d["id"]
        assert q["correct_answer"] == [i["id"] for i in q["items"]]
        assert q["id"] in st.index["questions"], "Câu ghép tư liệu phải vào sổ câu hỏi để ôn tập được"
        assert d["cite"] and all(c in st.sources["citations"] for c in d["cite"]), d["id"]
        assert len({tuple(p) for p in d["pieces"]}) == len(d["pieces"])
    assert next(d for d in docs if d["id"] == "doc_nqsh")["legend"], "Tác giả bài thơ chưa chắc chắn nên phải ghi tương truyền"


@pytest.mark.parametrize("level", ["man1", "man2", "man3"])
def test_annex_and_pieces_are_reachable(bot, level):
    st = bot.state
    world = get_world(st, level)
    spec = st.worlds[level]
    assert world.w == spec["size"][0] and world.annex["id"].startswith("a_")
    ok = reachable(world)
    ax, ay = world.annex["at"]
    assert (ax, ay) in ok, "Vùng mở rộng phải đi tới được từ chỗ xuất phát"
    kx, ky = world.annex["keeper"]
    assert any((kx + dx, ky + dy) in ok for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))), "Phải đứng cạnh người giữ kho được"
    for d in st.documents(level):
        for p in d["pieces"]:
            assert tuple(p) in ok, f"Mảnh {d['id']} ở {p} không đi tới được"
    disc = [x for x in st.extras["discoveries"] if x["level"] == level and x["id"] in ("d_van_mieu", "d_con_son", "d_atk")]
    assert len(disc) == 1


def test_walking_over_pieces_collects_them_and_archive_restores(bot):
    st = bot.state
    ws = WorldScene(bot, "man1", "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    doc = next(d for d in st.documents("man1") if d["id"] == "doc_nqsh")
    pieces = [a for a in ws.actors if a.kind == "piece" and a.data[0]["id"] == doc["id"]]
    assert len(pieces) == len(doc["pieces"])
    for a in pieces[:-1]:
        ws.x, ws.y = a.x, a.y
        ws.explore.update(0.016)
    assert len(st.doc_got(doc)) == len(pieces) - 1 and not st.doc_ready(doc)
    assert "1/4" not in (ws.explore.tracker() or "") and "Sông núi nước Nam" in (ws.explore.tracker() or "")
    assert not any(ws.explore.visible(a) for a in pieces[:-1]), "Mảnh đã nhặt phải biến mất khỏi map"
    ws.interact(pieces[-1])  # bấm E cũng nhặt được
    assert st.doc_ready(doc)
    before = st.skill_points_earned()

    archive = ArchiveScene(bot, "man1")
    bot.scenes.push(archive)
    bot.tick(2)
    assert archive.current["id"] == doc["id"], "Mở kho thì chọn sẵn tư liệu đã đủ mảnh"
    bot.press(archive.group, "Ghép lại tư liệu")
    assert isinstance(bot.scenes.top, QuestionScene)
    play_question(bot, doc["question"])
    bot.tick(2)
    assert bot.scenes.top is archive and doc["id"] in st.doc_done
    assert st.skill_points_earned() == before + progression.SP_DOCUMENT + progression.SP_FIRST_TRY, "Ghép đúng ngay lần đầu thì thêm cả điểm đúng ngay"
    assert not any(b.label == "Ghép lại tư liệu" for b in archive.group.buttons)
    bot.tick(3)


def test_wrong_restore_does_not_count(bot):
    st = bot.state
    doc = st.documents("man3")[0]
    for i in range(len(doc["pieces"])):
        st.take_piece(doc, i)
    archive = ArchiveScene(bot, "man3")
    bot.scenes.reset(archive)
    bot.tick(2)
    archive._restore()
    sc = bot.scenes.top
    assert isinstance(sc, QuestionScene)
    sc.result = {"correct": False, "points": 0, "final": True}
    bot.scenes.pop(True)
    bot.tick(2)
    assert doc["id"] not in st.doc_done and st.doc_ready(doc), "Ghép sai thì vẫn được thử lại"


def test_progress_survives_save_and_badge_after_all(bot):
    st = bot.state
    docs = st.documents()
    for d in docs[:-1]:
        for i in range(len(d["pieces"])):
            st.take_piece(d, i)
        assert not st.restore_doc(d)
    st.take_piece(docs[-1], 0)
    data = st.to_dict()
    st.reset()
    st.from_dict(data)
    assert st.doc_got(docs[-1]) == [0] and len(st.doc_done) == len(docs) - 1
    assert not st.take_piece(docs[-1], 0), "Không nhặt trùng một mảnh"
    for i in range(1, len(docs[-1]["pieces"])):
        st.take_piece(docs[-1], i)
    assert st.restore_doc(docs[-1]) and "giu_su" in st.badges


def test_hud_button_and_key_open_archive(bot):
    ws = WorldScene(bot, "man2", "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    bot.press(ws.group, "Mở menu")
    bot.press(ws.group, "Tư liệu")
    assert isinstance(bot.scenes.top, ArchiveScene)
    bot.tick(2)
    bot.scenes.pop()
    bot.tick(1)
    ws.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t, mod=0, unicode="t"))
    assert isinstance(bot.scenes.top, ArchiveScene)
    bot.tick(2)


def test_keeper_opens_archive_from_the_map(bot):
    ws = WorldScene(bot, "man3", "spawn")
    bot.scenes.reset(ws)
    bot.tick(2)
    keeper = next(a for a in ws.actors if a.kind == "archive")
    ws.x, ws.y = keeper.x, keeper.y + TILE * 0.6
    ws.interact(keeper)
    assert isinstance(bot.scenes.top, ArchiveScene)
    bot.tick(2)
