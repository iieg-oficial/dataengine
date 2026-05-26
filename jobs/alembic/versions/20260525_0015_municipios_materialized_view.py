"""materialized view mapalab.municipios (unifica IIEG + INEGI desde mapa_base)

Revision ID: 0015_municipios_materialized_view
Revises: 0014_layer_highlight_variant
Create Date: 2026-05-25
"""
from alembic import op


revision = "0015_municipios_materialized_view"
down_revision = "0014_layer_highlight_variant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mapalab.municipios AS
        SELECT
            iieg.clave_geo::text AS clave_geo,
            iieg.nombre,
            iieg.region,
            iieg.area_km2,
            iieg.area_ha,
            iieg.geom AS geom_iieg,
            inegi.geom AS geom_inegi
        FROM mapa_base.limite_municipal iieg
        LEFT JOIN mapa_base.limite_municipal_inegi inegi
            ON iieg.clave_geo::bpchar = inegi.clave_geo::text
        WITH DATA;
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_mapalab_municipios_clave "
        "ON mapalab.municipios (clave_geo);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mapalab_municipios_geom_iieg "
        "ON mapalab.municipios USING GIST (geom_iieg);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mapalab_municipios_geom_inegi "
        "ON mapalab.municipios USING GIST (geom_inegi);"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mapalab.municipios;")
