"""map_shares kind: 'compare' -> 'swipe'

Revision ID: 0013_map_shares_kind_swipe
Revises: 0012_bulk_ingest_plans
Create Date: 2026-05-25
"""
from alembic import op


revision = "0013_map_shares_kind_swipe"
down_revision = "0012_bulk_ingest_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE mapalab.map_shares DROP CONSTRAINT IF EXISTS ck_map_shares_kind")
    op.execute("DELETE FROM mapalab.map_shares WHERE kind = 'compare'")
    op.execute(
        "ALTER TABLE mapalab.map_shares "
        "ADD CONSTRAINT ck_map_shares_kind CHECK (kind IN ('single','swipe'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE mapalab.map_shares DROP CONSTRAINT IF EXISTS ck_map_shares_kind")
    op.execute("DELETE FROM mapalab.map_shares WHERE kind = 'swipe'")
    op.execute(
        "ALTER TABLE mapalab.map_shares "
        "ADD CONSTRAINT ck_map_shares_kind CHECK (kind IN ('single','compare'))"
    )
