"""asignar municipio a las parcelas de cultivo que caen dentro de Jalisco

La `0023` dejo `economia.cultivos` con 99.40 % de cobertura y **2 068 parcelas en
`NULL`**, anotadas entonces como "borde y costa". Medido el 2026-08-24, esas
2 068 son dos cosas distintas y solo una es un hueco:

- **1 873 (90.6 %) caen fuera del limite estatal.** La capa de cultivos cubre
  terreno de los estados vecinos: Ojuelos, Union de San Antonio, Jilotlan,
  Mezquitic y San Martin de Bolanos son los municipios limitrofes mas cercanos, a
  hasta 19 km. Para esas, `NULL` es la respuesta correcta y esta migracion no las
  toca: no tienen municipio de Jalisco porque no estan en Jalisco.
- **195 (9.4 %) caen dentro del estado** y aun asi ningun poligono municipal las
  contiene. **183 son de Jamay**, y el resto de Jocotepec, Tizapan el Alto y
  Tuxcueca: los cuatro son municipios riberenos de Chapala. Es tierra de cauce
  recuperado que el mosaico municipal no cubre.

Para esas 195 el municipio no es ambiguo: si la parcela esta en Jalisco,
pertenece a algun municipio, y el mas cercano es el unico candidato razonable
—entre 9 m y 1 311 m—. Se asignan por vecino mas cercano con el operador `<->`,
acotando a las que el limite estatal contiene.

**La regla es la pertenencia al estado, no una tolerancia en metros.** Un umbral
fijo habria rescatado parcelas de Zacatecas a 50 m de la frontera y dejado fuera
las de Jamay a 1.3 km, que son justo las que si son de Jalisco.

Son 195 filas, 615.6 ha. Solo toca las que quedaron nulas, asi que reaplicarla no
reescribe nada.

Queda pendiente aparte, y no es trabajo de esta migracion: el mosaico de
`mapa_base.limite_municipal` tiene huecos dentro del estado en la ribera de
Chapala. Lo correcto a mediano plazo es corregir el limite, no parchar cada capa
que caiga en el hueco.

Revision ID: 0044_cultivos_ribera_chapala
Revises: 0043_declarar_municipio_en_capas
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0044_cultivos_ribera_chapala"
down_revision = "0043_declarar_municipio_en_capas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT to_regclass('economia.cultivos')")).scalar() is None:
        return

    op.execute(
        """
        UPDATE economia.cultivos c
        SET clave_municipio = (
            SELECT m.clave_geo
            FROM mapa_base.limite_municipal m
            ORDER BY m.geom <-> ST_PointOnSurface(c.geom)
            LIMIT 1
        )
        WHERE c.clave_municipio IS NULL
          AND c.geom IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM mapa_base.limite_estatal e
              WHERE ST_Contains(e.geom, ST_PointOnSurface(c.geom))
          )
        """
    )
    op.execute("ANALYZE economia.cultivos")


def downgrade() -> None:
    pass
