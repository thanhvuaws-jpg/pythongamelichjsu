"""duel_records.draw: trận thách đấu hoà không còn bị ghi là thua cho cả hai

Revision ID: 0011_duel_draw
Revises: 0010_bot_players
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_duel_draw"
down_revision: str | None = "0010_bot_players"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "duel_records",
        sa.Column("draw", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("duel_records", "draw")
