"""Điểm vào Game_Client. pygbag yêu cầu vòng lặp async và await asyncio.sleep(0) mỗi khung hình."""

import asyncio
import sys
import traceback
from pathlib import Path

IS_WEB = sys.platform == "emscripten"
if not IS_WEB:
    # Trên desktop, thư mục `shared/` nằm cạnh `game/`; khi build web nó được chép vào cùng thư mục
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pygame  # noqa: E402
from core import audio, fonts, theme, ui  # noqa: E402
from core.audio import Audio  # noqa: E402
from core.scene import SceneManager  # noqa: E402
from core.state import GameState  # noqa: E402

MAX_DT = 0.05


class App:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.state = GameState()
        self.audio = Audio()
        self.audio.preload()
        self.audio.enabled = self.state.settings.get("sound", True)
        self.toasts = ui.Toasts()
        self.scenes = SceneManager()
        self.go_title()

    def toast(self, message: str, color=theme.GOLD, seconds: float = 3.0):
        self.toasts.add(message, color, seconds)

    def go_title(self):
        from scenes.title import TitleScene  # nhập muộn để màn hình tải hiện ra trước

        self.scenes.reset(TitleScene(self))

    def frame(self, dt: float, events) -> None:
        for event in events:
            self.scenes.handle(event)
        self.scenes.update(dt)
        self.toasts.update(dt)
        self.scenes.draw(self.screen)
        self.toasts.draw(self.screen)


def _make_screen() -> pygame.Surface:
    size = (theme.WIDTH, theme.HEIGHT)
    if IS_WEB:
        return pygame.display.set_mode(size)
    return pygame.display.set_mode(size, pygame.SCALED | pygame.RESIZABLE)


def _draw_loading(screen: pygame.Surface) -> None:
    screen.fill(theme.LACQUER)
    fonts.text(screen, "Sử Ký Điều Tra", fonts.font("black", 48), theme.GOLD_LIGHT, (theme.WIDTH // 2, 320), "center")
    fonts.text(screen, "Đang mở cuộn sử...", fonts.font("italic", 20), theme.PAPER_3, (theme.WIDTH // 2, 380), "center")
    pygame.display.flip()


def _draw_crash(screen: pygame.Surface, error: str) -> None:
    """Hiện lỗi ngay trên màn hình thay vì màn đen, để dễ báo lỗi khi chạy trên trình duyệt."""
    screen.fill((40, 16, 14))
    fonts.text(screen, "Game gặp lỗi. Hãy tải lại trang; tiến trình đã lưu vẫn còn.", fonts.font("bold", 22), theme.GOLD_LIGHT, (40, 40))
    y = 90
    for line in error.strip().splitlines()[-16:]:
        fonts.text(screen, line[:130], fonts.font("ui", 15), theme.PAPER, (40, y))
        y += 24
    pygame.display.flip()


async def main() -> None:
    try:
        pygame.mixer.pre_init(audio.MIXER_RATE, audio.MIXER_FORMAT, audio.MIXER_CHANNELS, audio.MIXER_BUFFER)
    except pygame.error:
        pass
    pygame.init()
    screen = _make_screen()
    pygame.display.set_caption("Sử Ký Điều Tra")
    _draw_loading(screen)
    await asyncio.sleep(0)
    clock = pygame.time.Clock()
    app = App(screen)
    running = True
    crashed = False
    while running:
        dt = min(MAX_DT, (clock.tick() if IS_WEB else clock.tick(60)) / 1000)
        events = pygame.event.get()
        if any(e.type == pygame.QUIT for e in events):
            running = False
        if not crashed:
            try:
                app.frame(dt, events)
                if not app.scenes.top:
                    app.go_title()
            except Exception:  # noqa: BLE001 - lỗi trong một khung hình không được làm treo trang web
                crashed = True
                error = traceback.format_exc()
                print(error)
                _draw_crash(screen, error)
        pygame.display.flip()
        await asyncio.sleep(0)
    app.state.save()
    pygame.quit()


asyncio.run(main())
