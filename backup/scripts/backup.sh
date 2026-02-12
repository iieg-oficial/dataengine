#!/bin/bash
set -e

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

PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h postgres-primary \
    -p 5432 \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --format=custom \
    --compress=9 \
    -f "$FILEPATH"

echo "Backup created: $FILEPATH"

/scripts/upload-ao.sh "$FILEPATH" "$FILENAME"
/scripts/cleanup.sh
