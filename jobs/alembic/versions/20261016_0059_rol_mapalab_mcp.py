"""rol propio para el servidor MCP publico de mapalab

El MCP se conectaba con el mismo usuario que el backend, que en el espejo es
superusuario. Es un servicio publico sin autenticacion: una inyeccion en cualquier
codigo que reutiliza le habria dado el cluster entero.

Desde esta revision el MCP entra como `mapalab_mcp`: lectura de las tablas del catalogo
que usa, escritura solo en `map_shares` y en `layer_tree_cache`, y sin acceso a los
schemas tematicos ni a las tablas de usuarios. Nace sin LOGIN: la password se asigna en
cada entorno con `ALTER ROLE mapalab_mcp LOGIN PASSWORD ...` y va al secret
`mcp_db_password` de mapalab. `scripts/mcp_grants.sql` reaplica los GRANT tras un restore.

Revision ID: 0059_rol_mapalab_mcp
Revises: 0058_columna_de_fecha
Create Date: 2026-10-16
"""
from alembic import op


revision = "0059_rol_mapalab_mcp"
down_revision = "0058_columna_de_fecha"
branch_labels = None
depends_on = None


_UPGRADE = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mapalab_mcp') THEN
        CREATE ROLE mapalab_mcp NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
    ALTER ROLE mapalab_mcp SET statement_timeout = '20s';

    GRANT USAGE ON SCHEMA mapalab TO mapalab_mcp;
    GRANT SELECT ON
        mapalab.layers, mapalab.workspaces, mapalab.layer_aliases, mapalab.initial_layer_order,
        mapalab.layer_metadata, mapalab.layer_stats, mapalab.municipios
    TO mapalab_mcp;
    GRANT SELECT, INSERT, UPDATE ON mapalab.layer_tree_cache, mapalab.map_shares TO mapalab_mcp;

    IF to_regclass('atributos.columnas') IS NOT NULL THEN
        GRANT USAGE ON SCHEMA atributos TO mapalab_mcp;
        GRANT SELECT ON atributos.columnas TO mapalab_mcp;
    END IF;

    IF to_regclass('public.layer_periodicity') IS NOT NULL THEN
        GRANT SELECT ON public.layer_periodicity TO mapalab_mcp;
    END IF;

    RAISE NOTICE 'GRANTs de mapalab_mcp aplicados';
END $$;
"""

_DOWNGRADE = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mapalab_mcp') THEN
        RETURN;
    END IF;
    REVOKE ALL ON ALL TABLES IN SCHEMA mapalab FROM mapalab_mcp;
    REVOKE USAGE ON SCHEMA mapalab FROM mapalab_mcp;
    IF to_regclass('atributos.columnas') IS NOT NULL THEN
        REVOKE ALL ON atributos.columnas FROM mapalab_mcp;
        REVOKE USAGE ON SCHEMA atributos FROM mapalab_mcp;
    END IF;
    IF to_regclass('public.layer_periodicity') IS NOT NULL THEN
        REVOKE ALL ON public.layer_periodicity FROM mapalab_mcp;
    END IF;
    DROP ROLE mapalab_mcp;
END $$;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
