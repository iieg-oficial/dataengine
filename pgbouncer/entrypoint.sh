#!/bin/sh
set -e

umask 077

POSTGRES_PASSWORD=$(cat "${POSTGRES_PASSWORD_FILE:?}")
ADMIN_PASSWORD=$(cat /run/secrets/dataengine_pgbouncer_admin_password)

if [ -z "$ADMIN_PASSWORD" ] || [ "$ADMIN_PASSWORD" = "$POSTGRES_PASSWORD" ]; then
    echo "dataengine_pgbouncer_admin_password vacio o igual al del superusuario" >&2
    exit 1
fi

printf '"%s" "%s"\n' "$POSTGRES_USER" "$POSTGRES_PASSWORD" > /etc/pgbouncer/userlist.txt
printf '"pgbouncer_admin" "%s"\n' "$ADMIN_PASSWORD" >> /etc/pgbouncer/userlist.txt

exec pgbouncer /etc/pgbouncer/pgbouncer.ini
