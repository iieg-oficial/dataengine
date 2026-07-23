"""tabla de render mapa_base.curvas_de_nivel_render (geometrias subdivididas en 3857)

mapa_base.curvas_de_nivel guarda cada curva como un LineString completo: la
mediana son 133 vertices, pero 47 features superan los 100k y la mayor llega a
910,621. Esas geometrias cruzan medio estado, asi que el indice GiST las
selecciona en casi cualquier tile y GeoServer termina procesando ~13.2 millones
de vertices por tile de 256px, sin importar el zoom (medido: 550 ms/tile a z=11
y 1120 ms/tile a z=15).

Se materializa una tabla de render con las mismas geometrias partidas con
ST_Subdivide (<=512 vertices por trozo) y ya reproyectadas a 3857, que es lo
que pide el visor. Medido sobre esta tabla: 13,206,693 -> 38,224 vertices por
tile a z=11, y la consulta espacial pasa de 164.7 ms a 0.49 ms.

La tabla original NO se toca: conserva las curvas completas en 6368 y sigue
siendo la fuente para descargas WFS.

Paso manual posterior (GeoServer, no DB): publicar el featuretype
general:curvas_de_nivel_render sobre esta tabla con SRS nativo 3857 y el estilo
curvas_de_nivel (filtra por curva_maestra, que se conserva). Luego apuntar
mapalab.layers.geoserver_layer a esa capa y dejar wfs_layer_name en la original
para que las descargas sigan entregando las curvas completas.

Revision ID: 0026_curvas_de_nivel_render
Revises: 0025_catalogo_capas
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa


revision = "0026_curvas_de_nivel_render"
down_revision = "0025_catalogo_capas"
branch_labels = None
depends_on = None


SCHEMA = "mapa_base"
SOURCE_TABLE = "curvas_de_nivel"
RENDER_TABLE = "curvas_de_nivel_render"
GEOM_INDEX = "sidx_curvas_de_nivel_render_geom"
MAESTRA_INDEX = "ix_curvas_de_nivel_render_curva_maestra"
MAX_VERTICES = 512
TARGET_SRID = 3857


def upgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text("SELECT to_regclass(:t)"), {"t": f"{SCHEMA}.{SOURCE_TABLE}"}
    ).scalar() is None:
        return

    op.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{RENDER_TABLE}")
    op.execute(
        f"CREATE TABLE {SCHEMA}.{RENDER_TABLE} AS "
        f"SELECT fid, elev, curva_maestra, "
        f"ST_Subdivide(ST_Transform(geom, {TARGET_SRID}), {MAX_VERTICES})::geometry(LineString, {TARGET_SRID}) AS geom "
        f"FROM {SCHEMA}.{SOURCE_TABLE} WHERE geom IS NOT NULL"
    )
    op.execute(
        f"ALTER TABLE {SCHEMA}.{RENDER_TABLE} ADD COLUMN gid bigserial PRIMARY KEY"
    )
    op.execute(
        f"CREATE INDEX {GEOM_INDEX} ON {SCHEMA}.{RENDER_TABLE} "
        f"USING gist (geom) WITH (fillfactor=100)"
    )
    op.execute(
        f"CREATE INDEX {MAESTRA_INDEX} ON {SCHEMA}.{RENDER_TABLE} (curva_maestra)"
    )
    op.execute(f"ANALYZE {SCHEMA}.{RENDER_TABLE}")


def downgrade() -> None:
    op.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{RENDER_TABLE}")
