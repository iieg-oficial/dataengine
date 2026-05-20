"""layer notice JSONB (mensaje configurable por capa)

Revision ID: 0009_layer_notice
Revises: 0008_symbol_catalog_excluir_baneados
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0009_layer_notice"
down_revision = "0008_symbol_catalog_excluir_baneados"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "layers",
        sa.Column("notice", JSONB(), nullable=True),
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_column("layers", "notice", schema="mapalab")
