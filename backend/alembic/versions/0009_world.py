"""world: chơi nhiều người (đồng minh, tổ đội, lịch sử thách đấu)

Revision ID: 0009_world
Revises: 0008_admin_bonus
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_world"
down_revision: str | None = "0008_admin_bonus"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "alliances",
        sa.Column(
            "user_low", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "user_high", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
    )
    op.create_index("ix_alliances_user_high", "alliances", ["user_high"])
    op.create_table(
        "parties",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("leader_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
    )
    op.create_table(
        "party_members",
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "party_id", UUID, sa.ForeignKey("parties.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
    )
    op.create_index("ix_party_members_party_id", "party_members", ["party_id"])
    op.create_table(
        "duel_records",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "reporter_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "opponent_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("win", sa.Boolean(), nullable=False),
        sa.Column("map_id", sa.String(32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
    )
    op.create_index("ix_duel_records_reporter_id", "duel_records", ["reporter_id"])
    op.create_index("ix_duel_records_opponent_id", "duel_records", ["opponent_id"])


def downgrade() -> None:
    op.drop_table("duel_records")
    op.drop_table("party_members")
    op.drop_table("parties")
    op.drop_table("alliances")
