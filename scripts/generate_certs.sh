#!/usr/bin/env bash
# Generate a CA, server and client cert for mTLS testing (prototype)
set -euo pipefail

OUTDIR=${1:-certs}
mkdir -p "$OUTDIR"
cd "$OUTDIR"

# CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -subj "/CN=PatchAgent-CA" -out ca.crt

# Create temporary OpenSSL config for SAN entries
cat > server_ext.cnf <<'EOF'
[ v3_req ]
subjectAltName = @alt_names
[ alt_names ]
DNS.1 = patch-agent.local
DNS.2 = agent
DNS.3 = localhost
IP.1  = 127.0.0.1
EOF

# Server
openssl genrsa -out server.key 4096
openssl req -new -key server.key -subj "/CN=patch-agent.local" -out server.csr
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days 365 -sha256 -extfile server_ext.cnf -extensions v3_req

# Client
openssl genrsa -out client.key 4096
openssl req -new -key client.key -subj "/CN=patch-controller" -out client.csr
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out client.crt -days 365 -sha256

# cleanup
rm -f server_ext.cnf

chmod 644 *.crt
chmod 600 *.key

echo "Generated certs in $OUTDIR: ca.crt, server.crt, server.key, client.crt, client.key"

# Example: copy certs to agent host /etc/patch-agent/certs and controller config
