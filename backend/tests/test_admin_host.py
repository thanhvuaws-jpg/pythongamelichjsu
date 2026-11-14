"""AdminHostMiddleware: tách cổng quản trị sang tên miền riêng (VPS, admin.vtkt.online)."""

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.middleware import AdminHostMiddleware


def _client() -> TestClient:
    async def trang(request):
        return PlainTextResponse(request.url.path)

    app = Starlette(routes=[Route("/{p:path}", trang)])
    app.add_middleware(AdminHostMiddleware, admin_host="admin.vtkt.online")
    return TestClient(app, follow_redirects=False)


def test_goc_ten_mien_quan_tri_chuyen_sang_admin():
    r = _client().get("/", headers={"host": "admin.vtkt.online"})
    assert r.status_code == 302 and r.headers["location"] == "/admin/"


def test_admin_tren_ten_mien_game_chuyen_sang_ten_mien_quan_tri():
    r = _client().get("/admin/users?page=2", headers={"host": "game.vtkt.online"})
    assert r.status_code == 302
    assert r.headers["location"] == "https://admin.vtkt.online/admin/users?page=2"


def test_api_va_trang_khac_khong_bi_dong_cham():
    c = _client()
    assert c.get("/api/v1/health", headers={"host": "admin.vtkt.online"}).text == "/api/v1/health"
    assert c.get("/admin/", headers={"host": "admin.vtkt.online"}).text == "/admin/"
    assert c.get("/", headers={"host": "game.vtkt.online"}).text == "/"
    assert c.get("/administrator", headers={"host": "game.vtkt.online"}).text == "/administrator"
