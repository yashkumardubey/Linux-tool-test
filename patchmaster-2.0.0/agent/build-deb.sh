#!/bin/bash
# Build a fully self-contained .deb package for PatchMaster Agent
# All Python dependencies are bundled in a virtualenv — NO internet needed on target.
#
# Usage: bash build-deb.sh [output-path]
#   Default output: ../backend/static/agent-latest.deb
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION="1.0.0"
PKG_NAME="patch-agent"
INSTALL_DIR="/opt/patch-agent"
OUTPUT="${1:-${SCRIPT_DIR}/../backend/static/agent-latest.deb}"

BUILD_ROOT="$(mktemp -d)"
trap 'rm -rf "$BUILD_ROOT"' EXIT

echo "=== Building ${PKG_NAME} ${VERSION} ==="
echo "    Build root: ${BUILD_ROOT}"

# --- 1. Create directory structure ---
mkdir -p "${BUILD_ROOT}${INSTALL_DIR}"
mkdir -p "${BUILD_ROOT}/DEBIAN"
mkdir -p "${BUILD_ROOT}/etc/patch-agent"

# --- 2. Copy agent source files ---
cp "${SCRIPT_DIR}/main.py"         "${BUILD_ROOT}${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/agent.py"        "${BUILD_ROOT}${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/requirements.txt" "${BUILD_ROOT}${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/__init__.py"     "${BUILD_ROOT}${INSTALL_DIR}/" 2>/dev/null || true

# --- 3. Create bundled virtualenv with all dependencies ---
echo "    Creating virtualenv with bundled dependencies..."
python3 -m venv "${BUILD_ROOT}${INSTALL_DIR}/venv"
"${BUILD_ROOT}${INSTALL_DIR}/venv/bin/pip" install --upgrade pip setuptools wheel -q
"${BUILD_ROOT}${INSTALL_DIR}/venv/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt" -q
echo "    Dependencies installed into venv."

# Remove pip/setuptools cache to reduce size
rm -rf "${BUILD_ROOT}${INSTALL_DIR}/venv/share" 2>/dev/null || true
find "${BUILD_ROOT}${INSTALL_DIR}/venv" -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_ROOT}${INSTALL_DIR}/venv" -name '*.pyc' -delete 2>/dev/null || true

# --- 4. Create wrapper scripts that use the bundled venv ---
cat > "${BUILD_ROOT}${INSTALL_DIR}/run-heartbeat.sh" <<'WRAPPER'
#!/bin/bash
exec /opt/patch-agent/venv/bin/python3 /opt/patch-agent/main.py "$@"
WRAPPER
chmod +x "${BUILD_ROOT}${INSTALL_DIR}/run-heartbeat.sh"

cat > "${BUILD_ROOT}${INSTALL_DIR}/run-api.sh" <<'WRAPPER'
#!/bin/bash
exec /opt/patch-agent/venv/bin/python3 /opt/patch-agent/agent.py --port 8080 --metrics-port 9100 "$@"
WRAPPER
chmod +x "${BUILD_ROOT}${INSTALL_DIR}/run-api.sh"

# --- 5. DEBIAN/control — minimal deps (just python3 for the venv) ---
cat > "${BUILD_ROOT}/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: admin
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.8)
Maintainer: PatchMaster Team <ops@patchmaster.local>
Description: PatchMaster Agent (self-contained)
 Fully offline patch management agent with bundled Python virtualenv.
 No internet required on target hosts.
EOF

# --- 6. DEBIAN/postinst — create user, dirs, fix venv paths ---
cat > "${BUILD_ROOT}/DEBIAN/postinst" <<'POSTINST'
#!/bin/bash
set -e

# Create service user if not exists
if ! id -u patchagent >/dev/null 2>&1; then
    useradd -r -s /usr/sbin/nologin -d /opt/patch-agent patchagent 2>/dev/null || true
fi

# Create runtime directories
mkdir -p /var/log/patch-agent
mkdir -p /var/lib/patch-agent/snapshots
mkdir -p /var/lib/patch-agent/offline-debs
mkdir -p /etc/patch-agent

# Fix virtualenv paths (they contain the build host path; rewrite to target)
VENV_DIR="/opt/patch-agent/venv"
if [ -f "${VENV_DIR}/bin/activate" ]; then
    sed -i "s|VIRTUAL_ENV=.*|VIRTUAL_ENV=\"${VENV_DIR}\"|g" "${VENV_DIR}/bin/activate" 2>/dev/null || true
fi
# Fix shebang lines in venv/bin scripts
find "${VENV_DIR}/bin" -type f -exec grep -l "^#!.*python" {} \; 2>/dev/null | while read f; do
    sed -i "1s|^#!.*python.*|#!${VENV_DIR}/bin/python3|" "$f" 2>/dev/null || true
done

echo "PatchMaster Agent installed to /opt/patch-agent"
echo "Use install.sh or configure manually:"
echo "  echo 'CONTROLLER_URL=http://<master>:8000' > /etc/patch-agent/env"
POSTINST
chmod 755 "${BUILD_ROOT}/DEBIAN/postinst"

# --- 7. DEBIAN/prerm — stop services on uninstall ---
cat > "${BUILD_ROOT}/DEBIAN/prerm" <<'PRERM'
#!/bin/bash
set -e
systemctl stop patch-agent.service 2>/dev/null || true
systemctl stop patch-agent-api.service 2>/dev/null || true
systemctl disable patch-agent.service 2>/dev/null || true
systemctl disable patch-agent-api.service 2>/dev/null || true
PRERM
chmod 755 "${BUILD_ROOT}/DEBIAN/prerm"

# --- 8. Build .deb ---
echo "    Building .deb package..."
dpkg-deb --build "$BUILD_ROOT" "$OUTPUT"

SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo ""
echo "=== Build complete ==="
echo "    Package: ${OUTPUT}"
echo "    Size:    ${SIZE}"
echo "    Install: dpkg -i ${OUTPUT}"
echo ""
echo "    This package is fully self-contained."
echo "    No internet required on target hosts."
