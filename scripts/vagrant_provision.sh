#!/usr/bin/env bash
set -euxo pipefail

# Run inside the vagrant VM (provisioner). Assumes /vagrant is synced with repo root.
apt-get update
apt-get install -y python3-pip python3-venv openssl

# Create user
if ! id -u patchagent >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin patchagent
fi

# Copy agent files
rm -rf /opt/patch-agent
mkdir -p /opt/patch-agent
cp -r /vagrant/agent/* /opt/patch-agent/
chown -R patchagent:patchagent /opt/patch-agent

# Install deps
python3 -m pip install --upgrade pip
pip3 install -r /opt/patch-agent/requirements.txt

# Generate certs inside VM (for demo only)
mkdir -p /etc/patch-agent/certs
/vagrant/scripts/generate_certs.sh /vagrant/certs
cp /vagrant/certs/server.crt /etc/patch-agent/certs/
cp /vagrant/certs/server.key /etc/patch-agent/certs/
cp /vagrant/certs/ca.crt /etc/patch-agent/certs/
chown -R root:root /etc/patch-agent/certs
chmod 640 /etc/patch-agent/certs/*

# Install systemd unit
cp /vagrant/systemd/patch-agent.service /etc/systemd/system/patch-agent.service
systemctl daemon-reload
systemctl enable --now patch-agent.service || true

# Wait for service
sleep 3

# Show status
systemctl status patch-agent --no-pager || true
