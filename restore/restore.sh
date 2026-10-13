#!/bin/bash
set -euo pipefail

VERBOSE_FLAG=""
if [ "${DEBUG:-0}" -eq 1 ]; then
    VERBOSE_FLAG="-v"
fi

FILE="$1"
FILEPATH="/restore/$FILE"

if [ -z "$FILE" ]; then
    echo "Uso: $0 <archivo>"
    exit 1
fi

if [ ! -f "$FILEPATH" ]; then
    echo "Error: archivo no encontrado en /restore/$FILE"
    exit 1
fi

export PGPASSWORD="${POSTGRES_PASSWORD:-$(cat "${POSTGRES_PASSWORD_FILE:?POSTGRES_PASSWORD o POSTGRES_PASSWORD_FILE}")}"

echo "Recreando base $POSTGRES_DB..."
psql -U "$POSTGRES_USER" -d postgres -q -v ON_ERROR_STOP=1 <<SQL
UPDATE pg_database SET datallowconn = false WHERE datname = '$POSTGRES_DB';
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
 WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();
SQL
psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\" WITH (FORCE);"
psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
    -c "CREATE DATABASE \"$POSTGRES_DB\";"

HEADER=$(od -A n -N 5 -t c "$FILEPATH" 2>/dev/null | tr -d ' \n')

if echo "$HEADER" | grep -q "PGDMP"; then
    echo "Detectado: custom format"
    set +e
    pg_restore $VERBOSE_FLAG -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl "$FILEPATH"
    RC=$?
    set -e
    if [ "$RC" -gt 1 ]; then
        echo "Error fatal en pg_restore (codigo: $RC)"
        exit "$RC"
    fi
elif echo "$FILE" | grep -qE '\.gz$'; then
    echo "Detectado: sql comprimido"
    gunzip -c "$FILEPATH" | psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
else
    echo "Detectado: sql plano"
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$FILEPATH"
fi

# pg_restore --no-acl no recrea GRANTs, asi que el rol mariachi_layers
# queda sin permisos sobre mapalab.* tras un restore. Re-aplicamos los
# GRANTs del Paso 3b de bootstrap-v14.sh. Idempotente; no-op si el rol o
# el schema no existen (ej. cluster recien iniciado pre-bootstrap).
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=0 <<SQL
DO \$\$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mariachi_layers')
       AND EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'mapalab') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA mapalab TO mariachi_layers';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA mapalab TO mariachi_layers';
        EXECUTE 'GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA mapalab TO mariachi_layers';
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA mapalab GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mariachi_layers', current_user);
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA mapalab GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO mariachi_layers', current_user);
        RAISE NOTICE 'GRANTs sobre mapalab.* re-aplicados a mariachi_layers';
    ELSE
        RAISE NOTICE 'Rol mariachi_layers o schema mapalab no existen; GRANTs omitidos';
    END IF;
END
\$\$;
SQL

if [ -f /scripts/stats_read_grants.sql ]; then
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=0 -f /scripts/stats_read_grants.sql
fi

echo "Restauracion completada: $FILE"
