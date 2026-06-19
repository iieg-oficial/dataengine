"""layer badge JSONB (etiqueta nueva/actualizada por capa)

Revision ID: 0019_layer_badge
Revises: 0018_layer_icon_overrides
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0019_layer_badge"
down_revision = "0018_layer_icon_overrides"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "layers",
        sa.Column("badge", JSONB(), nullable=True),
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_column("layers", "badge", schema="mapalab")
