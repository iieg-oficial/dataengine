"""version de las leyendas por workspace, para invalidar su cache sin tocar el gateway

El gateway guarda cada GetLegendGraphic seis horas e ignora el Cache-Control de GeoServer, asi que
una leyenda nueva no aparecia aunque se vaciara la cache de GeoServer. El visor agrega este numero
a la URL de la leyenda: subirlo cambia la URL, el gateway no la encuentra guardada y la pide de
nuevo. Lo sube el boton «Vaciar caches» de mariachi.

Revision ID: 0054_legend_version
Revises: 0053_capas_privadas
Create Date: 2026-10-05
"""
from alembic import op


revision = "0054_legend_version"
down_revision = "0053_capas_privadas"
branch_labels = None
depends_on = None


_UPGRADE = """
ALTER TABLE mapalab.workspaces ADD COLUMN IF NOT EXISTS legend_version integer NOT NULL DEFAULT 1;
"""

_DOWNGRADE = """
ALTER TABLE mapalab.workspaces DROP COLUMN IF EXISTS legend_version;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
