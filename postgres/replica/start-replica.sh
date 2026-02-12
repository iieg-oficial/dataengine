#!/bin/bash
set -e

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "Replica: running pg_basebackup from primary..."

    until PGPASSWORD="$REPLICATION_PASSWORD" pg_isready -h postgres-primary -p 5432 -U "$REPLICATION_USER"; do
        echo "Waiting for primary to be ready..."
        sleep 2
    done

    PGPASSWORD="$REPLICATION_PASSWORD" pg_basebackup \
        -h postgres-primary \
        -p 5432 \
        -U "$REPLICATION_USER" \
        -D "$PGDATA" \
        -Fp -Xs -P -R \
        -S replica_slot

    cat >> "$PGDATA/postgresql.auto.conf" <<EOF
primary_conninfo = 'host=postgres-primary port=5432 user=${REPLICATION_USER} password=${REPLICATION_PASSWORD}'
primary_slot_name = 'replica_slot'
EOF

    touch "$PGDATA/standby.signal"

    chown -R postgres:postgres "$PGDATA"
    chmod 700 "$PGDATA"
fi

exec docker-entrypoint.sh postgres
