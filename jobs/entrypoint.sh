#!/bin/sh
set -e

CRON_VARS='DATAENGINE_DB_USER DATAENGINE_DB_PASSWORD_FILE DATAENGINE_DB_HOST DATAENGINE_DB_PORT DATAENGINE_DB_NAME DATAENGINE_DB_SSLMODE AO_ENDPOINT MAPALAB_AO_BUCKET MAPALAB_AO_ACCESS_KEY_FILE MAPALAB_AO_SECRET_KEY_FILE GEOSERVER_URL'

: > /etc/environment
for name in $CRON_VARS; do
    value=$(printenv "$name" || true)
    if [ -n "$value" ]; then
        printf '%s=%s\n' "$name" "$value" >> /etc/environment
    fi
done
chmod 0644 /etc/environment

tail -F /var/log/cron.log &

exec "$@"
