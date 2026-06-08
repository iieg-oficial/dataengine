"""layer icon_overrides (JSONB: iconos por estado normal/hover para temas)

Revision ID: 0018_layer_icon_overrides
Revises: 0017_layer_municipio_field_type
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0018_layer_icon_overrides"
down_revision = "0017_layer_municipio_field_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "layers",
        sa.Column("icon_overrides", JSONB, nullable=True),
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_column("layers", "icon_overrides", schema="mapalab")
