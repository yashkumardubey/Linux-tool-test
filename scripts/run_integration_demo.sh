#!/usr/bin/env bash
set -euo pipefail
# Placeholder: run integration demo steps against the Vagrant VM
# Example: wait for agent to be up and run tests
AGENT_HOST=127.0.0.1
for i in {1..30}; do
  if curl -sS https://$AGENT_HOST:8080/health --insecure >/dev/null 2>&1; then
    echo "Agent is up"
    break
  fi
  sleep 2
done

# Run dry-run
curl -sSk -X POST https://$AGENT_HOST:8080/install_selected -H 'Content-Type: application/json' -d '{"packages": [], "hold": ["postgresql","pgpool2"]}' | jq . || true

echo "Integration demo finished"
