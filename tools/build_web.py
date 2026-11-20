"""Đóng gói game sang WebAssembly bằng pygbag.

    .venv/Scripts/python tools/build_web.py            # chỉ build
    .venv/Scripts/python tools/build_web.py --serve    # build xong chạy thử tại http://127.0.0.1:8000

Kết quả nằm ở build/sukydieutra/build/web/ (index.html + gói .apk + music/), chép lên bất kỳ static hosting nào.
Bản web nhẹ hơn bản chạy trên máy: phông cắt còn chữ Việt, nhạc nền tải ngầm, có màn tải riêng (xem web_extras.py).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import web_extras

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "game"
OUT = ROOT / "build" / "sukydieutra"
WEB_DIR = OUT / "build" / "web"
MUSIC_STASH = ROOT / "build" / "music_later"  # ngoài OUT để pygbag không gói vào
GAME_PARTS = ("main.py", "core", "scenes", "content", "assets")
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", ".save", "tests")
PAGE_STYLE = """<style>
html, body { background: #1a1210 !important; }
canvas.emscripten {
  width: min(100vw, calc(100vh * 16 / 9)) !important;
  height: min(100vh, calc(100vw * 9 / 16)) !important;
}
/* Điện thoại: 100vh tính cả thanh địa chỉ đang hiện nên khung bị cắt dưới đáy; dvh là phần nhìn thấy thật */
@supports (height: 100dvh) {
  canvas.emscripten {
    width: min(100vw, calc(100dvh * 16 / 9)) !important;
    height: min(100dvh, calc(100vw * 9 / 16)) !important;
  }
}
</style>
"""
# Chế độ Chơi thử mở thẳng /game/: gắn nhắc xoay ngang và nút toàn màn hình như trang chơi
PAGE_SCRIPT = """<script src="/js/mobile.js?v=1"></script>
"""


def collect() -> None:
    """pygbag đóng gói nguyên thư mục, nên chép `game/` và `shared/` vào một chỗ cho đúng đường dẫn import."""
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for part in GAME_PARTS:
        src = GAME / part
        if src.is_dir():
            shutil.copytree(src, OUT / part, ignore=SKIP)
        else:
            shutil.copy2(src, OUT / part)
    shutil.copytree(ROOT / "shared", OUT / "shared", ignore=SKIP)
    print("Làm nhẹ gói tải đầu:")
    web_extras.slim_fonts(OUT)
    web_extras.split_music(OUT, MUSIC_STASH)


def patch_html(path: Path) -> None:
    """Script của pygbag ép canvas thành hình vuông khi cửa sổ hẹp hơn 16:9, nên khoá tỉ lệ bằng CSS; thêm phần cho
    điện thoại (web/js/mobile.js)."""
    html = path.read_text(encoding="utf-8")
    html = html.replace("</head>", PAGE_STYLE + "</head>", 1)
    html = html.replace("</body>", PAGE_SCRIPT + "</body>", 1)
    html = version_bundle(path.parent, html)
    html = add_loader(path.parent, html)
    path.write_text(html, encoding="utf-8")


def add_loader(web_dir: Path, html: str) -> str:
    """Thay chữ "Downloading... / Loading, please wait" mặc định bằng màn tải của game (tools/loader/)."""
    m = re.search(r'"(sukydieutra-[0-9a-f]{12}\.tar\.gz)"', html)
    bundle = m.group(1) if m else ""
    size = (web_dir / bundle).stat().st_size if bundle else 0
    script, style, body = web_extras.loader_parts(bundle, size)
    # charset phải đứng đầu: script màn tải dài, đẩy thẻ meta charset của pygbag ra quá 1024 byte đầu nên trình duyệt
    # (khi máy chủ không ghi charset) đoán sai bảng mã và chữ Việt trong script bị vỡ
    html = html.replace('<html lang="en-us">', '<html lang="vi"><meta charset="UTF-8">' + script, 1)
    html = html.replace("<title>Su Ky Dieu Tra</title>", "<title>Sử Ký Điều Tra</title>", 1)
    html = html.replace("</head>", style + "</head>", 1)
    return html.replace("<body>", "<body>" + body, 1)


def version_bundle(web_dir: Path, html: str) -> str:
    """Gói game mang tên theo nội dung (sukydieutra-<băm>.tar.gz), trang trỏ vào tên đó.

    Cloudflare và trình duyệt giữ đệm tệp theo tên: cùng một tên sukydieutra.tar.gz thì sau khi cập nhật người chơi
    vẫn nhận gói cũ hàng giờ (gặp 15/11/2026). index.html không bị giữ đệm, nên đổi tên là đủ. Tệp tên cũ vẫn để lại
    cho --serve và bản itch.io (itch dùng .apk)."""
    goc = web_dir / "sukydieutra.tar.gz"
    cu = '"sukydieutra.tar.gz"'
    if not goc.exists() or cu not in html:
        return html
    moi = f"sukydieutra-{hashlib.sha256(goc.read_bytes()).hexdigest()[:12]}.tar.gz"
    for f in web_dir.glob("sukydieutra-*.tar.gz"):
        f.unlink()
    shutil.copy2(goc, web_dir / moi)
    return html.replace(cu, f'"{moi}"')


def build() -> None:
    cmd = [sys.executable, "-m", "pygbag", "--build", "--app_name", "sukydieutra", "--title", "Su Ky Dieu Tra", str(OUT)]
    # pygbag đọc main.py bằng bảng mã mặc định của máy; trên Windows phải bật UTF-8 kẻo lỗi với chữ tiếng Việt
    subprocess.run(cmd, check=True, cwd=ROOT, env={**os.environ, "PYTHONUTF8": "1"})
    if not (WEB_DIR / "index.html").exists():
        raise SystemExit(f"Build xong nhưng không thấy {WEB_DIR / 'index.html'}")
    patch_html(WEB_DIR / "index.html")
    web_extras.place_music(MUSIC_STASH, WEB_DIR)
    size = sum(f.stat().st_size for f in WEB_DIR.rglob("*") if f.is_file()) / 1024 / 1024
    print(f"\nBuild xong: {WEB_DIR} ({size:.1f} MB)")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # cửa sổ lệnh Windows mặc định cp1252, không in được chữ Việt
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help="chạy thử tại http://127.0.0.1:8000 sau khi build")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    collect()
    build()
    if args.serve:
        # Phải dùng 127.0.0.1: trên `localhost`, pygbag tải thư viện từ máy chủ dev riêng nên kẹt ở màn tải
        print(f"Mở http://127.0.0.1:{args.port} trong trình duyệt (Ctrl+C để dừng)")
        subprocess.run([sys.executable, "-m", "http.server", str(args.port), "--directory", str(WEB_DIR)], check=False)


if __name__ == "__main__":
    main()
