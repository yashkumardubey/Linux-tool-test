#!/usr/bin/env bash
###############################################################################
#  PatchMaster Package Builder
#  Creates a self-contained distributable tarball.
#  Usage:  ./build-package.sh [--output /path/to/output]
###############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="2.0.0"
OUTPUT_DIR="${PROJECT_ROOT}/dist"
PACKAGE_NAME="patchmaster-${VERSION}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[x]${NC} $*" >&2; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)   OUTPUT_DIR="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --output DIR   Output directory for the tarball (default: dist/)"
            echo "  -h, --help     Show this help"
            exit 0
            ;;
        *)  err "Unknown option: $1"; exit 1 ;;
    esac
done

echo -e "${BLUE}"
echo "  =============================================  "
echo "   PatchMaster v${VERSION} -- Package Builder    "
echo "  =============================================  "
echo -e "${NC}"

###############################################################################
# Step 1: Prepare staging area
###############################################################################
log "Preparing staging area..."

STAGING=$(mktemp -d)
STAGE="$STAGING/$PACKAGE_NAME"
mkdir -p "$STAGE"

trap 'rm -rf "$STAGING"' EXIT

###############################################################################
# Step 2: Copy project files
###############################################################################
log "Copying project files..."

# Use rsync to copy only needed files, excluding large/unnecessary dirs
rsync -a --quiet \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='.venv-1' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='dist' \
    --exclude='generate_sops.py' \
    --exclude='generate_prerequisites.py' \
    --exclude='.gitattributes' \
    --exclude='.gitignore' \
    "$PROJECT_ROOT/" "$STAGE/"

# Ensure docs/ folder has the SOP PDFs
mkdir -p "$STAGE/docs"
for pdf in "$PROJECT_ROOT"/SOP_PatchMaster_*.pdf; do
    [[ -f "$pdf" ]] && cp "$pdf" "$STAGE/docs/"
done
# Move PDFs out of root into docs/
rm -f "$STAGE"/SOP_PatchMaster_*.pdf

# Ensure certs dir exists
mkdir -p "$STAGE/certs"

log "  Copied: backend/ agent/ frontend/ monitoring/ packaging/ docs/"

###############################################################################
# Step 4: Copy env.example to root for easy access
###############################################################################
if [[ -f "$STAGE/packaging/env.example" ]]; then
    cp "$STAGE/packaging/env.example" "$STAGE/.env.example"
fi

###############################################################################
# Step 5: Make scripts executable
###############################################################################
log "Setting permissions..."

chmod +x "$STAGE/packaging/install.sh"
chmod +x "$STAGE/packaging/install-bare.sh"
chmod +x "$STAGE/packaging/uninstall.sh"
chmod +x "$STAGE/packaging/uninstall-bare.sh"
chmod +x "$STAGE/packaging/build-package.sh"
chmod +x "$STAGE/agent/build-deb.sh" 2>/dev/null || true

###############################################################################
# Step 6: Create INSTALL.md quick-start guide
###############################################################################
log "Generating quick-start guide..."

cat > "$STAGE/INSTALL.md" <<'GUIDE'
# PatchMaster Installation Guide

Two deployment options are available:
- **Bare-Metal** (recommended for production) -- installs directly on Linux
- **Docker** -- container-based deployment

---

## Option A: Bare-Metal Install (Production)

### Prerequisites
- Linux server: Ubuntu 20.04+, Debian 11+, RHEL 8+, or CentOS Stream 8+
- At least 2 GB RAM, 10 GB disk space
- Root/sudo access
- Internet access (for package downloads)

The installer will automatically install: PostgreSQL, Python 3, Node.js 18,
Nginx, Prometheus, and Grafana.

### Step 1: Extract
```bash
tar xzf patchmaster-*.tar.gz
cd patchmaster-*/
```

### Step 2: Configure (optional)
```bash
cp .env.example .env
nano .env
```

Key settings:
- `JWT_SECRET` -- MUST change for production
- `POSTGRES_PASSWORD` -- database password
- `SERVER_IP` -- auto-detected, override if needed
- Ports: `FRONTEND_PORT` (3000), `BACKEND_PORT` (8000), `GRAFANA_PORT` (3001)

### Step 3: Install
```bash
sudo ./packaging/install-bare.sh
# Or with custom env:
sudo ./packaging/install-bare.sh --env /path/to/.env
# Skip monitoring (Prometheus/Grafana):
sudo ./packaging/install-bare.sh --skip-monitoring
```

### Step 4: Access
- **Web UI**: http://YOUR-IP:3000
- **API Docs**: http://YOUR-IP:8000/docs
- **Grafana**: http://YOUR-IP:3001 (admin/patchmaster)
- **Prometheus**: http://YOUR-IP:9090

### Management
```bash
systemctl {start|stop|restart} patchmaster-backend
systemctl {start|stop|restart} nginx
systemctl {start|stop|restart} prometheus
systemctl {start|stop|restart} grafana-server

# Logs
tail -f /opt/patchmaster/logs/backend.log
journalctl -u patchmaster-backend -f
```

### Uninstall
```bash
sudo ./packaging/uninstall-bare.sh           # Keep data
sudo ./packaging/uninstall-bare.sh --purge   # Remove everything
```

---

## Option B: Docker Install

### Prerequisites
- Docker Engine 20.10+ with Docker Compose v2
- 2 GB RAM, 2 GB disk

### Install
```bash
tar xzf patchmaster-*.tar.gz
cd patchmaster-*/
sudo ./packaging/install.sh
```

### Management
```bash
sudo systemctl {start|stop|restart} patchmaster
cd /opt/patchmaster && docker compose logs -f
```

### Uninstall
```bash
sudo ./packaging/uninstall.sh           # Keep data
sudo ./packaging/uninstall.sh --purge   # Remove everything
```

---

## Installing Agents on Managed Hosts
On each Linux host you want to manage:
```bash
curl -sS http://YOUR-SERVER:3000/download/install.sh | sudo bash -s -- YOUR-SERVER
```

## Documentation
See `docs/` for complete SOPs: User Guide, Developer Guide, Prerequisites.
GUIDE

###############################################################################
# Step 7: Build tarball
###############################################################################
log "Building tarball..."

mkdir -p "$OUTPUT_DIR"
TARBALL="$OUTPUT_DIR/${PACKAGE_NAME}.tar.gz"

tar -czf "$TARBALL" -C "$STAGING" "$PACKAGE_NAME"

SIZE=$(du -sh "$TARBALL" | awk '{print $1}')
SHA256=$(sha256sum "$TARBALL" | awk '{print $1}')

# Write checksum file
echo "$SHA256  ${PACKAGE_NAME}.tar.gz" > "$OUTPUT_DIR/${PACKAGE_NAME}.sha256"

###############################################################################
# Summary
###############################################################################
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Package built successfully!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Package:  $TARBALL"
echo "  Size:     $SIZE"
echo "  SHA-256:  $SHA256"
echo "  Checksum: $OUTPUT_DIR/${PACKAGE_NAME}.sha256"
echo ""
echo "  To deploy on a target server:"
echo "    1. Copy ${PACKAGE_NAME}.tar.gz to the server"
echo "    2. tar xzf ${PACKAGE_NAME}.tar.gz"
echo "    3. cd ${PACKAGE_NAME}"
echo "    4. sudo ./packaging/install.sh"
echo ""
