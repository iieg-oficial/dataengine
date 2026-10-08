"""clave_municipio por coordenada en las capas de puntos que no la tenian

Trece tablas de puntos —estaciones y paradas de transporte, estaciones MiBici,
aeropuertos, sedes y puntos de eventos— no tenian forma de identificar su
municipio, asi que el visor las recortaba con el `BBOX` de la seleccion y el job
del hexbin las contaba con `clave_municipio` nula.

No traen ningun codigo del que derivarla, a diferencia de la `0040` y la `0041`,
asi que aqui si toca calcularla: spatial join punto-en-poligono contra
`mapa_base.limite_municipal`, el mismo camino de la `0023` para
`economia.cultivos`. Todas las tablas y el limite estan en EPSG:6368, asi que no
hay reproyeccion de por medio.

**Un punto pertenece a un solo municipio**, asi que el caso no tiene la
ambiguedad de las capas lineales y poligonales: ahi un 5-6 % de los features
cruza mas de un municipio y hay que decidir entre duplicar la fila o elegir una,
decision que este plan deja abierta. Aqui no se decide nada.

Se usa `ST_PointOnSurface` para cubrir los `MULTIPOINT`, que en estas tablas son
de un solo punto pero no lo garantiza el tipo.

Son 699 filas entre las trece. El backfill solo toca las que quedaron nulas, asi
que reaplicarla no reescribe nada.

Despues faltan los pasos que no son SQL: recargar el catalogo de GeoServer para
que publique la columna, declarar `municipio_field='clave_municipio'` y
`municipio_field_type='clave'` en las capas desde mariachi, refrescar el arbol y
re-correr `run_refresh_hexbin.py`.

Defensiva: cada tabla se omite si no existe.

Revision ID: 0042_puntos_clave_municipio
Revises: 0041_cabeceras_clave_geo
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0042_puntos_clave_municipio"
down_revision = "0041_cabeceras_clave_geo"
branch_labels = None
depends_on = None

_TABLAS: tuple[tuple[str, str], ...] = (
    ("eventos", "cierres_viales"),
    ("eventos", "elementos"),
    ("eventos", "estaciones_mibici"),
    ("eventos", "estaciones_tp_masivo"),
    ("eventos", "eventos"),
    ("eventos", "flujo_estaciones_mimacro"),
    ("eventos", "paradas_l1"),
    ("eventos", "public_viewing"),
    ("eventos", "pudo"),
    ("eventos", "puntos_ascensos_descensos_plataformas"),
    ("eventos", "puntos_fan_fest"),
    ("eventos", "ride_estadio"),
    ("mapa_base", "aeropuertos"),
)


def upgrade() -> None:
    bind = op.get_bind()
    op.execute(
        "CREATE INDEX IF NOT EXISTS sidx_limite_municipal_geom "
        "ON mapa_base.limite_municipal USING gist (geom)"
    )

    for esquema, tabla in _TABLAS:
        if bind.execute(
            sa.text(f"SELECT to_regclass('{esquema}.{tabla}')")
        ).scalar() is None:
            continue

        op.execute(
            f'ALTER TABLE "{esquema}"."{tabla}" '
            "ADD COLUMN IF NOT EXISTS clave_municipio varchar(5)"
        )
        op.execute(
            f'UPDATE "{esquema}"."{tabla}" AS p '
            "SET clave_municipio = m.clave_geo "
            "FROM mapa_base.limite_municipal AS m "
            "WHERE ST_Contains(m.geom, ST_PointOnSurface(p.geom)) "
            "  AND p.clave_municipio IS NULL"
        )
        op.execute(
            f'CREATE INDEX IF NOT EXISTS "idx_{tabla}_clave_municipio" '
            f'ON "{esquema}"."{tabla}" (clave_municipio)'
        )
        op.execute(f'ANALYZE "{esquema}"."{tabla}"')


def downgrade() -> None:
    bind = op.get_bind()
    for esquema, tabla in _TABLAS:
        if bind.execute(
            sa.text(f"SELECT to_regclass('{esquema}.{tabla}')")
        ).scalar() is None:
            continue
        op.execute(f'DROP INDEX IF EXISTS "{esquema}"."idx_{tabla}_clave_municipio"')
        op.execute(f'ALTER TABLE "{esquema}"."{tabla}" DROP COLUMN IF EXISTS clave_municipio')
