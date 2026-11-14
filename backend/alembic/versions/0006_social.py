"""social: leaderboard_cache, classes, class_members, error_reports

Revision ID: 0006_social
Revises: 0005_play
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0006_social"
down_revision: str | None = "0005_play"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPORT_STATUS = ("new", "confirmed", "rejected", "resolved")


def _ts(name: str, nullable: bool = True, now: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=sa.func.now() if now else None,
    )


def _user_fk(table: str, col: str, ondelete: str, nullable: bool, pk: bool = False) -> sa.Column:
    return sa.Column(
        col,
        pg.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete=ondelete, name=f"fk_{table}_{col}_users"),
        nullable=nullable,
        primary_key=pk,
    )


def upgrade() -> None:
    pg.ENUM(*REPORT_STATUS, name="report_status").create(op.get_bind(), checkfirst=True)

    op.create_table(
        "leaderboard_cache",
        sa.Column("key", sa.String(80)),
        _ts("period_start"),
        sa.Column("data", pg.JSONB(), nullable=False),
        _ts("computed_at", nullable=False),
        sa.PrimaryKeyConstraint("key", name="pk_leaderboard_cache"),
    )

    op.create_table(
        "classes",
        sa.Column("id", pg.UUID(as_uuid=True)),
        _user_fk("classes", "teacher_id", "CASCADE", nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("join_code", sa.CHAR(6), nullable=False),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_classes"),
        sa.UniqueConstraint("join_code", name="uq_classes_join_code"),
    )
    op.create_index("ix_classes_teacher_id", "classes", ["teacher_id"])

    op.create_table(
        "class_members",
        sa.Column(
            "class_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey(
                "classes.id", ondelete="CASCADE", name="fk_class_members_class_id_classes"
            ),
            nullable=False,
        ),
        _user_fk("class_members", "user_id", "CASCADE", nullable=False),
        _ts("joined_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("class_id", "user_id", name="pk_class_members"),
    )
    op.create_index("ix_class_members_user_id", "class_members", ["user_id"])

    op.create_table(
        "error_reports",
        sa.Column("id", pg.UUID(as_uuid=True)),
        _user_fk("error_reports", "reporter_id", "SET NULL", nullable=True),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("counter_source", sa.String(1000)),
        sa.Column(
            "status",
            pg.ENUM(*REPORT_STATUS, name="report_status", create_type=False),
            nullable=False,
        ),
        _user_fk("error_reports", "handled_by", "SET NULL", nullable=True),
        sa.Column("resolution", sa.Text()),
        sa.Column(
            "hidden_question_ids",
            pg.ARRAY(pg.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
        _ts("created_at", nullable=False, now=True),
        _ts("updated_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_error_reports"),
    )
    op.create_index("ix_error_reports_reporter_id", "error_reports", ["reporter_id"])
    op.create_index("ix_error_reports_entity", "error_reports", ["entity_type", "entity_id"])
    op.create_index("ix_error_reports_status", "error_reports", ["status", "created_at"])


def downgrade() -> None:
    for table in ("error_reports", "class_members", "classes", "leaderboard_cache"):
        op.drop_table(table)
    pg.ENUM(name="report_status").drop(op.get_bind(), checkfirst=True)
