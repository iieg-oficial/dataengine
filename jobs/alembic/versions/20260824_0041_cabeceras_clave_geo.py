"""columna clave_geo en mapa_base.cabeceras_municipales

La tabla ya traia `clave_municipio`, pero guarda la clave **sin el prefijo de
estado**: `varchar(3)` con valores `01`, `02`, `125`. El visor filtra con la
clave INEGI completa de cinco digitos, asi que un
`CQL_FILTER=clave_municipio IN ('14039','14120')` no empata con ninguna fila y
la capa se vaciaria al elegir municipio. Se detecto el 2026-08-24 al probar el
CQL real contra cada tabla antes de declararla: por nombre de columna esta
habria pasado como buena.

Se agrega `clave_geo` derivada, que es el nombre que usa el resto del ecosistema
para la clave de cinco digitos —`mapalab.municipios.clave_geo`— y el que el plan
`clave-municipio-en-tablas.md` ya daba por existente en esta tabla.

Verificado sobre las 125 filas: `'14' || lpad(clave_municipio, 3, '0')` empata
con `mapalab.municipios.clave_geo` en el 100 %, de `14001` a `14125`.

Como en la `0040`, la columna es generada y no un backfill: se deriva sola y no
puede quedar desalineada de la que la origina.

Despues de aplicarla faltan los pasos que no son SQL: recargar el catalogo de
GeoServer para que publique la columna, declarar `municipio_field='clave_geo'` y
`municipio_field_type='clave'` en la capa desde mariachi, y refrescar el arbol.

Defensiva: se omite si la tabla aun no existe.

Revision ID: 0041_cabeceras_clave_geo
Revises: 0040_espacios_publicos_clave_municipio
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0041_cabeceras_clave_geo"
down_revision = "0040_espacios_publicos_clave_municipio"
branch_labels = None
depends_on = None

_TABLA = "mapa_base.cabeceras_municipales"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text(f"SELECT to_regclass('{_TABLA}')")).scalar() is None:
        return

    op.execute(
        f"ALTER TABLE {_TABLA} "
        "ADD COLUMN IF NOT EXISTS clave_geo varchar(5) "
        "GENERATED ALWAYS AS ('14' || lpad(clave_municipio, 3, '0')) STORED"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_cabeceras_municipales_clave_geo "
        f"ON {_TABLA} (clave_geo)"
    )
    op.execute(f"ANALYZE {_TABLA}")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text(f"SELECT to_regclass('{_TABLA}')")).scalar() is None:
        return

    op.execute("DROP INDEX IF EXISTS mapa_base.idx_cabeceras_municipales_clave_geo")
    op.execute(f"ALTER TABLE {_TABLA} DROP COLUMN IF EXISTS clave_geo")
