"""Kiểm thử hồi ức dựng thành cảnh diễn: đủ cảnh cho mọi đoạn, chạy không lỗi, đúng các nguyên tắc trình bày."""

# isort: skip_file
from __future__ import annotations

import json
from pathlib import Path

import pygame
import pytest
from test_playthrough import Bot  # nạp trước: file này thêm đường dẫn game vào sys.path
from core import fx, platform_io, stage_scenes
from core.stage import Stage, Track
from scenes.story import StoryScene

CONTENT = Path(__file__).resolve().parents[1] / "content"
MODERN = ("tan_trao:", "ha_noi:", "ba_dinh:", "song_lo:", "bien_gioi:", "dien_bien:")


class Mute:
    def __init__(self):
        self.played = []

    def play(self, name, *_a, **_k):
        self.played.append(name)


def memory_nodes():
    """Mọi đoạn hồi ức trong nội dung, kèm mã hội thoại để báo lỗi dễ đọc."""
    out = []

    def walk(x, where):
        if isinstance(x, dict):
            nodes = x.get("nodes") or x.get("lines")
            if isinstance(nodes, list):
                for n in nodes:
                    if isinstance(n, dict) and n.get("memory"):
                        out.append((x.get("id", where), n))
            for v in x.values():
                walk(v, where)
        elif isinstance(x, list):
            for v in x:
                walk(v, where)

    for f in ("man1", "man2", "man3", "extras"):
        walk(json.loads((CONTENT / f"{f}.json").read_text(encoding="utf-8")), f)
    return out


@pytest.fixture(scope="module", autouse=True)
def display():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    yield screen


def run(key: str, violence: str, seconds: float = 9.0, screen=None):
    f = fx.Fx(violence, old=True)
    st = Stage(f, Mute())
    st.set_beat(key)
    surf = screen or pygame.Surface((1280, 720))
    dt = 1 / 30
    for _ in range(int(seconds / dt)):
        st.update(dt)
        f.update(dt)
        st.draw(surf, f.offset())
        f.draw(surf)
    return st


def test_every_memory_has_a_scene():
    nodes = memory_nodes()
    assert len(nodes) >= 50
    missing = [(did, n["text"][:50]) for did, n in nodes if not (n.get("stage") or n.get("cine"))]
    assert not missing, f"Đoạn hồi ức còn là tranh tĩnh: {missing}"
    unknown = [n["stage"] for _, n in nodes if n.get("stage") and n["stage"] not in stage_scenes.BEATS]
    assert not unknown, f"Thẻ stage không có kịch bản: {unknown}"
    used = {n["stage"] for _, n in nodes if n.get("stage")}
    assert used == set(stage_scenes.BEATS), f"Kịch bản thừa: {set(stage_scenes.BEATS) - used}"


@pytest.mark.parametrize("key", sorted(stage_scenes.BEATS))
@pytest.mark.parametrize("violence", ["day_du", "nhe"])
def test_scene_plays_through(key, violence, display):
    st = run(key, violence, screen=display)
    assert st.t > 8.9
    assert any(a.visible(st.t) for a in st.actors) or st.things, "Cảnh phải có người hoặc vật để xem"
    for a in st.actors:
        x, y = a.pos(1.0)
        assert -2000 < x < 3400 and -400 < y < 1200


@pytest.mark.parametrize("key", [k for k in stage_scenes.BEATS if k.startswith(MODERN)])
def test_modern_scenes_show_no_deaths(key):
    """Phần 1945 - 1954 không vẽ người ngã xuống, không có máu, giống phần trận đánh."""
    st = run(key, "day_du", 10.0)
    assert all(a.dead_at is None for a in st.actors)
    assert not st.fx.stains, "Cảnh hiện đại không được để lại vết máu"


def test_mild_violence_hides_falls():
    """Chế độ giảm nhẹ: không ai nằm xuống; lính địch tháo chạy, nhân vật chính quỳ xuống."""
    for key in ("tot_dong:ambush", "chi_linh:le_lai", "ai_chau:betray", "chi_lang:ma_yen"):
        st = run(key, "nhe", 9.0)
        assert all(a.dead_at is None for a in st.actors), key
    st = run("chi_linh:le_lai", "nhe", 9.0)
    lai = next(a for a in st.actors if a.mount)
    assert lai._mode(8.0) == "kneel"


def test_scene_is_a_pure_function_of_time():
    """Đọc chậm hay bấm nhanh, cùng một thời điểm luôn ra cùng một cảnh."""
    a = run("dien_hong:gather", "day_du", 4.0)
    b = Stage(fx.Fx("day_du", old=True), Mute())
    b.set_beat("dien_hong:gather")
    b.update(4.0)
    pa = [round(c, 3) for x in a.actors for c in x.pos(4.0)]
    pb = [round(c, 3) for x in b.actors for c in x.pos(4.0)]
    assert pa == pb


def test_track_moves_jumps_and_reports_direction():
    tr = Track(0, 0)
    end = tr.go(1.0, 100, 0, 50)
    assert end == pytest.approx(3.0)
    assert tr.at(0.5)[:3] == (0, 0, False)
    x, y, moving, d, _ = tr.at(2.0)
    assert (round(x), y, moving, d) == (50, 0, True, "right")
    tr.jump(4.0, 500, 300)
    assert tr.at(5.0)[:2] == (500, 300)
    assert tr.at(5.0)[3] == "right", "Sau khi đứng lại vẫn nhìn theo hướng vừa đi"


def test_labels_only_use_wording_from_the_story():
    """Mốc thời gian trên nhãn phải khớp lời kể của đoạn đó hoặc đoạn ngay trước, không tự thêm năm."""
    import re

    texts = {}
    for _, n in memory_nodes():
        if n.get("stage"):
            texts.setdefault(n["stage"], "")
            texts[n["stage"]] += " " + n["text"]
    for key, text in texts.items():
        st = Stage(fx.Fx("day_du", old=True), Mute())
        st.set_beat(key)
        years = set(re.findall(r"\b1[0-9]{3}\b|\b9[0-9]{2}\b", text))
        for th in st.things:
            if th.layer != 2:
                continue
            label = getattr(th, "text", "")
            for y in re.findall(r"\b1[0-9]{3}\b|\b9[0-9]{2}\b", label):
                assert y in years or key in ALLOWED_YEARS and y in ALLOWED_YEARS[key], (key, label)


# Năm nằm ở lời dẫn ngay trước đoạn hồi ức (không phải trong chính đoạn đó) hoặc là mốc quen thuộc của sự kiện
ALLOWED_YEARS = {
    "binh_than:orange": {"1282"},
    "dien_hong:gather": {"1284"},
    "thien_mac:hold": {"1285"},
    "lam_son:rise": {"1418"},
    "tra_lan:advance": {"1424"},
    "tan_trao:delegates": {"1945"},
    "tan_trao:congress": {"1945"},
    "ha_noi:uprising": {"1945"},
    "ba_dinh:crowd": {"1945"},
    "ha_noi:night1946": {"1946"},
    "song_lo:ships": {"1947"},
    "bien_gioi:ambush": {"1950"},
    "dien_bien:porters": {"1953", "1954"},
    "dien_bien:pull_out": {"1954"},
    "dien_bien:him_lam": {"1954"},
    "dien_bien:a1": {"1954"},
    "ha_song:ask": {"1258"},
    "hoi_the:oath": {"1427"},
    "binh_ngo:proclaim": {"1428"},
    "tong:raid": {"1075"},
    "ai_chau:betray": {"937"},
    "ai_chau:drive_931": {"931"},
}


def test_story_scene_uses_stage_for_memory(monkeypatch):
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    bot = Bot()
    bot.state.reset()
    dlg = {"id": "t", "bg": "lang_co", "nodes": [
        {"text": "Mở đầu", "speaker": "Bà"},
        {"text": "Hồi ức", "memory": True, "stage": "dien_hong:shout", "fx": ["drum", "clash"]},
        {"text": "Bạch Đằng", "memory": True, "cine": "lure"},
    ]}
    story = StoryScene(bot, dlg)
    bot.scenes.reset(story)
    bot.tick(2)
    story._advance()
    assert isinstance(story.cine, Stage)
    assert story.ambient.kinds == {"drum"}, "Cảnh tự diễn thì không vẽ lính ngẫu nhiên đè lên"
    bot.tick(40)
    story._advance()
    from core.cinematic import TideMemory

    assert isinstance(story.cine, TideMemory), "Chuyển từ cảnh diễn sang cảnh Bạch Đằng không được lỗi"
    bot.tick(10)
