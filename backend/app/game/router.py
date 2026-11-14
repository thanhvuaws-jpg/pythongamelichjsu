"""`/api/v1/game`: bản lưu theo tài khoản và thống kê.

Trang chơi đồng bộ bản lưu giữa localStorage của game và máy chủ, nên game không cần gọi mạng
trực tiếp. Mỗi lần lưu, máy chủ tính lại điểm và ghi các khoản mới vào `score_ledger`,
Bảng_Xếp_Hạng đọc từ sổ này như mọi nguồn điểm khác.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, require_role
from app.auth.jwt import now_utc
from app.config import get_settings
from app.db import get_session
from app.errors import AppError
from app.game.logic import aggregate, load_content, ref_id, score_items
from app.leaderboard.service import Period, top
from app.models import GameSave, Role, ScoreLedger, ScoreReason, User, UserStatus

router = APIRouter(prefix="/api/v1/game", tags=["game"])
Session = Annotated[AsyncSession, Depends(get_session)]
Staff = Annotated[User, Depends(require_role(Role.reviewer, Role.admin))]
MAX_SAVE_BYTES = 512 * 1024
ACTIVE_DAYS = 7
SIGNUP_DAYS = 14
HONOR_N = 20  # bảng vàng trong game: 20 tên mỗi bảng
POWER_MAX = 1_000_000


class SaveIn(BaseModel):
    data: dict[str, Any]


class BonusOut(BaseModel):
    bonus_points: int = 0
    bonus_skill_points: int = 0


class SaveOut(BonusOut):
    data: dict[str, Any] | None
    points: int
    updated_at: datetime | None


def _content():
    return load_content(get_settings().game_content_dir)


async def _bonus(session: AsyncSession, user_id) -> BonusOut:
    """Điểm quản trị viên đã tặng: điểm xếp hạng nằm trong sổ điểm, điểm kỹ năng nằm ở bản lưu."""
    points = await session.scalar(
        select(func.sum(ScoreLedger.points)).where(
            ScoreLedger.user_id == user_id, ScoreLedger.reason == ScoreReason.admin_bonus
        )
    )
    skill = await session.scalar(
        select(GameSave.bonus_skill_points).where(GameSave.user_id == user_id)
    )
    return BonusOut(bonus_points=int(points or 0), bonus_skill_points=int(skill or 0))


@router.get("/bonus", response_model=BonusOut)
async def get_bonus(session: Session, user: CurrentUser) -> BonusOut:
    """Trang chơi hỏi định kỳ, nhờ vậy điểm được tặng đến ngay cả khi người chơi đang chơi."""
    return await _bonus(session, user.id)


@router.get("/save", response_model=SaveOut)
async def get_save(session: Session, user: CurrentUser) -> SaveOut:
    row = await session.get(GameSave, user.id)
    bonus = await _bonus(session, user.id)
    if row is None:
        return SaveOut(data=None, points=0, updated_at=None, **bonus.model_dump())
    return SaveOut(
        data=row.data or None, points=row.points, updated_at=row.updated_at, **bonus.model_dump()
    )


@router.put("/save", response_model=SaveOut)
async def put_save(body: SaveIn, session: Session, user: CurrentUser) -> SaveOut:
    if len(json.dumps(body.data, ensure_ascii=False).encode("utf-8")) > MAX_SAVE_BYTES:
        raise AppError(413, "SAVE_TOO_LARGE", "Bản lưu quá lớn")
    items = score_items(body.data, _content())
    values = {"data": body.data, "points": sum(items.values())}
    stmt = insert(GameSave).values(user_id=user.id, **values)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[GameSave.user_id], set_={**values, "updated_at": func.now()}
        )
    )
    if items:
        # UNIQUE(user_id, reason, ref_id): mỗi câu chỉ được cộng điểm một lần trong đời tài khoản
        rows = [
            {
                "user_id": user.id,
                "points": points,
                "reason": ScoreReason(kind),
                "ref_id": ref_id(kind, key),
            }
            for (kind, key), points in items.items()
        ]
        await session.execute(insert(ScoreLedger).values(rows).on_conflict_do_nothing())
    await session.commit()
    row = await session.get(GameSave, user.id)
    await session.refresh(row)
    bonus = await _bonus(session, user.id)
    return SaveOut(data=None, points=row.points, updated_at=row.updated_at, **bonus.model_dump())


class HonorEntry(BaseModel):
    rank: int
    name: str
    value: int
    level: int = 0


class HonorOut(BaseModel):
    points: list[HonorEntry]
    power: list[HonorEntry]


def _clamp(value: Any, hi: int) -> int:
    try:
        return max(0, min(hi, int(value)))
    except (TypeError, ValueError):
        return 0


def rank_power(rows: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    """Xếp theo sức mạnh game tự ghi vào bản lưu (`rpg.power`).

    Bằng nhau thì cấp cao hơn đứng trước, rồi theo tên; cùng sức mạnh thì cùng hạng. Giá trị lạ
    (chữ, số âm, quá lớn) bị kẹp lại hoặc bỏ qua.
    """
    items = []
    for name, rpg in rows:
        if not isinstance(rpg, dict):
            continue
        power = _clamp(rpg.get("power"), POWER_MAX)
        if power > 0:
            items.append((power, _clamp(rpg.get("level"), 99), name))
    items.sort(key=lambda t: (-t[0], -t[1], t[2]))
    out: list[dict[str, Any]] = []
    prev, prev_rank = None, 0
    for i, (power, level, name) in enumerate(items[:HONOR_N], start=1):
        rank = prev_rank if power == prev else i
        prev, prev_rank = power, rank
        out.append({"rank": rank, "name": name, "value": power, "level": level})
    return out


@router.get("/honor", response_model=HonorOut)
async def honor(session: Session, _: CurrentUser) -> HonorOut:
    """Bảng vàng đặt ở map đầu.

    Gồm 20 người nhiều điểm học sử nhất (cùng sổ điểm với Bảng_Xếp_Hạng) và 20 người sức mạnh
    cao nhất. Chỉ trả tên hiển thị, chỉ tính tài khoản đang hoạt động.
    """
    entries, _computed = await top(session, Period.all, None, now_utc())
    points = [
        HonorEntry(rank=e["rank"], name=e["display_name"], value=e["points"])
        for e in entries[:HONOR_N]
    ]
    rows = await session.execute(
        select(User.display_name, GameSave.data["rpg"])
        .join(User, User.id == GameSave.user_id)
        .where(User.status == UserStatus.active)
    )
    power = [HonorEntry(**e) for e in rank_power([tuple(r) for r in rows])]
    await session.commit()  # lưu cache xếp hạng vừa tính
    return HonorOut(points=points, power=power)


@router.get("/analytics")
async def analytics(session: Session, _: Staff) -> dict[str, Any]:
    """Thống kê cho Quản_Trị_Viên và Thẩm_Định_Viên: ai học đến đâu, câu nào khó nhất."""
    # Hàng chưa có dữ liệu là người mới được tặng điểm, chưa chơi lần nào
    rows = [
        r for r in await session.scalars(select(GameSave)) if isinstance(r.data, dict) and r.data
    ]
    out = aggregate([r.data for r in rows], _content())
    since = now_utc() - timedelta(days=ACTIVE_DAYS)
    out["active_7d"] = sum(1 for r in rows if r.updated_at >= since)
    out["accounts"] = int(await session.scalar(select(func.count()).select_from(User)) or 0)
    out["accounts_active"] = int(
        await session.scalar(
            select(func.count()).select_from(User).where(User.status == UserStatus.active)
        )
        or 0
    )
    out["accounts_new_7d"] = int(
        await session.scalar(select(func.count()).select_from(User).where(User.created_at >= since))
        or 0
    )
    out["signups_daily"] = await _signups_daily(session)
    return out


async def _signups_daily(session: AsyncSession) -> list[dict[str, Any]]:
    """Số tài khoản mới mỗi ngày trong 14 ngày gần nhất (ngày UTC); ngày không có ai ghi 0."""
    start = now_utc().date() - timedelta(days=SIGNUP_DAYS - 1)
    day = func.date(func.timezone("UTC", User.created_at))
    rows = await session.execute(
        select(day, func.count())
        .where(User.created_at >= datetime.combine(start, datetime.min.time(), tzinfo=UTC))
        .group_by(day)
    )
    counts = {d: int(n) for d, n in rows}
    days = [start + timedelta(days=i) for i in range(SIGNUP_DAYS)]
    return [{"date": d.isoformat(), "count": counts.get(d, 0)} for d in days]
