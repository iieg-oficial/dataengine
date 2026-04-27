"""layer icon_url (solo aplica a temas)

Revision ID: 0006_layer_icon_url
Revises: 0005_map_shares
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_layer_icon_url"
down_revision = "0005_map_shares"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "layers",
        sa.Column("icon_url", sa.Text(), nullable=True),
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_column("layers", "icon_url", schema="mapalab")
