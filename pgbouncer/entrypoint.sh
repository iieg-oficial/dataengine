#!/bin/sh
set -e

echo "\"${POSTGRES_USER}\" \"${POSTGRES_PASSWORD}\"" > /etc/pgbouncer/userlist.txt
echo "\"pgbouncer_admin\" \"${POSTGRES_PASSWORD}\"" >> /etc/pgbouncer/userlist.txt

exec pgbouncer /etc/pgbouncer/pgbouncer.ini
