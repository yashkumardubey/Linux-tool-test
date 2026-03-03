"""CVE / Advisory mapping API — track vulnerabilities per host."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from auth import get_current_user, require_role
from models.db_models import CVE, HostCVE, Host, Severity, User

router = APIRouter(prefix="/api/cve", tags=["cve"])


# --- Schemas ---
class CVECreate(BaseModel):
    cve_id: str
    description: Optional[str] = None
    severity: Severity = Severity.medium
    cvss_score: Optional[float] = None
    affected_packages: list[str] = []
    fixed_in: list[str] = []
    advisory_url: Optional[str] = None


class HostCVECreate(BaseModel):
    host_id: int
    cve_id: int


# --- CVE CRUD ---
@router.get("/")
async def list_cves(
    severity: Optional[str] = None,
    search: Optional[str] = None,
    unpatched_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(CVE)
    if severity:
        q = q.where(CVE.severity == severity)
    if search:
        q = q.where(CVE.cve_id.ilike(f"%{search}%") | CVE.description.ilike(f"%{search}%"))
    q = q.order_by(CVE.cvss_score.desc().nullslast(), CVE.created_at.desc())
    q = q.offset(skip).limit(limit)
    result = await db.execute(q)
    cves = result.scalars().all()

    data = []
    for c in cves:
        # Count affected hosts
        affected = await db.scalar(select(func.count(HostCVE.id)).where(HostCVE.cve_id == c.id))
        patched = await db.scalar(
            select(func.count(HostCVE.id)).where(HostCVE.cve_id == c.id, HostCVE.is_patched == True)
        )
        if unpatched_only and affected == patched:
            continue
        data.append({
            "id": c.id,
            "cve_id": c.cve_id,
            "description": c.description,
            "severity": c.severity.value,
            "cvss_score": c.cvss_score,
            "affected_packages": c.affected_packages,
            "fixed_in": c.fixed_in,
            "advisory_url": c.advisory_url,
            "affected_hosts": affected,
            "patched_hosts": patched,
            "created_at": c.created_at.isoformat(),
        })
    return data


@router.get("/stats")
async def cve_stats(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    total = await db.scalar(select(func.count(CVE.id)))
    by_severity = {}
    for sev in Severity:
        count = await db.scalar(select(func.count(CVE.id)).where(CVE.severity == sev))
        by_severity[sev.value] = count

    open_vulns = await db.scalar(select(func.count(HostCVE.id)).where(HostCVE.is_patched == False))
    patched_vulns = await db.scalar(select(func.count(HostCVE.id)).where(HostCVE.is_patched == True))

    return {
        "total_cves": total,
        "by_severity": by_severity,
        "open_vulnerabilities": open_vulns,
        "patched_vulnerabilities": patched_vulns,
    }


@router.post("/", status_code=201)
async def create_cve(
    data: CVECreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "operator")),
):
    existing = await db.scalar(select(CVE).where(CVE.cve_id == data.cve_id))
    if existing:
        raise HTTPException(400, "CVE already exists")
    cve = CVE(**data.model_dump())
    db.add(cve)
    await db.commit()
    await db.refresh(cve)
    return {"id": cve.id, "cve_id": cve.cve_id}


@router.get("/{cve_id}")
async def get_cve(cve_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    cve = await db.get(CVE, cve_id)
    if not cve:
        raise HTTPException(404, "CVE not found")
    # Get affected hosts
    result = await db.execute(
        select(HostCVE).where(HostCVE.cve_id == cve_id).options(selectinload(HostCVE.host))
    )
    host_cves = result.scalars().all()
    return {
        "id": cve.id,
        "cve_id": cve.cve_id,
        "description": cve.description,
        "severity": cve.severity.value,
        "cvss_score": cve.cvss_score,
        "affected_packages": cve.affected_packages,
        "fixed_in": cve.fixed_in,
        "advisory_url": cve.advisory_url,
        "affected_hosts": [
            {
                "host_id": hc.host.id,
                "hostname": hc.host.hostname,
                "ip": hc.host.ip,
                "is_patched": hc.is_patched,
                "patched_at": hc.patched_at.isoformat() if hc.patched_at else None,
            }
            for hc in host_cves
        ],
    }


@router.delete("/{cve_id}", status_code=204)
async def delete_cve(
    cve_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    cve = await db.get(CVE, cve_id)
    if not cve:
        raise HTTPException(404, "CVE not found")
    await db.execute(delete(HostCVE).where(HostCVE.cve_id == cve_id))
    await db.delete(cve)
    await db.commit()


# --- Host-CVE Mapping ---
@router.post("/map", status_code=201)
async def map_cve_to_host(
    data: HostCVECreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "operator")),
):
    host = await db.get(Host, data.host_id)
    if not host:
        raise HTTPException(404, "Host not found")
    cve = await db.get(CVE, data.cve_id)
    if not cve:
        raise HTTPException(404, "CVE not found")
    existing = await db.scalar(
        select(HostCVE).where(HostCVE.host_id == data.host_id, HostCVE.cve_id == data.cve_id)
    )
    if existing:
        raise HTTPException(400, "Mapping already exists")
    hc = HostCVE(host_id=data.host_id, cve_id=data.cve_id)
    db.add(hc)
    # Update host CVE count
    host.cve_count = await db.scalar(
        select(func.count(HostCVE.id)).where(HostCVE.host_id == host.id, HostCVE.is_patched == False)
    ) + 1
    await db.commit()
    return {"id": hc.id}


@router.post("/map/{mapping_id}/mark-patched")
async def mark_patched(
    mapping_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "operator")),
):
    hc = await db.get(HostCVE, mapping_id)
    if not hc:
        raise HTTPException(404, "Mapping not found")
    hc.is_patched = True
    hc.patched_at = datetime.utcnow()
    # Update host CVE count
    host = await db.get(Host, hc.host_id)
    host.cve_count = max(0, host.cve_count - 1)
    await db.commit()
    return {"status": "patched"}


@router.get("/host/{host_id}")
async def host_cves(host_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Get all CVEs for a specific host."""
    host = await db.get(Host, host_id)
    if not host:
        raise HTTPException(404, "Host not found")
    result = await db.execute(
        select(HostCVE).where(HostCVE.host_id == host_id).options(selectinload(HostCVE.cve))
    )
    host_cves_list = result.scalars().all()
    return [
        {
            "mapping_id": hc.id,
            "cve_id": hc.cve.cve_id,
            "description": hc.cve.description,
            "severity": hc.cve.severity.value,
            "cvss_score": hc.cve.cvss_score,
            "is_patched": hc.is_patched,
            "patched_at": hc.patched_at.isoformat() if hc.patched_at else None,
        }
        for hc in host_cves_list
    ]
