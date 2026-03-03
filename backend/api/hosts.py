from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/hosts", tags=["hosts"])

# In-memory DB for demo
hosts_db = []

class Host(BaseModel):
    id: int
    name: str
    ip: str
    os: str

@router.get("/", response_model=List[Host])
def list_hosts():
    return hosts_db

@router.post("/", response_model=Host)
def add_host(host: Host):
    hosts_db.append(host)
    return host

@router.delete("/{host_id}")
def delete_host(host_id: int):
    global hosts_db
    hosts_db = [h for h in hosts_db if h.id != host_id]
    return {"ok": True}

@router.put("/{host_id}", response_model=Host)
def update_host(host_id: int, host: Host):
    for i, h in enumerate(hosts_db):
        if h.id == host_id:
            hosts_db[i] = host
            return host
    raise HTTPException(status_code=404, detail="Host not found")
