"""Chơi nhiều người: đồng minh, tổ đội, lịch sử thách đấu.

Vị trí người chơi trên map chỉ giữ trong bộ nhớ (thay đổi vài lần mỗi giây); những gì cần nhớ lâu
thì nằm ở đây.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import created_col, uuid_pk


class Alliance(Base):
    """Hai người kết đồng minh. Lưu một dòng cho mỗi cặp, id nhỏ hơn đứng trước để không trùng."""

    __tablename__ = "alliances"

    user_low: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    user_high: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = created_col()


class Party(Base):
    """Tổ đội tối đa bốn người, cùng đánh quái thì chia nhau kinh nghiệm."""

    __tablename__ = "parties"

    id: Mapped[uuid.UUID] = uuid_pk()
    leader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = created_col()


class PartyMember(Base):
    """Mỗi người chỉ ở một tổ đội nên khoá chính là user_id."""

    __tablename__ = "party_members"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    joined_at: Mapped[datetime] = created_col()


class DuelRecord(Base):
    """Kết quả một trận thách đấu, mỗi bên tự báo kết quả trận của mình."""

    __tablename__ = "duel_records"

    id: Mapped[uuid.UUID] = uuid_pk()
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opponent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    win: Mapped[bool] = mapped_column(Boolean, nullable=False)
    map_id: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    created_at: Mapped[datetime] = created_col()


class BotPlayer(Base):
    """Người chơi máy do quản trị viên thêm; máy chủ cho chạy suốt, chỉ lưu tên, map, việc, cấp."""

    __tablename__ = "bot_players"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    map_id: Mapped[str] = mapped_column(String(32), nullable=False)
    activity: Mapped[str] = mapped_column(String(16), nullable=False, default="mix")
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = created_col()
