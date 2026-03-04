# PatchMaster — Monitoring Integration Guide

PatchMaster exposes built-in endpoints for **Prometheus**, **Grafana**, and **Zabbix**.
You do NOT need to install these tools with PatchMaster — simply point your
existing monitoring infrastructure at the endpoints below.

> If you don't have monitoring tools yet, you can install them alongside
> PatchMaster by running the installer with `--with-monitoring`.

---

## 1. Prometheus (Existing Setup)

### Add PatchMaster as a scrape target

Edit your existing `prometheus.yml` and add these jobs:

```yaml
scrape_configs:
  # PatchMaster Backend — patch status, CVEs, host metrics
  - job_name: 'patchmaster'
    metrics_path: '/metrics'
    scrape_interval: 30s
    static_configs:
      - targets: ['PATCHMASTER_IP:8000']
        labels:
          instance: 'patchmaster-server'

  # PatchMaster Agents — per-host system metrics (port 9100)
  # Add one target per managed host running the PatchMaster agent
  - job_name: 'patchmaster-agents'
    static_configs:
      - targets:
          - 'HOST1_IP:9100'
          - 'HOST2_IP:9100'
        labels:
          component: 'agent'
```

Replace `PATCHMASTER_IP` with your PatchMaster server IP/hostname,
and `HOST*_IP` with IPs of hosts running the PatchMaster agent.

Then reload Prometheus:
```bash
# Option A: send SIGHUP
kill -HUP $(pidof prometheus)

# Option B: use lifecycle API (if --web.enable-lifecycle is set)
curl -X POST http://localhost:9090/-/reload
```

### Available Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `patchmaster_hosts_total` | Gauge | Total registered hosts |
| `patchmaster_hosts_online` | Gauge | Hosts reporting in last 10 min |
| `patchmaster_updates_pending` | Gauge | Total pending updates across all hosts |
| `patchmaster_updates_security` | Gauge | Security updates pending |
| `patchmaster_cves_total` | Gauge | Known CVEs across fleet |
| `patchmaster_cves_critical` | Gauge | Critical severity CVEs |
| `patchmaster_cves_high` | Gauge | High severity CVEs |
| `patchmaster_patches_applied_total` | Counter | Cumulative patches applied |
| `patchmaster_api_requests_total` | Counter | API requests by method/endpoint/status |
| `patchmaster_api_request_duration_seconds` | Histogram | API response times |

---

## 2. Grafana (Existing Setup)

### Step A — Add Prometheus Datasource (if not already done)

1. Go to **Grafana → Configuration → Data Sources → Add data source**
2. Select **Prometheus**
3. Set URL: `http://PROMETHEUS_IP:9090`
4. Click **Save & Test**

### Step B — Import the PatchMaster Dashboard

**Option 1: Import JSON file**
1. Go to **Grafana → Dashboards → Import**
2. Click **Upload JSON file**
3. Select: `<patchmaster-install-dir>/monitoring/grafana/dashboards/patchmaster-overview.json`
4. Select the Prometheus datasource you added above
5. Click **Import**

**Option 2: Copy provisioning files**
If you use Grafana provisioning, copy these files:

```bash
# Datasource (edit URL if your Prometheus is on a different host)
cp <patchmaster-dir>/monitoring/grafana/provisioning/datasources/prometheus.yml \
   /etc/grafana/provisioning/datasources/patchmaster.yml

# Dashboard provider
cp <patchmaster-dir>/monitoring/grafana/provisioning/dashboards/dashboards.yml \
   /etc/grafana/provisioning/dashboards/patchmaster.yml

# Dashboard JSON
cp <patchmaster-dir>/monitoring/grafana/dashboards/patchmaster-overview.json \
   /var/lib/grafana/dashboards/

# Restart Grafana
sudo systemctl restart grafana-server
```

---

## 3. Zabbix (Existing Setup)

PatchMaster provides Zabbix-compatible JSON endpoints that work with
**Zabbix HTTP Agent** items and **Low-Level Discovery (LLD)**.

### Available Zabbix API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/zabbix/discovery/hosts` | LLD — returns `{data: [{"{#HOST_ID}", "{#HOSTNAME}", ...}]}` |
| `GET /api/zabbix/discovery/cves` | LLD — returns `{data: [{"{#CVE_ID}", "{#SEVERITY}", ...}]}` |
| `GET /api/zabbix/items/overview` | Overview — total hosts, pending updates, CVE counts |
| `GET /api/zabbix/items/host/{id}` | Per-host — updates pending, last check-in, OS info |
| `GET /api/zabbix/export/trapper` | Zabbix trapper-format data for `zabbix_sender` |

### Step A — Create a Host for PatchMaster

1. Go to **Zabbix → Configuration → Hosts → Create host**
2. Host name: `PatchMaster`
3. Interfaces → Add **Agent** interface: `PATCHMASTER_IP:8000`

### Step B — Create Discovery Rules (LLD)

**Host Discovery:**
1. Go to the PatchMaster host → **Discovery rules → Create**
2. Name: `PatchMaster Host Discovery`
3. Type: **HTTP agent**
4. URL: `http://PATCHMASTER_IP:8000/api/zabbix/discovery/hosts`
5. Update interval: `5m`
6. Add **Item prototypes** using LLD macros (`{#HOSTNAME}`, `{#HOST_ID}`, etc.)

**CVE Discovery:**
1. Create another discovery rule
2. URL: `http://PATCHMASTER_IP:8000/api/zabbix/discovery/cves`
3. Use macros: `{#CVE_ID}`, `{#SEVERITY}`, `{#PACKAGE}`

### Step C — Create HTTP Agent Items (Overview)

1. Go to PatchMaster host → **Items → Create**
2. Type: **HTTP agent**
3. URL: `http://PATCHMASTER_IP:8000/api/zabbix/items/overview`
4. Key: `patchmaster.overview`
5. Type of information: **Text**
6. Add **Dependent items** to extract fields with JSONPath:
   - `$.total_hosts` → `patchmaster.hosts.total`
   - `$.pending_updates` → `patchmaster.updates.pending`
   - `$.critical_cves` → `patchmaster.cves.critical`

### Step D — (Alternative) Use Zabbix Sender

```bash
# Fetch trapper data and push to Zabbix server
curl -s http://PATCHMASTER_IP:8000/api/zabbix/export/trapper | \
    zabbix_sender -z ZABBIX_SERVER -i -
```

Add this as a cron job for periodic updates:
```bash
*/5 * * * * curl -s http://PATCHMASTER_IP:8000/api/zabbix/export/trapper | zabbix_sender -z ZABBIX_SERVER -i - >/dev/null 2>&1
```

---

## Quick Reference

| Tool | What to configure | PatchMaster endpoint |
|------|------------------|---------------------|
| Prometheus | `scrape_configs` target | `http://SERVER:8000/metrics` |
| Grafana | Import dashboard JSON | `monitoring/grafana/dashboards/patchmaster-overview.json` |
| Zabbix LLD | HTTP Agent discovery | `http://SERVER:8000/api/zabbix/discovery/hosts` |
| Zabbix Items | HTTP Agent item | `http://SERVER:8000/api/zabbix/items/overview` |
| Zabbix Trapper | `zabbix_sender` | `http://SERVER:8000/api/zabbix/export/trapper` |

---

## Troubleshooting

**Prometheus can't scrape PatchMaster:**
```bash
# Verify the metrics endpoint is reachable
curl http://PATCHMASTER_IP:8000/metrics

# Check firewall
sudo ufw status                    # Ubuntu
sudo firewall-cmd --list-ports     # RHEL
```

**Grafana shows "No Data":**
- Verify the Prometheus datasource is working (Test button)
- Check that PatchMaster scrape target is UP in Prometheus → Status → Targets

**Zabbix HTTP agent fails:**
- Ensure Zabbix server can reach `PATCHMASTER_IP:8000`
- Test: `curl http://PATCHMASTER_IP:8000/api/zabbix/items/overview`
