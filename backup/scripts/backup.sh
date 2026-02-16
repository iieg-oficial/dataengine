#!/bin/sh
set -e

umask 077

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)
DAY_OF_MONTH=$(date +%d)
BACKUP_DIR="/backups"

if [ "$DAY_OF_MONTH" = "01" ]; then
    PREFIX="monthly"
elif [ "$DAY_OF_WEEK" = "7" ]; then
    PREFIX="weekly"
else
    PREFIX="daily"
fi

FILENAME="${PREFIX}_${POSTGRES_DB}_${TIMESTAMP}.sql.gz"
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

UPLOAD_OK=0
/scripts/upload-ao.sh "$FILEPATH" "$FILENAME" && UPLOAD_OK=1 || UPLOAD_OK=0

/scripts/cleanup.sh "$UPLOAD_OK"
