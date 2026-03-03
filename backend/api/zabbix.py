"""Zabbix integration API — discovery, item data, and trap sender."""
import time
import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models.db_models import Host, PatchJob, CVE, HostCVE, JobStatus, User, Severity

router = APIRouter(prefix="/api/zabbix", tags=["zabbix"])


# ───────────────────────────────────────────────
# Zabbix LLD (Low-Level Discovery) Endpoints
# ───────────────────────────────────────────────

@router.get("/discovery/hosts")
async def discover_hosts(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Zabbix LLD: returns host list in Zabbix discovery JSON format."""
    result = await db.execute(select(Host).order_by(Host.hostname))
    hosts = result.scalars().all()
    return {
        "data": [
            {
                "{#HOST_ID}": str(h.id),
                "{#HOSTNAME}": h.hostname,
                "{#IP}": h.ip,
                "{#OS}": h.os or "",
                "{#OS_VERSION}": h.os_version or "",
            }
            for h in hosts
        ]
    }


@router.get("/discovery/cves")
async def discover_cves(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Zabbix LLD: returns CVE list in Zabbix discovery JSON format."""
    result = await db.execute(select(CVE).order_by(CVE.severity, CVE.cve_id))
    cves = result.scalars().all()
    return {
        "data": [
            {
                "{#CVE_ID}": c.cve_id,
                "{#SEVERITY}": c.severity,
                "{#PACKAGE}": c.affected_package or "",
            }
            for c in cves
        ]
    }


# ───────────────────────────────────────────────
# Zabbix Item Data Endpoints (for HTTP Agent items)
# ───────────────────────────────────────────────

@router.get("/items/overview")
async def zabbix_overview(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """All key metrics in one call — use with Zabbix dependent items."""
    total = (await db.execute(select(func.count(Host.id)))).scalar() or 0
    online = (await db.execute(select(func.count(Host.id)).where(Host.is_online == True))).scalar() or 0
    reboot = (await db.execute(select(func.count(Host.id)).where(Host.reboot_required == True))).scalar() or 0
    upgradable = (await db.execute(select(func.coalesce(func.sum(Host.upgradable_count), 0)))).scalar() or 0
    avg_compliance = (await db.execute(select(func.coalesce(func.avg(Host.compliance_score), 100.0)))).scalar() or 100.0

    # Jobs
    jobs_success = (await db.execute(
        select(func.count(PatchJob.id)).where(PatchJob.status == JobStatus.success)
    )).scalar() or 0
    jobs_failed = (await db.execute(
        select(func.count(PatchJob.id)).where(PatchJob.status == JobStatus.failed)
    )).scalar() or 0

    # CVEs
    cve_total = (await db.execute(select(func.count(CVE.id)))).scalar() or 0
    cve_critical = (await db.execute(
        select(func.count(CVE.id)).where(CVE.severity == Severity.critical)
    )).scalar() or 0
    cve_unpatched = (await db.execute(
        select(func.count(HostCVE.id)).where(HostCVE.is_patched == False)
    )).scalar() or 0

    return {
        "hosts_total": total,
        "hosts_online": online,
        "hosts_offline": total - online,
        "hosts_reboot_required": reboot,
        "packages_upgradable": upgradable,
        "compliance_avg": round(avg_compliance, 1),
        "jobs_success": jobs_success,
        "jobs_failed": jobs_failed,
        "cve_total": cve_total,
        "cve_critical": cve_critical,
        "cve_unpatched": cve_unpatched,
        "timestamp": int(time.time()),
    }


@router.get("/items/host/{host_id}")
async def zabbix_host_item(host_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Per-host metrics for Zabbix."""
    host = await db.get(Host, host_id)
    if not host:
        return {"error": "Host not found"}
    return {
        "hostname": host.hostname,
        "ip": host.ip,
        "is_online": 1 if host.is_online else 0,
        "compliance_score": host.compliance_score or 0,
        "upgradable_count": host.upgradable_count or 0,
        "installed_count": host.installed_count or 0,
        "reboot_required": 1 if host.reboot_required else 0,
        "cve_count": host.cve_count or 0,
        "last_heartbeat": host.last_heartbeat.isoformat() if host.last_heartbeat else "",
        "last_patched": host.last_patched.isoformat() if host.last_patched else "",
    }


# ───────────────────────────────────────────────
# Zabbix Trapper Data Format Export
# ───────────────────────────────────────────────

@router.get("/export/trapper")
async def zabbix_trapper_export(
    zabbix_host: str = Query("PatchMaster", description="Zabbix host name to send traps for"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Returns data in zabbix_sender format:
    Each line: <hostname> <key> <timestamp> <value>
    Pipe this to: zabbix_sender -z <zabbix-server> -i <file>
    """
    overview = await zabbix_overview(db=db, user=user)
    ts = overview["timestamp"]
    lines = []
    for key, val in overview.items():
        if key == "timestamp":
            continue
        lines.append(f"{zabbix_host} patchmaster.{key} {ts} {val}")

    # Per-host data
    result = await db.execute(select(Host))
    hosts = result.scalars().all()
    for h in hosts:
        prefix = f"{zabbix_host} patchmaster.host[{h.hostname}]"
        lines.append(f"{prefix}.online {ts} {1 if h.is_online else 0}")
        lines.append(f"{prefix}.compliance {ts} {h.compliance_score or 0}")
        lines.append(f"{prefix}.upgradable {ts} {h.upgradable_count or 0}")
        lines.append(f"{prefix}.reboot {ts} {1 if h.reboot_required else 0}")
        lines.append(f"{prefix}.cve_count {ts} {h.cve_count or 0}")

    return {"format": "zabbix_sender", "line_count": len(lines), "data": "\n".join(lines)}
