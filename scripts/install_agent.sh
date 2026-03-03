#!/bin/bash
# Bootstrap script: download and install agent, register with controller
set -e
CONTROLLER_URL=${1:-http://controller.example.com:8000}
AGENT_DEB=$(curl -s "$CONTROLLER_URL/api/downloads" | grep -o 'http[^"]*\.deb' | head -n1)
echo "Downloading agent: $AGENT_DEB"
curl -O "$AGENT_DEB"
sudo dpkg -i $(basename "$AGENT_DEB")
# Registration logic would go here
