-- Reaplica los GRANT de lectura que el motor de estadisticas dinamicas necesita.
--
-- Es el mismo bloque de la migracion 0031_stats_read_grants, extraido para poder
-- reejecutarlo sin tocar alembic_version. Hace falta porque un restore de dump sobre
-- una base ya migrada devuelve los privilegios al estado del dump: alembic sigue
-- reportando la revision aplicada y los GRANT ya no estan.
--
-- Sintoma: el preview y el recalculo de estadisticas en mariachi responden 502
-- "permission denied for schema <tema>", mientras el cron de dataengine (gisuser)
-- calcula sin problema.
--
-- Idempotente: correrlo de mas no cambia nada. Va despues de cada restore.
--
-- La password no esta en el entorno del contenedor: vive en el secret que apunta
-- POSTGRES_PASSWORD_FILE, asi que hay que pasarla por PGPASSWORD o psql la pide por
-- consola y el comando falla con "no password supplied".
--
--   docker exec dataengine-primary sh -c '\
--     PGPASSWORD=$(cat "$POSTGRES_PASSWORD_FILE") \
--     psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
--          -f /scripts/stats_read_grants.sql'

\set ON_ERROR_STOP on

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
        RAISE NOTICE 'grants aplicados sobre %', target_schema;
    END LOOP;
END $$;

-- Verificacion: una fila por workspace del catalogo, todas en true.
SELECT w.db_schema AS schema,
       has_schema_privilege('mariachi_layers', w.db_schema, 'USAGE') AS usage_ok
FROM (SELECT DISTINCT db_schema FROM mapalab.workspaces WHERE db_schema <> 'mapalab') w
JOIN information_schema.schemata i ON i.schema_name = w.db_schema
ORDER BY 1;
