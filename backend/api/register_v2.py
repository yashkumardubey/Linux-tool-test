"""Agent registration & heartbeat — persisted to PostgreSQL."""
from datetime import datetime
from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from database import get_db
from models.db_models import Host

router = APIRouter(tags=["agent"])


class RegisterRequest(BaseModel):
    hostname: str
    os: str
    os_version: str
    kernel: str
    arch: str
    ip: str


def _clean_ip(ip: str) -> str:
    return ip.split("/")[0].strip() if ip else ""


@router.post("/api/register")
async def register_agent(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    agent_token = str(uuid4())
    clean_ip = _clean_ip(req.ip)

    # Find by hostname first
    result = await db.execute(select(Host).where(Host.hostname == req.hostname))
    host = result.scalar_one_or_none()

    if host:
        host.ip = clean_ip
        host.os = req.os
        host.os_version = req.os_version
        host.kernel = req.kernel
        host.arch = req.arch
        host.agent_token = agent_token
        host.is_online = True
        host.last_heartbeat = datetime.utcnow()
    else:
        # Check by IP
        result = await db.execute(select(Host).where(Host.ip == clean_ip))
        host = result.scalar_one_or_none()
        if host:
            host.hostname = req.hostname
            host.os = req.os
            host.os_version = req.os_version
            host.kernel = req.kernel
            host.arch = req.arch
            host.agent_token = agent_token
            host.is_online = True
            host.last_heartbeat = datetime.utcnow()
        else:
            host = Host(
                hostname=req.hostname,
                ip=clean_ip,
                os=req.os,
                os_version=req.os_version,
                kernel=req.kernel,
                arch=req.arch,
                agent_token=agent_token,
                is_online=True,
                last_heartbeat=datetime.utcnow(),
            )
            db.add(host)

    await db.flush()
    return {"agent_token": agent_token}


@router.post("/api/heartbeat")
async def heartbeat(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    ip = _clean_ip(body.get("ip", ""))
    hostname = body.get("hostname", "")
    os_name = body.get("os", "")
    os_version = body.get("os_version", "")
    kernel = body.get("kernel", "")
    arch = body.get("arch", "")

    host = None
    if hostname:
        result = await db.execute(select(Host).where(Host.hostname == hostname))
        host = result.scalar_one_or_none()

    if not host and ip:
        result = await db.execute(select(Host).where(Host.ip == ip))
        host = result.scalar_one_or_none()

    if host:
        host.ip = ip or host.ip
        host.hostname = hostname or host.hostname
        host.os = os_name or host.os
        host.os_version = os_version or host.os_version
        host.kernel = kernel or host.kernel
        host.arch = arch or host.arch
        host.is_online = True
        host.last_heartbeat = datetime.utcnow()
    elif ip:
        host = Host(
            hostname=hostname,
            ip=ip,
            os=os_name,
            os_version=os_version,
            kernel=kernel,
            arch=arch,
            is_online=True,
            last_heartbeat=datetime.utcnow(),
        )
        db.add(host)

    return {"status": "ok"}
