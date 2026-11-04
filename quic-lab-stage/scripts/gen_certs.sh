#!/usr/bin/env bash
# Generate a self-signed TLS certificate for the local QUIC lab.
# Real deployments should use ACME (certbot) or ACM-issued certs instead.
set -euo pipefail

CERT_DIR="${1:-certs}"
mkdir -p "$CERT_DIR"

openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout "$CERT_DIR/server.key" \
  -out "$CERT_DIR/server.crt" \
  -days 30 \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "generated $CERT_DIR/server.crt and $CERT_DIR/server.key"
