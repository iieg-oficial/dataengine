#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE ${REPLICATION_USER} WITH REPLICATION LOGIN PASSWORD '${REPLICATION_PASSWORD}';
    SELECT pg_create_physical_replication_slot('replica_slot');
EOSQL

cat >> "$PGDATA/pg_hba.conf" <<EOF
host replication ${REPLICATION_USER} 0.0.0.0/0 scram-sha-256
EOF
