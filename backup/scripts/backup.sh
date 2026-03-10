#!/bin/sh
set -e

umask 077

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

FILENAME="${POSTGRES_DB}_${TIMESTAMP}.sql.gz"
FILEPATH="${BACKUP_DIR}/${FILENAME}"

mkdir -p "$BACKUP_DIR"

echo "postgres-primary:5432:*:${POSTGRES_USER}:${POSTGRES_PASSWORD}" > ~/.pgpass
chmod 600 ~/.pgpass

pg_dump \
    "host=postgres-primary port=5432 user=$POSTGRES_USER dbname=$POSTGRES_DB sslmode=verify-ca sslrootcert=/certs/ca.crt" \
    --format=custom \
    --compress=9 \
    -f "$FILEPATH"

rm -f ~/.pgpass

chmod 600 "$FILEPATH"

echo "Backup created: $FILEPATH"

/scripts/upload-ao.sh "$FILEPATH" "$FILENAME" || true

/scripts/cleanup.sh
