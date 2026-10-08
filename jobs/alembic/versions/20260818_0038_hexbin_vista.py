"""vista mapalab.hexbin_agregado para publicar el hexbin en GeoServer

La 0037 dejo los conteos en dos tablas: `hexbin_cells` con el poligono de cada
celda, compartido por todo el catalogo, y `hexbin_counts` con el conteo por
capa, anio y municipio. GeoServer necesita **una** entidad con geometria para
publicar una capa, asi que la vista hace el join y expone las dos juntas.

Se publica como vista de base y no como SQL view de GeoServer a proposito: asi
la definicion vive aqui, versionada y revisable, y GeoServer solo la registra.

`fid` existe porque el WFS necesita un identificador estable por fila y la
tabla de conteos no tiene una sola columna que lo sea: la unicidad es la tupla
completa (capa, resolucion, celda, anio, municipio).

El cliente filtra con CQL sobre las columnas planas. Para el total de una capa a
la resolucion 7:

    layer_key = 'violencia_familiar' AND resolution = 7
      AND anio IS NULL AND clave_municipio IS NULL

Revision ID: 0038_hexbin_vista
Revises: 0037_hexbin_agregado
Create Date: 2026-08-18
"""
from alembic import op


revision = "0038_hexbin_vista"
down_revision = "0037_hexbin_agregado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE VIEW mapalab.hexbin_agregado AS
        SELECT
            n.layer_key || '|' || n.resolution || '|' || n.h3_index || '|'
                || COALESCE(n.anio::text, '') || '|' || COALESCE(n.clave_municipio, '') AS fid,
            n.layer_key,
            n.resolution,
            n.h3_index,
            n.anio,
            n.clave_municipio,
            n.total,
            c.geom
        FROM mapalab.hexbin_counts n
        JOIN mapalab.hexbin_cells c
          ON c.resolution = n.resolution
         AND c.h3_index = n.h3_index;
        """
    )
    op.execute("GRANT SELECT ON mapalab.hexbin_agregado TO mariachi_layers;")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS mapalab.hexbin_agregado;")
