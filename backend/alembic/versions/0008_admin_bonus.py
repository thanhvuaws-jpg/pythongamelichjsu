"""admin_bonus: quản trị viên cộng điểm xếp hạng và điểm kỹ năng

Revision ID: 0008_admin_bonus
Revises: 0007_game_saves
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_admin_bonus"
down_revision: str | None = "0007_game_saves"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE score_reason ADD VALUE IF NOT EXISTS 'admin_bonus'")
    op.add_column(
        "game_saves",
        sa.Column("bonus_skill_points", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    # PostgreSQL không xoá được một giá trị của enum, nên giá trị admin_bonus được giữ lại
    op.execute("DELETE FROM score_ledger WHERE reason = 'admin_bonus'")
    op.drop_column("game_saves", "bonus_skill_points")
