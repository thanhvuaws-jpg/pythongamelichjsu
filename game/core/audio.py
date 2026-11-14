"""Âm thanh: ưu tiên file thật trong gói asset, thiếu thì tự tổng hợp. Tạo khi cần lần đầu vì khá tốn trên WebAssembly."""

from __future__ import annotations

import array
import random
from pathlib import Path

import pygame

MUSIC_DIR = Path(__file__).resolve().parent.parent / "assets" / "pixel" / "music"
SFX_DIR = MUSIC_DIR.parent / "sfx"
MUSIC_VOLUME = 0.35
SFX_VOLUME = 0.6
# Phải khớp với file nhạc (44100 Hz, stereo). Từng để 22050 Hz mono: máy phải hạ chất lượng ngay lúc phát nên nhạc bị rè.
# Bộ đệm lớn vì trên WebAssembly âm thanh chạy chung luồng với game, khung hình chậm một chút là thiếu dữ liệu và kêu "è è".
MIXER_RATE, MIXER_FORMAT, MIXER_CHANNELS, MIXER_BUFFER = 44100, -16, 2, 4096
AMBIENT_VOLUME = 0.22
AMBIENT_CHANNEL = 0  # chỉ giữ kênh đầu tiên cho tiếng nền, các kênh còn lại cho tiếng động
AMBIENT_FILES = ("rain", "river", "wind")
_FILES = {
    "no": "explosion", "va": "impact", "chem": "slash", "kiem": "sword", "ban": "launch", "lua": "fire", "nuoc": "splash",
    "click": "move", "dung": "coin", "sai": "cancel", "nhan": "powerup", "thang": "success", "nang": "levelup",
    "trung": "hit", "hoi": "heal", "phep": "magic", "buoc": "step",
    "giong1": "voice1", "giong2": "voice2", "giong3": "voice3", "giong4": "voice4",
}
# Âm lặp lại liên tục phải nhỏ hơn hẳn để khỏi át lời thoại và nhạc nền
_QUIET = {"buoc": 0.16, "click": 0.4, "giong1": 0.3, "giong2": 0.3, "giong3": 0.3, "giong4": 0.3}
_NOTES = {
    "click": ([(880, 0.03)], 0.07),
    "dung": ([(660, 0.07), (990, 0.12)], 0.14),
    "sai": ([(196, 0.16), (147, 0.2)], 0.14),
    "nhan": ([(784, 0.07), (988, 0.07), (1319, 0.14)], 0.13),
    "dau": ([(330, 0.05), (262, 0.1)], 0.2),
    "thang": ([(523, 0.1), (659, 0.1), (784, 0.1), (1047, 0.28)], 0.14),
    "buoc": ([(440, 0.03)], 0.04),
}
_NOISE = {"no": (0.5, 0.55), "va": (0.13, 0.3), "trong": (0.22, 0.5)}


class Audio:
    def __init__(self):
        self.enabled = True
        self._cache: dict[str, pygame.mixer.Sound] = {}
        self._ok = False
        self._track: str | None = None
        self._ambient: str | None = None
        try:
            init = pygame.mixer.get_init()
            if init and init[1] == -16:
                self.rate, _, self.channels = init
                self._ok = True
                pygame.mixer.set_reserved(AMBIENT_CHANNEL + 1)
        except pygame.error:
            pass

    def _tone(self, notes, vol):
        buf = array.array("h")
        for freq, dur in notes:
            n = int(self.rate * dur)
            for i in range(n):
                phase = (i * freq / self.rate) % 1.0
                wave = 1.0 if phase < 0.5 else -1.0
                env = min(1.0, i / (0.004 * self.rate)) * (1 - i / n) ** 1.5
                buf.extend([int(32767 * vol * env * wave)] * self.channels)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _noise(self, dur, vol):
        buf = array.array("h")
        n = int(self.rate * dur)
        y = 0.0
        for i in range(n):
            y += (random.uniform(-1, 1) - y) * 0.14
            v = int(32767 * vol * (1 - i / n) ** 2 * y * 3)
            buf.extend([max(-32767, min(32767, v))] * self.channels)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    @staticmethod
    def _from_file(name: str):
        """Âm thanh thật lấy từ gói asset; thiếu file thì quay về âm tự tổng hợp."""
        file = _FILES.get(name)
        if not file:
            return None
        try:
            snd = pygame.mixer.Sound(str(SFX_DIR / f"{file}.ogg"))
            snd.set_volume(_QUIET.get(name, SFX_VOLUME))
            return snd
        except (pygame.error, OSError):
            return None

    def music(self, name: str | None):
        """Phát lặp một bản nhạc nền; gọi lại cùng tên thì không phát lại từ đầu."""
        if name == self._track or not self._ok:
            return
        self._track = name
        try:
            if not name or not self.enabled:
                pygame.mixer.music.stop()
                return
            pygame.mixer.music.load(str(MUSIC_DIR / f"{name}.ogg"))
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass

    def ambient(self, name: str | None):
        """Tiếng nền lặp lại (mưa, sông, gió) trên một kênh riêng để tiếng động khác không chiếm mất."""
        if name == self._ambient or not self._ok:
            return
        self._ambient = name
        try:
            channel = pygame.mixer.Channel(AMBIENT_CHANNEL)
            channel.stop()
            if name and self.enabled:
                channel.play(self._ambient_sound(name), loops=-1)
        except (pygame.error, OSError):
            pass

    def _ambient_sound(self, name: str) -> pygame.mixer.Sound:
        snd = self._cache.get(f"nen:{name}")
        if snd is None:
            snd = pygame.mixer.Sound(str(SFX_DIR / f"{name}.ogg"))
            snd.set_volume(AMBIENT_VOLUME)
            self._cache[f"nen:{name}"] = snd
        return snd

    def preload(self):
        """Giải nén sẵn mọi âm thanh lúc còn ở màn hình tải; giải nén giữa lúc chơi sẽ làm khựng khung hình và giật nhạc."""
        if not self._ok:
            return
        try:
            for name in {*_FILES, *_NOTES, *_NOISE}:
                self._sound(name)
            for name in AMBIENT_FILES:
                self._ambient_sound(name)
        except (pygame.error, OSError):
            pass  # thiếu file thì phát sau cũng tự bỏ qua, không làm hỏng game

    def set_enabled(self, on: bool):
        self.enabled = on
        track, self._track = self._track, None
        self.music(track)
        nen, self._ambient = self._ambient, None
        self.ambient(nen)

    def play(self, name: str):
        if not (self._ok and self.enabled):
            return
        try:
            snd = self._sound(name)
            if snd is not None:
                snd.play()
        except pygame.error:
            self._ok = False

    def _sound(self, name: str) -> pygame.mixer.Sound | None:
        snd = self._cache.get(name)
        if snd is None:
            snd = self._from_file(name)
            if snd is None:
                if name in _NOTES:
                    snd = self._tone(*_NOTES[name])
                elif name in _NOISE:
                    snd = self._noise(*_NOISE[name])
                else:
                    return None
            self._cache[name] = snd
        return snd
