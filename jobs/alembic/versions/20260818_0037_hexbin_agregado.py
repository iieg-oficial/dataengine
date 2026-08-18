"""conteos H3 precalculados para el hexbin del visor

El visor agrupa puntos en hexagonos H3 desde mapalab 1.129.0, pero lo hace en el
navegador: hay que traerse los puntos. Medido contra la capa peor,
`delitos_fiscalia_violencia_familiar` con 110 215 puntos, eso son **50 MB de
GeoJSON y 82 MB de heap**, y se paga en cada F5 porque sessionStorage guarda el
estado, nunca las geometrias. De ahi el tope de 20 000 elementos del cliente.

Precalculando, el navegador recibe **4 503 hexagonos ya contados** en vez de
110 215 puntos. El calculo nunca fue el problema —129 ms— sino el transporte.

Son dos tablas y no una por una razon que solo H3 permite: la celda
`8a2a1072b59ffff` es la misma para delitos y para escuelas, asi que su poligono
se guarda **una vez para todo el catalogo**. Con una rejilla arbitraria habria
que repetirlo por capa.

    hexbin_cells   (resolution, h3_index) -> geom      ~15 000 filas, ~3 MB
    hexbin_counts  (layer_key, resolution, h3_index, anio, clave_municipio)

El conteo va por **anio y municipio como columnas**, no resuelto por geometria.
Una celda de r7 mide 1.5 km de lado y las del borde contienen puntos de dos
municipios: como columna el conteo es exacto, resuelto espacialmente seria
aproximado y no cuadraria con el filtro normal del visor. Medido, cuesta poco:
en r7 se pasa de 2 169 celdas a 9 171 filas, no a 2 169 x 10 anios x 125
municipios, porque cada punto cae en un solo anio y un solo municipio.

Las resoluciones que puebla el job son **3, 4, 6 y 7**: r3/r4 para la vista de
estado y r6/r7 para la de municipio. De r8 hacia abajo lo sigue cubriendo el
calculo en cliente, que ademas respeta cualquier filtro dinamico.

`anio` y `clave_municipio` son nullable a proposito: hay capas de puntos sin
columna de fecha y sin municipio, y ahi el conteo total sigue siendo valido. La
fila con los dos en NULL es el total de la celda sin desglosar.

No se toca ninguna tabla tematica: todo vive en el schema `mapalab` y la bajada
es un DROP.

Revision ID: 0037_hexbin_agregado
Revises: 0036_layer_geometry_type
Create Date: 2026-08-18
"""
from alembic import op


revision = "0037_hexbin_agregado"
down_revision = "0036_layer_geometry_type"
branch_labels = None
depends_on = None

SCHEMA = "mapalab"
SRID = 6368


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.hexbin_cells (
            resolution smallint NOT NULL,
            h3_index   text     NOT NULL,
            geom       geometry(Polygon, {SRID}) NOT NULL,
            CONSTRAINT pk_hexbin_cells PRIMARY KEY (resolution, h3_index),
            CONSTRAINT ck_hexbin_cells_resolution CHECK (resolution BETWEEN 0 AND 15)
        );
        """
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS idx_hexbin_cells_geom "
        f"ON {SCHEMA}.hexbin_cells USING GIST (geom);"
    )

    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.hexbin_counts (
            layer_key       text     NOT NULL,
            resolution      smallint NOT NULL,
            h3_index        text     NOT NULL,
            anio            smallint,
            clave_municipio text,
            total           integer  NOT NULL,
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_hexbin_counts_total CHECK (total > 0)
        );
        """
    )
    op.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS uq_hexbin_counts "
        f"ON {SCHEMA}.hexbin_counts "
        f"(layer_key, resolution, h3_index, COALESCE(anio, -1), COALESCE(clave_municipio, ''));"
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS idx_hexbin_counts_lookup "
        f"ON {SCHEMA}.hexbin_counts (layer_key, resolution, anio, clave_municipio);"
    )
    op.execute(
        f"ALTER TABLE {SCHEMA}.hexbin_counts "
        f"ADD CONSTRAINT fk_hexbin_counts_cell "
        f"FOREIGN KEY (resolution, h3_index) "
        f"REFERENCES {SCHEMA}.hexbin_cells (resolution, h3_index) ON DELETE CASCADE;"
    )

    for table in ("hexbin_cells", "hexbin_counts"):
        op.execute(f"GRANT SELECT ON {SCHEMA}.{table} TO mariachi_layers;")


def downgrade() -> None:
    op.execute(f"DROP TABLE IF EXISTS {SCHEMA}.hexbin_counts;")
    op.execute(f"DROP TABLE IF EXISTS {SCHEMA}.hexbin_cells;")
