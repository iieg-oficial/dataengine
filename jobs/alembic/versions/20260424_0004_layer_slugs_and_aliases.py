"""layer slugs + aliases

Revision ID: 0004_layer_slugs_aliases
Revises: 0003_metadata_stats
Create Date: 2026-04-24

Slug publico por capa + tabla de aliases para deeplinks (?layer=<slug>) y
para reemplazar IDs internos en el estado vivo de la URL del visor.
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_layer_slugs_aliases"
down_revision = "0003_metadata_stats"
branch_labels = None
depends_on = None


_SLUG_REGEX = "^[a-z0-9-]+$"


def upgrade() -> None:
    op.add_column(
        "layers",
        sa.Column("slug", sa.String(60), nullable=True),
        schema="mapalab",
    )
    op.create_unique_constraint(
        "uq_layers_slug",
        "layers",
        ["slug"],
        schema="mapalab",
    )
    op.create_index(
        "idx_layers_slug",
        "layers",
        ["slug"],
        schema="mapalab",
        postgresql_where=sa.text("slug IS NOT NULL"),
    )
    op.create_check_constraint(
        "ck_layers_slug_format",
        "layers",
        sa.text(f"slug IS NULL OR (slug ~ '{_SLUG_REGEX}' AND length(slug) <= 60)"),
        schema="mapalab",
    )

    op.create_table(
        "layer_aliases",
        sa.Column("alias", sa.String(60), primary_key=True),
        sa.Column(
            "layer_id",
            sa.String(100),
            sa.ForeignKey("mapalab.layers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"alias ~ '{_SLUG_REGEX}' AND length(alias) <= 60",
            name="ck_layer_aliases_format",
        ),
        schema="mapalab",
    )
    op.create_index(
        "idx_layer_aliases_layer_id",
        "layer_aliases",
        ["layer_id"],
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_index("idx_layer_aliases_layer_id", table_name="layer_aliases", schema="mapalab")
    op.drop_table("layer_aliases", schema="mapalab")

    op.drop_constraint("ck_layers_slug_format", "layers", schema="mapalab", type_="check")
    op.drop_index("idx_layers_slug", table_name="layers", schema="mapalab")
    op.drop_constraint("uq_layers_slug", "layers", schema="mapalab", type_="unique")
    op.drop_column("layers", "slug", schema="mapalab")
