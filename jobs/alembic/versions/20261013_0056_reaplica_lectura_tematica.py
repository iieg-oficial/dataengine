"""reaplica la lectura de los schemas tematicos a mariachi_layers y mapalab_stats

La 0031 dio USAGE y SELECT sobre los schemas de `mapalab.workspaces` a mariachi_layers, pero
un restore con `--no-acl` sobre una base que ya la tenia aplicada deja los GRANT fuera sin
tocar `alembic_version`. En el espejo de rojo la 0050 corrio despues del restore y
mapalab_stats quedo bien, mientras mariachi_layers se quedo solo con mapalab, atributos e
instituto: el editor de estadisticas de mariachi respondia 502 "permission denied for
schema educacion" en cualquier capa tematica.

Mismo bloque que `scripts/stats_read_grants.sql`: solo lectura, derivado del catalogo e
idempotente. El downgrade no revoca porque los GRANT pertenecen a la 0031 y la 0050.

Revision ID: 0056_reaplica_lectura_tematica
Revises: 0055_instituto_elementos
Create Date: 2026-10-13
"""
from alembic import op


revision = "0056_reaplica_lectura_tematica"
down_revision = "0055_instituto_elementos"
branch_labels = None
depends_on = None


_UPGRADE = """
DO $$
DECLARE
    target_schema text;
    target_role text;
BEGIN
    FOREACH target_role IN ARRAY ARRAY['mariachi_layers', 'mapalab_stats'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = target_role) THEN
            RAISE NOTICE 'rol % no existe, se omiten sus grants', target_role;
            CONTINUE;
        END IF;

        FOR target_schema IN
            SELECT DISTINCT w.db_schema
            FROM mapalab.workspaces w
            JOIN information_schema.schemata i ON i.schema_name = w.db_schema
            WHERE w.db_schema IS NOT NULL AND w.db_schema <> 'mapalab'
        LOOP
            EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', target_schema, target_role);
            EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO %I', target_schema, target_role);
            EXECUTE format(
                'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON TABLES TO %I',
                target_schema, target_role
            );
        END LOOP;
    END LOOP;
END $$;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    pass
