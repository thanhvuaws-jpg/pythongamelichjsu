"""play: progress, question_attempts, score_ledger, review_items, review_points, user_badges

Bảng notifications đã có từ 0003.

Revision ID: 0005_play
Revises: 0004_bundles
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0005_play"
down_revision: str | None = "0004_bundles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCORE_REASON = ("question", "timeline_bonus")


def _ts(name: str, nullable: bool = True, now: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=sa.func.now() if now else None,
    )


def _fk(table: str, col: str, target: str, primary_key: bool = False) -> sa.Column:
    ref_table = target.split(".")[0]
    return sa.Column(
        col,
        pg.UUID(as_uuid=True),
        sa.ForeignKey(target, ondelete="CASCADE", name=f"fk_{table}_{col}_{ref_table}"),
        nullable=False,
        primary_key=primary_key,
    )


def upgrade() -> None:
    pg.ENUM(*SCORE_REASON, name="score_reason").create(op.get_bind(), checkfirst=True)

    op.create_table(
        "progress",
        _fk("progress", "user_id", "users.id"),
        sa.Column("data", pg.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        _ts("updated_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("user_id", name="pk_progress"),
    )

    op.create_table(
        "question_attempts",
        _fk("question_attempts", "user_id", "users.id"),
        _fk("question_attempts", "question_id", "questions.id"),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("first_correct_attempt", sa.Integer()),
        sa.Column("scored", sa.Boolean(), nullable=False),
        _ts("created_at", nullable=False, now=True),
        _ts("updated_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("user_id", "question_id", name="pk_question_attempts"),
    )

    op.create_table(
        "score_ledger",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        _fk("score_ledger", "user_id", "users.id"),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column(
            "reason", pg.ENUM(*SCORE_REASON, name="score_reason", create_type=False), nullable=False
        ),
        sa.Column("ref_id", pg.UUID(as_uuid=True), nullable=False),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_score_ledger"),
        sa.UniqueConstraint("user_id", "reason", "ref_id", name="uq_score_ledger_user_reason_ref"),
    )
    op.create_index("ix_score_ledger_user_id", "score_ledger", ["user_id"])
    op.create_index("ix_score_ledger_created_user", "score_ledger", ["created_at", "user_id"])

    op.create_table(
        "review_items",
        _fk("review_items", "user_id", "users.id"),
        _fk("review_items", "question_id", "questions.id"),
        sa.Column("stage", sa.SmallInteger()),
        _ts("due_at", nullable=False),
        sa.Column("last_result", sa.Boolean()),
        _ts("last_reviewed_at"),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("user_id", "question_id", name="pk_review_items"),
    )
    op.create_index("ix_review_items_user_due", "review_items", ["user_id", "due_at"])

    op.create_table(
        "review_points",
        _fk("review_points", "user_id", "users.id"),
        sa.Column("total", sa.Integer(), nullable=False),
        _ts("updated_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("user_id", name="pk_review_points"),
    )

    op.create_table(
        "user_badges",
        _fk("user_badges", "user_id", "users.id"),
        _fk("user_badges", "badge_id", "badges.id"),
        _ts("awarded_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("user_id", "badge_id", name="pk_user_badges"),
    )


def downgrade() -> None:
    for table in (
        "user_badges",
        "review_points",
        "review_items",
        "score_ledger",
        "question_attempts",
        "progress",
    ):
        op.drop_table(table)
    pg.ENUM(name="score_reason").drop(op.get_bind(), checkfirst=True)
