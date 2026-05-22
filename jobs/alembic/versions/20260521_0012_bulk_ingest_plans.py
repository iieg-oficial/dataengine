"""bulk ingest plans (preview -> apply de metadata + numeralia desde CSV/XLSX)

Revision ID: 0012_bulk_ingest_plans
Revises: 0011_layer_deleted_at
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0012_bulk_ingest_plans"
down_revision = "0011_layer_deleted_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bulk_ingest_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("dependencia", sa.String(length=100), nullable=False),
        sa.Column("source_filename", sa.String(length=500), nullable=False),
        sa.Column("source_object_key", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            sa.CheckConstraint(
                "status IN ('pending','applied','cancelled','expired')",
                name="ck_bulk_ingest_plans_status",
            ),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("plan_json", postgresql.JSONB, nullable=False),
        sa.Column("column_mapping", postgresql.JSONB, nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        schema="mapalab",
    )
    op.create_index(
        "ix_bulk_ingest_plans_pending",
        "bulk_ingest_plans",
        ["created_by", sa.text("created_at DESC")],
        schema="mapalab",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_bulk_ingest_plans_expiry",
        "bulk_ingest_plans",
        ["expires_at"],
        schema="mapalab",
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bulk_ingest_plans_expiry",
        table_name="bulk_ingest_plans",
        schema="mapalab",
    )
    op.drop_index(
        "ix_bulk_ingest_plans_pending",
        table_name="bulk_ingest_plans",
        schema="mapalab",
    )
    op.drop_table("bulk_ingest_plans", schema="mapalab")
