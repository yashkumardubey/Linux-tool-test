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
