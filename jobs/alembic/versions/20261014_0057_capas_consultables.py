"""capas consultables: el visor solo pide GetFeatureInfo a las capas con `queryable`

Hasta ahora la unica forma de que una capa no abriera la infobox era la regla del workspace
`general` del visor, que solo la descarta si hay otra capa tematica encendida. Las curvas de
nivel abrian infobox cuando eran la unica capa activa. Con esta columna se apaga por capa
desde mariachi, y las curvas nacen apagadas.

Revision ID: 0057_capas_consultables
Revises: 0056_reaplica_lectura_tematica
Create Date: 2026-10-14
"""
from alembic import op


revision = "0057_capas_consultables"
down_revision = "0056_reaplica_lectura_tematica"
branch_labels = None
depends_on = None


_UPGRADE = """
ALTER TABLE mapalab.layers ADD COLUMN IF NOT EXISTS queryable boolean NOT NULL DEFAULT TRUE;
UPDATE mapalab.layers SET queryable = FALSE WHERE id = 'curvas_de_nivel';
"""

_DOWNGRADE = """
ALTER TABLE mapalab.layers DROP COLUMN IF EXISTS queryable;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
