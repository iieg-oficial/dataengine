"""layer metadata + stats

Revision ID: 0003_metadata_stats
Revises: 0002_tree_cache
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_metadata_stats"
down_revision = "0002_tree_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "layer_metadata",
        sa.Column("layer_key", sa.String(300), primary_key=True),
        sa.Column("workspace", sa.String(200)),
        sa.Column("layer_name_db", sa.String(200)),
        sa.Column("layer_name_usuario", sa.String(300)),
        sa.Column("descripcion", sa.Text),
        sa.Column("fuentes", postgresql.JSONB),
        sa.Column("metodologia", postgresql.JSONB),
        sa.Column("metadato", postgresql.JSONB),
        sa.Column("frecuencia", sa.String(200)),
        sa.Column("fecha_ultima", sa.String(200)),
        sa.Column("tipo_mapa", sa.String(100)),
        sa.Column("tipo_mapa_enlace", sa.String(500)),
        sa.Column("texto_leyenda", sa.Text),
        sa.Column("tarjeta_punto_poligono", sa.String(50)),
        sa.Column("link_final_capa", sa.String(500)),
        sa.Column("downloadable", sa.Boolean, server_default=sa.text("TRUE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_by", sa.String(100)),
        schema="mapalab",
    )
    op.create_index("idx_layer_metadata_workspace", "layer_metadata", ["workspace"], schema="mapalab")

    op.create_table(
        "layer_stats",
        sa.Column(
            "layer_key", sa.String(300),
            sa.ForeignKey("mapalab.layer_metadata.layer_key", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("stats_config", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("values", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("pie_numeralia", sa.String(500)),
        sa.Column("values_refreshed_at", sa.DateTime(timezone=True)),
        sa.Column("ttl_minutes", sa.Integer, nullable=False, server_default="1440"),
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_table("layer_stats", schema="mapalab")
    op.drop_index("idx_layer_metadata_workspace", table_name="layer_metadata", schema="mapalab")
    op.drop_table("layer_metadata", schema="mapalab")
