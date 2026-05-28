#!/bin/sh
set -e

printenv | grep -E '^(DATAENGINE_|AO_|MAPALAB_AO_)' > /etc/environment

tail -F /var/log/cron.log &

python /app/ontoy_server.py &

exec "$@"
