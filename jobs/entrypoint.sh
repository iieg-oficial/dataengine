#!/bin/sh
set -e

if [ -f /app/alembic/mapalab_card/alembic.ini ]; then
    alembic -c /app/alembic/mapalab_card/alembic.ini upgrade head || true
fi

printenv | grep -E '^(MAPALAB_CARD_|DATAENGINE_)' > /etc/environment

tail -F /var/log/cron.log &

exec "$@"
