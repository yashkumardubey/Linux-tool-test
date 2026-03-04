#!/usr/bin/env bash
###############################################################################
#  PatchMaster — Release Builder
#  Creates separate distributable packages for Product and Vendor Portal.
#
#  Output:
#    dist/patchmaster-product-VERSION.tar.gz   — Customer deployment package
#    dist/patchmaster-vendor-VERSION.tar.gz    — Internal vendor portal package
#
#  Usage:  ./scripts/build-release.sh
###############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="2.0.0"
OUTPUT_DIR="${PROJECT_ROOT}/dist"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }

echo -e "${BLUE}"
echo "  ╔═══════════════════════════════════════════════╗"
echo "  ║  PatchMaster v${VERSION} — Release Builder         ║"
echo "  ╚═══════════════════════════════════════════════╝"
echo -e "${NC}"

mkdir -p "$OUTPUT_DIR"
STAGING=$(mktemp -d)
trap 'rm -rf "$STAGING"' EXIT

###############################################################################
#  1. Build PRODUCT Package (User End)
###############################################################################
log "Building Product package..."

PROD_DIR="$STAGING/patchmaster-product-${VERSION}"
mkdir -p "$PROD_DIR"

# Copy product components
for dir in agent backend frontend monitoring packaging; do
    if [[ -d "$PROJECT_ROOT/$dir" ]]; then
        rsync -a --quiet \
            --exclude='__pycache__' --exclude='*.pyc' --exclude='node_modules' \
            --exclude='.env' --exclude='*.db' \
            "$PROJECT_ROOT/$dir/" "$PROD_DIR/$dir/"
    fi
done

# Copy root configs
cp "$PROJECT_ROOT/docker-compose.yml"       "$PROD_DIR/"
cp "$PROJECT_ROOT/docker-compose.prod.yml"  "$PROD_DIR/"
cp "$PROJECT_ROOT/.env.production"          "$PROD_DIR/.env.production"
cp "$PROJECT_ROOT/Makefile"                 "$PROD_DIR/"
cp "$PROJECT_ROOT/LICENSE"                  "$PROD_DIR/" 2>/dev/null || true

# Copy docs
mkdir -p "$PROD_DIR/docs"
for pdf in "$PROJECT_ROOT"/SOP_PatchMaster_*.pdf; do
    [[ -f "$pdf" ]] && cp "$pdf" "$PROD_DIR/docs/"
done
for md in "$PROJECT_ROOT"/docs/*.md; do
    [[ -f "$md" ]] && cp "$md" "$PROD_DIR/docs/"
done

# Make scripts executable
find "$PROD_DIR" -name "*.sh" -exec chmod +x {} +

# Create quick-start README
cat > "$PROD_DIR/README.md" <<'EOF'
# PatchMaster v2.0.0 — Product

Enterprise Linux Patch Management Platform.

## Quick Start

### 1. Configure
```bash
cp .env.production .env
nano .env   # Set POSTGRES_PASSWORD, JWT_SECRET, etc.
```

### 2. Deploy (Docker)
```bash
make prod                   # Without monitoring
make prod-monitoring        # With Prometheus + Grafana
```

### 3. Deploy (Bare Metal)
```bash
sudo ./packaging/install-bare.sh --env .env
```

### 4. Access
- Web UI: http://YOUR-IP:3000
- API:    http://YOUR-IP:8000/docs
- Grafana: http://YOUR-IP:3001 (if monitoring enabled)

### Management
```bash
make status     # Service status
make logs       # Follow logs
make health     # Health check
make backup     # Database backup
```

See `docs/` for full documentation.
EOF

# Create tarball
cd "$STAGING"
tar czf "$OUTPUT_DIR/patchmaster-product-${VERSION}.tar.gz" "patchmaster-product-${VERSION}/"
PROD_SHA=$(sha256sum "$OUTPUT_DIR/patchmaster-product-${VERSION}.tar.gz" | cut -d' ' -f1)
echo "$PROD_SHA  patchmaster-product-${VERSION}.tar.gz" > "$OUTPUT_DIR/patchmaster-product-${VERSION}.sha256"

log "  Product package: dist/patchmaster-product-${VERSION}.tar.gz"
log "  SHA256: $PROD_SHA"

###############################################################################
#  2. Build VENDOR Package (Our End)
###############################################################################
log "Building Vendor package..."

VEND_DIR="$STAGING/patchmaster-vendor-${VERSION}"
mkdir -p "$VEND_DIR"

# Copy vendor portal
rsync -a --quiet \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='*.db' \
    --exclude='data/' --exclude='backups/' --exclude='.env' \
    "$PROJECT_ROOT/vendor/" "$VEND_DIR/"

# Create tarball
cd "$STAGING"
tar czf "$OUTPUT_DIR/patchmaster-vendor-${VERSION}.tar.gz" "patchmaster-vendor-${VERSION}/"
VEND_SHA=$(sha256sum "$OUTPUT_DIR/patchmaster-vendor-${VERSION}.tar.gz" | cut -d' ' -f1)
echo "$VEND_SHA  patchmaster-vendor-${VERSION}.tar.gz" > "$OUTPUT_DIR/patchmaster-vendor-${VERSION}.sha256"

log "  Vendor package: dist/patchmaster-vendor-${VERSION}.tar.gz"
log "  SHA256: $VEND_SHA"

###############################################################################
#  Summary
###############################################################################
echo ""
echo -e "${BLUE}  ── Release Artifacts ──${NC}"
echo ""
ls -lh "$OUTPUT_DIR"/patchmaster-*-${VERSION}.* 2>/dev/null | awk '{printf "  %-50s %s\n", $NF, $5}'
echo ""
log "Release build complete."
