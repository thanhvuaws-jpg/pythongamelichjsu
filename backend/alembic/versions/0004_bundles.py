"""bundles

Revision ID: 0004_bundles
Revises: 0003_content
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0004_bundles"
down_revision: str | None = "0003_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bundles",
        sa.Column("id", pg.UUID(as_uuid=True)),
        sa.Column(
            "level_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("levels.id", ondelete="CASCADE", name="fk_bundles_level_id_levels"),
            nullable=False,
        ),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_by",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_bundles_created_by_users"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bundles"),
        sa.UniqueConstraint("level_id", "version_no", name="uq_bundles_level_version"),
        sa.UniqueConstraint("storage_path", name="uq_bundles_storage_path"),
    )
    op.create_index("ix_bundles_level_id", "bundles", ["level_id"])


def downgrade() -> None:
    op.drop_table("bundles")
