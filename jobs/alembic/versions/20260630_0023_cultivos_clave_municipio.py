"""columna clave_municipio en economia.cultivos (filtro por municipio)

mapalab filtra "Vista por municipio" con un CQL sobre un campo de la capa, pero
economia.cultivos no tenia forma de identificar el municipio. Se materializa
clave_municipio (clave INEGI de 5 digitos) via spatial join contra
mapa_base.limite_municipal (ambos en EPSG:6368), usando el punto interior de
cada parcela. Asi mapalab puede filtrar `clave_municipio IN (...)`.

Defensiva: se omite si la tabla aun no existe.

Revision ID: 0023_cultivos_clave_municipio
Revises: 0022_cultivos_geom_3857
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa


revision = "0023_cultivos_clave_municipio"
down_revision = "0022_cultivos_geom_3857"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text("SELECT to_regclass('economia.cultivos')")
    ).scalar() is None:
        return

    op.execute(
        "CREATE INDEX IF NOT EXISTS sidx_limite_municipal_geom "
        "ON mapa_base.limite_municipal USING gist (geom)"
    )
    op.execute(
        "ALTER TABLE economia.cultivos "
        "ADD COLUMN IF NOT EXISTS clave_municipio varchar(5)"
    )
    op.execute(
        """
        UPDATE economia.cultivos c
        SET clave_municipio = m.clave_geo
        FROM mapa_base.limite_municipal m
        WHERE ST_Contains(m.geom, ST_PointOnSurface(c.geom))
          AND c.clave_municipio IS NULL
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_cultivos_clave_municipio "
        "ON economia.cultivos (clave_municipio)"
    )
    op.execute("ANALYZE economia.cultivos")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS economia.idx_cultivos_clave_municipio")
    op.execute(
        "ALTER TABLE economia.cultivos DROP COLUMN IF EXISTS clave_municipio"
    )
