"""excluir emojis baneados del catalogo de simbolos

Revision ID: 0008_symbol_catalog_excluir_baneados
Revises: 0007_symbol_catalog
Create Date: 2026-05-13

Limpieza idempotente para ambientes donde la 0007 ya se aplico con la lista
vieja: elimina 'dedo grosero', 'caca' y 'bomba' del catalogo mapalab.symbols.

En ambientes nuevos (volumenes recien creados) la 0007 ya no inserta estos
emojis, asi que esta migracion no encuentra nada que borrar y simplemente
pasa. Por eso es segura de aplicar siempre.
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_symbol_catalog_excluir_baneados"
down_revision = "0007_symbol_catalog"
branch_labels = None
depends_on = None


BANNED_EMOJIS = ("🖕", "💩", "💣")


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM mapalab.symbols "
            "WHERE kind = 'emoji' AND value = ANY(:values)"
        ),
        {"values": list(BANNED_EMOJIS)},
    )


def downgrade() -> None:
    pass
