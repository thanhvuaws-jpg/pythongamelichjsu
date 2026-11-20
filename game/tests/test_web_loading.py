"""Bản web tải nhanh hơn: nhạc nền tải ngầm sau khi vào game, phông cắt còn chữ Việt, màn tải riêng (tools/web_extras.py)."""

# isort: skip_file
from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

import pygame
import pytest
from test_playthrough import Bot  # noqa: F401 - nạp trước: file này thêm đường dẫn game vào sys.path
from core import audio

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import web_extras  # noqa: E402


@pytest.fixture()
def mixer():
    pygame.init()
    a = audio.Audio()
    if not a._ok:
        pytest.skip("Máy không có bộ trộn âm thanh")
    yield a
    pygame.mixer.music.stop()


def test_title_music_stays_in_the_first_download():
    assert "title" not in audio.LATER_MUSIC, "Màn tựa đề là cảnh đầu tiên, nhạc của nó phải có sẵn"
    for name in audio.LATER_MUSIC:
        assert (audio.MUSIC_DIR / f"{name}.ogg").exists(), name
    assert web_extras.later_music() == audio.LATER_MUSIC, "Lúc build phải tách đúng các bản game sẽ tải ngầm"


def test_missing_music_waits_then_plays_when_fetched(mixer, tmp_path, monkeypatch):
    monkeypatch.setattr(audio, "MUSIC_DIR", tmp_path)
    real = (ROOT / "game" / "assets" / "pixel" / "music" / "road.ogg").read_bytes()
    mixer.music("road")
    assert not pygame.mixer.music.get_busy(), "Chưa tải xong thì im, không được lỗi"

    async def fake_fetch(url):
        assert url == "music/road.ogg"
        return real

    asyncio.run(mixer.fetch_music(("road",), fetch=fake_fetch))
    assert (tmp_path / "road.ogg").read_bytes() == real
    assert not list(tmp_path.glob("*.tai")), "Tệp tạm phải được đổi tên xong"
    assert pygame.mixer.music.get_busy(), "Cảnh đang đợi đúng bản này thì tải xong phải tự phát"


def test_fetch_music_skips_files_it_has_and_survives_errors(mixer, tmp_path, monkeypatch):
    monkeypatch.setattr(audio, "MUSIC_DIR", tmp_path)
    (tmp_path / "road.ogg").write_bytes(b"co san")
    asked = []

    async def flaky(url):
        asked.append(url)
        if "temple" in url:
            raise OSError("mất mạng")
        return b"du lieu"

    asyncio.run(mixer.fetch_music(("road", "temple", "fight"), fetch=flaky))
    assert asked == ["music/temple.ogg", "music/fight.ogg"], "Bản đã có thì không tải lại"
    assert not (tmp_path / "temple.ogg").exists()
    assert (tmp_path / "fight.ogg").read_bytes() == b"du lieu", "Một bản lỗi không được chặn các bản sau"


def test_slim_fonts_keep_every_vietnamese_letter(tmp_path):
    pytest.importorskip("fontTools")
    from fontTools.ttLib import TTFont

    fonts = tmp_path / "assets" / "fonts"
    shutil.copytree(ROOT / "game" / "assets" / "fonts", fonts)
    (tmp_path / "chu.py").write_text('MOT = "Chữ riêng trong mã: ✦"', encoding="utf-8")
    web_extras.slim_fonts(tmp_path)
    viet = "ĂÂÊÔƠƯĐăâêôơưđ" + "".join(chr(c) for c in range(0x1EA0, 0x1EFA)) + "“”…—–·₫→★"
    for ttf in fonts.glob("*.ttf"):
        before = TTFont(ROOT / "game" / "assets" / "fonts" / ttf.name).getBestCmap()
        after = TTFont(ttf).getBestCmap()
        lost = [c for c in viet + "✦" if ord(c) in before and ord(c) not in after]
        assert not lost, f"{ttf.name} mất chữ {lost}"
        assert "fvar" not in TTFont(ttf), "Phông biến thiên phải được chốt về kiểu mặc định"


def test_loader_page_parts_are_filled():
    script, style, body = web_extras.loader_parts("sukydieutra-abc.tar.gz", 1_800_000)
    assert "__SK_CONFIG__" not in script and "sukydieutra-abc.tar.gz" in script
    assert "</script" not in script[len("<script>"):-len("</script>\n")], "Dữ liệu chèn vào không được đóng thẻ script"
    assert 'id="sk-load"' in body and "__skSetup" in body
    facts = web_extras._facts()
    assert len(facts) >= 20 and all(f["y"] and f["t"] for f in facts)
    assert sum(1 for f in facts if f["src"]) >= len(facts) - 2, "Mẩu sử trên màn tải phải kèm nguồn"
