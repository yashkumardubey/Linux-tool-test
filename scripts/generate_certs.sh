#!/usr/bin/env bash
# Generate a CA, server and client cert for mTLS testing (prototype)
set -euo pipefail

OUTDIR=${1:-certs}
mkdir -p "$OUTDIR"
cd "$OUTDIR"

# CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -subj "/CN=PatchAgent-CA" -out ca.crt

# Server
openssl genrsa -out server.key 4096
openssl req -new -key server.key -subj "/CN=patch-agent.local" -out server.csr
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365 -sha256

# Client
openssl genrsa -out client.key 4096
openssl req -new -key client.key -subj "/CN=patch-controller" -out client.csr
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 365 -sha256

chmod 644 *.crt
chmod 600 *.key

echo "Generated certs in $OUTDIR: ca.crt, server.crt, server.key, client.crt, client.key"

# Example: copy certs to agent host /etc/patch-agent/certs and controller config
