"""Hosts API — CRUD with PostgreSQL, groups, tags."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional

from database import get_db
from auth import get_current_user, require_role
from models.db_models import Host, HostGroup, Tag, UserRole, User, host_group_assoc, host_tag_assoc

router = APIRouter(prefix="/api/hosts", tags=["hosts"])


# ── Schemas ──

class HostOut(BaseModel):
    id: int
    hostname: str
    ip: str
    os: str
    os_version: str
    kernel: str
    arch: str
    agent_version: str
    is_online: bool
    last_heartbeat: Optional[datetime] = None
    last_patched: Optional[datetime] = None
    reboot_required: bool
    installed_count: int
    upgradable_count: int
    cve_count: int
    compliance_score: float
    groups: List[str] = []
    tags: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True

class HostCreate(BaseModel):
    hostname: str
    ip: str
    os: str = ""
    os_version: str = ""
    groups: List[str] = []
    tags: List[str] = []

class HostUpdate(BaseModel):
    hostname: Optional[str] = None
    ip: Optional[str] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    groups: Optional[List[str]] = None
    tags: Optional[List[str]] = None


# ── Helpers ──

async def _get_or_create_groups(db: AsyncSession, names: List[str]) -> List[HostGroup]:
    groups = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        result = await db.execute(select(HostGroup).where(HostGroup.name == name))
        grp = result.scalar_one_or_none()
        if not grp:
            grp = HostGroup(name=name)
            db.add(grp)
            await db.flush()
        groups.append(grp)
    return groups


async def _get_or_create_tags(db: AsyncSession, names: List[str]) -> List[Tag]:
    tags = []
    for name in names:
        name = name.strip().lower()
        if not name:
            continue
        result = await db.execute(select(Tag).where(Tag.name == name))
        tag = result.scalar_one_or_none()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            await db.flush()
        tags.append(tag)
    return tags


def _host_to_out(host: Host) -> dict:
    return {
        **{c.name: getattr(host, c.name) for c in host.__table__.columns},
        "groups": [g.name for g in host.groups],
        "tags": [t.name for t in host.tags],
    }


# ── Endpoints ──

@router.get("/", response_model=List[HostOut])
async def list_hosts(
    search: str = "",
    group: str = "",
    tag: str = "",
    online_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Host).options(selectinload(Host.groups), selectinload(Host.tags))
    if search:
        q = q.where(or_(Host.hostname.ilike(f"%{search}%"), Host.ip.ilike(f"%{search}%")))
    if online_only:
        q = q.where(Host.is_online == True)
    if group:
        q = q.join(host_group_assoc).join(HostGroup).where(HostGroup.name == group)
    if tag:
        q = q.join(host_tag_assoc).join(Tag).where(Tag.name == tag)
    q = q.order_by(Host.hostname)
    result = await db.execute(q)
    hosts = result.scalars().unique().all()
    return [_host_to_out(h) for h in hosts]


@router.get("/{host_id}", response_model=HostOut)
async def get_host(host_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Host).options(selectinload(Host.groups), selectinload(Host.tags)).where(Host.id == host_id)
    )
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Host not found")
    return _host_to_out(host)


@router.post("/", response_model=HostOut)
async def add_host(
    body: HostCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    existing = await db.execute(select(Host).where(Host.hostname == body.hostname))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Host with this hostname already exists")
    host = Host(hostname=body.hostname, ip=body.ip, os=body.os, os_version=body.os_version)
    if body.groups:
        host.groups = await _get_or_create_groups(db, body.groups)
    if body.tags:
        host.tags = await _get_or_create_tags(db, body.tags)
    db.add(host)
    await db.flush()
    await db.refresh(host, ["groups", "tags"])
    return _host_to_out(host)


@router.put("/{host_id}", response_model=HostOut)
async def update_host(
    host_id: int,
    body: HostUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    result = await db.execute(
        select(Host).options(selectinload(Host.groups), selectinload(Host.tags)).where(Host.id == host_id)
    )
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Host not found")
    if body.hostname is not None:
        host.hostname = body.hostname
    if body.ip is not None:
        host.ip = body.ip
    if body.os is not None:
        host.os = body.os
    if body.os_version is not None:
        host.os_version = body.os_version
    if body.groups is not None:
        host.groups = await _get_or_create_groups(db, body.groups)
    if body.tags is not None:
        host.tags = await _get_or_create_tags(db, body.tags)
    await db.flush()
    await db.refresh(host, ["groups", "tags"])
    return _host_to_out(host)


@router.delete("/{host_id}")
async def delete_host(
    host_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Host not found")
    await db.delete(host)
    return {"ok": True}


# ── Stats ──
@router.get("/stats/summary")
async def host_stats(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    total = await db.scalar(select(func.count(Host.id)))
    online = await db.scalar(select(func.count(Host.id)).where(Host.is_online == True))
    reboot = await db.scalar(select(func.count(Host.id)).where(Host.reboot_required == True))
    avg_compliance = await db.scalar(select(func.avg(Host.compliance_score))) or 0
    total_cves = await db.scalar(select(func.sum(Host.cve_count))) or 0
    total_upgradable = await db.scalar(select(func.sum(Host.upgradable_count))) or 0
    return {
        "total": total,
        "online": online,
        "offline": total - online,
        "reboot_required": reboot,
        "avg_compliance": round(avg_compliance, 1),
        "total_cves": total_cves,
        "total_upgradable": total_upgradable,
    }
