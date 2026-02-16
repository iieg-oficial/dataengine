#!/bin/sh
set -e

CERT_DIR="/var/lib/postgresql/certs"

if [ ! -f "$CERT_DIR/server.crt" ] || [ ! -f "$CERT_DIR/server.key" ] || [ ! -f "$CERT_DIR/ca.crt" ]; then
    echo "Generating SSL certificates..."

    mkdir -p "$CERT_DIR"

    openssl req -new -x509 -days 3650 -nodes \
        -keyout "$CERT_DIR/ca.key" \
        -out "$CERT_DIR/ca.crt" \
        -subj "/CN=dataengine-ca"

    openssl req -new -nodes \
        -keyout "$CERT_DIR/server.key" \
        -out "$CERT_DIR/server.csr" \
        -subj "/CN=postgres-primary"

    openssl x509 -req -days 730 \
        -in "$CERT_DIR/server.csr" \
        -CA "$CERT_DIR/ca.crt" \
        -CAkey "$CERT_DIR/ca.key" \
        -CAcreateserial \
        -out "$CERT_DIR/server.crt"

    rm -f "$CERT_DIR/server.csr" "$CERT_DIR/ca.srl"

    chmod 600 "$CERT_DIR/ca.key" "$CERT_DIR/server.key"
    chmod 644 "$CERT_DIR/ca.crt" "$CERT_DIR/server.crt"
    chown -R postgres:postgres "$CERT_DIR"

    echo "SSL certificates generated successfully."
else
    echo "SSL certificates already exist, skipping generation."
fi

exec docker-entrypoint.sh "$@"
