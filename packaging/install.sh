#!/usr/bin/env bash
###############################################################################
#  PatchMaster Installer
#  Deploys the full PatchMaster stack from a distribution package.
#  Usage:  sudo ./install.sh [--env /path/to/.env]
###############################################################################
set -euo pipefail

VERSION="2.0.0"
INSTALL_DIR="/opt/patchmaster"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Project root is one level up from packaging/
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE=""
SKIP_DOCKER_CHECK=false

# ── Colors ──
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[x]${NC} $*" >&2; }
banner() {
    echo -e "${BLUE}"
    echo "  =============================================  "
    echo "   PatchMaster v${VERSION} -- Installer          "
    echo "  =============================================  "
    echo -e "${NC}"
}

usage() {
    echo "Usage: sudo $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --env FILE          Path to environment config file (default: .env in package)"
    echo "  --install-dir DIR   Installation directory (default: /opt/patchmaster)"
    echo "  --skip-docker       Skip Docker installation check"
    echo "  -h, --help          Show this help"
    exit 0
}

# ── Parse args ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)          ENV_FILE="$2"; shift 2 ;;
        --install-dir)  INSTALL_DIR="$2"; shift 2 ;;
        --skip-docker)  SKIP_DOCKER_CHECK=true; shift ;;
        -h|--help)      usage ;;
        *)              err "Unknown option: $1"; usage ;;
    esac
done

# ── Root check ──
if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (sudo)."
    exit 1
fi

banner

###############################################################################
# Step 1: Check prerequisites
###############################################################################
log "Step 1/7: Checking prerequisites..."

# Docker
if [[ "$SKIP_DOCKER_CHECK" == "false" ]]; then
    if ! command -v docker &>/dev/null; then
        warn "Docker not found. Attempting to install..."
        if command -v apt-get &>/dev/null; then
            curl -fsSL https://get.docker.com | sh
        elif command -v dnf &>/dev/null; then
            dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            systemctl enable --now docker
        elif command -v yum &>/dev/null; then
            yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            systemctl enable --now docker
        else
            err "Cannot auto-install Docker. Please install Docker manually and re-run."
            exit 1
        fi
    fi

    if ! docker compose version &>/dev/null; then
        err "Docker Compose v2 is required but not found."
        err "Install it: https://docs.docker.com/compose/install/"
        exit 1
    fi

    log "  Docker $(docker --version | awk '{print $3}' | tr -d ',')"
    log "  Docker Compose $(docker compose version --short)"
fi

# Check disk space (need at least 2GB free)
AVAIL_KB=$(df --output=avail "$(dirname "$INSTALL_DIR")" | tail -1 | tr -d ' ')
if [[ $AVAIL_KB -lt 2097152 ]]; then
    warn "Less than 2 GB free disk space. Deployment may fail."
fi

###############################################################################
# Step 2: Create install directory
###############################################################################
log "Step 2/7: Setting up install directory..."

mkdir -p "$INSTALL_DIR"

# Copy package contents — PROJECT_ROOT is the directory containing docker-compose.yml
if [[ -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
    cp -a "$PROJECT_ROOT/"* "$INSTALL_DIR/" 2>/dev/null || true
    # Also copy hidden files (e.g. .env)
    cp -a "$PROJECT_ROOT/".env* "$INSTALL_DIR/" 2>/dev/null || true
    # Fix Windows line endings on all text files
    find "$INSTALL_DIR" -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.py" \
        -o -name "*.sh" -o -name "*.env*" -o -name "*.txt" -o -name "*.json" \
        -o -name "*.js" -o -name "*.css" -o -name "*.html" -o -name "*.conf" \
        -o -name "*.md" -o -name "Dockerfile" \) -exec sed -i 's/\r$//' {} + 2>/dev/null || true
else
    err "Cannot find PatchMaster files (no docker-compose.yml in $PROJECT_ROOT)."
    err "Run this from the extracted package: cd patchmaster-*/ && sudo ./packaging/install.sh"
    exit 1
fi

log "  Installed to: $INSTALL_DIR"

###############################################################################
# Step 3: Configure environment
###############################################################################
log "Step 3/7: Configuring environment..."

cd "$INSTALL_DIR"

# Load env file
if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
    cp "$ENV_FILE" "$INSTALL_DIR/.env"
    log "  Using custom env: $ENV_FILE"
elif [[ -f "$INSTALL_DIR/.env" ]]; then
    log "  Using existing .env"
elif [[ -f "$INSTALL_DIR/packaging/env.example" ]]; then
    cp "$INSTALL_DIR/packaging/env.example" "$INSTALL_DIR/.env"
    log "  Created .env from template"
else
    warn "  No .env file found. Using defaults."
fi

# Source env if exists
if [[ -f "$INSTALL_DIR/.env" ]]; then
    # Fix Windows line endings if present
    sed -i 's/\r$//' "$INSTALL_DIR/.env"
    set -a
    # shellcheck disable=SC1091
    source "$INSTALL_DIR/.env"
    set +a
fi

# Auto-detect server IP if not set
if [[ -z "${SERVER_IP:-}" ]]; then
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [[ -z "$SERVER_IP" ]]; then
        SERVER_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')
    fi
    if [[ -z "$SERVER_IP" ]]; then
        SERVER_IP="127.0.0.1"
    fi
    log "  Auto-detected server IP: $SERVER_IP"
fi

# Apply port configuration to docker-compose.yml
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
GRAFANA_PORT="${GRAFANA_PORT:-3001}"
PROMETHEUS_PORT="${PROMETHEUS_PORT:-9090}"
POSTGRES_USER="${POSTGRES_USER:-patchmaster}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-patchmaster}"
POSTGRES_DB="${POSTGRES_DB:-patchmaster}"
JWT_SECRET="${JWT_SECRET:-change-me-to-a-secure-random-string}"
GF_ADMIN_USER="${GF_ADMIN_USER:-admin}"
GF_ADMIN_PASSWORD="${GF_ADMIN_PASSWORD:-patchmaster}"
PROMETHEUS_RETENTION="${PROMETHEUS_RETENTION:-30d}"

# Generate docker-compose.override.yml with environment-specific settings
cat > "$INSTALL_DIR/docker-compose.override.yml" <<OVERRIDE
services:
  db:
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}

  backend:
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - JWT_SECRET=${JWT_SECRET}

  frontend:
    ports:
      - "${FRONTEND_PORT}:80"

  prometheus:
    ports:
      - "${PROMETHEUS_PORT}:9090"
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=${PROMETHEUS_RETENTION}"

  grafana:
    ports:
      - "${GRAFANA_PORT}:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GF_ADMIN_USER}
      - GF_SECURITY_ADMIN_PASSWORD=${GF_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/var/lib/grafana/dashboards/patchmaster-overview.json
OVERRIDE

log "  Generated docker-compose.override.yml"

###############################################################################
# Step 4: Build and start services
###############################################################################
log "Step 4/7: Building and starting Docker services..."

cd "$INSTALL_DIR"
docker compose build --quiet 2>&1 | tail -5
docker compose up -d

# Wait for DB to be healthy
log "  Waiting for database..."
TRIES=0
until docker compose exec -T db pg_isready -U "$POSTGRES_USER" &>/dev/null || [[ $TRIES -ge 30 ]]; do
    sleep 2
    TRIES=$((TRIES + 1))
done

if [[ $TRIES -ge 30 ]]; then
    warn "  Database health check timed out. Check logs: docker compose logs db"
else
    log "  Database ready."
fi

###############################################################################
# Step 5: Verify services
###############################################################################
log "Step 5/7: Verifying services..."

sleep 5  # Give services a moment to fully start

SERVICES_OK=true
for SVC in db backend frontend prometheus grafana; do
    STATUS=$(docker compose ps --format '{{.Status}}' "$SVC" 2>/dev/null | head -1)
    if echo "$STATUS" | grep -qi "up"; then
        log "  $SVC: running"
    else
        err "  $SVC: $STATUS"
        SERVICES_OK=false
    fi
done

# Test backend health
if curl -sf "http://localhost:${BACKEND_PORT}/api/health" &>/dev/null; then
    log "  Backend API: healthy"
else
    warn "  Backend API: not responding yet (may still be starting)"
fi

###############################################################################
# Step 6: Create systemd service (optional, for auto-start)
###############################################################################
log "Step 6/7: Creating systemd service..."

cat > /etc/systemd/system/patchmaster.service <<SYSTEMD
[Unit]
Description=PatchMaster - Linux Patch Management Platform
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose up -d --build
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
systemctl enable patchmaster.service &>/dev/null

log "  Created patchmaster.service (auto-start on boot)"

###############################################################################
# Step 7: Print summary
###############################################################################
log "Step 7/7: Installation complete!"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  PatchMaster v${VERSION} installed successfully!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Install directory:  $INSTALL_DIR"
echo ""
echo "  Service URLs:"
echo "    Web UI:      http://${SERVER_IP}:${FRONTEND_PORT}"
echo "    Backend API: http://${SERVER_IP}:${BACKEND_PORT}"
echo "    Grafana:     http://${SERVER_IP}:${GRAFANA_PORT}  (${GF_ADMIN_USER}/${GF_ADMIN_PASSWORD})"
echo "    Prometheus:  http://${SERVER_IP}:${PROMETHEUS_PORT}"
echo ""
echo "  First-time setup:"
echo "    1. Open http://${SERVER_IP}:${FRONTEND_PORT} in your browser"
echo "    2. Click 'Register' to create the admin account"
echo "    3. Go to 'Onboarding' page to install agents on hosts"
echo ""
echo "  Agent install command (run on each Linux host):"
echo "    curl -sS http://${SERVER_IP}:${FRONTEND_PORT}/download/install.sh | sudo bash -s -- ${SERVER_IP}"
echo ""
echo "  Management commands:"
echo "    sudo systemctl start patchmaster     # Start"
echo "    sudo systemctl stop patchmaster      # Stop"
echo "    sudo systemctl restart patchmaster   # Restart"
echo "    cd $INSTALL_DIR && docker compose logs -f  # View logs"
echo ""
if [[ "$JWT_SECRET" == "change-me-to-a-secure-random-string" ]]; then
    echo -e "  ${YELLOW}WARNING: You are using the default JWT_SECRET.${NC}"
    echo -e "  ${YELLOW}Edit $INSTALL_DIR/.env and change JWT_SECRET for production!${NC}"
    echo ""
fi
