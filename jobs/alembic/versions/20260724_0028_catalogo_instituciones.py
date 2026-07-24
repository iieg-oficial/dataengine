"""instituciones del catalogo (agrupacion de capas por dependencia)

Tabla que agrupa las capas de `mapalab.catalogo_capas` por la institucion que
las produce. El slug alimenta la ruta publica /catalogo/<institucion> y no debe
colisionar con el slug de una capa (validado en mariachi). `logo_url` queda
preparada para mostrar el logo en las pills; la primera version usa solo el
nombre. `orden` define el orden de las pills; `deleted_at` es papelera.

Revision ID: 0028_catalogo_instituciones
Revises: 0027_catalogo_capas_orden
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0028_catalogo_instituciones"
down_revision = "0027_catalogo_capas_orden"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalogo_instituciones",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("orden", sa.Integer, server_default=sa.text("0"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        schema="mapalab",
    )
    op.create_index(
        "uq_catalogo_instituciones_slug_alive",
        "catalogo_instituciones",
        ["slug"],
        unique=True,
        schema="mapalab",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_catalogo_instituciones_orden",
        "catalogo_instituciones",
        ["orden"],
        schema="mapalab",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.add_column(
        "catalogo_capas",
        sa.Column("institucion_id", sa.Integer, nullable=True),
        schema="mapalab",
    )
    op.create_foreign_key(
        "fk_catalogo_capas_institucion",
        "catalogo_capas",
        "catalogo_instituciones",
        ["institucion_id"],
        ["id"],
        source_schema="mapalab",
        referent_schema="mapalab",
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_catalogo_capas_institucion",
        "catalogo_capas",
        ["institucion_id"],
        schema="mapalab",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_catalogo_capas_institucion",
        table_name="catalogo_capas",
        schema="mapalab",
    )
    op.drop_constraint(
        "fk_catalogo_capas_institucion",
        "catalogo_capas",
        schema="mapalab",
        type_="foreignkey",
    )
    op.drop_column("catalogo_capas", "institucion_id", schema="mapalab")
    op.drop_index(
        "ix_catalogo_instituciones_orden",
        table_name="catalogo_instituciones",
        schema="mapalab",
    )
    op.drop_index(
        "uq_catalogo_instituciones_slug_alive",
        table_name="catalogo_instituciones",
        schema="mapalab",
    )
    op.drop_table("catalogo_instituciones", schema="mapalab")
