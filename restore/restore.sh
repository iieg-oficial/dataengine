#!/bin/bash
set -euo pipefail

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

export PGPASSWORD="${POSTGRES_PASSWORD}"

psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -c "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS postgis_topology;"

HEADER=$(od -A n -N 5 -t c "$FILEPATH" 2>/dev/null | tr -d ' \n')

if echo "$HEADER" | grep -q "PGDMP"; then
    echo "Detectado: custom format"
    set +e
    pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-acl "$FILEPATH"
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

echo "Restauracion completada: $FILE"
