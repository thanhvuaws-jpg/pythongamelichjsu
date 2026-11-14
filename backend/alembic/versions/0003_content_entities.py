"""content entities, content_versions, review_actions, notifications

Revision ID: 0003_content
Revises: 0002_sources
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0003_content"
down_revision: str | None = "0002_sources"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUMS = {
    "content_status": ("draft", "pending", "published", "archived"),
    "date_precision": ("day", "month", "year", "year_range", "century"),
    "causal_kind": ("cause_of", "leads_to", "context_of"),
    "map_layer_kind": ("boundary", "route", "ancient_place"),
    "fragment_kind": ("text", "artifact_image", "old_map", "photo"),
    "question_kind": ("single", "multi", "order", "match", "map_pick"),
    "objective_kind": ("go_to", "collect", "dialogue", "answer", "timeline"),
    "review_action_kind": ("submit", "approve", "reject", "restore"),
}


def _enum(name: str) -> pg.ENUM:
    # Kiểu enum được tạo một lần ở đầu upgrade, các bảng chỉ tham chiếu
    return pg.ENUM(*ENUMS[name], name=name, create_type=False)


def _ts(name: str, nullable: bool = True, now: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=sa.func.now() if now else None,
    )


def _fk(
    table: str, col: str, target: str, nullable: bool = True, ondelete: str = "SET NULL"
) -> sa.Column:
    ref_table = target.split(".")[0]
    return sa.Column(
        col,
        pg.UUID(as_uuid=True),
        sa.ForeignKey(target, ondelete=ondelete, name=f"fk_{table}_{col}_{ref_table}"),
        nullable=nullable,
    )


def _uuid_array(name: str) -> sa.Column:
    return sa.Column(
        name, pg.ARRAY(pg.UUID(as_uuid=True)), nullable=False, server_default="{}"
    )


def _jsonb(name: str, nullable: bool = True, default: str | None = None) -> sa.Column:
    return sa.Column(
        name,
        pg.JSONB(),
        nullable=nullable,
        server_default=sa.text(f"'{default}'::jsonb") if default else None,
    )


def _content_table(table: str, *columns: sa.Column | sa.Constraint) -> None:
    """Tạo bảng nội dung kèm cột chung và chỉ mục status."""
    op.create_table(
        table,
        sa.Column("id", pg.UUID(as_uuid=True)),
        sa.Column("status", _enum("content_status"), nullable=False),
        sa.Column("is_fiction", sa.Boolean(), nullable=False),
        _fk(table, "author_id", "users.id"),
        _fk(table, "last_editor_id", "users.id"),
        _fk(table, "published_version_id", "content_versions.id"),
        sa.Column("hidden_by_report", sa.Boolean(), nullable=False),
        _ts("created_at", nullable=False, now=True),
        _ts("updated_at", nullable=False, now=True),
        *columns,
        sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
    )
    op.create_index(f"ix_{table}_status", table, ["status"])


def _index_fks(table: str, *cols: str) -> None:
    for col in cols:
        op.create_index(f"ix_{table}_{col}", table, [col])


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in ENUMS.items():
        pg.ENUM(*values, name=name).create(bind, checkfirst=True)

    op.create_table(
        "content_versions",
        sa.Column("id", pg.UUID(as_uuid=True)),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot", pg.JSONB(), nullable=False),
        sa.Column("editor_id", pg.UUID(as_uuid=True)),
        sa.Column("status_at_save", _enum("content_status"), nullable=False),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_content_versions"),
        sa.UniqueConstraint(
            "entity_type", "entity_id", "version_no", name="uq_content_versions_entity_version"
        ),
    )
    op.create_index(
        "ix_content_versions_entity", "content_versions", ["entity_type", "entity_id"]
    )

    _content_table(
        "levels",
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("period_label", sa.Text(), nullable=False),
        sa.Column("intro", sa.Text(), nullable=False),
        _uuid_array("place_ids"),
        _jsonb("routes", nullable=False, default="[]"),
        _jsonb("unlock_rule"),
        _jsonb("map_bounds"),
    )

    _content_table(
        "places",
        _jsonb("names", nullable=False),
        sa.Column("modern_name", sa.Text(), nullable=False),
        sa.Column("lat", sa.Numeric(8, 5), nullable=False),
        sa.Column("lon", sa.Numeric(8, 5), nullable=False),
        sa.Column("description", sa.Text()),
        _jsonb("unlock_rule"),
        sa.CheckConstraint("lat BETWEEN -90 AND 90", name="ck_places_lat_range"),
        sa.CheckConstraint("lon BETWEEN -180 AND 180", name="ck_places_lon_range"),
    )

    _content_table(
        "persons",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("alt_names", pg.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("birth_year", sa.Integer()),
        sa.Column("death_year", sa.Integer()),
        sa.Column("birth_death_precision", _enum("date_precision")),
        sa.Column("bio", sa.Text()),
        _fk("persons", "portrait_media_id", "media.id"),
        sa.Column("portrait_is_illustration", sa.Boolean(), nullable=False),
    )
    _index_fks("persons", "portrait_media_id")

    _content_table(
        "events",
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("significance", sa.Text()),
        sa.Column("date_start", sa.Date()),
        sa.Column("date_end", sa.Date()),
        sa.Column("date_precision", _enum("date_precision")),
        sa.Column("lunar_date_text", sa.Text()),
        sa.Column("era_name", sa.Text()),
        _fk("events", "place_id", "places.id"),
        _fk("events", "level_id", "levels.id"),
        _uuid_array("person_ids"),
        _jsonb("numeric_facts", nullable=False, default="{}"),
        sa.CheckConstraint(
            "date_end IS NULL OR date_end >= date_start", name="ck_events_date_order"
        ),
    )
    _index_fks("events", "place_id", "level_id")

    _content_table(
        "causal_links",
        _fk("causal_links", "from_event_id", "events.id", nullable=False, ondelete="CASCADE"),
        _fk("causal_links", "to_event_id", "events.id", nullable=False, ondelete="CASCADE"),
        sa.Column("kind", _enum("causal_kind"), nullable=False),
        sa.Column("note", sa.Text()),
        sa.CheckConstraint("from_event_id <> to_event_id", name="ck_causal_links_distinct_events"),
    )
    _index_fks("causal_links", "from_event_id", "to_event_id")

    _content_table(
        "map_layers",
        _fk("map_layers", "level_id", "levels.id", nullable=False, ondelete="CASCADE"),
        sa.Column("kind", _enum("map_layer_kind"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        _jsonb("geojson"),
        _fk("map_layers", "media_id", "media.id"),
    )
    _index_fks("map_layers", "level_id", "media_id")

    _content_table(
        "fragments",
        _fk("fragments", "event_id", "events.id", nullable=False, ondelete="RESTRICT"),
        _fk("fragments", "place_id", "places.id"),
        sa.Column("kind", _enum("fragment_kind"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("han_nom_original", sa.Text()),
        sa.Column("translation", sa.Text()),
        _fk("fragments", "media_id", "media.id"),
    )
    _index_fks("fragments", "event_id", "place_id", "media_id")

    _content_table(
        "dialogues",
        _fk("dialogues", "place_id", "places.id"),
        _fk("dialogues", "speaker_person_id", "persons.id"),
        sa.Column("title", sa.Text(), nullable=False),
        _jsonb("nodes", nullable=False),
    )
    _index_fks("dialogues", "place_id", "speaker_person_id")

    # Ghi_Chú_Sử_Học tạo ở 0002 trước khi có bảng events
    op.create_foreign_key(
        "fk_historian_notes_event_id_events",
        "historian_notes",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )

    _content_table(
        "questions",
        _fk("questions", "event_id", "events.id", nullable=False, ondelete="RESTRICT"),
        sa.Column("kind", _enum("question_kind"), nullable=False),
        sa.Column("difficulty", sa.SmallInteger(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        _jsonb("options", nullable=False, default="[]"),
        sa.Column("correct_answer", pg.JSONB(), nullable=False),
        sa.Column("tolerance_km", sa.Numeric(8, 3)),
        sa.Column("explanation", sa.Text(), nullable=False),
        _fk("questions", "historian_note_id", "historian_notes.id"),
        _jsonb("answer_basis", nullable=False, default="[]"),
        sa.CheckConstraint("difficulty IN (1, 2, 3)", name="ck_questions_difficulty_range"),
    )
    _index_fks("questions", "event_id", "historian_note_id")

    _content_table(
        "quests",
        _fk("quests", "level_id", "levels.id", nullable=False, ondelete="CASCADE"),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("central_question", sa.Text(), nullable=False),
        sa.Column("answer_summary", sa.Text()),
        sa.Column("is_optional", sa.Boolean(), nullable=False),
        _jsonb("unlock_rule"),
    )
    _index_fks("quests", "level_id")

    _content_table(
        "objectives",
        _fk("objectives", "quest_id", "quests.id", nullable=False, ondelete="CASCADE"),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("kind", _enum("objective_kind"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("target_id", pg.UUID(as_uuid=True)),
        sa.Column("required", sa.Boolean(), nullable=False),
    )
    _index_fks("objectives", "quest_id")

    _content_table(
        "badges",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        _fk("badges", "media_id", "media.id"),
        _jsonb("condition", nullable=False),
    )
    _index_fks("badges", "media_id")

    op.create_table(
        "review_actions",
        sa.Column("id", pg.UUID(as_uuid=True)),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", pg.UUID(as_uuid=True), nullable=False),
        _fk("review_actions", "version_id", "content_versions.id"),
        sa.Column("reviewer_id", pg.UUID(as_uuid=True)),
        sa.Column("action", _enum("review_action_kind"), nullable=False),
        sa.Column("reason", sa.Text()),
        _uuid_array("checked_citation_ids"),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_review_actions"),
    )
    op.create_index("ix_review_actions_entity", "review_actions", ["entity_type", "entity_id"])

    op.create_table(
        "notifications",
        sa.Column("id", pg.UUID(as_uuid=True)),
        _fk("notifications", "user_id", "users.id", nullable=False, ondelete="CASCADE"),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("payload", pg.JSONB(), nullable=False),
        _ts("read_at"),
        _ts("created_at", nullable=False, now=True),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read_at"])


def downgrade() -> None:
    op.drop_constraint("fk_historian_notes_event_id_events", "historian_notes", type_="foreignkey")
    for table in (
        "notifications",
        "review_actions",
        "badges",
        "objectives",
        "quests",
        "questions",
        "dialogues",
        "fragments",
        "map_layers",
        "causal_links",
        "events",
        "persons",
        "places",
        "levels",
        "content_versions",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    for name in ENUMS:
        pg.ENUM(name=name).drop(bind, checkfirst=True)
