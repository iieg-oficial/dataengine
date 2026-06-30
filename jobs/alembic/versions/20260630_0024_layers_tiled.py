"""columna mapalab.layers.tiled (servir capa por tiles)

Permite marcar por capa si el visor la pide como TileWMS (cacheable en GWC) en
vez de ImageWMS. Reemplaza la lista local TILED_LAYERS del frontend por config
editable desde mariachi.

Revision ID: 0024_layers_tiled
Revises: 0023_cultivos_clave_municipio
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa


revision = "0024_layers_tiled"
down_revision = "0023_cultivos_clave_municipio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "layers",
        sa.Column("tiled", sa.Boolean(), server_default="false", nullable=False),
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_column("layers", "tiled", schema="mapalab")
