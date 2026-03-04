#!/usr/bin/env bash
###############################################################################
#  PatchMaster Vendor Portal — Database Backup Script
#  Usage: ./scripts/backup-db.sh [--output /path/to/backups]
###############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENDOR_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${1:-$VENDOR_DIR/backups}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$OUTPUT_DIR/customers-$TIMESTAMP.db"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

mkdir -p "$OUTPUT_DIR"

echo -e "${GREEN}[+]${NC} Backing up vendor database..."

# If running in Docker, copy from volume
if docker compose -f "$VENDOR_DIR/docker-compose.yml" ps --status running app &>/dev/null 2>&1; then
    docker compose -f "$VENDOR_DIR/docker-compose.yml" exec -T app \
        sqlite3 /app/data/customers.db ".backup /tmp/backup.db"
    docker compose -f "$VENDOR_DIR/docker-compose.yml" cp app:/tmp/backup.db "$BACKUP_FILE"
elif [[ -f "$VENDOR_DIR/data/customers.db" ]]; then
    # Local file — use sqlite3 backup
    sqlite3 "$VENDOR_DIR/data/customers.db" ".backup '$BACKUP_FILE'"
else
    echo -e "${YELLOW}[!]${NC} No database found."
    exit 1
fi

# Compress
gzip "$BACKUP_FILE"

echo -e "${GREEN}[+]${NC} Backup saved: ${BACKUP_FILE}.gz"
echo -e "${GREEN}[+]${NC} Size: $(du -h "${BACKUP_FILE}.gz" | cut -f1)"

# Cleanup old backups (keep last 30)
BACKUP_COUNT=$(find "$OUTPUT_DIR" -name "customers-*.db.gz" | wc -l)
if [[ $BACKUP_COUNT -gt 30 ]]; then
    echo -e "${YELLOW}[!]${NC} Cleaning up old backups (keeping last 30)..."
    find "$OUTPUT_DIR" -name "customers-*.db.gz" -type f | sort | head -n -30 | xargs rm -f
fi
