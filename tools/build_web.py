"""Đóng gói game sang WebAssembly bằng pygbag.

    .venv/Scripts/python tools/build_web.py            # chỉ build
    .venv/Scripts/python tools/build_web.py --serve    # build xong chạy thử tại http://127.0.0.1:8000

Kết quả nằm ở build/sukydieutra/build/web/ (index.html + gói .apk), chép lên bất kỳ static hosting nào.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "game"
OUT = ROOT / "build" / "sukydieutra"
WEB_DIR = OUT / "build" / "web"
GAME_PARTS = ("main.py", "core", "scenes", "content", "assets")
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", ".save", "tests")
PAGE_STYLE = """<style>
html, body { background: #1a1210 !important; }
canvas.emscripten {
  width: min(100vw, calc(100vh * 16 / 9)) !important;
  height: min(100vh, calc(100vw * 9 / 16)) !important;
}
</style>
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


def patch_html(path: Path) -> None:
    """Script của pygbag ép canvas thành hình vuông khi cửa sổ hẹp hơn 16:9, nên khoá tỉ lệ bằng CSS."""
    html = path.read_text(encoding="utf-8")
    html = html.replace("</head>", PAGE_STYLE + "</head>", 1)
    path.write_text(html, encoding="utf-8")


def build() -> None:
    cmd = [sys.executable, "-m", "pygbag", "--build", "--app_name", "sukydieutra", "--title", "Su Ky Dieu Tra", str(OUT)]
    # pygbag đọc main.py bằng bảng mã mặc định của máy; trên Windows phải bật UTF-8 kẻo lỗi với chữ tiếng Việt
    subprocess.run(cmd, check=True, cwd=ROOT, env={**os.environ, "PYTHONUTF8": "1"})
    if not (WEB_DIR / "index.html").exists():
        raise SystemExit(f"Build xong nhưng không thấy {WEB_DIR / 'index.html'}")
    patch_html(WEB_DIR / "index.html")
    size = sum(f.stat().st_size for f in WEB_DIR.rglob("*") if f.is_file()) / 1024 / 1024
    print(f"\nBuild xong: {WEB_DIR} ({size:.1f} MB)")


def main() -> None:
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
