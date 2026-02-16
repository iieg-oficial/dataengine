#!/bin/sh
set -e

FILEPATH="$1"
FILENAME="$2"

if [ -z "$AO_BUCKET" ] || [ -z "$AO_ACCESS_KEY" ]; then
    echo "Acervo not configured, skipping upload"
    exit 0
fi

mc alias set acervo "$AO_ENDPOINT" "$AO_ACCESS_KEY" "$AO_SECRET_KEY"

mc cp "$FILEPATH" "acervo/${AO_BUCKET}/${FILENAME}"

echo "Uploaded to Acervo: ${AO_BUCKET}/${FILENAME}"
