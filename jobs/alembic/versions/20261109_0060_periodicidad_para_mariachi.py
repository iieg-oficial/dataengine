"""lectura de layer_periodicity para mariachi

El motor de estadisticas de mariachi liga `@fecha` a la columna que resolvio la
periodicidad (`public.layer_periodicity.date_column`). El rol `mariachi_layers` no podia
leer esa tabla y, sin el fallback de mariachi 2.154.1, la vista previa, «Recalcular» y la
aprobacion de borradores fallaban para cualquier capa con estadisticas.
`scripts/stats_read_grants.sql` reaplica este GRANT tras un restore.

Revision ID: 0060_periodicidad_para_mariachi
Revises: 0059_rol_mapalab_mcp
Create Date: 2026-11-09
"""
from alembic import op


revision = "0060_periodicidad_para_mariachi"
down_revision = "0059_rol_mapalab_mcp"
branch_labels = None
depends_on = None


_UPGRADE = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mariachi_layers')
       AND to_regclass('public.layer_periodicity') IS NOT NULL THEN
        GRANT SELECT ON public.layer_periodicity TO mariachi_layers;
        RAISE NOTICE 'mariachi_layers ya lee public.layer_periodicity';
    END IF;
END
$$;
"""

_DOWNGRADE = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mariachi_layers')
       AND to_regclass('public.layer_periodicity') IS NOT NULL THEN
        REVOKE SELECT ON public.layer_periodicity FROM mariachi_layers;
    END IF;
END
$$;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
