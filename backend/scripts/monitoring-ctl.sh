#!/usr/bin/env bash
###############################################################################
#  PatchMaster ─ Monitoring Service Controller
#  Manages Prometheus, Grafana, and Zabbix services based on license tier.
#
#  Called by the PatchMaster backend via sudo.
#  Must be run as root.
#
#  Usage:
#    monitoring-ctl.sh status                 # JSON status of all services
#    monitoring-ctl.sh start   [service]      # Start service(s)
#    monitoring-ctl.sh stop    [service]       # Stop service(s)
#    monitoring-ctl.sh install [service]       # Install + configure service(s)
#    monitoring-ctl.sh enforce <has_feature>   # Full enforcement (1=start, 0=stop)
###############################################################################
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/patchmaster}"

# ── Service definitions ──
declare -A SVC_SYSTEMD=(
  [prometheus]="prometheus"
  [grafana]="grafana-server"
  [zabbix]="zabbix-server"
)

declare -A SVC_PORT=(
  [prometheus]="9090"
  [grafana]="3001"
  [zabbix]="10051"
)

ALL_SERVICES="prometheus grafana zabbix"

# ── Helpers ──
is_installed() {
  local svc="${SVC_SYSTEMD[$1]}"
  systemctl list-unit-files "${svc}.service" 2>/dev/null | grep -q "$svc" && return 0
  command -v "$1" &>/dev/null && return 0
  return 1
}

is_running() {
  local svc="${SVC_SYSTEMD[$1]}"
  systemctl is-active "$svc" &>/dev/null
}

detect_distro() {
  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    source /etc/os-release
    case "$ID" in
      ubuntu|debian|linuxmint|pop) echo "debian" ;;
      rhel|centos|rocky|alma|fedora|ol) echo "rhel" ;;
      *) command -v apt-get &>/dev/null && echo "debian" || echo "rhel" ;;
    esac
  else
    command -v apt-get &>/dev/null && echo "debian" || echo "rhel"
  fi
}

# ── Status (JSON output) ──
cmd_status() {
  echo "{"
  local first=true
  for key in $ALL_SERVICES; do
    $first || echo ","
    first=false
    local installed="false" running="false"
    is_installed "$key" && installed="true"
    [[ "$installed" == "true" ]] && is_running "$key" && running="true"
    echo "  \"$key\": {\"installed\": $installed, \"running\": $running, \"port\": ${SVC_PORT[$key]}}"
  done
  echo "}"
}

# ── Start ──
cmd_start() {
  local target="${1:-all}"
  local services="$ALL_SERVICES"
  [[ "$target" != "all" ]] && services="$target"

  for key in $services; do
    local svc="${SVC_SYSTEMD[$key]}"
    if is_installed "$key"; then
      systemctl enable "$svc" 2>/dev/null || true
      systemctl start "$svc" 2>/dev/null || true
      echo "{\"service\": \"$key\", \"action\": \"started\", \"success\": true}"
    else
      echo "{\"service\": \"$key\", \"action\": \"start\", \"success\": false, \"error\": \"not_installed\"}"
    fi
  done
}

# ── Stop ──
cmd_stop() {
  local target="${1:-all}"
  local services="$ALL_SERVICES"
  [[ "$target" != "all" ]] && services="$target"

  for key in $services; do
    local svc="${SVC_SYSTEMD[$key]}"
    if is_installed "$key" && is_running "$key"; then
      systemctl stop "$svc" 2>/dev/null || true
      systemctl disable "$svc" 2>/dev/null || true
      echo "{\"service\": \"$key\", \"action\": \"stopped\", \"success\": true}"
    else
      echo "{\"service\": \"$key\", \"action\": \"stop\", \"success\": true, \"note\": \"already stopped or not installed\"}"
    fi
  done
}

# ── Install ──
install_prometheus() {
  if is_installed prometheus; then
    echo "{\"service\": \"prometheus\", \"action\": \"install\", \"success\": true, \"note\": \"already installed\"}"
    return
  fi

  local distro
  distro=$(detect_distro)
  local PROM_VER="2.51.2"
  local PROM_ARCH="linux-amd64"

  if [[ "$distro" == "debian" ]]; then
    # Try apt first
    if apt-cache show prometheus &>/dev/null 2>&1; then
      DEBIAN_FRONTEND=noninteractive apt-get install -y -qq prometheus >/dev/null 2>&1
    else
      # Download binary
      local TMP_DIR
      TMP_DIR=$(mktemp -d)
      curl -fsSL "https://github.com/prometheus/prometheus/releases/download/v${PROM_VER}/prometheus-${PROM_VER}.${PROM_ARCH}.tar.gz" \
        -o "$TMP_DIR/prometheus.tar.gz"
      tar -xzf "$TMP_DIR/prometheus.tar.gz" -C "$TMP_DIR"
      cp "$TMP_DIR/prometheus-${PROM_VER}.${PROM_ARCH}/prometheus" /usr/local/bin/
      cp "$TMP_DIR/prometheus-${PROM_VER}.${PROM_ARCH}/promtool"   /usr/local/bin/
      rm -rf "$TMP_DIR"

      # Create user
      id prometheus &>/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin prometheus

      # Directories
      mkdir -p /etc/prometheus /var/lib/prometheus
      chown prometheus:prometheus /var/lib/prometheus

      # Default config
      if [[ ! -f /etc/prometheus/prometheus.yml ]]; then
        cat > /etc/prometheus/prometheus.yml <<'PCFG'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'patchmaster'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8000']
        labels:
          instance: 'patchmaster-server'
PCFG
      fi
      chown -R prometheus:prometheus /etc/prometheus
      mkdir -p /etc/prometheus/agents

      # Systemd unit
      cat > /etc/systemd/system/prometheus.service <<'PSVC'
[Unit]
Description=Prometheus Monitoring
After=network.target

[Service]
Type=simple
User=prometheus
Group=prometheus
ExecStart=/usr/local/bin/prometheus \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/var/lib/prometheus \
    --storage.tsdb.retention.time=30d \
    --web.listen-address=0.0.0.0:9090 \
    --web.enable-lifecycle
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
PSVC
      systemctl daemon-reload
    fi
  elif [[ "$distro" == "rhel" ]]; then
    dnf install -y -q prometheus 2>/dev/null || yum install -y -q prometheus 2>/dev/null || {
      echo "{\"service\": \"prometheus\", \"action\": \"install\", \"success\": false, \"error\": \"package not available\"}"
      return
    }
  fi

  echo "{\"service\": \"prometheus\", \"action\": \"installed\", \"success\": true}"
}

install_grafana() {
  if is_installed grafana; then
    echo "{\"service\": \"grafana\", \"action\": \"install\", \"success\": true, \"note\": \"already installed\"}"
    return
  fi

  local distro
  distro=$(detect_distro)

  if [[ "$distro" == "debian" ]]; then
    apt-get install -y -qq apt-transport-https software-properties-common >/dev/null 2>&1
    if [[ ! -f /usr/share/keyrings/grafana-archive-keyring.gpg ]]; then
      curl -fsSL https://apt.grafana.com/gpg.key | gpg --dearmor -o /usr/share/keyrings/grafana-archive-keyring.gpg 2>/dev/null
      echo "deb [signed-by=/usr/share/keyrings/grafana-archive-keyring.gpg] https://apt.grafana.com stable main" \
        > /etc/apt/sources.list.d/grafana.list
      apt-get update -qq >/dev/null 2>&1
    fi
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq grafana >/dev/null 2>&1
  elif [[ "$distro" == "rhel" ]]; then
    if [[ ! -f /etc/yum.repos.d/grafana.repo ]]; then
      cat > /etc/yum.repos.d/grafana.repo <<'GREPO'
[grafana]
name=Grafana OSS
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
GREPO
    fi
    dnf install -y -q grafana 2>/dev/null || yum install -y -q grafana 2>/dev/null
  fi

  # Configure Grafana port to 3001
  if [[ -f /etc/grafana/grafana.ini ]]; then
    sed -i 's/^;http_port = .*/http_port = 3001/' /etc/grafana/grafana.ini
    sed -i 's/^http_port = .*/http_port = 3001/' /etc/grafana/grafana.ini
  fi

  # Provision Prometheus datasource
  mkdir -p /etc/grafana/provisioning/datasources
  cat > /etc/grafana/provisioning/datasources/patchmaster.yml <<'GFDS'
apiVersion: 1
datasources:
  - name: PatchMaster-Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    editable: true
GFDS

  # Provision dashboards directory
  mkdir -p /etc/grafana/provisioning/dashboards /var/lib/grafana/dashboards
  cat > /etc/grafana/provisioning/dashboards/patchmaster.yml <<'GFDP'
apiVersion: 1
providers:
  - name: PatchMaster
    folder: PatchMaster
    type: file
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
GFDP

  # Copy dashboard if available
  if [[ -f "${INSTALL_DIR}/monitoring/grafana/dashboards/patchmaster-overview.json" ]]; then
    cp "${INSTALL_DIR}/monitoring/grafana/dashboards/patchmaster-overview.json" \
      /var/lib/grafana/dashboards/
  fi

  systemctl daemon-reload
  echo "{\"service\": \"grafana\", \"action\": \"installed\", \"success\": true}"
}

install_zabbix() {
  if is_installed zabbix; then
    echo "{\"service\": \"zabbix\", \"action\": \"install\", \"success\": true, \"note\": \"already installed\"}"
    return
  fi

  local distro
  distro=$(detect_distro)

  if [[ "$distro" == "debian" ]]; then
    # Add Zabbix repository
    local ZBX_VER="6.4"
    local CODENAME
    CODENAME=$(lsb_release -cs 2>/dev/null || echo "jammy")
    if [[ ! -f /etc/apt/sources.list.d/zabbix.list ]]; then
      curl -fsSL "https://repo.zabbix.com/zabbix/${ZBX_VER}/ubuntu/pool/main/z/zabbix-release/zabbix-release_${ZBX_VER}-1+ubuntu22.04_all.deb" \
        -o /tmp/zabbix-release.deb 2>/dev/null && dpkg -i /tmp/zabbix-release.deb 2>/dev/null || true
      apt-get update -qq >/dev/null 2>&1
    fi
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq zabbix-server-pgsql zabbix-frontend-php zabbix-agent >/dev/null 2>&1 || {
      echo "{\"service\": \"zabbix\", \"action\": \"install\", \"success\": false, \"error\": \"package install failed\"}"
      return
    }
  elif [[ "$distro" == "rhel" ]]; then
    rpm -Uvh "https://repo.zabbix.com/zabbix/6.4/rhel/8/x86_64/zabbix-release-6.4-1.el8.noarch.rpm" 2>/dev/null || true
    dnf install -y -q zabbix-server-pgsql zabbix-web-pgsql zabbix-agent 2>/dev/null || {
      echo "{\"service\": \"zabbix\", \"action\": \"install\", \"success\": false, \"error\": \"package install failed\"}"
      return
    }
  fi

  systemctl daemon-reload
  echo "{\"service\": \"zabbix\", \"action\": \"installed\", \"success\": true}"
}

cmd_install() {
  local target="${1:-all}"

  if [[ "$target" == "all" ]]; then
    install_prometheus
    install_grafana
    install_zabbix
  else
    case "$target" in
      prometheus) install_prometheus ;;
      grafana)    install_grafana ;;
      zabbix)     install_zabbix ;;
      *) echo "{\"error\": \"Unknown service: $target\"}" ;;
    esac
  fi
}

# ── Enforce — full lifecycle management based on license ──
cmd_enforce() {
  local has_feature="${1:-0}"

  if [[ "$has_feature" == "1" ]]; then
    # Licensed: install if needed, then start all
    install_prometheus
    install_grafana
    install_zabbix
    cmd_start all
  else
    # Not licensed: stop all monitoring services
    cmd_stop all
  fi

  # Return final status
  cmd_status
}

# ── Main ──
case "${1:-help}" in
  status)   cmd_status ;;
  start)    cmd_start "${2:-all}" ;;
  stop)     cmd_stop "${2:-all}" ;;
  install)  cmd_install "${2:-all}" ;;
  enforce)  cmd_enforce "${2:-0}" ;;
  *)
    echo "Usage: $0 {status|start|stop|install|enforce} [service|0|1]"
    echo "Services: prometheus, grafana, zabbix, all"
    exit 1
    ;;
esac
