"""formato de imagen y antialias configurables por capa

mapalab pedia siempre image/png con el antialias por defecto de GeoServer. Medido
sobre un tile de 256x256 de mapa_base.curvas_de_nivel_render: png 21465 B,
png8 12114 B (-44%) y png8 sin antialias 3594 B (-83%). El ajuste optimo depende
de la capa (una rampa continua sufre con png8, una linea monocroma no), asi que
se configura por capa desde la pestana Servicios de mariachi.

Los defaults reproducen el comportamiento actual: ninguna capa cambia de aspecto
al aplicar la migracion.

Revision ID: 0032_layer_render_options
Revises: 0031_stats_read_grants
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa


revision = "0032_layer_render_options"
down_revision = "0031_stats_read_grants"
branch_labels = None
depends_on = None

SCHEMA = "mapalab"
TABLE = "layers"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column("image_format", sa.String(length=32), server_default="image/png", nullable=False),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column("antialias", sa.String(length=8), server_default="full", nullable=False),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_layers_image_format",
        TABLE,
        "image_format IN ('image/png', 'image/png8', 'image/jpeg')",
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_layers_antialias",
        TABLE,
        "antialias IN ('full', 'text', 'none')",
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint("ck_layers_antialias", TABLE, schema=SCHEMA, type_="check")
    op.drop_constraint("ck_layers_image_format", TABLE, schema=SCHEMA, type_="check")
    op.drop_column(TABLE, "antialias", schema=SCHEMA)
    op.drop_column(TABLE, "image_format", schema=SCHEMA)
