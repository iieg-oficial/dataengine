"""tipo de geometria por capa en el catalogo

El visor y el plugin de QGIS ya saben dibujar el tipo de geometria de una capa
—`GeometryTypeBadge` en el panel de capas activas, `_pintar_geometria` en el
delegate del plugin— pero el dato no existia en ninguna parte. Cada cliente lo
resolvia por su cuenta con un `DescribeFeatureType` por capa y en caliente: el
visor lo pedia al abrir el panel, el plugin al pintar cada fila. Con 119 capas
distintas eso es una rafaga de peticiones a GeoServer por cada sesion, y basta
que una falle para que el icono no aparezca.

La columna guarda el dato una sola vez. Los valores son los que ya espera el
frontend, sin traduccion intermedia:

    point | line | polygon | raster

Queda nullable a proposito. Los nodos que no son capa (tema, category, label,
group) no tienen geometria, y entre las hojas hay una —`curvas_de_nivel`— que
se publica solo por WMS: su `wfs_available` es FALSE y GeoServer responde
`Could not find type` al describirla, asi que no hay forma de deducir el tipo
sin red. Un NULL ahi significa «no se pudo determinar», y se corrige a mano
desde el editor de capas de mariachi.

La migracion solo agrega la columna: el poblado inicial corre aparte con
`jobs/run_backfill_geometry_type.py`, que necesita hablar con GeoServer y no
tiene por que bloquear un `alembic upgrade`.

Los GRANT de `mariachi_layers` sobre `mapalab.layers` son a nivel de tabla, no
de columna, asi que la columna nueva queda accesible sin tocar permisos.

Revision ID: 0036_layer_geometry_type
Revises: 0035_curvas_render_catalogo
Create Date: 2026-08-10
"""
from alembic import op
import sqlalchemy as sa


revision = "0036_layer_geometry_type"
down_revision = "0035_curvas_render_catalogo"
branch_labels = None
depends_on = None

SCHEMA = "mapalab"
TABLE = "layers"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column("geometry_type", sa.String(length=20), nullable=True),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_layers_geometry_type",
        TABLE,
        "geometry_type IS NULL OR geometry_type IN ('point', 'line', 'polygon', 'raster')",
        schema=SCHEMA,
    )
    op.execute(
        """
        UPDATE mapalab.layers
           SET geometry_type = 'raster',
               updated_at = now()
         WHERE geometry_type IS NULL
           AND deleted_at IS NULL
           AND node_type = 'leaf'
           AND (raster_periodicity IS NOT NULL OR workspace_alias IN ('raster', 'lluvia', 'temperatura'));
        """
    )
    op.execute("DELETE FROM mapalab.layer_tree_cache;")


def downgrade() -> None:
    op.execute("DELETE FROM mapalab.layer_tree_cache;")
    op.drop_constraint("ck_layers_geometry_type", TABLE, schema=SCHEMA, type_="check")
    op.drop_column(TABLE, "geometry_type", schema=SCHEMA)
