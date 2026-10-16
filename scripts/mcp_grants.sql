-- Reaplica los GRANT del rol mapalab_mcp, el que usa el servidor MCP publico de mapalab.
--
-- Es el mismo bloque de la migracion 0059_rol_mapalab_mcp, extraido para reejecutarlo
-- sin tocar alembic_version: un restore con --no-acl deja al rol sin permisos y el MCP
-- responde "permission denied" en cada tool. restore/restore.sh lo corre al terminar.
--
-- La lista de tablas es explicita a proposito: el MCP es publico y no hereda nada por
-- ALTER DEFAULT PRIVILEGES. Si el MCP empieza a leer una tabla nueva, se agrega aqui y en
-- una migracion.
--
--   docker exec dataengine-primary sh -c '\
--     PGPASSWORD=$(cat "$POSTGRES_PASSWORD_FILE") \
--     psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
--          -f /scripts/mcp_grants.sql'

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mapalab_mcp') THEN
        RAISE NOTICE 'rol mapalab_mcp no existe; GRANTs omitidos';
        RETURN;
    END IF;

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

SELECT
    has_table_privilege('mapalab_mcp', 'mapalab.layers', 'SELECT') AS lee_capas,
    has_table_privilege('mapalab_mcp', 'mapalab.map_shares', 'INSERT') AS crea_compartidos,
    has_table_privilege('mapalab_mcp', 'mapalab.layers', 'UPDATE') AS escribe_capas
WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mapalab_mcp');
