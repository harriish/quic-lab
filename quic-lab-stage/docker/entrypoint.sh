#!/usr/bin/env bash
# Container entrypoint: generate a self-signed cert on first start, then exec CMD.
# Real deployments should mount ACME/ACM-issued certs instead.
set -euo pipefail

CERT_DIR="${QUIC_LAB_CERT_DIR:-/app/certs}"
if [ ! -f "$CERT_DIR/server.crt" ]; then
  mkdir -p "$CERT_DIR"
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -days 30 \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
  echo "generated self-signed cert in $CERT_DIR"
fi

exec "$@"
