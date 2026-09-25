"""rol de solo lectura para el refresh de estadisticas dinamicas

El cron `run_refresh_layer_stats.py` ejecuta los `stats_config` que se capturan en
mariachi. Corria como el superusuario de la base, asi que una configuracion podia leer
cualquier tabla del cluster, `pg_authid` incluida, y dejar el resultado en
`mapalab.layer_stats.values`, que el visor publica.

Desde esta revision cada stat corre bajo `SET LOCAL ROLE mapalab_stats`: un rol sin
login que solo tiene USAGE y SELECT sobre los schemas tematicos declarados en
`mapalab.workspaces`. Los schemas se derivan del catalogo igual que en la 0031, y un
workspace nuevo necesita reaplicar `scripts/stats_read_grants.sql`.

Revision ID: 0050_rol_stats_lectura
Revises: 0049_curvas_nivel_geometry_type
Create Date: 2026-09-24
"""
from alembic import op


revision = "0050_rol_stats_lectura"
down_revision = "0049_curvas_nivel_geometry_type"
branch_labels = None
depends_on = None


_UPGRADE = """
DO $$
DECLARE target_schema text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mapalab_stats') THEN
        CREATE ROLE mapalab_stats NOLOGIN;
    END IF;

    FOR target_schema IN
        SELECT DISTINCT w.db_schema
        FROM mapalab.workspaces w
        JOIN information_schema.schemata i ON i.schema_name = w.db_schema
        WHERE w.db_schema IS NOT NULL AND w.db_schema <> 'mapalab'
    LOOP
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO mapalab_stats', target_schema);
        EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO mapalab_stats', target_schema);
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON TABLES TO mapalab_stats',
            target_schema
        );
    END LOOP;
END $$;
"""

_DOWNGRADE = """
DO $$
DECLARE target_schema text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mapalab_stats') THEN
        RETURN;
    END IF;

    FOR target_schema IN
        SELECT DISTINCT w.db_schema
        FROM mapalab.workspaces w
        JOIN information_schema.schemata i ON i.schema_name = w.db_schema
        WHERE w.db_schema IS NOT NULL AND w.db_schema <> 'mapalab'
    LOOP
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I REVOKE SELECT ON TABLES FROM mapalab_stats',
            target_schema
        );
        EXECUTE format('REVOKE SELECT ON ALL TABLES IN SCHEMA %I FROM mapalab_stats', target_schema);
        EXECUTE format('REVOKE USAGE ON SCHEMA %I FROM mapalab_stats', target_schema);
    END LOOP;

    DROP ROLE mapalab_stats;
END $$;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
