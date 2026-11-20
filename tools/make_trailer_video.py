"""Xuất video cho trang giới thiệu: trailer hướng dẫn, rồi nhiệm vụ cuối và đoạn kết của game. Cần có ffmpeg.

    .venv/Scripts/python tools/make_trailer_video.py
    .venv/Scripts/python tools/make_trailer_video.py --doan-ket duong/dan/doan_ket.mp4   # thêm bản chỉ có đoạn kết

Video gồm ba đoạn, mỗi đoạn một nhạc nền:
1. Trailer hướng dẫn: chạy đúng scene TrailerScene từng khung hình, nên luôn khớp với thứ người chơi thấy trong game.
2. Nhiệm vụ cuối: trận Chiến dịch Điện Biên Phủ (SiegeBattle) diễn theo nhịp xem được: chọn phương châm, kéo pháo, đánh
   từng cứ điểm theo đúng đợt.
3. Qua cổng cuối Màn 3 rồi đoạn kết (EndingScene) có cờ, có nguồn.
Trước khi quay đoạn 2 và 3, người chơi máy chơi hết ba màn (không ghi hình) để màn "Hành trình của bạn" hiện số liệu thật.
Phần hướng dẫn xem trong game (TrailerScene) không có đoạn kết, chỉ video trên trang giới thiệu có.

Pixel art rất dễ nhoè khi nén: yuv420p chỉ giữ màu ở nửa độ phân giải, nên viền màu bị bệt. Mỗi đoạn được ghi tạm ở 4:4:4,
khi ghép thì phóng đúng gấp đôi bằng điểm ảnh gần nhất: mỗi điểm ảnh gốc thành khối 2x2 và giữ nguyên màu.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "game"), str(ROOT / "game" / "tests")]

import pygame  # noqa: E402
from core import diorama, fonts, platform_io, theme, ui  # noqa: E402
from core.sprites import TILE  # noqa: E402
from scenes import battle as battle_mod  # noqa: E402
from scenes.battle import make_battle  # noqa: E402
from scenes.ending import BEATS as END_BEATS  # noqa: E402
from scenes.ending import EndingScene  # noqa: E402
from scenes.trailer import BEATS, CAPTION, TrailerScene  # noqa: E402
from test_playthrough import Bot, play_relic, play_story, play_timeline, walk_near  # noqa: E402

FPS = 30
DT = 1 / FPS
OUT = ROOT / "web" / "video" / "trailer.mp4"
POSTER = ROOT / "web" / "img" / "trailer.png"
MUSIC_DIR = ROOT / "game" / "assets" / "pixel" / "music"
POSTER_BEAT = "_b_battle"
POSTER_AT = 0.7
VIDEO_SCALE = 2
CRF = 24
CARD_TIME = 5.5
FADE = 0.6
END_HOLD = 6.0  # dừng ở cảnh "Hành trình của bạn" bấy nhiêu giây rồi tối dần

CARD_FINAL = ("Nhiệm vụ cuối: Chiến dịch Điện Biên Phủ năm 1954",
              "Di tích cuối của Màn 3, Lòng chảo Điện Biên Phủ, là trận đánh cuối của game: chọn phương châm tác chiến, "
              "kéo pháo đúng nhịp qua sườn núi, rồi đánh từng cứ điểm theo đúng đợt của chiến dịch.")
CARD_GATE = ("Qua cổng cuối là đoạn kết",
             "Báo cáo Cụ Đồ Sử, dựng xong dòng thời gian thì cổng cuối của Màn 3 mở ra. Bước qua cổng là đoạn kết: những "
             "lá cờ năm 1954, và lời nhắc phải đến ngày 30/4/1975 đất nước mới thống nhất.")


class Segment:
    """Ghi một đoạn video tạm (chưa có tiếng) từ màn hình game, đếm số khung hình để biết dài bao nhiêu."""

    def __init__(self, path: Path, size: tuple[int, int]):
        self.path = path
        self.frames = 0
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}",
               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "10", "-pix_fmt", "yuv444p",
               str(path)]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, screen: pygame.Surface):
        self.proc.stdin.write(pygame.image.tobytes(screen, "RGB"))
        self.frames += 1

    @property
    def seconds(self) -> float:
        return self.frames / FPS

    def close(self) -> float:
        self.proc.stdin.close()
        if self.proc.wait() != 0:
            raise SystemExit("ffmpeg báo lỗi khi ghi đoạn tạm")
        return self.seconds


def fade(screen: pygame.Surface, alpha: float):
    if alpha > 0:
        ui.veil(screen, (0, 0, 0, int(255 * min(1.0, alpha))))


def frame(bot, seg: Segment, black: float = 0.0):
    bot.scenes.update(DT)
    bot.scenes.draw(bot.screen)
    fade(bot.screen, black)
    seg.write(bot.screen)


def run(bot, seg: Segment, seconds: float, fade_in: float = 0.0, fade_out: float = 0.0):
    n = max(1, round(seconds * FPS))
    for i in range(n):
        t = i / FPS
        black = 0.0
        if fade_in and t < fade_in:
            black = 1 - t / fade_in
        if fade_out and seconds - t < fade_out:
            black = 1 - (seconds - t) / fade_out
        frame(bot, seg, black)


def card(bot, seg: Segment, bg: str, title: str, text: str):
    """Thẻ chuyển đoạn, cùng kiểu khung lời dẫn của trailer."""
    back = diorama.scene(bg).copy()
    ui.veil(back, (10, 6, 4, 150))
    ui.lacquer_panel(back, CAPTION, 246)
    fonts.text(back, title, fonts.font("bold", 26), theme.GOLD_LIGHT, (CAPTION.x + 30, CAPTION.y + 18))
    fonts.paragraph(back, text, fonts.font("serif", 19), theme.PAPER, CAPTION.x + 30, CAPTION.y + 60, CAPTION.w - 60, gap=2)
    n = round(CARD_TIME * FPS)
    for i in range(n):
        t = i / FPS
        bot.screen.blit(back, (0, 0))
        fade(bot.screen, max(1 - t / FADE, 1 - (CARD_TIME - t) / FADE, 0.0))
        seg.write(bot.screen)


def press(group, label: str):
    for b in group.buttons:
        if label in b.label and b.enabled:
            b.click()
            return
    raise SystemExit(f"Không thấy nút '{label}'")


# ----- 1. trailer hướng dẫn -----
def record_trailer(bot, seg: Segment):
    scene = TrailerScene(bot, recording=True)
    bot.scenes.reset(scene)
    total = sum(beat[2] for beat in BEATS)
    poster_done = False
    for _ in range(int(total * FPS)):
        frame(bot, seg)
        beat = BEATS[scene.i]
        if not poster_done and beat[3] == POSTER_BEAT and scene.t >= beat[2] * POSTER_AT:
            pygame.image.save(bot.screen, POSTER)
            poster_done = True


# ----- chơi hết ba màn (không ghi hình) -----
def play_to_last_gate(bot):
    """Người chơi máy chơi hết ba màn như bộ kiểm thử, dừng trước cổng cuối của Màn 3 (cổng đã mở)."""
    st = bot.state
    st.tutorial_seen = True
    bot.go_title()
    bot.tick(3)
    bot.press(bot.scenes.top.group, "Bắt đầu hành trình")
    play_story(bot)
    for i, lid in enumerate(st.order):
        ws = bot.scenes.top
        bot.tick(3)
        for relic in sorted(st.levels[lid]["relics"], key=lambda r: bool(r.get("optional"))):
            play_relic(bot, ws, relic)
        walk_near(bot, ws, ws.mentor)
        ws.interact(ws.mentor)
        play_story(bot)
        play_timeline(bot, bot.scenes.top, lid)
        if i + 1 < len(st.order):
            ws.x, ws.y = ws.portal.x, ws.portal.y - 10
            while bot.scenes.top is ws:
                bot.tick()
    ws = bot.scenes.top
    assert ws.level_id == st.order[-1] and ws._portal_open(), "Chưa tới được cổng cuối"
    return ws


# ----- 2. nhiệm vụ cuối: Chiến dịch Điện Biên Phủ -----
def record_final_battle(bot, ws, seg: Segment):
    card(bot, seg, "dien_bien", *CARD_FINAL)
    data = ws.state.levels[ws.level_id]["battles"][-1]
    sc = make_battle(bot, data)
    bot.scenes.push(sc)
    run(bot, seg, 7.0, fade_in=FADE)  # màn giới thiệu trận: tên trận, bối cảnh, cách chơi
    press(sc.group, "Vào trận")
    run(bot, seg, 4.0)  # chọn phương châm
    press(sc.group, "Đánh chắc")
    last = -9.0
    guard = 0
    while sc.stage == "haul":  # kéo pháo: bấm đúng lúc vạch nhịp vào giữa
        guard += 1
        if guard > 60 * FPS:
            raise SystemExit("Kéo pháo không xong")
        if sc.arrive_t is None and abs(sc.mark - 0.5) <= battle_mod.SWEET * 0.5 and seg.seconds - last > 0.6:
            press(sc.group, "DÔ TA")
            last = seg.seconds
        frame(bot, seg)
    run(bot, seg, 2.0)
    for ph in battle_mod.PHASES:  # đánh từng cứ điểm theo đúng đợt
        for nid in ph["targets"]:
            run(bot, seg, 1.2)
            sc._attack(nid)
            guard = 0
            while sc.busy > 0:
                guard += 1
                if guard > 10 * FPS:
                    raise SystemExit("Đánh cứ điểm không xong")
                frame(bot, seg)
    guard = 0
    while sc.stage != "result":
        guard += 1
        if guard > 20 * FPS:
            raise SystemExit("Trận không kết thúc")
        frame(bot, seg)
    run(bot, seg, 8.0, fade_out=1.0)  # màn kết quả: lời kết của trận và nguồn
    bot.scenes.pop(None)  # bỏ trận quay thử, không tính lại kết quả


# ----- 3. qua cổng cuối, đoạn kết -----
def record_gate_and_ending(bot, ws, seg: Segment, poster: Path | None) -> float:
    card(bot, seg, "huong_dan", *CARD_GATE)
    ws.banner = None
    ws.x, ws.y = ws.portal.x, ws.portal.y + TILE * 3
    ws._snap_camera()
    run(bot, seg, 1.5, fade_in=FADE)
    ws._walk_to(ws.portal.x, ws.portal.y)
    guard = 0
    while not isinstance(bot.scenes.top, EndingScene):
        guard += 1
        if guard == 4 * FPS:  # đường bị chắn thì đặt sát cổng cho cổng tự kéo vào
            ws.x, ws.y = ws.portal.x, ws.portal.y - 10
        if guard > 10 * FPS:
            raise SystemExit("Không qua được cổng cuối")
        frame(bot, seg)
    start = seg.seconds
    ending = bot.scenes.top
    poster_done = poster is None
    total = sum(b[2] for b in END_BEATS[:-1]) + END_HOLD
    n = round(total * FPS)
    for i in range(n):
        frame(bot, seg, max(0.0, 1 - (n - i) / (1.5 * FPS)))
        if not poster_done and END_BEATS[ending.i][3] == "_e_cotco" and ending.t >= 6.0:
            pygame.image.save(bot.screen, poster)
            poster_done = True
    return start


# ----- ghép -----
def audio_chain(i: int, dur: float, volume: float, fade_in: bool) -> str:
    parts = [f"[{i}:a]atrim=0:{dur:.3f}", "asetpts=PTS-STARTPTS", "aresample=44100", "aformat=channel_layouts=stereo",
             f"volume={volume}"]
    if fade_in:
        parts.append("afade=t=in:d=1")
    parts.append(f"afade=t=out:st={max(0.0, dur - 1.5):.3f}:d=1.5")
    return ",".join(parts)


def mux(segments: list[tuple[Segment, str, float]], out: Path):
    """Ghép các đoạn tạm, mỗi đoạn một nhạc nền, phóng gấp đôi bằng điểm ảnh gần nhất rồi nén lần cuối."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for seg, _music, _vol in segments:
        cmd += ["-i", str(seg.path)]
    for _seg, music, _vol in segments:
        cmd += ["-stream_loop", "-1", "-i", str(MUSIC_DIR / f"{music}.ogg")]
    n = len(segments)
    v = "".join(f"[{i}:v]" for i in range(n))
    chains = [f"{v}concat=n={n}:v=1:a=0,scale=iw*{VIDEO_SCALE}:ih*{VIDEO_SCALE}:flags=neighbor,format=yuv420p[v]"]
    for k, (seg, _music, vol) in enumerate(segments):
        chains.append(audio_chain(n + k, seg.seconds, vol, k > 0) + f"[a{k}]")
    chains.append("".join(f"[a{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1[a]")
    cmd += ["-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(CRF), "-tune", "animation",
            "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)]
    if subprocess.run(cmd).returncode != 0:
        raise SystemExit("ffmpeg báo lỗi khi ghép")


def cut_ending(seg: Segment, start: float, out: Path):
    """Bản chỉ có đoạn kết (để chèn slide): giữ khung 1280x720 cho nhẹ, nhạc nền của đoạn kết."""
    dur = seg.seconds - start
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", str(seg.path),
           "-stream_loop", "-1", "-i", str(MUSIC_DIR / "title.ogg"),
           "-filter_complex", f"[0:v]format=yuv420p[v];{audio_chain(1, dur, 0.7, True)}[a]",
           "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "slow", "-crf", "22",
           "-tune", "animation", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)]
    if subprocess.run(cmd).returncode != 0:
        raise SystemExit("ffmpeg báo lỗi khi cắt đoạn kết")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doan-ket", type=Path, help="xuất thêm bản chỉ có đoạn kết (mp4) và ảnh bìa (png cùng tên)")
    args = ap.parse_args()
    platform_io.write_save = lambda data: None
    platform_io.load_save = lambda: None
    pygame.init()
    bot = Bot()
    bot.state.reset()
    size = bot.screen.get_size()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        intro = Segment(tmp / "1_trailer.mkv", size)
        record_trailer(bot, intro)
        intro.close()
        print(f"Đoạn 1, trailer: {intro.seconds:.0f} giây")
        ws = play_to_last_gate(bot)
        print("Người chơi máy đã chơi hết ba màn, đứng trước cổng cuối")
        final = Segment(tmp / "2_final.mkv", size)
        record_final_battle(bot, ws, final)
        final.close()
        print(f"Đoạn 2, Chiến dịch Điện Biên Phủ: {final.seconds:.0f} giây")
        end = Segment(tmp / "3_ending.mkv", size)
        poster = args.doan_ket.with_suffix(".png") if args.doan_ket else None
        start = record_gate_and_ending(bot, ws, end, poster)
        end.close()
        print(f"Đoạn 3, cổng cuối và đoạn kết: {end.seconds:.0f} giây (đoạn kết từ giây {start:.1f})")
        mux([(intro, "road", 0.7), (final, "fight", 0.55), (end, "title", 0.7)], OUT)
        total = intro.seconds + final.seconds + end.seconds
        print(f"Đã xuất {OUT.name}: {total:.0f} giây, {OUT.stat().st_size / 1024 / 1024:.1f} MB")
        if args.doan_ket:
            args.doan_ket.parent.mkdir(parents=True, exist_ok=True)
            cut_ending(end, start, args.doan_ket)
            print(f"Đã xuất {args.doan_ket}: {end.seconds - start:.0f} giây, {args.doan_ket.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
