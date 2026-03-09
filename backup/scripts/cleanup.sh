#!/bin/sh
set -e

BACKUP_DIR="/backups"

find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Cleanup completed at $(date)"
