"""historial de ediciones por celda + auditoria en layer_stats

Revision ID: 0030_grid_cell_history
Revises: 0029_catalogo_capas_infobox
Create Date: 2026-07-28
"""
from alembic import op
import sqlalchemy as sa


revision = "0030_grid_cell_history"
down_revision = "0029_catalogo_capas_infobox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "layer_stats",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        schema="mapalab",
    )
    op.add_column(
        "layer_stats",
        sa.Column("updated_by", sa.String(150), nullable=True),
        schema="mapalab",
    )

    op.create_table(
        "grid_cell_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("resource", sa.String(60), nullable=False),
        sa.Column("row_key", sa.String(300), nullable=False),
        sa.Column("column_key", sa.String(100), nullable=False),
        sa.Column("from_value", sa.Text),
        sa.Column("to_value", sa.Text),
        sa.Column("changed_by", sa.String(150)),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="grid"),
        schema="mapalab",
    )
    op.create_index(
        "idx_grid_cell_history_resource_row",
        "grid_cell_history",
        ["resource", "row_key", "changed_at"],
        schema="mapalab",
    )
    op.create_index(
        "idx_grid_cell_history_changed_at",
        "grid_cell_history",
        ["changed_at"],
        schema="mapalab",
    )
    op.create_index(
        "idx_grid_cell_history_changed_by",
        "grid_cell_history",
        ["changed_by"],
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_index("idx_grid_cell_history_changed_by", table_name="grid_cell_history", schema="mapalab")
    op.drop_index("idx_grid_cell_history_changed_at", table_name="grid_cell_history", schema="mapalab")
    op.drop_index("idx_grid_cell_history_resource_row", table_name="grid_cell_history", schema="mapalab")
    op.drop_table("grid_cell_history", schema="mapalab")
    op.drop_column("layer_stats", "updated_by", schema="mapalab")
    op.drop_column("layer_stats", "updated_at", schema="mapalab")
