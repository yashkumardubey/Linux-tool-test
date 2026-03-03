from fastapi import APIRouter, Request
from pydantic import BaseModel
from uuid import uuid4
from api.hosts import hosts_db, Host

router = APIRouter()

class RegisterRequest(BaseModel):
    hostname: str
    os: str
    os_version: str
    kernel: str
    arch: str
    ip: str

def _clean_ip(ip: str) -> str:
    """Strip CIDR suffix and whitespace."""
    return ip.split('/')[0].strip() if ip else ""


def _find_host_by_hostname(hostname: str):
    """Find existing host by hostname."""
    for h in hosts_db:
        if h.name == hostname:
            return h
    return None


@router.post("/api/register")
async def register_agent(req: RegisterRequest):
    agent_token = str(uuid4())
    clean_ip = _clean_ip(req.ip)
    os_info = f"{req.os} {req.os_version}".strip()
    # Check if host already exists by hostname — update IP/OS if so
    existing = _find_host_by_hostname(req.hostname)
    if existing:
        existing.ip = clean_ip
        existing.os = os_info
    else:
        # Also check by IP
        existing_ips = {h.ip for h in hosts_db}
        if clean_ip not in existing_ips:
            next_id = max((h.id for h in hosts_db), default=0) + 1
            host = Host(id=next_id, name=req.hostname, ip=clean_ip, os=os_info)
            hosts_db.append(host)
    return {"agent_token": agent_token}


@router.post("/api/heartbeat")
async def heartbeat(request: Request):
    body = await request.json()
    ip = _clean_ip(body.get("ip", ""))
    hostname = body.get("hostname", "")
    os_info = f"{body.get('os', '')} {body.get('os_version', '')}".strip()
    # Check by hostname first, then IP
    existing = _find_host_by_hostname(hostname) if hostname else None
    if existing:
        existing.ip = ip
        if os_info:
            existing.os = os_info
    else:
        existing_ips = {h.ip for h in hosts_db}
        if ip and ip not in existing_ips:
            next_id = max((h.id for h in hosts_db), default=0) + 1
            host = Host(id=next_id, name=hostname, ip=ip, os=os_info)
            hosts_db.append(host)
        else:
            for h in hosts_db:
                if h.ip == ip:
                    h.name = hostname or h.name
                    if os_info:
                        h.os = os_info
    return {"status": "ok"}
