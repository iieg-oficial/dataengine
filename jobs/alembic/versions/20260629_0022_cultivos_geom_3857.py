"""columna materializada geom_3857 en economia.cultivos

mapalab renderiza el mapa en EPSG:3857 y su ImageWMS pide cada GetMap en 3857,
pero economia.cultivos esta almacenada en EPSG:6368, asi que GeoServer
reproyecta las geometrias on-the-fly en cada request. Se materializa una
columna geom_3857 (con su indice GiST) para publicar la capa nativa en 3857 y
eliminar la reproyeccion. La geom original (6368) se conserva.

Paso manual posterior (GeoServer, no DB): re-publicar el featuretype de
cultivos apuntando geom_3857 como columna de geometria por defecto (o crear una
capa nueva sobre ella) y declarar el SRS nativo 3857.

Revision ID: 0022_cultivos_geom_3857
Revises: 0021_cultivos_drop_dup_index
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa


revision = "0022_cultivos_geom_3857"
down_revision = "0021_cultivos_drop_dup_index"
branch_labels = None
depends_on = None


SCHEMA = "economia"
TABLE = "cultivos"
COLUMN = "geom_3857"
INDEX = "sidx_cultivos_geom_3857"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text("SELECT to_regclass(:t)"), {"t": f"{SCHEMA}.{TABLE}"}
    ).scalar() is None:
        return

    op.execute(
        f"ALTER TABLE {SCHEMA}.{TABLE} "
        f"ADD COLUMN IF NOT EXISTS {COLUMN} geometry(MultiPolygon, 3857)"
    )
    op.execute(
        f"UPDATE {SCHEMA}.{TABLE} "
        f"SET {COLUMN} = ST_Transform(geom, 3857) "
        f"WHERE {COLUMN} IS NULL AND geom IS NOT NULL"
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {INDEX} ON {SCHEMA}.{TABLE} "
        f"USING gist ({COLUMN}) WITH (fillfactor=100)"
    )
    op.execute(f"ANALYZE {SCHEMA}.{TABLE}")


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.{INDEX}")
    op.execute(f"ALTER TABLE {SCHEMA}.{TABLE} DROP COLUMN IF EXISTS {COLUMN}")
