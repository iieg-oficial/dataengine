#!/bin/sh
set -e

CERT_DIR="/var/lib/postgresql/certs"

if [ ! -f "$CERT_DIR/server.crt" ] || [ ! -f "$CERT_DIR/server.key" ] || [ ! -f "$CERT_DIR/ca.crt" ]; then
    echo "ERROR: SSL certificates not found in $CERT_DIR"
    echo "Run 'make certs' on the host before starting the services."
    exit 1
fi

chown postgres:postgres "$CERT_DIR"/server.key "$CERT_DIR"/server.crt "$CERT_DIR"/ca.crt
chmod 600 "$CERT_DIR/server.key"

exec docker-entrypoint.sh "$@"
