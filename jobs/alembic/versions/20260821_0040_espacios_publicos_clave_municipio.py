"""columna clave_municipio en espacios_publicos_y_lugares_recreativos

Seis capas del visor salen de esta tabla —plaza, mercado, instalacion
deportiva o recreativa, centro comercial, instalacion gubernamental e
instalacion de servicios— y ninguna se puede filtrar por municipio: no tienen
campo que lo identifique. En `mapalab.hexbin_counts` eso se ve como 6 222
puntos con `clave_municipio` nula, todo el faltante del precalculado salvo una
fila.

No hace falta spatial join: la clave ya esta en el dato. `cvegeo` es el
geocodigo INEGI a nivel manzana y sus primeros cinco digitos son la clave del
municipio. Verificado el 2026-08-21 sobre las 5 780 filas: `left(cvegeo, 5)`
empata con `mapalab.municipios.clave_geo` en el 100 %, sin nulos, incluidas las
seis filas de 13 caracteres.

Por eso la columna es GENERATED ALWAYS ... STORED y no un backfill: se deriva
sola en cada alta y no puede quedar desalineada del `cvegeo` que la origina.

Despues de aplicarla faltan dos pasos que no son SQL: declarar
`municipio_field='clave_municipio'` y `municipio_field_type='clave'` en las seis
capas desde mariachi, y correr `make refresh-layer-tree`.

Defensiva: se omite si la tabla aun no existe.

Revision ID: 0040_espacios_publicos_clave_municipio
Revises: 0039_matviews_unique_fid
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa


revision = "0040_espacios_publicos_clave_municipio"
down_revision = "0039_matviews_unique_fid"
branch_labels = None
depends_on = None

_TABLA = "recursos_y_calidad_de_vida.espacios_publicos_y_lugares_recreativos"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text(f"SELECT to_regclass('{_TABLA}')")).scalar() is None:
        return

    op.execute(
        f"ALTER TABLE {_TABLA} "
        "ADD COLUMN IF NOT EXISTS clave_municipio varchar(5) "
        "GENERATED ALWAYS AS (left(cvegeo, 5)) STORED"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_espacios_publicos_clave_municipio "
        f"ON {_TABLA} (clave_municipio)"
    )
    op.execute(f"ANALYZE {_TABLA}")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text(f"SELECT to_regclass('{_TABLA}')")).scalar() is None:
        return

    op.execute("DROP INDEX IF EXISTS recursos_y_calidad_de_vida.idx_espacios_publicos_clave_municipio")
    op.execute(f"ALTER TABLE {_TABLA} DROP COLUMN IF EXISTS clave_municipio")
