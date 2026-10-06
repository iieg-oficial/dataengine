"""merge: la 0035a de tamal-verde entra a la linea de tamal-rojo

La `0035a_formato_anio_tarjetitas` salio en verde colgando de la
`0035_curvas_render_catalogo`, y en rojo la `0036_layer_geometry_type` cuelga de
esa misma revision. Al bajar verde a rojo quedan dos cabezas, asi que se unen
aqui en vez de reapuntar el `down_revision` de ninguna de las dos: un entorno
que ya aplico una de ellas la da por corrida y nunca la ejecutaria.

Esta revision no toca la base. Solo junta las dos ramas.

Revision ID: 0048_merge_formato_anio
Revises: 0035a_formato_anio_tarjetitas, 0047_sugerencias_periodicidad
Create Date: 2026-09-17
"""

revision = '0048_merge_formato_anio'
down_revision = ('0035a_formato_anio_tarjetitas', '0047_sugerencias_periodicidad')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
