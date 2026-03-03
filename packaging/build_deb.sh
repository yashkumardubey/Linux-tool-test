#!/usr/bin/env bash
# Build a simple .deb for the patch agent (prototype)
set -euo pipefail
umask 0022

PKG=patch-agent
VER=${1:-0.1.0}
OUTDIR=./dist
PKGDIR=./debpkg
rm -rf "$PKGDIR" "$OUTDIR"
mkdir -p "$PKGDIR/opt/$PKG"
mkdir -p "$PKGDIR/DEBIAN"
chmod 0755 "$PKGDIR/DEBIAN"

# Copy files into package
cp -r ../agent/* "$PKGDIR/opt/$PKG/"
cp -r ../systemd/patch-agent.service "$PKGDIR/opt/$PKG/"

# Control file
cat > "$PKGDIR/DEBIAN/control" <<EOF
Package: $PKG
Version: $VER
Section: base
Priority: optional
Architecture: amd64
Depends: python3, python3-flask, python3-requests, python3-psutil
Recommends: python3-pip, python3-prometheus-client
Maintainer: Patch Team <ops@example.com>
Description: Offline patch agent (enterprise)
 A modular agent to manage patching and reporting.
EOF

# postinst: create user, dirs, two systemd units, reload
cat > "$PKGDIR/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
if ! id -u patchagent >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin patchagent || true
fi
mkdir -p /opt/patch-agent
# Install python dependencies
apt-get install -y python3-flask python3-requests python3-psutil python3-prometheus-client 2>/dev/null || true
if command -v pip3 >/dev/null 2>&1; then
  cd /opt/patch-agent && pip3 install --break-system-packages -r requirements.txt 2>/dev/null || true
fi

# Create required directories
mkdir -p /var/log/patch-agent
mkdir -p /var/lib/patch-agent/snapshots
mkdir -p /var/lib/patch-agent/offline-debs
mkdir -p /etc/patch-agent
chown -R patchagent:patchagent /var/log/patch-agent
chown -R patchagent:patchagent /var/lib/patch-agent
chown -R patchagent:patchagent /etc/patch-agent

# Service 1: heartbeat / registration client
cat > /etc/systemd/system/patch-agent.service <<EOT
[Unit]
Description=Patch Agent - Heartbeat
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /opt/patch-agent/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOT

# Service 2: Flask API (snapshot, rollback, packages, offline, patching)
cat > /etc/systemd/system/patch-agent-api.service <<EOT
[Unit]
Description=Patch Agent - API Server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /opt/patch-agent/agent.py --port 8080 --metrics-port 9100
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOT

systemctl daemon-reload || true
systemctl enable --now patch-agent.service || true
systemctl enable --now patch-agent-api.service || true
EOF
chmod 0755 "$PKGDIR/DEBIAN/postinst"

mkdir -p "$OUTDIR"

dpkg-deb --build "$PKGDIR" "$OUTDIR/${PKG}_${VER}_amd64.deb"

echo "Built $OUTDIR/${PKG}_${VER}_amd64.deb"
