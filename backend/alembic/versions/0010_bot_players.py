"""bot_players: người chơi máy do quản trị viên thêm

Revision ID: 0010_bot_players
Revises: 0009_world
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_bot_players"
down_revision: str | None = "0009_world"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bot_players",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("map_id", sa.String(32), nullable=False),
        sa.Column("activity", sa.String(16), nullable=False, server_default="mix"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("bot_players")
