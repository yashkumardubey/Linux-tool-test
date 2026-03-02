#!/usr/bin/env bash
# Generate certs, build docker images and run docker-compose for an end-to-end automated demo.
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

CERT_DIR=./certs
# always regenerate to pick up any SAN or config changes
rm -rf "$CERT_DIR"
echo "Generating certs in $CERT_DIR"
./scripts/generate_certs.sh certs

echo "Updating controller config to use client certs"
# ensure controller config exists and points to certs
if [ -f controller/config.yml ]; then
  if command -v python3 >/dev/null; then
    python3 - <<PY
import yaml
p='controller/config.yml'
with open(p,'r') as f:
    cfg=yaml.safe_load(f) or {}
cfg['client_cert']='./certs/client.crt'
cfg['client_key']='./certs/client.key'
cfg['ca_cert']='./certs/ca.crt'
with open(p,'w') as f:
    yaml.safe_dump(cfg,f)
print('wrote',p)
PY
  else
    # Fallback: manual sed/cat update
    cat > controller/config.yml <<EOF
agent_token: "REPLACE_WITH_SECRET_TOKEN"
client_cert: "./certs/client.crt"
client_key: "./certs/client.key"
ca_cert: "./certs/ca.crt"
EOF
    echo "Wrote controller/config.yml (python3 not available; used fallback)"
  fi
fi

echo "Building docker images and starting services"
docker-compose build --pull

docker-compose up -d

echo "Waiting for services to be healthy..."
# wait for controller
for i in {1..30}; do
  if curl -sS http://localhost:5000/ >/dev/null 2>&1; then
    echo "controller up"
    break
  fi
  sleep 2
done

# Run integration demo inside controller container to use proxied requests
echo "Running integration demo via controller proxy"
# call list updates against agent via controller proxy
curl -sS -X POST http://localhost:5000/api/proxy/updates -H 'Content-Type: application/json' -d '{"host":"agent"}' || true

echo "Triggering a dry-run install_selected via controller proxy"
curl -sS -X POST http://localhost:5000/api/proxy/install_selected -H 'Content-Type: application/json' -d '{"host":"agent","body":{"packages":[],"hold":["postgresql","pgpool2"]}}' || true

echo "Demo started. Access controller UI at http://localhost:5000, Prometheus at http://localhost:9090, Grafana at http://localhost:3000"
