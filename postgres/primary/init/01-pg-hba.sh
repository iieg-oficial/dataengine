#!/bin/sh
set -e

echo "Configuring pg_hba.conf dynamically for ALLOWED_HOSTS: '$ALLOWED_HOSTS'"

cat > "$PGDATA/pg_hba.conf" <<INNER_EOF
local   all             all                                     scram-sha-256
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
host    all             all             172.16.0.0/12           scram-sha-256
INNER_EOF

if [ -n "$ALLOWED_HOSTS" ]; then
    for HOST in $ALLOWED_HOSTS; do
        echo "hostssl all             all             ${HOST}    scram-sha-256" >> "$PGDATA/pg_hba.conf"
    done
fi

cat >> "$PGDATA/pg_hba.conf" <<INNER_EOF

host    all             all             0.0.0.0/0               reject
host    all             all             ::/0                    reject
INNER_EOF

echo "pg_hba.conf configured successfully."