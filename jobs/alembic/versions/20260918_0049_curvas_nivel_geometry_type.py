"""fija el tipo de geometria de la capa de curvas de nivel

El backfill de geometry_type no puede clasificar `curvas_de_nivel`: su
`wfs_layer_name` apunta a `curvas_de_nivel` (la tabla original, para las
descargas en 6368, segun la 0035), y en los entornos donde esa tabla no esta
publicada por WFS el `DescribeFeatureType` responde 400 y la capa queda sin
clasificar. Las curvas de nivel son LineStrings, asi que el valor correcto del
contrato es `line`. En entornos donde el backfill ya la clasifico, el UPDATE
con `IS DISTINCT FROM` no cambia nada.

Hay que borrar `mapalab.layer_tree_cache` o el cambio no llega al visor, igual
que en la 0035.

Revision ID: 0049_curvas_nivel_geometry_type
Revises: 0048_merge_formato_anio
Create Date: 2026-09-18
"""
from alembic import op


revision = "0049_curvas_nivel_geometry_type"
down_revision = "0048_merge_formato_anio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE mapalab.layers
           SET geometry_type = 'line',
               updated_at = now()
         WHERE id = 'curvas_de_nivel'
           AND geometry_type IS DISTINCT FROM 'line';
        """
    )
    op.execute("DELETE FROM mapalab.layer_tree_cache;")


def downgrade() -> None:
    op.execute(
        """
        UPDATE mapalab.layers
           SET geometry_type = NULL,
               updated_at = now()
         WHERE id = 'curvas_de_nivel'
           AND geometry_type = 'line';
        """
    )
    op.execute("DELETE FROM mapalab.layer_tree_cache;")
