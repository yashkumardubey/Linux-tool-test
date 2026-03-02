#!/usr/bin/env bash
# Build a simple .deb for the patch agent (prototype)
set -euo pipefail

PKG=patch-agent
VER=${1:-0.1.0}
OUTDIR=./dist
PKGDIR=./debpkg
rm -rf "$PKGDIR" "$OUTDIR"
mkdir -p "$PKGDIR/opt/$PKG"
mkdir -p "$PKGDIR/DEBIAN"

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
Depends: python3, python3-pip
Maintainer: Patch Team <ops@example.com>
Description: Offline patch agent (prototype)
 A small agent to manage offline patching and snapshots.
EOF

# postinst: create user, move systemd unit, reload
cat > "$PKGDIR/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
if ! id -u patchagent >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin patchagent || true
fi
mkdir -p /opt/patch-agent
cp -r /opt/patch-agent/* /opt/patch-agent/ || true
cp /opt/patch-agent/patch-agent.service /etc/systemd/system/patch-agent.service || true
mkdir -p /var/log/patch-agent
chown -R patchagent:patchagent /var/log/patch-agent
systemctl daemon-reload || true
systemctl enable --now patch-agent.service || true
EOF
chmod 0755 "$PKGDIR/DEBIAN/postinst"

mkdir -p "$OUTDIR"

dpkg-deb --build "$PKGDIR" "$OUTDIR/${PKG}_${VER}_amd64.deb"

echo "Built $OUTDIR/${PKG}_${VER}_amd64.deb"
