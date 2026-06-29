"""elimina indice espacial duplicado en economia.cultivos

economia.cultivos arrastraba dos indices GiST identicos sobre geom:
`sidx_cultivos_prueba_geom` (legado, de cuando la tabla era cultivos_prueba)
y `sidx_cultivos_geom` (el provisionado en 0020). Dos indices iguales solo
duplican espacio y el costo de escritura; el planner usa uno solo. Se elimina
el legado.

Revision ID: 0021_cultivos_drop_dup_index
Revises: 0020_cultivos_spatial_index
Create Date: 2026-06-29
"""
from alembic import op


revision = "0021_cultivos_drop_dup_index"
down_revision = "0020_cultivos_spatial_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS economia.sidx_cultivos_prueba_geom")


def downgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS sidx_cultivos_prueba_geom "
        "ON economia.cultivos USING gist (geom)"
    )
