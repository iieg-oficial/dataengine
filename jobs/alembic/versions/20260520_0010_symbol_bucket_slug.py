"""bucket_slug en mapalab.symbols + svg como archivo (no inline)

Revision ID: 0010_symbol_bucket_slug
Revises: 0009_layer_notice
Create Date: 2026-05-20

Agrega columna `bucket_slug` para que cada simbolo declare en que bucket de
Acervo vive su archivo. Default 'mapalab' para retrocompatibilidad (todos los
emoji-png e image actuales viven en `mapalab/simbologia/`).

Tambien limpia entradas legacy con kind='svg' que se almacenaban como XML
inline en `value` — esa modalidad nunca rendereaba en GeoServer (SLD inline
no soportado por _apply_sld) y el SymbolPicker ya las deshabilitaba. A partir
de esta migracion, kind='svg' significa archivo SVG subido al bucket `iieg`
bajo el prefijo `leyendas/`.
"""
from alembic import op
import sqlalchemy as sa


revision = "0010_symbol_bucket_slug"
down_revision = "0009_layer_notice"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "symbols",
        sa.Column(
            "bucket_slug",
            sa.String(length=50),
            nullable=False,
            server_default="mapalab",
        ),
        schema="mapalab",
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM mapalab.symbols "
            "WHERE kind = 'svg' AND image_object_key IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("symbols", "bucket_slug", schema="mapalab")
