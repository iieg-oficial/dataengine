"""layer municipio_field_type (clave|nombre) para CQL filtering por capa

Revision ID: 0017_layer_municipio_field_type
Revises: 0016_layer_downloads
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa


revision = "0017_layer_municipio_field_type"
down_revision = "0016_layer_downloads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "layers",
        sa.Column("municipio_field_type", sa.String(20), nullable=True),
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_column("layers", "municipio_field_type", schema="mapalab")
