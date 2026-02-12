#!/bin/bash
set -e

BACKUP_DIR="/backups"

find "$BACKUP_DIR" -name "daily_*" -mtime +7 -delete
find "$BACKUP_DIR" -name "weekly_*" -mtime +28 -delete
find "$BACKUP_DIR" -name "monthly_*" -mtime +90 -delete

echo "Cleanup completed at $(date)"
