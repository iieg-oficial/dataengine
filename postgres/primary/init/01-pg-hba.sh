#!/bin/sh
set -e

cat > "$PGDATA/pg_hba.conf" <<EOF
# Local
local   all             all                                     scram-sha-256
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256

# Docker internal network
hostssl all             all             172.16.0.0/12           scram-sha-256

# Allowed external hosts
hostssl all             all             ${ALLOWED_HOST_1}/32    scram-sha-256
hostssl all             all             ${ALLOWED_HOST_2}/32    scram-sha-256

# Replication
hostssl replication     ${REPLICATION_USER}    ${ALLOWED_HOST_1}/32    scram-sha-256
hostssl replication     ${REPLICATION_USER}    ${ALLOWED_HOST_2}/32    scram-sha-256
hostssl replication     ${REPLICATION_USER}    172.16.0.0/12           scram-sha-256

# Reject everything else
host    all             all             0.0.0.0/0               reject
host    all             all             ::/0                    reject
EOF

echo "pg_hba.conf configured with allowed hosts: ${ALLOWED_HOST_1}, ${ALLOWED_HOST_2}"
