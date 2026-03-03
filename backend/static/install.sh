#!/bin/bash
# PatchMaster Agent Installer
# Usage: curl -sS http://<master-ip>:3000/download/install.sh | sudo bash -s -- <master-ip>
set -euo pipefail

MASTER_IP="${1:-}"
if [ -z "$MASTER_IP" ]; then
  echo "ERROR: Master IP required."
  echo "Usage: curl -sS http://<master-ip>:3000/download/install.sh | sudo bash -s -- <master-ip>"
  exit 1
fi

MASTER_URL="http://${MASTER_IP}:3000"
DEB_URL="${MASTER_URL}/download/agent-latest.deb"
TMP_DEB="/tmp/patch-agent.deb"

echo "============================================"
echo "  PatchMaster Agent Installer"
echo "============================================"
echo "Master Server: ${MASTER_IP}"
echo ""

# Check root
if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: This script must be run as root (use sudo)."
  exit 1
fi

# Check OS
if ! command -v dpkg >/dev/null 2>&1; then
  echo "ERROR: This installer requires a Debian/Ubuntu system (dpkg not found)."
  exit 1
fi

# Download agent .deb
echo "[1/6] Downloading agent package..."
if command -v curl >/dev/null 2>&1; then
  curl -fsSL -o "$TMP_DEB" "$DEB_URL"
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP_DEB" "$DEB_URL"
else
  echo "ERROR: Neither curl nor wget found. Install one and retry."
  exit 1
fi
echo "      Downloaded to ${TMP_DEB}"

# Install .deb
echo "[2/6] Installing agent package..."
dpkg -i "$TMP_DEB" || true
apt-get install -f -y >/dev/null 2>&1 || true
echo "      Package installed."

# Install Python dependencies
echo "[3/6] Installing Python dependencies..."
apt-get install -y python3-flask python3-requests python3-psutil python3-prometheus-client 2>/dev/null || true
if command -v pip3 >/dev/null 2>&1; then
  pip3 install --break-system-packages flask prometheus_client psutil requests 2>/dev/null || true
fi
echo "      Dependencies installed."

# Configure master URL
echo "[4/6] Configuring agent to report to ${MASTER_IP}..."
mkdir -p /etc/patch-agent
cat > /etc/patch-agent/env <<EOF
CONTROLLER_URL=http://${MASTER_IP}:8000
EOF
chown -R patchagent:patchagent /etc/patch-agent 2>/dev/null || true

# Update systemd services to use env file
cat > /etc/systemd/system/patch-agent.service <<EOF
[Unit]
Description=PatchMaster Agent - Heartbeat
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
EnvironmentFile=/etc/patch-agent/env
ExecStart=/usr/bin/python3 /opt/patch-agent/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/patch-agent-api.service <<EOF
[Unit]
Description=PatchMaster Agent - API Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
EnvironmentFile=/etc/patch-agent/env
ExecStart=/usr/bin/python3 /opt/patch-agent/agent.py --port 8080 --metrics-port 9100
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Start agent services
echo "[5/6] Starting agent services..."
systemctl daemon-reload
systemctl enable --now patch-agent.service
systemctl enable --now patch-agent-api.service
sleep 3

echo "[6/6] Verifying..."
if systemctl is-active --quiet patch-agent && systemctl is-active --quiet patch-agent-api; then
  echo ""
  echo "============================================"
  echo "  Agent installed and running!"
  echo "  - Heartbeat service: active"
  echo "  - API service (port 8080): active"
  echo "  Host will appear in PatchMaster dashboard"
  echo "  within 60 seconds."
  echo "============================================"
else
  echo ""
  echo "WARNING: One or more services may not have started."
  echo "Check: sudo systemctl status patch-agent"
  echo "Check: sudo systemctl status patch-agent-api"
  echo "Logs:  sudo journalctl -u patch-agent -n 20"
fi

# Cleanup
rm -f "$TMP_DEB"
