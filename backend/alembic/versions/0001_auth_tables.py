"""auth tables: users, refresh_tokens, login_attempts, one_time_tokens,
guardian_consents, audit_log

Revision ID: 0001_auth
Revises:
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001_auth"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = sa.Enum("player", "editor", "reviewer", "admin", name="user_role")
user_status = sa.Enum("pending_guardian", "active", "disabled", "deleting", name="user_status")
token_purpose = sa.Enum("verify_email", "reset_password", name="token_purpose")


def _ts(name: str, nullable: bool = True, now: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=sa.func.now() if now else None,
    )


def _user_fk(table: str) -> sa.Column:
    return sa.Column(
        "user_id",
        pg.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE", name=f"fk_{table}_user_id_users"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("password_hash", sa.Text()),
        sa.Column("google_sub", sa.String(255)),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("birth_year", sa.Integer()),
        sa.Column("avatar_media_id", pg.UUID(as_uuid=True)),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_teacher", sa.Boolean(), nullable=False),
        sa.Column("status", user_status, nullable=False),
        _ts("deleted_request_at"),
        sa.Column("consent_version", sa.String(32)),
        _ts("consent_at"),
        _ts("created_at", nullable=False, now=True),
        _ts("updated_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("google_sub", name="uq_users_google_sub"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", pg.UUID(as_uuid=True)),
        _user_fk("refresh_tokens"),
        sa.Column("token_hash", sa.String(64), nullable=False),
        _ts("expires_at", nullable=False),
        _ts("revoked_at"),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("email", sa.String(320), nullable=False),
        _ts("attempted_at", nullable=False, now=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_login_attempts"),
    )
    op.create_index("ix_login_attempts_email_time", "login_attempts", ["email", "attempted_at"])

    op.create_table(
        "one_time_tokens",
        sa.Column("id", pg.UUID(as_uuid=True)),
        _user_fk("one_time_tokens"),
        sa.Column("purpose", token_purpose, nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        _ts("expires_at", nullable=False),
        _ts("used_at"),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_one_time_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_one_time_tokens_token_hash"),
    )
    op.create_index("ix_one_time_tokens_user_id", "one_time_tokens", ["user_id"])

    op.create_table(
        "guardian_consents",
        sa.Column("id", pg.UUID(as_uuid=True)),
        _user_fk("guardian_consents"),
        sa.Column("guardian_email", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        _ts("expires_at", nullable=False),
        _ts("confirmed_at"),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_guardian_consents"),
        sa.UniqueConstraint("token_hash", name="uq_guardian_consents_token_hash"),
    )
    op.create_index("ix_guardian_consents_user_id", "guardian_consents", ["user_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("actor_id", pg.UUID(as_uuid=True)),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(64)),
        sa.Column("before", pg.JSONB()),
        sa.Column("after", pg.JSONB()),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_audit_log"),
    )
    op.create_index("ix_audit_log_target", "audit_log", ["target_type", "target_id"])


def downgrade() -> None:
    for table in (
        "audit_log",
        "guardian_consents",
        "one_time_tokens",
        "login_attempts",
        "refresh_tokens",
        "users",
    ):
        op.drop_table(table)
    for enum in (token_purpose, user_status, user_role):
        enum.drop(op.get_bind(), checkfirst=True)
