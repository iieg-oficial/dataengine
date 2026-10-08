"""retira la tabla legado public.mapalab_card

`public.mapalab_card` era el ETL del Google Sheet que alimentaba la tarjeta de las capas antes
de v1.4. Su contenido se migro a `mapalab.layer_metadata` y `mapalab.layer_stats` con el
bootstrap de v14 y nada la lee desde entonces. El 2026-09-24 se verifico contra una copia de
produccion que sus 132 filas (130 capas distintas) estan todas cubiertas por `layer_metadata`.

`IF EXISTS` porque los entornos creados despues del bootstrap nunca la tuvieron. El downgrade
no la recrea: su contenido ya vive en `mapalab.*` y un esquema vacio no serviria de nada.

Revision ID: 0051_drop_mapalab_card
Revises: 0050_rol_stats_lectura
Create Date: 2026-09-24
"""
from alembic import op


revision = "0051_drop_mapalab_card"
down_revision = "0050_rol_stats_lectura"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.mapalab_card")


def downgrade() -> None:
    pass
