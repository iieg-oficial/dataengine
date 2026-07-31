"""defaults de render: antialias solo en texto y tiles activados

La 0032 dejo los defaults reproduciendo el comportamiento anterior (`full`,
`tiled=false`) para que ninguna capa cambiara de aspecto al migrar. Medido
despues sobre un tile de 256x256 de curvas de nivel, el suavizado completo pesa
21.5 KB contra 8.7 KB sin el (-59%) y conserva la transparencia, a diferencia de
`image/png8`, que sale como paleta indexada sin canal alfa y tapa el relieve.

`text` es el punto medio: quita el suavizado de las geometrias y lo conserva en
las etiquetas, que es donde se nota. `tiled` habilita GeoWebCache.

Aviso: una capa con `tiled` y un CQL_FILTER **no declarado** como parameter
filter en GWC pierde el metatiling 4x4 y sus poligonos salen cortados en los
bordes de cada tile. Tras aplicar esta migracion hay que declarar los filtros en
`sextante/config/gwc-filters.txt` (`scripts/init-gwc-filters.sh --learn`).

Revision ID: 0033_layer_render_defaults
Revises: 0032_layer_render_options
Create Date: 2026-07-31
"""
from alembic import op


revision = "0033_layer_render_defaults"
down_revision = "0032_layer_render_options"
branch_labels = None
depends_on = None

SCHEMA = "mapalab"
TABLE = "layers"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {SCHEMA}.{TABLE} ALTER COLUMN antialias SET DEFAULT 'text'")
    op.execute(f"ALTER TABLE {SCHEMA}.{TABLE} ALTER COLUMN tiled SET DEFAULT TRUE")
    op.execute(f"UPDATE {SCHEMA}.{TABLE} SET antialias = 'text' WHERE antialias = 'full'")
    op.execute(f"UPDATE {SCHEMA}.{TABLE} SET image_format = 'image/png' WHERE image_format <> 'image/png'")


def downgrade() -> None:
    op.execute(f"ALTER TABLE {SCHEMA}.{TABLE} ALTER COLUMN antialias SET DEFAULT 'full'")
    op.execute(f"ALTER TABLE {SCHEMA}.{TABLE} ALTER COLUMN tiled SET DEFAULT FALSE")
