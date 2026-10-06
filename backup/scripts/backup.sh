#!/bin/sh
set -e

umask 077

VERBOSE_FLAG=""
if [ "${DEBUG:-0}" -eq 1 ]; then
    VERBOSE_FLAG="-v"
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

FILENAME="${POSTGRES_DB}_${TIMESTAMP}.sql.gz"
FILEPATH="${BACKUP_DIR}/${FILENAME}"

mkdir -p "$BACKUP_DIR"

echo "postgres-primary:5432:*:${POSTGRES_USER}:$(cat "${POSTGRES_PASSWORD_FILE:?}")" > ~/.pgpass
chmod 600 ~/.pgpass

pg_dump $VERBOSE_FLAG \
    "host=postgres-primary port=5432 user=$POSTGRES_USER dbname=$POSTGRES_DB sslmode=verify-ca sslrootcert=/certs/ca.crt" \
    --format=custom \
    --compress=5 \
    -f "$FILEPATH"

rm -f ~/.pgpass

chmod 600 "$FILEPATH"

if [ -n "${BACKUP_UID}" ] && [ -n "${BACKUP_GID}" ]; then
    chown "${BACKUP_UID}:${BACKUP_GID}" "$FILEPATH"
fi

echo "Backup created: $FILEPATH"

UPLOAD_STATUS=0
/scripts/upload-ao.sh "$FILEPATH" "$FILENAME" || UPLOAD_STATUS=$?

/scripts/cleanup.sh

if [ "$UPLOAD_STATUS" -ne 0 ]; then
    echo "No se subio el respaldo al acervo (codigo $UPLOAD_STATUS): solo existe en este servidor" >&2
    exit "$UPLOAD_STATUS"
fi
