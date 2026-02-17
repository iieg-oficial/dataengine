#!/bin/sh
set -e

HOST_1=$(echo "$ALLOWED_HOST_1" | awk '{print $1}')
HOST_2=$(echo "$ALLOWED_HOST_2" | awk '{print $1}')

echo "Configuring pg_hba.conf with hosts: '$HOST_1', '$HOST_2'"

cat > "$PGDATA/pg_hba.conf" <<EOF
local   all             all                                     scram-sha-256
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256

hostssl all             all             172.16.0.0/12           scram-sha-256

hostssl all             all             ${HOST_1}/32    scram-sha-256
hostssl all             all             ${HOST_2}/32    scram-sha-256

hostssl replication     ${REPLICATION_USER}    ${HOST_1}/32    scram-sha-256
hostssl replication     ${REPLICATION_USER}    ${HOST_2}/32    scram-sha-256
hostssl replication     ${REPLICATION_USER}    172.16.0.0/12           scram-sha-256

host    all             all             0.0.0.0/0               reject
host    all             all             ::/0                    reject
EOF

echo "pg_hba.conf configured successfully."
