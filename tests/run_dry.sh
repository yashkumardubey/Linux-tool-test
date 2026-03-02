#!/usr/bin/env bash
# Simple test harness: calls local agent endpoints for a dry-run
set -euo pipefail

AGENT_HOST=127.0.0.1

echo "Listing updates from agent..."
curl -sS http://${AGENT_HOST}:8080/updates | jq .

echo "Triggering dry-run upgrade via install_selected (no packages)..."
curl -sS -X POST http://${AGENT_HOST}:8080/install_selected -H 'Content-Type: application/json' -d '{"packages": [], "hold": ["postgresql","pgpool2"]}' | jq .
