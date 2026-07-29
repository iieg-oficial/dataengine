"""lectura de schemas tematicos para mariachi_layers (motor de stats dinamicas)

Revision ID: 0031_stats_read_grants
Revises: 0030_grid_cell_history
Create Date: 2026-07-29

El motor de estadisticas dinamicas de mariachi (preview y refresh on-demand) corre
como mariachi_layers, que solo tenia SELECT en mapalab. Sin lectura de los schemas
tematicos, toda stat sobre datos reales respondia 502 "permission denied for schema".

Solo SELECT: el motor unicamente agrega (count/sum/avg/min/max/latest). Los schemas
se derivan de mapalab.workspaces para que el grant siga al catalogo real de cada
entorno en vez de una lista fija.
"""
from alembic import op


revision = "0031_stats_read_grants"
down_revision = "0030_grid_cell_history"
branch_labels = None
depends_on = None


_GRANT = """
DO $$
DECLARE target_schema text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mariachi_layers') THEN
        RAISE NOTICE 'rol mariachi_layers no existe, se omiten los grants';
        RETURN;
    END IF;

    FOR target_schema IN
        SELECT DISTINCT w.db_schema
        FROM mapalab.workspaces w
        JOIN information_schema.schemata i ON i.schema_name = w.db_schema
        WHERE w.db_schema IS NOT NULL AND w.db_schema <> 'mapalab'
    LOOP
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO mariachi_layers', target_schema);
        EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO mariachi_layers', target_schema);
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON TABLES TO mariachi_layers',
            target_schema
        );
    END LOOP;
END $$;
"""

_REVOKE = """
DO $$
DECLARE target_schema text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mariachi_layers') THEN
        RETURN;
    END IF;

    FOR target_schema IN
        SELECT DISTINCT w.db_schema
        FROM mapalab.workspaces w
        JOIN information_schema.schemata i ON i.schema_name = w.db_schema
        WHERE w.db_schema IS NOT NULL AND w.db_schema <> 'mapalab'
    LOOP
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I REVOKE SELECT ON TABLES FROM mariachi_layers',
            target_schema
        );
        EXECUTE format('REVOKE SELECT ON ALL TABLES IN SCHEMA %I FROM mariachi_layers', target_schema);
        EXECUTE format('REVOKE USAGE ON SCHEMA %I FROM mariachi_layers', target_schema);
    END LOOP;
END $$;
"""


def upgrade() -> None:
    op.execute(_GRANT)


def downgrade() -> None:
    op.execute(_REVOKE)
