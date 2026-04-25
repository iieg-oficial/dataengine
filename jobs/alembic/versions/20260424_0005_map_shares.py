"""map shares (snapshots persistidos del estado del mapa)

Revision ID: 0005_map_shares
Revises: 0004_layer_slugs_aliases
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_map_shares"
down_revision = "0004_layer_slugs_aliases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "map_shares",
        sa.Column("id", sa.String(10), primary_key=True),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("schema_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "last_accessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("access_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pinned_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_ip_hash", sa.String(64), nullable=True),
        sa.CheckConstraint("kind IN ('single','compare')", name="ck_map_shares_kind"),
        schema="mapalab",
    )
    op.create_index(
        "idx_map_shares_last_accessed",
        "map_shares",
        ["last_accessed_at"],
        schema="mapalab",
        postgresql_where=sa.text("pinned_until IS NULL"),
    )
    op.create_index(
        "idx_map_shares_pinned",
        "map_shares",
        ["pinned_until"],
        schema="mapalab",
        postgresql_where=sa.text("pinned_until IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_map_shares_pinned", table_name="map_shares", schema="mapalab")
    op.drop_index("idx_map_shares_last_accessed", table_name="map_shares", schema="mapalab")
    op.drop_table("map_shares", schema="mapalab")
