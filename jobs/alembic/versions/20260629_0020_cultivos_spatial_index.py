"""indice espacial GiST + cluster en economia.cultivos

Optimiza las lecturas WMS/WFS de GeoServer sobre economia.cultivos.
Reemplaza al antiguo scripts/optimize-cultivos.py del repo geoserver, que
corria via docker exec en cada arranque (no funcionaba cross-host en
produccion). La tabla casi nunca se actualiza, asi que el indice se crea una
sola vez aqui y el CLUSTER/ANALYZE se aplican como mantenimiento puntual.

economia.cultivos se carga por fuera del ETL: la migracion es defensiva y se
omite si la tabla aun no existe.

Revision ID: 0020_cultivos_spatial_index
Revises: 0019_layer_badge
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa


revision = "0020_cultivos_spatial_index"
down_revision = "0019_layer_badge"
branch_labels = None
depends_on = None


SCHEMA = "economia"
TABLE = "cultivos"
INDEX = "sidx_cultivos_geom"
COLUMN = "geom"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text("SELECT to_regclass(:t)"), {"t": f"{SCHEMA}.{TABLE}"}
    ).scalar() is None:
        return

    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.{INDEX}")
    op.execute(
        f"CREATE INDEX {INDEX} ON {SCHEMA}.{TABLE} "
        f"USING gist ({COLUMN}) WITH (fillfactor=100)"
    )
    op.execute(f"CLUSTER {SCHEMA}.{TABLE} USING {INDEX}")
    op.execute(f"ANALYZE {SCHEMA}.{TABLE}")


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.{INDEX}")
