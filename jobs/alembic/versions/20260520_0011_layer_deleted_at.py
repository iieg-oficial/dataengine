"""soft delete para layers (deleted_at + deleted_by)

Revision ID: 0011_layer_deleted_at
Revises: 0010_symbol_bucket_slug
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa


revision = "0011_layer_deleted_at"
down_revision = "0010_symbol_bucket_slug"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "layers",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="mapalab",
    )
    op.add_column(
        "layers",
        sa.Column("deleted_by", sa.String(length=100), nullable=True),
        schema="mapalab",
    )
    op.create_index(
        "ix_layers_alive",
        "layers",
        ["id"],
        unique=False,
        schema="mapalab",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_layers_deleted",
        "layers",
        ["deleted_at"],
        unique=False,
        schema="mapalab",
        postgresql_where=sa.text("deleted_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_layers_deleted", table_name="layers", schema="mapalab")
    op.drop_index("ix_layers_alive", table_name="layers", schema="mapalab")
    op.drop_column("layers", "deleted_by", schema="mapalab")
    op.drop_column("layers", "deleted_at", schema="mapalab")
