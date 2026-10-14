"""columna de fecha por capa: el visor filtra y anima por la columna que se elija en mariachi

Hasta ahora la periodicidad de una capa vectorial salia de la columna `fecha` o, desde mapalab
con zootropo, de la columna con el comentario `mapalab:fecha`. Las tablas las carga el ETL externo
y nadie escribe esos comentarios; con esta columna se elige desde el editor de capas y gana sobre
el comentario. NULL deja la resolucion automatica.

Revision ID: 0058_columna_de_fecha
Revises: 0057_capas_consultables
Create Date: 2026-10-14
"""
from alembic import op


revision = "0058_columna_de_fecha"
down_revision = "0057_capas_consultables"
branch_labels = None
depends_on = None


_UPGRADE = """
ALTER TABLE mapalab.layers ADD COLUMN IF NOT EXISTS date_column varchar(100);
"""

_DOWNGRADE = """
ALTER TABLE mapalab.layers DROP COLUMN IF EXISTS date_column;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
