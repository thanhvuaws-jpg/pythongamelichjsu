"""Xuất trailer hướng dẫn trong game thành video cho trang giới thiệu. Cần có ffmpeg.

    .venv/Scripts/python tools/make_trailer_video.py

Chạy đúng scene TrailerScene từng khung hình, nên video luôn khớp với thứ người chơi thấy trong game.

Pixel art rất dễ nhoè khi nén: yuv420p chỉ giữ màu ở nửa độ phân giải, nên viền màu bị bệt. Phóng đúng gấp đôi bằng
điểm ảnh gần nhất thì mỗi điểm ảnh gốc thành khối 2x2 và giữ nguyên màu; trình duyệt thu nhỏ lại cũng vẫn nét.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "game"), str(ROOT / "game" / "tests")]

import pygame  # noqa: E402
from core import platform_io  # noqa: E402
from scenes.trailer import BEATS, TrailerScene  # noqa: E402
from test_playthrough import Bot  # noqa: E402

FPS = 30
OUT = ROOT / "web" / "video" / "trailer.mp4"
POSTER = ROOT / "web" / "img" / "trailer.png"
MUSIC = ROOT / "game" / "assets" / "pixel" / "music" / "road.ogg"
POSTER_BEAT = "_b_battle"
POSTER_AT = 0.7
VIDEO_SCALE = 2
CRF = 24


def main() -> None:
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    pygame.init()
    bot = Bot()
    bot.state.reset()
    scene = TrailerScene(bot, recording=True)
    bot.scenes.reset(scene)
    total = sum(beat[2] for beat in BEATS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{bot.screen.get_width()}x{bot.screen.get_height()}", "-r", str(FPS), "-i", "-",
        "-stream_loop", "-1", "-i", str(MUSIC),
        "-t", f"{total:.2f}", "-af", f"volume=0.7,afade=t=out:st={total - 2:.2f}:d=2",
        "-vf", f"scale=iw*{VIDEO_SCALE}:ih*{VIDEO_SCALE}:flags=neighbor",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(CRF), "-tune", "animation", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(OUT),
    ]
    encoder = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    poster_done = False
    for _ in range(int(total * FPS)):
        bot.scenes.update(1 / FPS)
        bot.scenes.draw(bot.screen)
        encoder.stdin.write(pygame.image.tobytes(bot.screen, "RGB"))
        beat = BEATS[scene.i]
        if not poster_done and beat[3] == POSTER_BEAT and scene.t >= beat[2] * POSTER_AT:
            pygame.image.save(bot.screen, POSTER)
            poster_done = True
    encoder.stdin.close()
    if encoder.wait() != 0:
        raise SystemExit("ffmpeg báo lỗi")
    print(f"Đã xuất {OUT.name}: {total:.0f} giây, {OUT.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
