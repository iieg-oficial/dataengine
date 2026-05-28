"""tabla mapalab.layer_downloads (cache de CSVs pre-generados en Acervo)

Revision ID: 0016_layer_downloads
Revises: 0015_municipios_materialized_view
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa


revision = "0016_layer_downloads"
down_revision = "0015_municipios_materialized_view"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mapalab.layer_downloads (
            layer_key TEXT PRIMARY KEY,
            db_schema TEXT NOT NULL,
            db_table TEXT NOT NULL,
            object_key TEXT NOT NULL,
            size_bytes BIGINT NOT NULL,
            row_count BIGINT,
            generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_layer_downloads_generated_at "
        "ON mapalab.layer_downloads (generated_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mapalab.layer_downloads;")
