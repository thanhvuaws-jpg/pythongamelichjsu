"""`/api/v1/world`: thế giới chung cho nhiều người chơi.

- WebSocket `/api/v1/world/ws`: tin đầu tiên phải là {"t": "auth", "token": <mã truy cập>}; sau đó
  trang chơi gửi vị trí, lời mời, kết quả thách đấu; máy chủ gửi lại người cùng map, lời mời, tổ
  đội, đồng minh.
- REST: số người đang chơi theo map, đồng minh của tôi, lịch sử thách đấu của tôi.
- Người chơi máy (chỉ quản trị viên): xem, thêm, xoá. Máy chủ cho bot chạy trong `run_bots`, bắt đầu
  cùng ứng dụng; bot lưu ở bảng `bot_players` nên khởi động lại máy chủ không mất.
"""

import asyncio
import json
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.auth.deps import CurrentUser, require_role
from app.auth.jwt import TokenError, decode_access_token
from app.config import get_settings
from app.db import SessionLocal, get_session
from app.errors import AppError
from app.models import AuditLog, BotPlayer, Role, User, UserStatus
from app.models.world import Alliance, DuelRecord, Party, PartyMember
from app.world.bots import ACTIVITIES, MAX_BOTS, BotWorld
from app.world.hub import Hub

router = APIRouter(prefix="/api/v1/world", tags=["world"])
Session = Annotated[AsyncSession, Depends(get_session)]
Admin = Annotated[User, Depends(require_role(Role.admin))]
log = logging.getLogger(__name__)
BOT_TICK = 0.2  # máy chủ cho bot đi năm nhịp mỗi giây
BOT_SAVE_EVERY = 60.0  # lưu cấp mới của bot mỗi phút
AUTH_TIMEOUT = 10.0
MAX_MESSAGE = 8 * 1024


def _pair(a: str, b: str) -> tuple[uuid.UUID, uuid.UUID]:
    x, y = sorted((uuid.UUID(a), uuid.UUID(b)))
    return x, y


class DbStore:
    """Đồng minh, tổ đội, kết quả thách đấu lưu trong PostgreSQL."""

    async def allies(self, uid: str) -> set[str]:
        me = uuid.UUID(uid)
        async with SessionLocal() as s:
            rows = await s.execute(
                select(Alliance).where(or_(Alliance.user_low == me, Alliance.user_high == me))
            )
            return {str(r.user_high if r.user_low == me else r.user_low) for r in rows.scalars()}

    async def add_alliance(self, a: str, b: str) -> None:
        low, high = _pair(a, b)
        async with SessionLocal() as s:
            await s.execute(
                insert(Alliance).values(user_low=low, user_high=high).on_conflict_do_nothing()
            )
            await s.commit()

    async def remove_alliance(self, a: str, b: str) -> None:
        low, high = _pair(a, b)
        async with SessionLocal() as s:
            await s.execute(
                delete(Alliance).where(Alliance.user_low == low, Alliance.user_high == high)
            )
            await s.commit()

    async def party_of(self, uid: str):
        async with SessionLocal() as s:
            pid = await s.scalar(
                select(PartyMember.party_id).where(PartyMember.user_id == uuid.UUID(uid))
            )
            if pid is None:
                return None
            party = await s.get(Party, pid)
            members = (
                await s.scalars(select(PartyMember.user_id).where(PartyMember.party_id == pid))
            ).all()
            return str(pid), str(party.leader_id), [str(m) for m in members]

    async def create_party(self, leader: str, member: str) -> str:
        async with SessionLocal() as s:
            party = Party(leader_id=uuid.UUID(leader))
            s.add(party)
            await s.flush()
            for u in (leader, member):
                await s.execute(delete(PartyMember).where(PartyMember.user_id == uuid.UUID(u)))
                s.add(PartyMember(user_id=uuid.UUID(u), party_id=party.id))
            await s.commit()
            return str(party.id)

    async def join_party(self, pid: str, uid: str) -> None:
        async with SessionLocal() as s:
            await s.execute(delete(PartyMember).where(PartyMember.user_id == uuid.UUID(uid)))
            s.add(PartyMember(user_id=uuid.UUID(uid), party_id=uuid.UUID(pid)))
            await s.commit()

    async def leave_party(self, uid: str) -> None:
        me = uuid.UUID(uid)
        async with SessionLocal() as s:
            pid = await s.scalar(select(PartyMember.party_id).where(PartyMember.user_id == me))
            if pid is None:
                return
            await s.execute(delete(PartyMember).where(PartyMember.user_id == me))
            left = (
                await s.scalars(select(PartyMember.user_id).where(PartyMember.party_id == pid))
            ).all()
            if not left:
                await s.execute(delete(Party).where(Party.id == pid))
            else:
                await s.execute(
                    update(Party)
                    .where(Party.id == pid, Party.leader_id == me)
                    .values(leader_id=left[0])
                )
            await s.commit()

    async def record_duel(self, reporter: str, opponent: str, win: bool, map_id: str) -> None:
        try:
            other = uuid.UUID(opponent)
        except ValueError:
            return
        async with SessionLocal() as s:
            if await s.get(User, other) is None:
                return
            s.add(
                DuelRecord(
                    reporter_id=uuid.UUID(reporter), opponent_id=other, win=win, map_id=map_id[:32]
                )
            )
            await s.commit()


hub = Hub(DbStore(), bots=BotWorld())


_bot_sessions: async_sessionmaker | None = None


def _bot_db() -> async_sessionmaker:
    """Kết nối riêng cho vòng chạy bot, không giữ kết nối trong kho (vòng sống ngoài request)."""
    global _bot_sessions
    if _bot_sessions is None:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        _bot_sessions = async_sessionmaker(engine, expire_on_commit=False)
    return _bot_sessions


async def load_bots() -> None:
    """Đưa các bot đã lưu vào thế giới; bot ở map không còn tồn tại thì bỏ qua."""
    async with _bot_db()() as s:
        for row in (await s.scalars(select(BotPlayer))).all():
            if row.map_id in hub.bots.maps:
                hub.bots.add(str(row.id), row.name, row.map_id, row.activity, row.level)


async def save_bot_levels() -> None:
    dirty = [b for b in hub.bots.bots.values() if b.dirty]
    if not dirty:
        return
    async with _bot_db()() as s:
        for b in dirty:
            await s.execute(
                update(BotPlayer).where(BotPlayer.id == uuid.UUID(b.id)).values(level=b.level)
            )
            b.dirty = False
        await s.commit()


async def run_bots() -> None:
    """Vòng chạy của người chơi máy, sống cùng ứng dụng. Lỗi cơ sở dữ liệu không làm dừng vòng."""
    try:
        await load_bots()
    except Exception:  # noqa: BLE001  chưa có cơ sở dữ liệu (chạy thử): bot thêm sau vẫn chạy
        log.warning("Không nạp được người chơi máy đã lưu", exc_info=True)
    since_save = 0.0
    while True:
        await asyncio.sleep(BOT_TICK)
        try:
            await hub.tick(BOT_TICK)
            since_save += BOT_TICK
            if since_save >= BOT_SAVE_EVERY:
                since_save = 0.0
                await save_bot_levels()
        except Exception:  # noqa: BLE001
            log.warning("Lỗi một nhịp người chơi máy", exc_info=True)


async def _user_from_token(token) -> User | None:
    if not isinstance(token, str):
        return None
    try:
        uid = uuid.UUID(decode_access_token(token)["sub"])
    except (TokenError, ValueError, KeyError):
        return None
    async with SessionLocal() as s:
        user = await s.get(User, uid)
    return user if user is not None and user.status == UserStatus.active else None


@router.websocket("/ws")
async def world_ws(ws: WebSocket) -> None:
    await ws.accept()
    try:
        first = json.loads(await asyncio.wait_for(ws.receive_text(), AUTH_TIMEOUT))
    except (TimeoutError, WebSocketDisconnect, ValueError):
        await ws.close(code=4401)
        return
    user = await _user_from_token(
        first.get("token") if isinstance(first, dict) and first.get("t") == "auth" else None
    )
    if user is None:
        await ws.send_json({"t": "error", "code": "auth"})
        await ws.close(code=4401)
        return
    uid = str(user.id)
    lock = asyncio.Lock()

    async def send(msg: dict) -> None:
        async with lock:  # nhiều người cùng gửi tin tới một kết nối: xếp hàng cho khỏi lẫn
            await ws.send_json(msg)

    await hub.connect(uid, user.display_name, send)
    try:
        while True:
            raw = await ws.receive_text()
            if len(raw) > MAX_MESSAGE:
                continue
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            await hub.handle(uid, msg)
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(uid, send)


class AllyOut(BaseModel):
    id: str
    name: str
    online: bool


class DuelOut(BaseModel):
    opponent: str
    win: bool
    map_id: str
    created_at: str


@router.get("/online")
async def online() -> dict[str, int]:
    """Số người đang ở mỗi map (không lộ ai ở đâu)."""
    return hub.online()


@router.get("/allies", response_model=list[AllyOut])
async def my_allies(user: CurrentUser, session: Session) -> list[AllyOut]:
    me = user.id
    rows = (
        (
            await session.execute(
                select(Alliance).where(or_(Alliance.user_low == me, Alliance.user_high == me))
            )
        )
        .scalars()
        .all()
    )
    ids = [r.user_high if r.user_low == me else r.user_low for r in rows]
    names = (
        {
            u.id: u.display_name
            for u in (await session.scalars(select(User).where(User.id.in_(ids)))).all()
        }
        if ids
        else {}
    )
    return [AllyOut(id=str(i), name=names.get(i, ""), online=str(i) in hub.people) for i in ids]


@router.get("/duels", response_model=list[DuelOut])
async def my_duels(user: CurrentUser, session: Session) -> list[DuelOut]:
    rows = (
        await session.scalars(
            select(DuelRecord)
            .where(DuelRecord.reporter_id == user.id)
            .order_by(DuelRecord.created_at.desc())
            .limit(20)
        )
    ).all()
    ids = {r.opponent_id for r in rows}
    names = (
        {
            u.id: u.display_name
            for u in (await session.scalars(select(User).where(User.id.in_(ids)))).all()
        }
        if ids
        else {}
    )
    return [
        DuelOut(
            opponent=names.get(r.opponent_id, ""),
            win=r.win,
            map_id=r.map_id,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


# ----- người chơi máy (quản trị viên) -----
class BotIn(BaseModel):
    map_id: str
    activity: str = "mix"
    count: int = Field(1, ge=1, le=20)
    level: int = Field(1, ge=1, le=40)
    name: str | None = Field(None, max_length=40)


class BotRow(BaseModel):
    id: str
    name: str
    map_id: str
    map_name: str
    activity: str
    level: int
    doing: str


class BotsOut(BaseModel):
    bots: list[BotRow]
    maps: list[dict[str, str]]
    activities: dict[str, str]
    max: int
    online_people: int


def _bot_rows() -> list[BotRow]:
    world = hub.bots
    rows = [
        BotRow(
            id=b.id,
            name=b.name,
            map_id=b.map_id,
            map_name=world.maps[b.map_id].name,
            activity=b.activity,
            level=b.level,
            doing=world.doing(b),
        )
        for b in world.bots.values()
    ]
    return sorted(rows, key=lambda r: (r.map_id, r.name))


def _bots_out() -> BotsOut:
    return BotsOut(
        bots=_bot_rows(),
        maps=[{"id": k, "name": m.name} for k, m in hub.bots.maps.items()],
        activities=ACTIVITIES,
        max=MAX_BOTS,
        online_people=len(hub.people),
    )


@router.get("/bots", response_model=BotsOut)
async def list_bots(_: Admin) -> BotsOut:
    """Các người chơi máy đang chạy, mỗi bot đang làm gì."""
    return _bots_out()


@router.post("/bots", response_model=BotsOut, status_code=201)
async def add_bots(body: BotIn, admin: Admin, session: Session) -> BotsOut:
    world = hub.bots
    if body.map_id not in world.maps:
        raise AppError(422, "BAD_MAP", "Không có map này")
    if body.activity not in ACTIVITIES:
        raise AppError(422, "BAD_ACTIVITY", "Việc cho bot không hợp lệ")
    if len(world.bots) + body.count > MAX_BOTS:
        raise AppError(422, "TOO_MANY_BOTS", f"Tối đa {MAX_BOTS} người chơi máy")
    added = []
    base = (body.name or "").strip()
    for i in range(body.count):
        if not base:
            name = world.free_name()
        else:
            name = base if body.count == 1 else f"{base} {i + 1}"
        row = BotPlayer(
            name=name[:40], map_id=body.map_id, activity=body.activity, level=body.level
        )
        session.add(row)
        await session.flush()
        world.add(str(row.id), row.name, row.map_id, row.activity, row.level)
        added.append({"id": str(row.id), "name": row.name})
    session.add(
        AuditLog(
            actor_id=admin.id,
            action="bot_add",
            target_type="bot_players",
            target_id=body.map_id,
            after={"map": body.map_id, "activity": body.activity, "bots": added},
        )
    )
    await session.commit()
    return _bots_out()


@router.delete("/bots/{bot_id}", response_model=BotsOut)
async def remove_bot(bot_id: uuid.UUID, admin: Admin, session: Session) -> BotsOut:
    bot = hub.bots.bots.get(str(bot_id))
    await session.execute(delete(BotPlayer).where(BotPlayer.id == bot_id))
    hub.bots.remove(str(bot_id))
    session.add(
        AuditLog(
            actor_id=admin.id,
            action="bot_remove",
            target_type="bot_players",
            target_id=str(bot_id),
            before={"name": bot.name, "map": bot.map_id} if bot else None,
        )
    )
    await session.commit()
    return _bots_out()


@router.delete("/bots", response_model=BotsOut)
async def remove_all_bots(admin: Admin, session: Session) -> BotsOut:
    count = len(hub.bots.bots)
    await session.execute(delete(BotPlayer))
    hub.bots.bots.clear()
    session.add(
        AuditLog(
            actor_id=admin.id,
            action="bot_remove",
            target_type="bot_players",
            target_id="all",
            before={"count": count},
        )
    )
    await session.commit()
    return _bots_out()
