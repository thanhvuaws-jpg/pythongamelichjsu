"""Quản lý người dùng cho Quản_Trị_Viên (Req 25.1–25.4)."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.auth.jwt import revoke_all_refresh_tokens
from app.config import get_settings
from app.db import get_session
from app.errors import AppError
from app.game.logic import load_content
from app.leaderboard.service import invalidate_cache
from app.models import AuditLog, GameSave, Role, ScoreLedger, ScoreReason, User, UserStatus

router = APIRouter(prefix="/api/v1/users", tags=["users"])
Session = Annotated[AsyncSession, Depends(get_session)]
Admin = Annotated[User, Depends(require_role(Role.admin))]
PAGE_SIZE = 50
AUDIT_PAGE_SIZE = 40
HISTORY_LIMIT = 12
MAX_GRANT_POINTS = 1_000_000
MAX_GRANT_SKILL = 10_000


class UserAdminOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: Role
    is_teacher: bool
    status: UserStatus
    email_verified: bool
    created_at: datetime
    points: int = 0
    bonus_skill_points: int = 0


class UserPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[UserAdminOut]


class RoleIn(BaseModel):
    role: Role
    is_teacher: bool | None = None


class DisableIn(BaseModel):
    reason: Annotated[str | None, Field(max_length=500)] = None


class GrantIn(BaseModel):
    """Số dương là cộng, số âm là trừ."""

    points: Annotated[int, Field(ge=-MAX_GRANT_POINTS, le=MAX_GRANT_POINTS)] = 0
    skill_points: Annotated[int, Field(ge=-MAX_GRANT_SKILL, le=MAX_GRANT_SKILL)] = 0
    reason: Annotated[str | None, Field(max_length=500)] = None


class AuditOut(BaseModel):
    """Một dòng nhật ký quản trị, kèm tên người làm và người bị tác động nếu tài khoản còn."""

    id: int
    action: str
    actor_id: uuid.UUID | None
    actor_name: str | None
    target_type: str
    target_id: str | None
    target_name: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    created_at: datetime


class AuditPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AuditOut]


class LevelProgress(BaseModel):
    id: str
    title: str
    completed: bool


class SaveSummary(BaseModel):
    """Tóm tắt bản lưu để quản trị viên biết người chơi đang ở đâu, không trả nguyên bản lưu."""

    has_save: bool
    updated_at: datetime | None
    levels: list[LevelProgress]
    stamps: int
    total_relics: int
    solved: int
    badges: int
    skills: int
    discovered: int
    cases: int
    sides: int
    arena_wins: int
    level: int = 1
    realm: str = "Tân binh"
    mobs_killed: int = 0
    guards_beaten: int = 0


class UserDetailOut(UserAdminOut):
    save: SaveSummary
    history: list[AuditOut]


def _count(value: Any) -> int:
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, list):
        return len({v for v in value if isinstance(v, str)})
    return 0


# Tên cảnh giới theo thứ tự trong game/core/rpg.py (REALMS)
REALM_NAMES = ("Tân binh", "Sử sinh", "Sử quan", "Đại sử quan")


def _int(value: Any, low: int = 0, high: int = 10**9) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return low


def _summary(row: GameSave | None) -> SaveSummary:
    content = load_content(get_settings().game_content_dir)
    data = row.data if row is not None and isinstance(row.data, dict) else {}
    levels = data.get("completed_levels")
    done = set(levels) if isinstance(levels, list) else set()
    rpg = data.get("rpg") if isinstance(data.get("rpg"), dict) else {}
    return SaveSummary(
        has_save=bool(data),
        updated_at=row.updated_at if row is not None and data else None,
        levels=[
            LevelProgress(id=lv["id"], title=lv["title"], completed=lv["id"] in done)
            for lv in content.levels
        ],
        stamps=_count(data.get("stamps")),
        total_relics=content.relics,
        solved=_count(data.get("solved")),
        badges=_count(data.get("badges")),
        skills=_count(data.get("skill_levels")),
        discovered=_count(data.get("discovered")),
        cases=_count(data.get("case_done")),
        sides=_count(data.get("side_done")),
        arena_wins=_count(data.get("arena_wins")),
        level=_int(rpg.get("level", 1), 1, 99),
        realm=REALM_NAMES[_int(rpg.get("realm", 0), 0, len(REALM_NAMES) - 1)],
        mobs_killed=_int(rpg.get("mobs_killed", 0)),
        guards_beaten=_count(rpg.get("bosses_beaten")),
    )


async def _audit_rows(session: AsyncSession, logs: list[AuditLog]) -> list[AuditOut]:
    """Gắn tên người làm và tên tài khoản bị tác động; tài khoản đã xoá thì để trống."""
    ids: set[uuid.UUID] = {log.actor_id for log in logs if log.actor_id}
    for log in logs:
        if log.target_type == "users" and log.target_id:
            try:
                ids.add(uuid.UUID(log.target_id))
            except ValueError:
                pass
    names: dict[str, str] = {}
    if ids:
        rows = await session.execute(select(User.id, User.display_name).where(User.id.in_(ids)))
        names = {str(uid): name for uid, name in rows}
    return [
        AuditOut(
            id=log.id,
            action=log.action,
            actor_id=log.actor_id,
            actor_name=names.get(str(log.actor_id)) if log.actor_id else None,
            target_type=log.target_type,
            target_id=log.target_id,
            target_name=names.get(log.target_id or "") if log.target_type == "users" else None,
            before=log.before,
            after=log.after,
            created_at=log.created_at,
        )
        for log in logs
    ]


def _out(u: User, points: int = 0, bonus_skill_points: int = 0) -> UserAdminOut:
    return UserAdminOut(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        role=u.role,
        is_teacher=u.is_teacher,
        status=u.status,
        email_verified=u.email_verified,
        created_at=u.created_at,
        points=points,
        bonus_skill_points=bonus_skill_points,
    )


async def _scores(
    session: AsyncSession, ids: list[uuid.UUID]
) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int]]:
    """Tổng điểm xếp hạng và điểm kỹ năng được tặng của một nhóm tài khoản."""
    totals = await session.execute(
        select(ScoreLedger.user_id, func.sum(ScoreLedger.points))
        .where(ScoreLedger.user_id.in_(ids))
        .group_by(ScoreLedger.user_id)
    )
    bonus = await session.execute(
        select(GameSave.user_id, GameSave.bonus_skill_points).where(GameSave.user_id.in_(ids))
    )
    return {uid: int(n) for uid, n in totals}, {uid: int(n) for uid, n in bonus}


async def _out_one(session: AsyncSession, u: User) -> UserAdminOut:
    points, bonus = await _scores(session, [u.id])
    return _out(u, points.get(u.id, 0), bonus.get(u.id, 0))


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _lock_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise AppError(404, "USER_NOT_FOUND", "Không tìm thấy người dùng")
    return user


async def ensure_not_last_admin(session: AsyncSession, target: User) -> None:
    """Chặn gỡ hoặc vô hiệu hóa Quản_Trị_Viên cuối cùng đang hoạt động (Req 25.4).

    Khóa mọi hàng admin đang hoạt động để hai thao tác đồng thời không cùng vượt qua.
    """
    if target.role != Role.admin or target.status != UserStatus.active:
        return
    admins = await session.scalars(
        select(User.id)
        .where(User.role == Role.admin, User.status == UserStatus.active)
        .with_for_update()
    )
    if set(admins) <= {target.id}:
        raise AppError(
            403, "LAST_ADMIN", "Không thể gỡ quyền Quản trị viên cuối cùng đang hoạt động"
        )


@router.get("", response_model=UserPage)
async def search_users(
    session: Session,
    _: Admin,
    q: Annotated[str | None, Query(max_length=320)] = None,
    role: Role | None = None,
    status: UserStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
) -> UserPage:
    """Tìm theo email hoặc tên hiển thị, lọc vai trò/trạng thái, 50 bản ghi mỗi trang (Req 25.1)."""
    conds = []
    if q and q.strip():
        pattern = f"%{_escape_like(q.strip())}%"
        conds.append(
            or_(
                User.email.ilike(pattern, escape="\\"),
                User.display_name.ilike(pattern, escape="\\"),
            )
        )
    if role is not None:
        conds.append(User.role == role)
    if status is not None:
        conds.append(User.status == status)
    total = await session.scalar(select(func.count()).select_from(User).where(*conds))
    rows = list(
        await session.scalars(
            select(User)
            .where(*conds)
            .order_by(User.created_at.desc(), User.id)
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )
    )
    points, bonus = await _scores(session, [u.id for u in rows])
    items = [_out(u, points.get(u.id, 0), bonus.get(u.id, 0)) for u in rows]
    return UserPage(total=int(total or 0), page=page, page_size=PAGE_SIZE, items=items)


@router.get("/audit", response_model=AuditPage)
async def audit_log(
    session: Session,
    _: Admin,
    page: Annotated[int, Query(ge=1)] = 1,
    action: Annotated[str | None, Query(max_length=64)] = None,
) -> AuditPage:
    """Nhật ký thao tác quản trị, mới nhất trước. Phải khai báo trước /{user_id}."""
    where = [AuditLog.action == action] if action else []
    total = int(await session.scalar(select(func.count()).select_from(AuditLog).where(*where)) or 0)
    logs = list(
        await session.scalars(
            select(AuditLog)
            .where(*where)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * AUDIT_PAGE_SIZE)
            .limit(AUDIT_PAGE_SIZE)
        )
    )
    return AuditPage(
        total=total, page=page, page_size=AUDIT_PAGE_SIZE, items=await _audit_rows(session, logs)
    )


@router.get("/{user_id}", response_model=UserDetailOut)
async def user_detail(user_id: uuid.UUID, session: Session, _: Admin) -> UserDetailOut:
    """Hồ sơ một tài khoản: điểm, tiến trình tóm tắt và các thao tác quản trị gần đây lên nó."""
    target = await session.get(User, user_id)
    if target is None:
        raise AppError(404, "USER_NOT_FOUND", "Không tìm thấy người dùng")
    base = await _out_one(session, target)
    row = await session.get(GameSave, user_id)
    logs = list(
        await session.scalars(
            select(AuditLog)
            .where(AuditLog.target_type == "users", AuditLog.target_id == str(user_id))
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(HISTORY_LIMIT)
        )
    )
    return UserDetailOut(
        **base.model_dump(), save=_summary(row), history=await _audit_rows(session, logs)
    )


@router.patch("/{user_id}/role", response_model=UserAdminOut)
async def change_role(
    user_id: uuid.UUID, body: RoleIn, session: Session, actor: Admin
) -> UserAdminOut:
    """Đổi vai trò, ghi nhật ký kiểm toán người thực hiện, cũ, mới, thời điểm (Req 25.2)."""
    target = await _lock_user(session, user_id)
    if body.role != Role.admin:
        await ensure_not_last_admin(session, target)
    before = {"role": target.role.value, "is_teacher": target.is_teacher}
    target.role = body.role
    if body.is_teacher is not None:
        target.is_teacher = body.is_teacher
    after = {"role": target.role.value, "is_teacher": target.is_teacher}
    if before != after:
        session.add(
            AuditLog(
                actor_id=actor.id,
                action="user_role_change",
                target_type="users",
                target_id=str(target.id),
                before=before,
                after=after,
            )
        )
    await session.commit()
    await session.refresh(target)
    return await _out_one(session, target)


@router.post("/{user_id}/disable", response_model=UserAdminOut)
async def disable_user(
    user_id: uuid.UUID, session: Session, actor: Admin, body: DisableIn | None = None
) -> UserAdminOut:
    """Vô hiệu hóa: thu hồi mọi refresh token, ẩn khỏi Bảng_Xếp_Hạng (Req 25.3)."""
    target = await _lock_user(session, user_id)
    await ensure_not_last_admin(session, target)
    before = target.status.value
    if target.status != UserStatus.disabled:
        target.status = UserStatus.disabled
        await revoke_all_refresh_tokens(session, target.id)
        await invalidate_cache(session)
        session.add(
            AuditLog(
                actor_id=actor.id,
                action="user_disable",
                target_type="users",
                target_id=str(target.id),
                before={"status": before},
                after={"status": target.status.value, "reason": body.reason if body else None},
            )
        )
    await session.commit()
    await session.refresh(target)
    return await _out_one(session, target)


@router.post("/{user_id}/enable", response_model=UserAdminOut)
async def enable_user(user_id: uuid.UUID, session: Session, actor: Admin) -> UserAdminOut:
    target = await _lock_user(session, user_id)
    before = target.status
    # Tài khoản chờ phụ huynh xác nhận: quản trị viên kích hoạt thay khi không gửi được email
    if before not in (UserStatus.disabled, UserStatus.pending_guardian):
        raise AppError(
            409,
            "INVALID_TRANSITION",
            "Chỉ kích hoạt được tài khoản đang khoá hoặc đang chờ xác nhận",
        )
    target.status = UserStatus.active
    await invalidate_cache(session)
    session.add(
        AuditLog(
            actor_id=actor.id,
            action="user_enable",
            target_type="users",
            target_id=str(target.id),
            before={"status": before.value},
            after={"status": UserStatus.active.value},
        )
    )
    await session.commit()
    await session.refresh(target)
    return await _out_one(session, target)


@router.post("/{user_id}/grant", response_model=UserAdminOut)
async def grant_points(
    user_id: uuid.UUID, body: GrantIn, session: Session, actor: Admin
) -> UserAdminOut:
    """Cộng hoặc trừ điểm cho bất kỳ tài khoản nào, kể cả chính mình; lần nào cũng ghi nhật ký."""
    if not body.points and not body.skill_points:
        raise AppError(400, "NOTHING_TO_GRANT", "Hãy nhập số điểm cần cộng hoặc trừ")
    target = await _lock_user(session, user_id)
    if body.points:
        session.add(
            ScoreLedger(
                user_id=target.id,
                points=body.points,
                reason=ScoreReason.admin_bonus,
                ref_id=uuid.uuid4(),  # mỗi lần tặng là một dòng riêng trong sổ điểm
            )
        )
    if body.skill_points:
        await session.execute(
            insert(GameSave)
            .values(
                user_id=target.id,
                data={},
                points=0,
                bonus_skill_points=max(0, body.skill_points),
            )
            .on_conflict_do_update(
                index_elements=[GameSave.user_id],
                set_={
                    "bonus_skill_points": func.greatest(
                        0, GameSave.bonus_skill_points + body.skill_points
                    )
                },
            )
        )
    await invalidate_cache(session)
    session.add(
        AuditLog(
            actor_id=actor.id,
            action="user_grant",
            target_type="users",
            target_id=str(target.id),
            after={"points": body.points, "skill_points": body.skill_points, "reason": body.reason},
        )
    )
    await session.commit()
    return await _out_one(session, target)


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: uuid.UUID, session: Session, actor: Admin) -> Response:
    """Xoá vĩnh viễn tài khoản cùng tiến trình và điểm. Không khôi phục được."""
    if user_id == actor.id:
        raise AppError(400, "CANNOT_DELETE_SELF", "Không thể tự xoá tài khoản đang đăng nhập")
    target = await _lock_user(session, user_id)
    await ensure_not_last_admin(session, target)
    role = target.role.value
    await session.delete(target)
    await invalidate_cache(session)
    # Nhật ký không có khoá ngoại nên còn lại sau khi xoá; không ghi email để khỏi giữ dữ liệu riêng
    session.add(
        AuditLog(
            actor_id=actor.id,
            action="user_delete",
            target_type="users",
            target_id=str(user_id),
            before={"role": role},
        )
    )
    await session.commit()
    return Response(status_code=204)
