"""orden manual en catalogo_capas (reordenar por drag desde mariachi)

Agrega la columna `orden` a `mapalab.catalogo_capas` para poder ordenar
manualmente las capas del catalogo desde el admin y reflejar ese orden en la
vista publica. Inicializa `orden` respetando el orden alfabetico actual (por
`nombre`) entre las filas vivas.

Revision ID: 0027_catalogo_capas_orden
Revises: 0026_curvas_de_nivel_render
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa


revision = "0027_catalogo_capas_orden"
down_revision = "0026_curvas_de_nivel_render"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catalogo_capas",
        sa.Column("orden", sa.Integer, server_default=sa.text("0"), nullable=False),
        schema="mapalab",
    )
    op.execute(
        """
        UPDATE mapalab.catalogo_capas AS c
        SET orden = sub.rn
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (ORDER BY nombre) - 1 AS rn
            FROM mapalab.catalogo_capas
            WHERE deleted_at IS NULL
        ) AS sub
        WHERE c.id = sub.id
        """
    )
    op.create_index(
        "ix_catalogo_capas_orden",
        "catalogo_capas",
        ["orden"],
        schema="mapalab",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_catalogo_capas_orden",
        table_name="catalogo_capas",
        schema="mapalab",
    )
    op.drop_column("catalogo_capas", "orden", schema="mapalab")
