"""layer tree cache

Revision ID: 0002_tree_cache
Revises: 0001_mapalab_init
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_tree_cache"
down_revision = "0001_mapalab_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "layer_tree_cache",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("etag", sa.String(64), nullable=False),
        sa.Column("tree", postgresql.JSONB, nullable=False),
        sa.Column("initial_order", postgresql.JSONB, nullable=False),
        sa.Column("workspaces", postgresql.JSONB, nullable=False),
        sa.Column("source_max_updated_at", sa.DateTime(timezone=True)),
        sa.Column("layer_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="ck_layer_tree_cache_singleton"),
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_table("layer_tree_cache", schema="mapalab")
