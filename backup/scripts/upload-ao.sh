#!/bin/sh
set -e

FILEPATH="$1"
FILENAME="$2"

if [ -z "$AO_BUCKET" ] || [ -z "$AO_ACCESS_KEY" ]; then
    echo "AO_BUCKET o AO_ACCESS_KEY no definido: el respaldo no puede subirse al acervo" >&2
    exit 1
fi

if [ -z "$BACKUP_AGE_RECIPIENT" ]; then
    echo "BACKUP_AGE_RECIPIENT no definido: no se sube un respaldo sin cifrar" >&2
    exit 1
fi

umask 077
ENCRYPTED="${FILEPATH}.age"
trap 'rm -f "$ENCRYPTED"' EXIT

age -r "$BACKUP_AGE_RECIPIENT" -o "$ENCRYPTED" "$FILEPATH"

export RCLONE_CONFIG_ACERVO_TYPE=s3
export RCLONE_CONFIG_ACERVO_PROVIDER=Other
export RCLONE_CONFIG_ACERVO_ENDPOINT="$AO_ENDPOINT"
export RCLONE_CONFIG_ACERVO_ACCESS_KEY_ID="$AO_ACCESS_KEY"
export RCLONE_CONFIG_ACERVO_SECRET_ACCESS_KEY="$AO_SECRET_KEY"
export RCLONE_CONFIG_ACERVO_FORCE_PATH_STYLE=true

rclone copyto --s3-no-check-bucket "$ENCRYPTED" "acervo:${AO_BUCKET}/${FILENAME}.age"

echo "Uploaded to Acervo: ${AO_BUCKET}/${FILENAME}.age"
