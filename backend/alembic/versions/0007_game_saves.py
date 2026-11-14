"""game_saves: bản lưu của game theo tài khoản

Revision ID: 0007_game_saves
Revises: 0006_social
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0007_game_saves"
down_revision: str | None = "0006_social"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_saves",
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_game_saves_user_id_users"),
            nullable=False,
        ),
        sa.Column("data", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_game_saves"),
    )


def downgrade() -> None:
    op.drop_table("game_saves")
