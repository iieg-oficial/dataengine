"""layer highlight color + shape (resaltado del feature seleccionado en InfoBox)

Revision ID: 0014_layer_highlight_variant
Revises: 0013_map_shares_kind_swipe
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa


revision = "0014_layer_highlight_variant"
down_revision = "0013_map_shares_kind_swipe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "layers",
        sa.Column("highlight_color", sa.String(length=20), nullable=True),
        schema="mapalab",
    )
    op.add_column(
        "layers",
        sa.Column("highlight_shape", sa.String(length=20), nullable=True),
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_column("layers", "highlight_shape", schema="mapalab")
    op.drop_column("layers", "highlight_color", schema="mapalab")
