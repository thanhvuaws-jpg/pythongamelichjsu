"""Đi hết luồng thật qua API với PostgreSQL: tài khoản, lưu game, xếp hạng, phân quyền, user.

Cần cơ sở dữ liệu đã chạy migration; không kết nối được thì bỏ qua để máy không có PostgreSQL
vẫn chạy được phần test còn lại.
"""

import uuid

import httpx
import pytest
from sqlalchemy import select

from app.db import SessionLocal, engine, ping_db
from app.main import app
from app.models import Role, User

PASSWORD = "mat-khau-dai-du-roi"


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _register(c, email, year=1990, **extra):
    return await c.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "display_name": email.split("@")[0],
            "birth_year": year,
            "accept_policy": True,
            **extra,
        },
    )


async def _login(c, email):
    r = await c.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _set_role(email, role):
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        user.role = role
        await session.commit()
        return user.id


async def test_full_account_and_save_flow(monkeypatch):
    try:
        await ping_db()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Không có PostgreSQL: {type(exc).__name__}")
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "skip_email_verification", True)
    tag = uuid.uuid4().hex[:8]
    player, other, boss = f"nguoi{tag}@test.vn", f"khac{tag}@test.vn", f"admin{tag}@test.vn"

    async with client() as c:
        # Đăng ký xong đăng nhập được ngay khi tắt xác minh email
        r = await _register(c, player)
        assert r.status_code == 201 and r.json()["ready"] is True
        head = await _login(c, player)
        me = await c.get("/api/v1/auth/me", headers=head)
        assert me.json()["role"] == "player"

        # Chưa đăng nhập thì không đọc được bản lưu
        assert (await c.get("/api/v1/game/save")).status_code == 401
        empty = await c.get("/api/v1/game/save", headers=head)
        assert empty.json()["data"] is None

        # Lưu game: điểm do máy chủ tính, không tin số điểm gửi lên
        save = {
            "points": 999999,
            "solved": ["q_dl_1", "gia_mao"],
            "attempts": {"q_dl_1": 1},
            "stamps": ["r_duong_lam"],
        }
        r = await c.put("/api/v1/game/save", json={"data": save}, headers=head)
        assert r.status_code == 200 and r.json()["points"] == 10
        got = await c.get("/api/v1/game/save", headers=head)
        assert got.json()["data"]["stamps"] == ["r_duong_lam"] and got.json()["points"] == 10

        # Gửi lại nhiều lần không được cộng trùng
        await c.put("/api/v1/game/save", json={"data": save}, headers=head)
        board = await c.get("/api/v1/leaderboard?period=all", headers=head)
        assert board.json()["me"]["points"] == 10

        # Ván mới có ít tiến độ hơn thì bản lưu đổi nhưng điểm đã ghi sổ không mất
        await c.put("/api/v1/game/save", json={"data": {"solved": []}}, headers=head)
        board = await c.get("/api/v1/leaderboard?period=all", headers=head)
        assert board.json()["me"]["points"] == 10

        # Bản lưu quá lớn bị từ chối
        r = await c.put(
            "/api/v1/game/save", json={"data": {"rac": "x" * (600 * 1024)}}, headers=head
        )
        assert r.status_code == 413

        # Người chơi thường không vào được trang quản trị
        assert (await c.get("/api/v1/game/analytics", headers=head)).status_code == 403
        assert (await c.get("/api/v1/users", headers=head)).status_code == 403

        # Quản trị viên: xem thống kê, tìm user, đổi vai trò, khoá rồi mở lại
        assert (await _register(c, boss)).status_code == 201
        await _set_role(boss, Role.admin)
        admin = await _login(c, boss)
        stats = await c.get("/api/v1/game/analytics", headers=admin)
        assert stats.status_code == 200 and stats.json()["accounts"] >= 2
        found = await c.get("/api/v1/users", params={"q": player}, headers=admin)
        assert found.json()["total"] == 1
        uid = found.json()["items"][0]["id"]
        r = await c.patch(f"/api/v1/users/{uid}/role", json={"role": "editor"}, headers=admin)
        assert r.json()["role"] == "editor"
        r = await c.post(f"/api/v1/users/{uid}/disable", json={"reason": "kiểm thử"}, headers=admin)
        assert r.json()["status"] == "disabled"
        assert (await c.get("/api/v1/game/save", headers=head)).status_code == 401, (
            "Bị khoá thì token cũ hết tác dụng ngay"
        )
        bad = await c.post("/api/v1/auth/login", json={"email": player, "password": PASSWORD})
        assert bad.status_code == 403
        await c.post(f"/api/v1/users/{uid}/enable", headers=admin)
        assert (
            await c.get("/api/v1/game/save", headers=await _login(c, player))
        ).status_code == 200

        # Người dưới 16 tuổi chờ xác nhận, quản trị viên kích hoạt được khi chưa gửi được email
        r = await _register(c, other, year=2015, guardian_email=f"giaovien{tag}@test.vn")
        assert r.status_code == 201 and r.json()["ready"] is False
        blocked = await c.post("/api/v1/auth/login", json={"email": other, "password": PASSWORD})
        assert blocked.status_code == 403
        kid = (await c.get("/api/v1/users", params={"q": other}, headers=admin)).json()["items"][0]
        assert kid["status"] == "pending_guardian"
        assert (await c.post(f"/api/v1/users/{kid['id']}/enable", headers=admin)).status_code == 200
        assert (
            await c.post("/api/v1/auth/login", json={"email": other, "password": PASSWORD})
        ).status_code == 200

        # Làm mới phiên bằng cookie, đăng xuất thì hết
        again = await c.post("/api/v1/auth/login", json={"email": player, "password": PASSWORD})
        assert again.status_code == 200
        assert (await c.post("/api/v1/auth/refresh")).status_code == 200
        assert (await c.post("/api/v1/auth/logout")).status_code == 204
        assert (await c.post("/api/v1/auth/refresh")).status_code == 401

    # Dọn các tài khoản vừa tạo
    async with SessionLocal() as session:
        emails = (player, other, boss)
        for row in await session.scalars(select(User).where(User.email.in_(emails))):
            await session.delete(row)
        await session.commit()
    await engine.dispose()


async def test_admin_can_grant_lock_and_delete(monkeypatch):
    try:
        await ping_db()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Không có PostgreSQL: {type(exc).__name__}")
    from app.config import get_settings
    from app.models import AuditLog

    monkeypatch.setattr(get_settings(), "skip_email_verification", True)
    tag = uuid.uuid4().hex[:8]
    player, other, boss = f"a{tag}@test.vn", f"b{tag}@test.vn", f"c{tag}@test.vn"

    async with client() as c:
        for email in (player, other, boss):
            assert (await _register(c, email)).status_code == 201
        boss_id = await _set_role(boss, Role.admin)
        admin = await _login(c, boss)
        head = await _login(c, player)
        uid = (await c.get("/api/v1/users", params={"q": player}, headers=admin)).json()["items"][
            0
        ]["id"]
        other_id = (await c.get("/api/v1/users", params={"q": other}, headers=admin)).json()[
            "items"
        ][0]["id"]

        # Người chơi thường không được cộng điểm hay xoá ai, kể cả cho chính mình
        grant = {"points": 999, "skill_points": 9}
        assert (
            await c.post(f"/api/v1/users/{uid}/grant", json=grant, headers=head)
        ).status_code == 403
        assert (await c.delete(f"/api/v1/users/{other_id}", headers=head)).status_code == 403
        assert (await c.post(f"/api/v1/users/{uid}/grant", json=grant)).status_code == 401

        # Cộng cho người khác: điểm vào bảng xếp hạng, người chơi nhận được qua API
        r = await c.post(
            f"/api/v1/users/{uid}/grant",
            json={"points": 500, "skill_points": 7, "reason": "thưởng kiểm thử"},
            headers=admin,
        )
        assert r.status_code == 200 and r.json()["points"] == 500
        assert r.json()["bonus_skill_points"] == 7
        bonus = await c.get("/api/v1/game/bonus", headers=head)
        assert bonus.json() == {"bonus_points": 500, "bonus_skill_points": 7}
        board = await c.get("/api/v1/leaderboard?period=all", headers=head)
        assert board.json()["me"]["points"] == 500

        # Chưa từng chơi: tặng điểm không biến thành "đã chơi", bản lưu vẫn trống
        assert (await c.get("/api/v1/game/save", headers=head)).json()["data"] is None

        # Bản lưu người chơi gửi lên không xoá được điểm đã tặng
        rpg = {"level": 12, "realm": 1, "mobs_killed": 7, "bosses_beaten": ["r_duong_lam"]}
        body = {"data": {"solved": ["q_dl_1"], "rpg": rpg}}
        await c.put("/api/v1/game/save", json=body, headers=head)
        out = await c.get("/api/v1/game/save", headers=head)
        assert out.json()["bonus_skill_points"] == 7 and out.json()["bonus_points"] == 500

        # Cộng cho chính mình và trừ bớt (500 + 10 của câu vừa giải - 100); điểm kỹ năng không âm
        mine = await c.post(
            f"/api/v1/users/{boss_id}/grant",
            json={"points": 1000, "skill_points": 3},
            headers=admin,
        )
        assert mine.json()["points"] == 1000
        r = await c.post(
            f"/api/v1/users/{uid}/grant", json={"points": -100, "skill_points": -50}, headers=admin
        )
        assert r.json()["points"] == 410 and r.json()["bonus_skill_points"] == 0

        # Không nhập gì, hoặc vượt giới hạn, đều bị từ chối
        assert (
            await c.post(f"/api/v1/users/{uid}/grant", json={}, headers=admin)
        ).status_code == 400
        too_big = {"points": 10**9}
        assert (
            await c.post(f"/api/v1/users/{uid}/grant", json=too_big, headers=admin)
        ).status_code == 422

        # Danh sách người dùng hiện điểm
        found = await c.get("/api/v1/users", params={"q": player}, headers=admin)
        assert found.json()["items"][0]["points"] == 410

        # Hồ sơ một tài khoản: điểm, tóm tắt bản lưu, lịch sử thao tác lên tài khoản đó
        detail = await c.get(f"/api/v1/users/{uid}", headers=admin)
        assert detail.status_code == 200, detail.text
        d = detail.json()
        assert d["points"] == 410 and d["save"]["has_save"] and d["save"]["solved"] == 1
        assert [lv["id"] for lv in d["save"]["levels"]] == ["man1", "man2", "man3"]
        assert d["save"]["total_relics"] >= 18
        sv = d["save"]
        got = (sv["level"], sv["realm"], sv["mobs_killed"], sv["guards_beaten"])
        assert got == (12, "Sử sinh", 7, 1), "Quản trị viên thấy cấp, cảnh giới của người chơi"
        grants = [h for h in d["history"] if h["action"] == "user_grant"]
        assert len(grants) == 2 and grants[0]["after"]["points"] == -100, "Mới nhất đứng trước"
        assert grants[1]["after"]["reason"] == "thưởng kiểm thử"
        assert grants[0]["actor_name"] == boss.split("@")[0]
        assert (await c.get(f"/api/v1/users/{uid}", headers=head)).status_code == 403
        assert (await c.get(f"/api/v1/users/{uuid.uuid4()}", headers=admin)).status_code == 404

        # Nhật ký chung: lọc theo loại thao tác, người thường không xem được
        log = await c.get("/api/v1/users/audit", params={"action": "user_grant"}, headers=admin)
        assert log.status_code == 200, log.text
        rows = log.json()["items"]
        assert rows and all(r["action"] == "user_grant" for r in rows)
        assert any(r["target_name"] == player.split("@")[0] for r in rows)
        assert (await c.get("/api/v1/users/audit", headers=head)).status_code == 403

        # Thống kê có số tài khoản mới theo ngày, đủ 14 ngày, hôm nay có ít nhất ba người vừa tạo
        stats = (await c.get("/api/v1/game/analytics", headers=admin)).json()
        days = stats["signups_daily"]
        assert len(days) == 14 and days[-1]["count"] >= 3

        # Không tự xoá được mình
        assert (await c.delete(f"/api/v1/users/{boss_id}", headers=admin)).status_code == 400

        # Xoá thật: mất tài khoản, tiến trình, điểm; không đăng nhập lại được; xoá lần hai báo 404
        assert (await c.delete(f"/api/v1/users/{uid}", headers=admin)).status_code == 204
        assert (await c.get("/api/v1/game/save", headers=head)).status_code == 401
        bad = await c.post("/api/v1/auth/login", json={"email": player, "password": PASSWORD})
        assert bad.status_code == 401
        assert (await c.delete(f"/api/v1/users/{uid}", headers=admin)).status_code == 404
        board = await c.get("/api/v1/leaderboard?period=all", headers=admin)
        assert all(row["user_id"] != uid for row in board.json()["entries"])

        # Mọi thao tác đều có nhật ký
        async with SessionLocal() as session:
            actions = set(
                await session.scalars(
                    select(AuditLog.action).where(AuditLog.actor_id == uuid.UUID(str(boss_id)))
                )
            )
        assert {"user_grant", "user_delete"} <= actions

        # Dọn tài khoản kiểm thử
        await c.delete(f"/api/v1/users/{other_id}", headers=admin)
        async with SessionLocal() as session:
            await session.delete(await session.get(User, boss_id))
            await session.commit()
    await engine.dispose()
