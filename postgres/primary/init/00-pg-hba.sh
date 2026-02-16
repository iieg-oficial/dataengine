#!/bin/sh
set -e

cat > "$PGDATA/pg_hba.conf" <<EOF
# Local
local   all             all                                     trust
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256

# Docker internal network
host    all             all             172.16.0.0/12           scram-sha-256

# Allowed external hosts
host    all             all             ${ALLOWED_HOST_1}/32    scram-sha-256
host    all             all             ${ALLOWED_HOST_2}/32    scram-sha-256

# Replication
host    replication     ${REPLICATION_USER}    ${ALLOWED_HOST_1}/32    scram-sha-256
host    replication     ${REPLICATION_USER}    ${ALLOWED_HOST_2}/32    scram-sha-256
host    replication     ${REPLICATION_USER}    172.16.0.0/12           scram-sha-256

# Reject everything else
host    all             all             0.0.0.0/0               reject
host    all             all             ::/0                    reject
EOF

echo "pg_hba.conf configured with allowed hosts: ${ALLOWED_HOST_1}, ${ALLOWED_HOST_2}"
