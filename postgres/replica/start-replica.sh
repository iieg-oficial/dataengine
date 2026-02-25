#!/bin/sh
set -e

SSL_OPTS="sslmode=verify-ca sslrootcert=/var/lib/postgresql/certs/ca.crt"

PGPASSFILE="/var/lib/postgresql/.pgpass"
export PGPASSFILE

setup_pgpass() {
    echo "postgres-primary:5432:*:${REPLICATION_USER}:${REPLICATION_PASSWORD}" > "$PGPASSFILE"
    chmod 0600 "$PGPASSFILE"
    chown postgres:postgres "$PGPASSFILE"
}

cleanup_pgpass() {
    :
}

init_replica() {
    echo "Replica: running pg_basebackup from primary..."

    setup_pgpass

    until pg_isready -h postgres-primary -p 5432 -U "$REPLICATION_USER" -d postgres; do
        echo "Waiting for primary to be ready..."
        sleep 2
    done

    rm -rf "$PGDATA"/*

    pg_basebackup \
        -h postgres-primary \
        -p 5432 \
        -U "$REPLICATION_USER" \
        -D "$PGDATA" \
        -Fp -Xs -P -R \
        -S replica_slot \
        -d "host=postgres-primary port=5432 user=$REPLICATION_USER $SSL_OPTS"

    touch "$PGDATA/standby.signal"

    chown -R postgres:postgres "$PGDATA"
    chmod 700 "$PGDATA"

    cleanup_pgpass
}

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    init_replica
else
    setup_pgpass
    PRIMARY_ID=$(psql "host=postgres-primary user=$REPLICATION_USER dbname=postgres $SSL_OPTS" -tAc "SELECT system_identifier FROM pg_control_system()" 2>/dev/null || echo "")
    cleanup_pgpass
    LOCAL_ID=$(pg_controldata "$PGDATA" 2>/dev/null | grep "Database system identifier" | awk '{print $NF}' || echo "")

    if [ -n "$PRIMARY_ID" ] && [ -n "$LOCAL_ID" ] && [ "$PRIMARY_ID" != "$LOCAL_ID" ]; then
        echo "Replica: system identifier mismatch (primary=$PRIMARY_ID, local=$LOCAL_ID). Re-initializing..."
        init_replica
    fi
fi

exec docker-entrypoint.sh postgres -c config_file=/etc/postgresql/postgresql.conf
