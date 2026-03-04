# PatchMaster Vendor Portal

Internal management tool for tracking customers, purchases, licenses, and product versions.

> **This is an INTERNAL tool — never deploy on customer-facing infrastructure.**

## Features

| Feature | Description |
|---------|------------|
| **Customer Management** | Full CRUD — name, email, company, phone, address, status, notes |
| **Purchase Tracking** | Record purchases with tier, plan, amount, payment method |
| **License Generation** | Auto-generates signed license keys (HMAC-SHA256) on purchase |
| **License Lifecycle** | View, revoke, regenerate license keys |
| **Version Management** | Track tool releases, codenames, changelogs, min-tier requirements |
| **Reports & Analytics** | Revenue by tier/month, license status, expiring licenses |
| **Activity Log** | Audit trail of all vendor operations |
| **CLI License Tool** | Standalone `generate-license.py` for command-line key generation |

## Quick Start

### Development (Local)
```bash
pip install -r requirements.txt
make dev
# → http://127.0.0.1:5050 (admin / admin123)
```

### Production (Docker)
```bash
# 1. Configure
make setup
nano .env   # Set CM_SECRET_KEY, CM_ADMIN_PASS

# 2. Deploy
make prod
# → http://YOUR-IP:8080
```

### CLI License Generation
```bash
python generate-license.py --tier enterprise --plan 1-year --customer "Acme Corp"
python generate-license.py --plan testing --customer "Demo User"
python generate-license.py --tier standard --plan 2-year --customer "Mid Corp" -o license.key
```

## Architecture

```
vendor/
├── app.py                  # Flask application (production-ready)
├── generate-license.py     # CLI license generator
├── Dockerfile              # Production container (Gunicorn + non-root)
├── docker-compose.yml      # Production stack (App + Nginx reverse proxy)
├── nginx.conf              # Nginx with rate limiting & security headers
├── requirements.txt        # Python dependencies
├── Makefile                # Management commands
├── .env.example            # Environment template
├── templates/              # Jinja2 templates (Bootstrap 5 dark theme)
├── scripts/
│   └── backup-db.sh        # Database backup script
├── data/                   # SQLite database (gitignored, Docker volume)
└── backups/                # Database backups (gitignored)
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CM_SECRET_KEY` | **YES** | random | Flask session signing key (64-char hex) |
| `CM_ADMIN_USER` | no | `admin` | Admin username |
| `CM_ADMIN_PASS` | **YES** | `admin123` | Admin password |
| `CM_DB_PATH` | no | `data/customers.db` | SQLite database path |
| `LICENSE_SIGN_KEY` | no | `PatchMaster-License-*` | License signing key (must match product) |
| `VENDOR_PORT` | no | `8080` | External port (nginx) |
| `LOG_LEVEL` | no | `info` | Logging level |

## License Tiers

| Tier | Multiplier | Features |
|------|-----------|----------|
| Basic | 1.0x | 10 features — patching, hosts, groups, schedules |
| Standard | 2.0x | 16 features — + compliance, CVE, audit, monitoring |
| DevOps | 3.0x | 18 features — + CI/CD, Git integration |
| Enterprise | 5.0x | 20 features — all features enabled |

## Operations

```bash
make status    # Service status
make logs      # Follow logs
make health    # Health check
make backup    # Backup database
make restart   # Restart services
make stop      # Stop services
```

## Backup & Restore

```bash
# Automated backup
make backup

# Manual backup (Docker)
docker compose exec app sqlite3 /app/data/customers.db ".backup /tmp/backup.db"
docker compose cp app:/tmp/backup.db ./backups/manual-backup.db

# Restore
docker compose cp ./backups/manual-backup.db app:/app/data/customers.db
docker compose restart app
```

## Security Notes

- Change `CM_ADMIN_PASS` and `CM_SECRET_KEY` before production deployment
- Nginx applies rate limiting on `/login` (5 req/min)
- Session cookies are HTTP-only with SameSite=Lax
- Set `HTTPS_ENABLED=true` when behind TLS for secure cookies
- License signing key must match the product's `LICENSE_SIGN_KEY`
- Run on a private network — this portal should NOT be internet-facing

## SSL / HTTPS

The vendor portal supports HTTPS when SSL certificates are provided. Nginx auto-detects certs and redirects HTTP → HTTPS.

```bash
# 1. Place certificates
mkdir -p certs/
cp /path/to/fullchain.pem certs/
cp /path/to/privkey.pem   certs/
chmod 600 certs/privkey.pem

# 2. Enable secure cookies in .env
echo "HTTPS_ENABLED=true" >> .env

# 3. Start — auto-detects certs
make prod

# 4. Verify
make ssl-check
```

Default: HTTP :8080 → HTTPS :8443. Override `VENDOR_SSL_PORT` in `.env`.
