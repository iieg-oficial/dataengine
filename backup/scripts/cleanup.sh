#!/bin/sh
set -e

UPLOAD_OK="${1:-0}"

if [ "$UPLOAD_OK" != "1" ]; then
    echo "Cleanup skipped: upload was not successful"
    exit 0
fi

BACKUP_DIR="/backups"

find "$BACKUP_DIR" -name "daily_*" -mtime +7 -delete
find "$BACKUP_DIR" -name "weekly_*" -mtime +28 -delete
find "$BACKUP_DIR" -name "monthly_*" -mtime +90 -delete

echo "Cleanup completed at $(date)"
