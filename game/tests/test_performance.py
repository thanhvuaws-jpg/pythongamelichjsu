"""Giữ cho khung hình không bị khựng khi đi lại: trên web nhạc chạy chung luồng với game nên khựng là nhạc kêu "è è"."""

# isort: skip_file
from __future__ import annotations

import pygame
import pytest
from test_playthrough import Bot  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import audio, platform_io, tilemap
from core.sprites import TILE
from core.tilemap import CHUNK, MAX_CHUNKS, TileMap
from scenes.world import H, W, WorldScene
from shared import quest_engine

DT = 1 / 60


@pytest.fixture()
def bot():
    pygame.init()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    b = Bot()
    b.state.reset()
    yield b


def world(bot, level="man1"):
    ws = WorldScene(bot, level, "spawn")
    bot.scenes.reset(ws)
    ws.noclip = True  # đi thẳng một mạch, không vướng cây để đo cho đều
    ws.x, ws.y = 40 * TILE, 31 * TILE
    ws._snap_camera()
    ws.map.forget()
    return ws


def settle(bot, frames=120):
    bot.tick(frames)


def count_builds(monkeypatch):
    counter = {"n": 0}
    original = TileMap._build_chunk

    def counted(self, cx, cy):
        counter["n"] += 1
        return original(self, cx, cy)

    monkeypatch.setattr(TileMap, "_build_chunk", counted)
    return counter


def test_quest_logic_is_not_recomputed_every_frame(bot, monkeypatch):
    world(bot)
    settle(bot, 5)
    calls = {"n": 0}
    original = quest_engine.evaluate

    def counted(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(quest_engine, "evaluate", counted)
    bot.tick(30)
    assert calls["n"] == 0, "Tiến trình không đổi thì không được tính lại danh sách di tích đã mở"


def test_quest_cache_sees_new_progress(bot):
    st = bot.state
    engine = st.engine("man1")
    assert engine.done_quests() is engine.done_quests(), "Gọi lại phải dùng kết quả đã lưu"
    first = st.levels["man1"]["relics"][0]
    second = st.levels["man1"]["relics"][1]
    assert first["id"] not in engine.done_quests()
    assert second["place"] not in engine.unlocked_places()
    quest = next(q for q in engine.quests if q["id"] == first["id"])
    for obj in quest["objectives"]:
        st.progress.completed_objectives.add(obj["id"])
    assert first["id"] in engine.done_quests(), "Xong nhiệm vụ phải thấy ngay"
    assert second["place"] in engine.unlocked_places(), "Di tích tiếp theo phải mở ngay"


def test_effects_of_unlocking_still_reported(bot):
    """Sự kiện mở khoá so sánh trước và sau khi nhận tiến trình, không được hỏng vì lưu kết quả."""
    st = bot.state
    engine = st.engine("man1")
    relic = st.levels["man1"]["relics"][0]
    quest = next(q for q in engine.quests if q["id"] == relic["id"])
    unlocks = []
    for obj in quest["objectives"]:
        if obj["kind"] == "go_to":
            effects = engine.on_arrive(obj["target_id"])
        elif obj["kind"] == "dialogue":
            effects = engine.on_dialogue_done(obj["target_id"])
        elif obj["kind"] == "answer":
            effects = engine.on_question_correct(obj["target_id"])
        elif obj["kind"] == "collect":
            effects = engine.on_collect(obj["target_id"])
        else:
            effects = engine.on_battle_done(obj["target_id"])
        unlocks.extend(e for e in effects if getattr(e, "kind", "") == "place")
    assert unlocks, "Xong di tích đầu tiên phải báo mở địa danh mới"


@pytest.mark.parametrize("dx,dy,frames", [(1, 0, 500), (-1, 0, 500), (0, 1, 300), (0, -1, 300)])
def test_walking_builds_at_most_one_chunk_per_frame(bot, monkeypatch, dx, dy, frames):
    ws = world(bot)
    settle(bot)
    counter = count_builds(monkeypatch)
    built_total = 0
    for _ in range(frames):
        before = counter["n"]
        ws._move(dx, dy, DT)
        bot.tick()
        made = counter["n"] - before
        assert made <= 1, f"Một khung hình dựng tới {made} mảng map"
        built_total += made
    assert built_total > 0, "Đi xa phải có dựng thêm mảng mới, nếu không phép đo này không có ý nghĩa"


def test_chunks_are_ready_before_the_camera_arrives(bot, monkeypatch):
    """Đi bình thường thì hàm vẽ không bao giờ phải tự dựng, mảng đã được dựng trước."""
    ws = world(bot)
    settle(bot)
    size = CHUNK * TILE
    for _ in range(400):
        ws._move(1, 0, DT)
        ws.update(DT)
        cx0, cy0 = int(ws.cam_x // size), int(ws.cam_y // size)
        cx1, cy1 = int((ws.cam_x + W) // size), int((ws.cam_y + H) // size)
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                inside = 0 <= cx * CHUNK < ws.map.w and 0 <= cy * CHUNK < ws.map.h
                assert not inside or (cx, cy) in ws.map._chunks, f"Mảng {cx},{cy} chưa có khi đã vào khung nhìn"
        ws.draw(bot.screen)


def test_chunk_memory_stays_limited(bot):
    ws = world(bot)
    settle(bot, 60)
    for i in range(1500):
        ws._move(1 if (i // 500) % 2 == 0 else -1, 0, DT)
        bot.tick()
        assert len(ws.map._chunks) <= MAX_CHUNKS
    assert tilemap.PREFETCH_MARGIN >= 1


def test_prefetch_does_nothing_once_ready(bot, monkeypatch):
    world(bot)
    settle(bot)
    counter = count_builds(monkeypatch)
    bot.tick(60)
    assert counter["n"] == 0, "Đứng yên thì không dựng gì thêm"


def test_sound_effects_still_play_after_ambient_starts():
    """Lỗi cũ: giữ cả 8 kênh cho tiếng nền nên mọi tiếng động trên map bị tắt tiếng."""
    pygame.init()
    a = audio.Audio()
    if not a._ok:
        pytest.skip("Máy không có bộ trộn âm thanh")
    a.ambient("river")
    assert pygame.mixer.Channel(audio.AMBIENT_CHANNEL).get_busy(), "Tiếng nền phải đang phát"
    effect = pygame.mixer.Sound(str(audio.SFX_DIR / "step.ogg"))
    channel = effect.play()
    assert channel is not None, "Vẫn phải còn kênh cho tiếng động"
    a.ambient(None)
    assert not pygame.mixer.Channel(audio.AMBIENT_CHANNEL).get_busy()


def test_buttons_and_map_are_drawn_from_ready_images(bot):
    """Vẽ lại nút nhiều lần phải dùng đúng một ảnh đã ghép, nút đổi trạng thái thì có ảnh riêng."""
    from core import ui

    ui._button_cache.clear()
    button = ui.Button((10, 10, 120, 40), "Thử", None, "gold")
    surface = pygame.Surface((200, 80))
    button.draw(surface)
    button.draw(surface)
    assert len(ui._button_cache) == 1
    button.hover = True
    button.draw(surface)
    assert len(ui._button_cache) == 2


def test_offscreen_actors_are_skipped(bot, monkeypatch):
    ws = world(bot)
    settle(bot, 5)
    calls = {"n": 0}
    original = ws._visible

    def counted(a):
        calls["n"] += 1
        return original(a)

    monkeypatch.setattr(ws, "_visible", counted)
    ws.draw(bot.screen)
    assert calls["n"] < len(ws.actors), "Không được hỏi trạng thái của mọi vật thể mỗi khung"


def test_sounds_can_be_preloaded():
    pygame.init()
    a = audio.Audio()
    if not a._ok:
        pytest.skip("Máy không có bộ trộn âm thanh")
    a.preload()
    assert "buoc" in a._cache and "chem" in a._cache and "trong" in a._cache
    assert "nen:rain" in a._cache, "Tiếng nền phải được giải nén sẵn"


def test_audio_buffer_is_large_enough_for_the_web():
    assert audio.MIXER_BUFFER / audio.MIXER_RATE >= 0.08, "Bộ đệm phải chịu được một khung hình chậm trên web"
