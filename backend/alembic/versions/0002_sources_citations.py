"""sources, citations, historian_notes, media

Revision ID: 0002_sources
Revises: 0001_auth
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0002_sources"
down_revision: str | None = "0001_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

source_status = sa.Enum("pending", "approved", "rejected", name="source_status")
media_license = sa.Enum(
    "public_domain",
    "cc0",
    "cc_by",
    "cc_by_sa",
    "self_made",
    "written_permission",
    name="media_license",
)


def _ts(name: str, nullable: bool = True, now: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=sa.func.now() if now else None,
    )


def _user_ref(col: str, table: str) -> sa.Column:
    return sa.Column(
        col,
        pg.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL", name=f"fk_{table}_{col}_users"),
    )


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", pg.UUID(as_uuid=True)),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", sa.Text()),
        sa.Column("translators", sa.Text()),
        sa.Column("publisher", sa.Text()),
        sa.Column("year", sa.Integer()),
        sa.Column("edition", sa.String(64)),
        sa.Column("volume", sa.String(64)),
        sa.Column("tier", sa.SmallInteger()),
        sa.Column("isbn_or_archive_code", sa.String(64)),
        sa.Column("url", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", source_status, nullable=False),
        _user_ref("proposed_by", "sources"),
        _user_ref("approved_by", "sources"),
        _ts("approved_at"),
        sa.Column("rejection_reason", sa.Text()),
        _ts("created_at", nullable=False, now=True),
        _ts("updated_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.CheckConstraint("tier IS NULL OR tier IN (1, 2, 3)", name="ck_sources_tier_range"),
        sa.CheckConstraint(
            "status <> 'approved' OR tier IS NOT NULL", name="ck_sources_approved_has_tier"
        ),
    )
    op.create_index("ix_sources_status", "sources", ["status"])

    op.create_table(
        "citations",
        sa.Column("id", pg.UUID(as_uuid=True)),
        sa.Column(
            "source_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="RESTRICT", name="fk_citations_source_id_sources"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("field_path", sa.String(128), nullable=False),
        sa.Column("locator", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text()),
        sa.Column("is_verbatim_quote", sa.Boolean(), nullable=False),
        _user_ref("created_by", "citations"),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_citations"),
    )
    op.create_index("ix_citations_source_id", "citations", ["source_id"])
    op.create_index("ix_citations_entity", "citations", ["entity_type", "entity_id"])

    op.create_table(
        "historian_notes",
        sa.Column("id", pg.UUID(as_uuid=True)),
        sa.Column("event_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("field_path", sa.String(128), nullable=False),
        sa.Column("variants", pg.JSONB(), nullable=False),
        sa.Column("default_variant_idx", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text()),
        _ts("created_at", nullable=False, now=True),
        _ts("updated_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_historian_notes"),
    )
    op.create_index("ix_historian_notes_event_id", "historian_notes", ["event_id"])

    op.create_table(
        "media",
        sa.Column("id", pg.UUID(as_uuid=True)),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("mime", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("license", media_license, nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("license_url", sa.Text()),
        sa.Column("attribution", sa.Text()),
        sa.Column("permission_doc_path", sa.Text()),
        _user_ref("uploaded_by", "media"),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_media"),
        sa.UniqueConstraint("storage_path", name="uq_media_storage_path"),
    )


def downgrade() -> None:
    for table in ("media", "historian_notes", "citations", "sources"):
        op.drop_table(table)
    for enum in (media_license, source_status):
        enum.drop(op.get_bind(), checkfirst=True)
