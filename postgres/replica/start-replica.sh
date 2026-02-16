#!/bin/sh
set -e

init_replica() {
    echo "Replica: running pg_basebackup from primary..."

    until PGPASSWORD="$REPLICATION_PASSWORD" pg_isready -h postgres-primary -p 5432 -U "$REPLICATION_USER"; do
        echo "Waiting for primary to be ready..."
        sleep 2
    done

    rm -rf "$PGDATA"/*

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
}

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    init_replica
else
    PRIMARY_ID=$(PGPASSWORD="$REPLICATION_PASSWORD" psql -h postgres-primary -U "$REPLICATION_USER" -d postgres -tAc "SELECT system_identifier FROM pg_control_system()" 2>/dev/null || echo "")
    LOCAL_ID=$(pg_controldata "$PGDATA" 2>/dev/null | grep "Database system identifier" | awk '{print $NF}' || echo "")

    if [ -n "$PRIMARY_ID" ] && [ -n "$LOCAL_ID" ] && [ "$PRIMARY_ID" != "$LOCAL_ID" ]; then
        echo "Replica: system identifier mismatch (primary=$PRIMARY_ID, local=$LOCAL_ID). Re-initializing..."
        init_replica
    fi
fi

exec docker-entrypoint.sh postgres -c config_file=/etc/postgresql/postgresql.conf
