"""Trang HTML không bị trình duyệt giữ bản cũ; trang game cũ vẫn lấy được gói game hiện tại.

Lỗi 20/11/2026: bạn của người dùng vào trang chơi thì kẹt ở "Loading, please wait" vì trình
duyệt giữ /game/index.html cũ, bản đó gọi gói game đã bị thay (404).
"""

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, PlainTextResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient

from app.middleware import FreshPagesMiddleware, GameBundleFallbackMiddleware

HIEN_TAI = "/game/sukydieutra-aaaaaaaaaaaa.tar.gz"
CU = "/game/sukydieutra-05a59bd107d0.tar.gz"


def _client(game_dir=None) -> TestClient:
    async def trang(request):
        p = request.url.path
        if p.endswith(".html") or p == "/":
            return HTMLResponse("<p>trang</p>")
        if p == "/tu-dat":
            return Response("x", media_type="text/html", headers={"cache-control": "max-age=60"})
        return PlainTextResponse(p)

    app = Starlette(routes=[Route("/{p:path}", trang)])
    app.add_middleware(FreshPagesMiddleware)
    if game_dir:
        app.add_middleware(GameBundleFallbackMiddleware, game_dir=str(game_dir))
    return TestClient(app, follow_redirects=False)


def test_trang_html_luon_bat_hoi_lai():
    c = _client()
    assert c.get("/game/index.html").headers["cache-control"] == "no-cache"
    assert c.get("/").headers["cache-control"] == "no-cache"
    # tệp khác để Cloudflare và trình duyệt giữ như cũ; trang tự đặt Cache-Control thì không đè
    assert "cache-control" not in c.get("/js/play.js").headers
    assert c.get("/tu-dat").headers["cache-control"] == "max-age=60"


def test_goi_game_cu_chuyen_sang_goi_hien_tai(tmp_path):
    (tmp_path / HIEN_TAI.rsplit("/", 1)[1]).write_bytes(b"goi moi")
    c = _client(tmp_path)
    r = c.get(CU)
    assert r.status_code == 307 and r.headers["location"] == HIEN_TAI
    assert c.get(HIEN_TAI).text == HIEN_TAI, "Gói hiện tại thì phục vụ bình thường"
    assert c.get("/game/khac.tar.gz").status_code == 200


def test_khong_doan_bua_khi_khong_ro_goi_nao(tmp_path):
    c = _client(tmp_path)  # chưa build: không có gói nào
    assert c.get(CU).status_code == 200  # để StaticFiles phía sau tự trả 404 như cũ
