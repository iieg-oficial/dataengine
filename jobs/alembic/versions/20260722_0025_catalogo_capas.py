"""catalogo de capas (seccion "Catalogo" del visor: capas por descarga directa)

Tabla que alimenta la vista simplificada /catalogo de mapalab. Las capas se dan
de alta explicitamente desde mariachi. Guarda `workspace_alias` (no el workspace
real de GeoServer, que se resuelve al leer) + `geoserver_layer`. `enabled` es
visibilidad en el catalogo; `deleted_at` es papelera (soft-delete). El slug es
unico solo entre filas vivas (indice unico parcial).

Revision ID: 0025_catalogo_capas
Revises: 0024_layers_tiled
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0025_catalogo_capas"
down_revision = "0024_layers_tiled"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalogo_capas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("workspace_alias", sa.String(length=100), nullable=False),
        sa.Column("geoserver_layer", sa.String(length=255), nullable=False),
        sa.Column("search_tags", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean,
            server_default=sa.text("TRUE"),
            nullable=False,
        ),
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
        "uq_catalogo_capas_slug_alive",
        "catalogo_capas",
        ["slug"],
        unique=True,
        schema="mapalab",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_catalogo_capas_enabled",
        "catalogo_capas",
        ["enabled"],
        schema="mapalab",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_catalogo_capas_enabled",
        table_name="catalogo_capas",
        schema="mapalab",
    )
    op.drop_index(
        "uq_catalogo_capas_slug_alive",
        table_name="catalogo_capas",
        schema="mapalab",
    )
    op.drop_table("catalogo_capas", schema="mapalab")
