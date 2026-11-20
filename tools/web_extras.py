"""Phần thêm cho bản web (build_web.py gọi): làm nhẹ gói tải đầu và dựng màn tải.

Đo ngày 20/11/2026, lần đầu vào game phải tải 16,5 MB, nối đuôi nhau: bộ chạy Python của pygbag (~9 MB), rồi gói game
6,1 MB, rồi pygame 1,5 MB. Trong gói game, phông NotoSerif chiếm 1,8 MB (đủ chữ Hy Lạp, Nga...) và 5 bản nhạc chiếm 4,3 MB.

- slim_fonts: chỉ giữ chữ Việt và ký hiệu game dùng. Be Vietnam Pro vẽ ra giống hệt từng điểm ảnh; NotoSerif là phông
  biến thiên nên chốt về kiểu mặc định (đúng kiểu pygame vẫn vẽ): cùng kích thước chữ, mép chữ lệch khoảng 1-2/255 độ
  đậm (đo 20/11), đổi lại 1,8 MB còn 155 KB.
- split_music: nhạc nền ngoài màn tựa đề tách ra music/ cạnh index.html, game tải ngầm (core/audio.py, fetch_music).
- loader_parts: màn tải (tools/loader/) thay giao diện tải mặc định của pygbag, và tải song song gói game với pygame.
"""

from __future__ import annotations

import base64
import json
import math
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOADER = Path(__file__).resolve().parent / "loader"
CONTENT = ROOT / "game" / "content"
# Bộ chạy pygbag 0.9.3 (main.js + main.wasm + main.data, đo khi tải thật) và bánh xe pygame mà nó cài: cố định theo
# phiên bản pygbag, đổi pygbag thì đo lại (xem Network của trình duyệt, lọc "cdn").
WHEEL_URL = "https://pygame-web.github.io/cdn/cp312/pygame_ce-2.5.7-cp312-cp312-wasm32_bi_emscripten.whl"
WHEEL_BYTES = 1_524_000
RUNTIME_BYTES = 9_330_000
# Chữ Việt (cả dạng tổ hợp), dấu câu, tiền tệ, mũi tên, toán, hình khối, sao...: người chơi gõ tên và chat bằng mọi chữ
# Việt nên phải giữ trọn các khối này, không chỉ những chữ đang có trong mã.
FONT_RANGES = [(0x20, 0x7E), (0xA0, 0x24F), (0x300, 0x36F), (0x1E00, 0x1EFF), (0x2000, 0x206F), (0x20A0, 0x20CF),
               (0x2100, 0x214F), (0x2190, 0x21FF), (0x2200, 0x22FF), (0x2460, 0x24FF), (0x2500, 0x25FF),
               (0x2600, 0x27BF)]


def _used_chars(root: Path) -> set[int]:
    chars: set[int] = set()
    for f in root.rglob("*"):
        if f.suffix in (".py", ".json", ".txt") and f.is_file():
            chars |= {ord(c) for c in f.read_text(encoding="utf-8", errors="ignore")}
    return chars


def slim_fonts(root: Path) -> None:
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    codes = _used_chars(root) | {c for a, b in FONT_RANGES for c in range(a, b + 1)}
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]
    opts.notdef_outline = True
    opts.hinting = True
    for ttf in sorted((root / "assets" / "fonts").glob("*.ttf")):
        before = ttf.stat().st_size
        font = TTFont(ttf)
        if "fvar" in font:  # pygame vẽ phông biến thiên ở toạ độ mặc định: chốt đúng toạ độ đó
            font = instancer.instantiateVariableFont(font, {a.axisTag: a.defaultValue for a in font["fvar"].axes})
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=codes)
        sub.subset(font)
        font.save(ttf)
        print(f"  phông {ttf.name}: {before / 1024:.0f} KB -> {ttf.stat().st_size / 1024:.0f} KB")


def later_music() -> tuple[str, ...]:
    """Đọc LATER_MUSIC trong game/core/audio.py (không import để khỏi cần pygame lúc build)."""
    src = (ROOT / "game" / "core" / "audio.py").read_text(encoding="utf-8")
    m = re.search(r"^LATER_MUSIC = \(([^)]*)\)", src, re.M)
    return tuple(re.findall(r'"([^"]+)"', m.group(1))) if m else ()


def split_music(root: Path, stash: Path) -> None:
    if stash.exists():
        shutil.rmtree(stash)
    stash.mkdir(parents=True)
    music = root / "assets" / "pixel" / "music"
    for name in later_music():
        f = music / f"{name}.ogg"
        if f.exists():
            shutil.move(str(f), stash / f.name)
    moved = sum(f.stat().st_size for f in stash.iterdir()) / 1024 / 1024
    print(f"  nhạc tải ngầm sau: {', '.join(f.stem for f in sorted(stash.iterdir()))} ({moved:.1f} MB)")


def place_music(stash: Path, web_dir: Path) -> None:
    out = web_dir / "music"
    out.mkdir(exist_ok=True)
    for f in stash.iterdir():
        shutil.copy2(f, out / f.name)


def _facts() -> list[dict]:
    """Mốc sử trong dòng thời gian của game (cùng nguồn với dòng "Biết không?" ở màn tựa đề), kèm nguồn đã ghi."""
    srcs = json.loads((CONTENT / "sources.json").read_text(encoding="utf-8"))
    out = []
    for man in ("man1", "man2", "man3"):
        data = json.loads((CONTENT / f"{man}.json").read_text(encoding="utf-8"))
        for e in data.get("events", []):
            where = []
            for cid in e.get("citations", [])[:1]:
                c = srcs["citations"].get(cid)
                s = c and srcs["sources"].get(c["source"])
                if s:
                    where.append(f"{s['title']}, {c['locator']}" if c.get("locator") else s["title"])
            out.append({"d": e["date"]["start"], "y": e["date"]["label"], "t": e["title"], "s": e.get("summary", ""),
                        "src": "; ".join(where)})
    out.sort(key=lambda f: f["d"])
    for f in out:
        del f["d"]
    return out


def _emblem_svg() -> str:
    """Mặt trống đồng phỏng theo kiểu Đông Sơn, vẽ giống core/emblem.py (hình trang trí, không phải một chiếc trống cụ
    thể): sao 14 cánh ở tâm, vành chấm, răng cưa, vạch, và vành chim bay ngược chiều kim đồng hồ."""
    c, r = 60, 56
    line, bronze, dark, light, star = "#563a1e", "#a87c42", "#704e28", "#d6ac68", "#f0cc78"

    def pt(rad, a):
        return f"{c + math.cos(a) * rad:.2f},{c + math.sin(a) * rad:.2f}"

    parts = [f'<defs><radialGradient id="skg" cx="38%" cy="36%" r="70%"><stop offset="0" stop-color="{light}"/>'
             f'<stop offset="1" stop-color="{bronze}"/></radialGradient></defs>',
             f'<circle cx="{c}" cy="{c}" r="{r + 2}" fill="{dark}"/><circle cx="{c}" cy="{c}" r="{r}" fill="url(#skg)"/>']
    for frac in (0.18, 0.27, 0.37, 0.63, 0.87, 0.97):
        parts.append(f'<circle cx="{c}" cy="{c}" r="{r * frac:.2f}" fill="none" stroke="{line}" stroke-width="1"/>')
    for frac, n in ((0.225, 16), (0.92, 40)):
        dots = "".join(f'<circle cx="{pt(r * frac, math.tau * i / n).split(",")[0]}" '
                       f'cy="{pt(r * frac, math.tau * i / n).split(",")[1]}" r="1.1"/>' for i in range(n))
        parts.append(f'<g fill="none" stroke="{line}" stroke-width=".6">{dots}</g>')
    zig = " ".join(pt(r * (0.29 if i % 2 else 0.35), math.tau * i / 56) for i in range(57))
    parts.append(f'<polyline points="{zig}" fill="none" stroke="{line}" stroke-width=".9"/>')
    hatch = "".join(f'<line x1="{pt(r * 0.39, a).split(",")[0]}" y1="{pt(r * 0.39, a).split(",")[1]}" '
                    f'x2="{pt(r * 0.61, a + 0.05).split(",")[0]}" y2="{pt(r * 0.61, a + 0.05).split(",")[1]}"/>'
                    for a in (math.tau * i / 72 for i in range(72)))
    parts.append(f'<g stroke="{line}" stroke-width=".5" opacity=".7">{hatch}</g>')
    bird = (f'<g fill="{line}"><path d="M-6 0 L1.6 -1.2 L4.2 0 L1.6 1.2Z"/><path d="M4.2 0 L9 -.6 L4.2 .5Z"/>'
            f'<path d="M-1 0 L1 -5 L2.4 -.6Z"/><path d="M-.6 0 L1.4 5 L2.6 .6Z"/><path d="M-5 0 L-9 -2.6 L-9 2.6Z"/></g>')
    birds = "".join(f'<g transform="translate({pt(r * 0.75, math.tau * i / 10)}) rotate({360 * i / 10 - 90:.1f}) '
                    f'scale(.78)">{bird}</g>' for i in range(10))
    parts.append(f'<g class="ring2">{birds}</g>')
    star_pts = " ".join(pt(r * (0.165 if i % 2 == 0 else 0.055), math.tau * i / 28 - math.pi / 2) for i in range(28))
    parts.append(f'<g class="star"><polygon points="{star_pts}" fill="{star}" stroke="{line}" stroke-width=".6"/>'
                 f'<circle cx="{c}" cy="{c}" r="{r * 0.05:.2f}" fill="{light}"/></g>')
    return (f'<svg class="sk-sun" viewBox="0 0 120 120" role="img" aria-label="Mặt trống đồng trang trí">'
            f'{"".join(parts)}</svg>')


def loader_parts(bundle: str, bundle_bytes: int) -> tuple[str, str, str]:
    """(script đặt đầu trang, CSS cho <head>, khối HTML ngay sau <body>)."""
    cfg = {"bundle": bundle, "bundleBytes": bundle_bytes, "wheel": WHEEL_URL, "wheelBytes": WHEEL_BYTES,
           "runtimeBytes": RUNTIME_BYTES, "facts": _facts()}
    js = (LOADER / "loader.js").read_text(encoding="utf-8").replace(
        "__SK_CONFIG__", json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/"))
    script = f"<script>{js}</script>\n"
    walk = base64.b64encode((ROOT / "web" / "img" / "walk.png").read_bytes()).decode()
    style = (
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:ital,wght@0,600;0,800;1,400'
        '&display=swap&subset=vietnamese" rel="stylesheet">\n'
        f"<style>{(LOADER / 'loader.css').read_text(encoding='utf-8')}</style>\n"
    )
    body = f"""
<div id="sk-load" role="status" aria-live="polite" style="--walk: url(data:image/png;base64,{walk})">
  <div class="sk-head">
    {_emblem_svg()}
    <div>
      <h1>SỬ KÝ ĐIỀU TRA</h1>
      <p class="sk-sub">Game nhập vai học lịch sử Việt Nam</p>
    </div>
  </div>
  <div class="sk-progress">
    <div class="sk-road"><div class="sk-walker" id="sk-walker"></div></div>
    <div class="sk-bar"><div><i id="sk-fill"></i></div></div>
    <div class="sk-row"><b id="sk-step">Đang chuẩn bị…</b><span id="sk-pct">0%</span></div>
    <p class="sk-note" id="sk-note">Lần đầu cần tải khoảng {(RUNTIME_BYTES + WHEEL_BYTES + bundle_bytes) / 1048576:.0f} MB,
      lần sau trình duyệt nhớ sẵn nên vào nhanh hơn nhiều.</p>
  </div>
  <button id="sk-go" type="button" hidden>Bấm để vào game</button>
  <figure class="sk-fact" id="sk-fact">
    <header><span class="sk-tag">Biết không?</span><em id="sk-year"></em><b id="sk-title"></b></header>
    <p id="sk-text"></p>
    <small id="sk-src"></small>
  </figure>
</div>
<script>window.__skSetup && __skSetup()</script>
"""
    return script, style, body
