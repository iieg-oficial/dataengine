"""layer_metadata: fecha y frecuencia sugeridas desde la periodicidad

`public.layer_periodicity` ya sabe, para cada tabla con columna `fecha`, todos
los periodos que existen: la llena un cron cada noche recorriendo dataengine.
De ahi salen gratis dos datos que hoy se capturan a mano en la ficha de la capa,
`fecha_ultima` y `frecuencia`, y que en 85 capas estan vacios aunque su
periodicidad si este calculada.

Estas dos columnas guardan la **sugerencia**, no el valor. Lo capturado a mano
gana siempre: el job nunca pisa `fecha_ultima` ni `frecuencia`, solo deja al
lado lo que la periodicidad indica para que el editor pueda ofrecerlo. Sin esa
separacion no habria manera de distinguir «nadie lo ha llenado» de «alguien
decidio este valor», y una correccion deliberada se perderia en el siguiente
refresh.

Se guardan como texto y no como fecha porque `fecha_ultima` admite dos
precisiones —`2024` y `2024-11-30`— y la sugerencia tiene que poder expresar la
misma que el dato original.

`frecuencia_sugerida` cae en los valores del catalogo que ya usa el editor
(Mensual, Anual, …) para que aplicarla no introduzca sintaxis nueva.

Revision ID: 0047_sugerencias_periodicidad
Revises: 0046_atributos_columnas
Create Date: 2026-09-04
"""
from alembic import op

revision = '0047_sugerencias_periodicidad'
down_revision = '0046_atributos_columnas'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        'ALTER TABLE mapalab.layer_metadata '
        'ADD COLUMN IF NOT EXISTS fecha_ultima_sugerida VARCHAR(20)'
    )
    op.execute(
        'ALTER TABLE mapalab.layer_metadata '
        'ADD COLUMN IF NOT EXISTS frecuencia_sugerida VARCHAR(40)'
    )
    op.execute(
        'ALTER TABLE mapalab.layer_metadata '
        'ADD COLUMN IF NOT EXISTS sugerencias_actualizadas_en TIMESTAMPTZ'
    )


def downgrade() -> None:
    op.execute('ALTER TABLE mapalab.layer_metadata DROP COLUMN IF EXISTS sugerencias_actualizadas_en')
    op.execute('ALTER TABLE mapalab.layer_metadata DROP COLUMN IF EXISTS frecuencia_sugerida')
    op.execute('ALTER TABLE mapalab.layer_metadata DROP COLUMN IF EXISTS fecha_ultima_sugerida')
