#!/usr/bin/env bash
###############################################################################
#  PatchMaster — Bare-Metal Installer
#  Installs PatchMaster directly on a Linux server (no Docker required).
#
#  Supports: Ubuntu 20.04+, Debian 11+, RHEL 8+/CentOS Stream 8+
#  Usage:    sudo ./install-bare.sh [--env /path/to/.env]
###############################################################################
set -euo pipefail

VERSION="2.0.0"
INSTALL_DIR="/opt/patchmaster"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE=""
SKIP_MONITORING=false
DISTRO=""
PKG_MGR=""

# Unprivileged service user
SVC_USER="patchmaster"
SVC_GROUP="patchmaster"

# ── Colors ──
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[x]${NC} $*" >&2; }
banner() {
    echo -e "${BLUE}"
    echo "  ╔═══════════════════════════════════════════════╗"
    echo "  ║  PatchMaster v${VERSION}  —  Bare-Metal Installer  ║"
    echo "  ╚═══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

usage() {
    echo "Usage: sudo $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --env FILE           Path to environment config file"
    echo "  --install-dir DIR    Installation directory (default: /opt/patchmaster)"
    echo "  --skip-monitoring    Skip Prometheus & Grafana installation"
    echo "  -h, --help           Show this help"
    exit 0
}

# ── Parse args ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)             ENV_FILE="$2"; shift 2 ;;
        --install-dir)     INSTALL_DIR="$2"; shift 2 ;;
        --skip-monitoring) SKIP_MONITORING=true; shift ;;
        -h|--help)         usage ;;
        *)                 err "Unknown option: $1"; usage ;;
    esac
done

# ── Root check ──
if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (sudo)."
    exit 1
fi

banner

###############################################################################
# Helper: Detect distro
###############################################################################
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        # shellcheck disable=SC1091
        source /etc/os-release
        case "$ID" in
            ubuntu|debian|linuxmint|pop) DISTRO="debian"; PKG_MGR="apt" ;;
            rhel|centos|rocky|alma|fedora|ol) DISTRO="rhel"; PKG_MGR="dnf" ;;
            *)
                if command -v apt-get &>/dev/null; then
                    DISTRO="debian"; PKG_MGR="apt"
                elif command -v dnf &>/dev/null; then
                    DISTRO="rhel"; PKG_MGR="dnf"
                elif command -v yum &>/dev/null; then
                    DISTRO="rhel"; PKG_MGR="yum"
                else
                    err "Unsupported distribution: $ID"
                    exit 1
                fi
                ;;
        esac
    else
        err "Cannot detect distribution (missing /etc/os-release)."
        exit 1
    fi
    log "  Detected: $ID ($DISTRO family), package manager: $PKG_MGR"
}

###############################################################################
# Step 1: Check prerequisites & detect OS
###############################################################################
log "Step 1/9: Detecting operating system..."
detect_distro

###############################################################################
# Step 2: Install system packages
###############################################################################
log "Step 2/9: Installing system packages..."

if [[ "$DISTRO" == "debian" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq \
        python3 python3-venv python3-pip python3-dev \
        postgresql postgresql-contrib libpq-dev \
        nginx curl gcc make \
        > /dev/null 2>&1

    # Node.js 18 LTS for building React frontend
    if ! command -v node &>/dev/null || [[ $(node -v | tr -d 'v' | cut -d. -f1) -lt 18 ]]; then
        log "  Installing Node.js 18..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash - > /dev/null 2>&1
        apt-get install -y -qq nodejs > /dev/null 2>&1
    fi

elif [[ "$DISTRO" == "rhel" ]]; then
    $PKG_MGR install -y -q \
        python3 python3-devel python3-pip \
        postgresql-server postgresql-contrib libpq-devel \
        nginx curl gcc make \
        > /dev/null 2>&1

    # Node.js 18
    if ! command -v node &>/dev/null || [[ $(node -v | tr -d 'v' | cut -d. -f1) -lt 18 ]]; then
        log "  Installing Node.js 18..."
        curl -fsSL https://rpm.nodesource.com/setup_18.x | bash - > /dev/null 2>&1
        $PKG_MGR install -y -q nodejs > /dev/null 2>&1
    fi

    # Initialize PostgreSQL on RHEL if needed
    if [[ ! -f /var/lib/pgsql/data/PG_VERSION ]]; then
        postgresql-setup --initdb 2>/dev/null || /usr/bin/postgresql-setup initdb 2>/dev/null || true
    fi
fi

log "  Python $(python3 --version | awk '{print $2}')"
log "  Node $(node --version)"
log "  PostgreSQL $(psql --version | awk '{print $3}')"
log "  Nginx $(nginx -v 2>&1 | awk -F/ '{print $2}')"

###############################################################################
# Step 3: Create service user & install directory
###############################################################################
log "Step 3/9: Setting up user and directories..."

# Create system user if not exists
if ! id "$SVC_USER" &>/dev/null; then
    useradd --system --shell /usr/sbin/nologin --home-dir "$INSTALL_DIR" "$SVC_USER"
    log "  Created system user: $SVC_USER"
fi

# Create directories
mkdir -p "$INSTALL_DIR"/{backend,frontend,agent,monitoring,certs,logs}

# Copy application files
if [[ -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
    cp -a "$PROJECT_ROOT/backend/"* "$INSTALL_DIR/backend/"
    cp -a "$PROJECT_ROOT/frontend/" "$INSTALL_DIR/frontend/"
    cp -a "$PROJECT_ROOT/agent/" "$INSTALL_DIR/agent/"
    cp -a "$PROJECT_ROOT/monitoring/" "$INSTALL_DIR/monitoring/" 2>/dev/null || true
    cp -a "$PROJECT_ROOT/packaging/" "$INSTALL_DIR/packaging/" 2>/dev/null || true
    cp "$PROJECT_ROOT/README.md" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$PROJECT_ROOT/LICENSE" "$INSTALL_DIR/" 2>/dev/null || true
else
    err "Cannot find PatchMaster source files at $PROJECT_ROOT"
    exit 1
fi

# Fix Windows line endings on all text files
find "$INSTALL_DIR" -type f \( -name "*.py" -o -name "*.txt" -o -name "*.yml" \
    -o -name "*.yaml" -o -name "*.json" -o -name "*.js" -o -name "*.css" \
    -o -name "*.html" -o -name "*.conf" -o -name "*.sh" -o -name "*.md" \
    -o -name "*.env*" \) -exec sed -i 's/\r$//' {} + 2>/dev/null || true

log "  Installed to: $INSTALL_DIR"

###############################################################################
# Step 4: Load environment configuration
###############################################################################
log "Step 4/9: Configuring environment..."

# Determine .env source
if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
    cp "$ENV_FILE" "$INSTALL_DIR/.env"
    log "  Using custom env: $ENV_FILE"
elif [[ -f "$INSTALL_DIR/.env" ]]; then
    log "  Using existing .env"
elif [[ -f "$INSTALL_DIR/packaging/env.example" ]]; then
    cp "$INSTALL_DIR/packaging/env.example" "$INSTALL_DIR/.env"
    log "  Created .env from template"
fi

# Source env
if [[ -f "$INSTALL_DIR/.env" ]]; then
    sed -i 's/\r$//' "$INSTALL_DIR/.env"
    set -a
    # shellcheck disable=SC1091
    source "$INSTALL_DIR/.env"
    set +a
fi

# Auto-detect server IP
if [[ -z "${SERVER_IP:-}" ]]; then
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    [[ -z "$SERVER_IP" ]] && SERVER_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')
    [[ -z "$SERVER_IP" ]] && SERVER_IP="127.0.0.1"
    log "  Auto-detected server IP: $SERVER_IP"
fi

# Set defaults
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

DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}"

log "  Backend port: $BACKEND_PORT, Frontend port: $FRONTEND_PORT"

###############################################################################
# Step 5: Setup PostgreSQL
###############################################################################
log "Step 5/9: Configuring PostgreSQL..."

# Start PostgreSQL
systemctl enable postgresql
systemctl start postgresql

# Wait for PostgreSQL to be ready
TRIES=0
until su - postgres -c "pg_isready" &>/dev/null || [[ $TRIES -ge 15 ]]; do
    sleep 1
    TRIES=$((TRIES + 1))
done

# Create database user and database (ignore errors if they already exist)
su - postgres -c "psql -c \"CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';\"" 2>/dev/null || true
su - postgres -c "psql -c \"CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};\"" 2>/dev/null || true
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};\"" 2>/dev/null || true

# Ensure local password auth works (md5/scram instead of peer)
PG_HBA=$(su - postgres -c "psql -t -c 'SHOW hba_file;'" | tr -d ' ')
if [[ -f "$PG_HBA" ]]; then
    # Add a line for the patchmaster user before the default local entries
    if ! grep -q "patchmaster" "$PG_HBA"; then
        sed -i "/^local.*all.*all/i local   ${POSTGRES_DB}   ${POSTGRES_USER}                                md5" "$PG_HBA"
        # Also allow TCP connections from localhost
        if ! grep -q "host.*${POSTGRES_DB}.*${POSTGRES_USER}" "$PG_HBA"; then
            echo "host    ${POSTGRES_DB}   ${POSTGRES_USER}   127.0.0.1/32   md5" >> "$PG_HBA"
            echo "host    ${POSTGRES_DB}   ${POSTGRES_USER}   ::1/128        md5" >> "$PG_HBA"
        fi
        systemctl reload postgresql
    fi
fi

log "  PostgreSQL ready — database: $POSTGRES_DB, user: $POSTGRES_USER"

###############################################################################
# Step 6: Setup Backend (Python + FastAPI)
###############################################################################
log "Step 6/9: Setting up backend..."

cd "$INSTALL_DIR/backend"

# Create Python virtual environment
python3 -m venv "$INSTALL_DIR/backend/venv"
"$INSTALL_DIR/backend/venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/backend/venv/bin/pip" install -r requirements.txt -q

log "  Python venv created, dependencies installed"

# Write backend environment file
cat > "$INSTALL_DIR/backend/.env" <<BENV
DATABASE_URL=${DATABASE_URL}
JWT_SECRET=${JWT_SECRET}
TOKEN_EXPIRE_MINUTES=${TOKEN_EXPIRE_MINUTES:-480}
BENV

# Create systemd service for backend
cat > /etc/systemd/system/patchmaster-backend.service <<UNIT
[Unit]
Description=PatchMaster Backend API
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=${SVC_USER}
Group=${SVC_GROUP}
WorkingDirectory=${INSTALL_DIR}/backend
EnvironmentFile=${INSTALL_DIR}/backend/.env
ExecStart=${INSTALL_DIR}/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port ${BACKEND_PORT} --workers 4
Restart=always
RestartSec=5
StandardOutput=append:${INSTALL_DIR}/logs/backend.log
StandardError=append:${INSTALL_DIR}/logs/backend-error.log

[Install]
WantedBy=multi-user.target
UNIT

log "  Created patchmaster-backend.service"

###############################################################################
# Step 7: Build & serve Frontend (React → Nginx)
###############################################################################
log "Step 7/9: Building frontend..."

cd "$INSTALL_DIR/frontend"

# Install npm dependencies and build
npm install --silent 2>/dev/null
REACT_APP_API_URL="" npm run build --silent 2>/dev/null

log "  React app built"

# Configure Nginx
cat > /etc/nginx/sites-available/patchmaster <<NGINX
server {
    listen ${FRONTEND_PORT};
    server_name _;

    root ${INSTALL_DIR}/frontend/build;
    index index.html;

    # Proxy API requests to FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_read_timeout 300s;
    }

    # Serve agent .deb downloads from backend static
    location /download/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT}/static/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # React SPA — serve index.html for all other routes
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
NGINX

# Enable the site
if [[ -d /etc/nginx/sites-enabled ]]; then
    ln -sf /etc/nginx/sites-available/patchmaster /etc/nginx/sites-enabled/patchmaster
    # Remove default if it conflicts with our port
    if [[ "$FRONTEND_PORT" == "80" ]] && [[ -f /etc/nginx/sites-enabled/default ]]; then
        rm -f /etc/nginx/sites-enabled/default
    fi
elif [[ -d /etc/nginx/conf.d ]]; then
    # RHEL-style: use conf.d
    cp /etc/nginx/sites-available/patchmaster /etc/nginx/conf.d/patchmaster.conf
fi

# Test nginx config
nginx -t 2>/dev/null
systemctl enable nginx
systemctl restart nginx || {
    warn "  Nginx failed to start — port $FRONTEND_PORT may be in use."
    warn "  Check with: ss -tlnp | grep :$FRONTEND_PORT"
}

log "  Nginx configured on port $FRONTEND_PORT"

###############################################################################
# Step 8: Install Prometheus & Grafana (optional)
###############################################################################
if [[ "$SKIP_MONITORING" == "false" ]]; then
    log "Step 8/9: Installing monitoring stack..."

    # ── Prometheus ──
    if ! command -v prometheus &>/dev/null && [[ ! -f /usr/local/bin/prometheus ]]; then
        log "  Installing Prometheus..."
        PROM_VERSION="2.51.0"
        PROM_ARCH="linux-amd64"
        PROM_TMP=$(mktemp -d)
        cd "$PROM_TMP"
        curl -sSL "https://github.com/prometheus/prometheus/releases/download/v${PROM_VERSION}/prometheus-${PROM_VERSION}.${PROM_ARCH}.tar.gz" -o prometheus.tar.gz
        tar xzf prometheus.tar.gz --strip-components=1
        cp prometheus promtool /usr/local/bin/
        mkdir -p /etc/prometheus /var/lib/prometheus
        cp -r consoles console_libraries /etc/prometheus/ 2>/dev/null || true
        rm -rf "$PROM_TMP"
    fi

    # Create Prometheus user
    if ! id prometheus &>/dev/null; then
        useradd --system --no-create-home --shell /usr/sbin/nologin prometheus
    fi

    # Configure Prometheus to scrape the backend
    cat > /etc/prometheus/prometheus.yml <<PROMCFG
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "patchmaster-backend"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["localhost:${BACKEND_PORT}"]

  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:${PROMETHEUS_PORT}"]
PROMCFG

    chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus

    cat > /etc/systemd/system/prometheus.service <<PROMUNIT
[Unit]
Description=Prometheus Monitoring
After=network.target

[Service]
Type=exec
User=prometheus
Group=prometheus
ExecStart=/usr/local/bin/prometheus --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/var/lib/prometheus --storage.tsdb.retention.time=${PROMETHEUS_RETENTION} --web.listen-address=0.0.0.0:${PROMETHEUS_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
PROMUNIT

    log "  Prometheus installed"

    # ── Grafana ──
    if ! command -v grafana-server &>/dev/null; then
        log "  Installing Grafana..."
        if [[ "$DISTRO" == "debian" ]]; then
            apt-get install -y -qq apt-transport-https software-properties-common > /dev/null 2>&1
            curl -fsSL https://apt.grafana.com/gpg.key | gpg --dearmor -o /usr/share/keyrings/grafana.gpg 2>/dev/null
            echo "deb [signed-by=/usr/share/keyrings/grafana.gpg] https://apt.grafana.com stable main" > /etc/apt/sources.list.d/grafana.list
            apt-get update -qq > /dev/null 2>&1
            apt-get install -y -qq grafana > /dev/null 2>&1
        elif [[ "$DISTRO" == "rhel" ]]; then
            cat > /etc/yum.repos.d/grafana.repo <<'GREPO'
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
GREPO
            $PKG_MGR install -y -q grafana > /dev/null 2>&1
        fi
    fi

    # Configure Grafana
    GRAFANA_INI="/etc/grafana/grafana.ini"
    if [[ -f "$GRAFANA_INI" ]]; then
        sed -i "s/^;http_port = 3000/http_port = ${GRAFANA_PORT}/" "$GRAFANA_INI"
        sed -i "s/^http_port = .*/http_port = ${GRAFANA_PORT}/" "$GRAFANA_INI"
        sed -i "s/^;admin_user = admin/admin_user = ${GF_ADMIN_USER}/" "$GRAFANA_INI"
        sed -i "s/^;admin_password = admin/admin_password = ${GF_ADMIN_PASSWORD}/" "$GRAFANA_INI"
    fi

    # Provision Prometheus datasource
    mkdir -p /etc/grafana/provisioning/datasources
    cat > /etc/grafana/provisioning/datasources/patchmaster.yml <<GFDS
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:${PROMETHEUS_PORT}
    isDefault: true
    editable: false
GFDS

    # Provision dashboard
    mkdir -p /etc/grafana/provisioning/dashboards /var/lib/grafana/dashboards
    cat > /etc/grafana/provisioning/dashboards/patchmaster.yml <<GFDP
apiVersion: 1
providers:
  - name: PatchMaster
    orgId: 1
    folder: ""
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
GFDP

    # Copy dashboard JSON
    if [[ -f "$INSTALL_DIR/monitoring/grafana/dashboards/patchmaster-overview.json" ]]; then
        cp "$INSTALL_DIR/monitoring/grafana/dashboards/patchmaster-overview.json" /var/lib/grafana/dashboards/
        chown grafana:grafana /var/lib/grafana/dashboards/patchmaster-overview.json
    fi

    log "  Grafana installed and configured"
else
    log "Step 8/9: Skipping monitoring (--skip-monitoring)"
fi

###############################################################################
# Step 9: Set permissions, start everything
###############################################################################
log "Step 9/9: Starting services..."

# Set ownership
chown -R "$SVC_USER:$SVC_GROUP" "$INSTALL_DIR"
# Logs dir needs write access
chmod 755 "$INSTALL_DIR/logs"

# Reload systemd
systemctl daemon-reload

# Start backend
systemctl enable patchmaster-backend
systemctl start patchmaster-backend

log "  patchmaster-backend started"

# Start monitoring
if [[ "$SKIP_MONITORING" == "false" ]]; then
    systemctl enable prometheus
    systemctl start prometheus
    log "  prometheus started"

    systemctl enable grafana-server
    systemctl start grafana-server
    log "  grafana started"
fi

# Wait for backend to be ready
log "  Waiting for backend..."
TRIES=0
until curl -sf "http://localhost:${BACKEND_PORT}/api/health" &>/dev/null || [[ $TRIES -ge 30 ]]; do
    sleep 2
    TRIES=$((TRIES + 1))
done

if [[ $TRIES -ge 30 ]]; then
    warn "  Backend not responding yet — check: journalctl -u patchmaster-backend"
else
    log "  Backend API: healthy"
fi

###############################################################################
# Summary
###############################################################################
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  PatchMaster v${VERSION} installed successfully! (bare-metal)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Install directory:  $INSTALL_DIR"
echo ""
echo "  Service URLs:"
echo "    Web UI:      http://${SERVER_IP}:${FRONTEND_PORT}"
echo "    Backend API: http://${SERVER_IP}:${BACKEND_PORT}/docs"
echo "    Grafana:     http://${SERVER_IP}:${GRAFANA_PORT}  (${GF_ADMIN_USER}/${GF_ADMIN_PASSWORD})"
echo "    Prometheus:  http://${SERVER_IP}:${PROMETHEUS_PORT}"
echo ""
echo "  First-time setup:"
echo "    1. Open http://${SERVER_IP}:${FRONTEND_PORT}"
echo "    2. Register the admin account"
echo "    3. Go to 'Onboarding' to install agents on hosts"
echo ""
echo "  Agent install (run on each Linux host):"
echo "    curl -sS http://${SERVER_IP}:${FRONTEND_PORT}/download/install.sh | sudo bash -s -- ${SERVER_IP}"
echo ""
echo "  Management:"
echo "    systemctl {start|stop|restart} patchmaster-backend"
echo "    systemctl {start|stop|restart} nginx"
echo "    systemctl {start|stop|restart} prometheus"
echo "    systemctl {start|stop|restart} grafana-server"
echo ""
echo "  Logs:"
echo "    tail -f $INSTALL_DIR/logs/backend.log"
echo "    journalctl -u patchmaster-backend -f"
echo "    journalctl -u nginx -f"
echo ""
if [[ "$JWT_SECRET" == "change-me-to-a-secure-random-string" ]]; then
    echo -e "  ${YELLOW}WARNING: Change JWT_SECRET in $INSTALL_DIR/backend/.env for production!${NC}"
    echo ""
fi
