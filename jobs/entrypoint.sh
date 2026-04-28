#!/bin/sh
set -e

printenv | grep -E '^DATAENGINE_' > /etc/environment

tail -F /var/log/cron.log &

python /app/ontoy_server.py &

exec "$@"
