"""Patch Jobs API — tracks all patch operations in PostgreSQL."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional

from database import get_db
from auth import get_current_user, require_role
from models.db_models import PatchJob, Host, JobStatus, PatchAction, UserRole, User

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobOut(BaseModel):
    id: int
    host_id: int
    host_name: str = ""
    host_ip: str = ""
    action: str
    status: str
    packages: list = []
    dry_run: bool
    auto_snapshot: bool
    auto_rollback: bool
    result: Optional[dict] = None
    output: str = ""
    initiated_by: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class JobCreate(BaseModel):
    host_id: int
    action: str = "server_patch"
    packages: List[str] = []
    hold_packages: List[str] = []
    dry_run: bool = False
    auto_snapshot: bool = True
    auto_rollback: bool = True


def _job_to_out(job: PatchJob) -> dict:
    d = {c.name: getattr(job, c.name) for c in job.__table__.columns}
    d["action"] = job.action.value if job.action else ""
    d["status"] = job.status.value if job.status else ""
    d["host_name"] = job.host.hostname if job.host else ""
    d["host_ip"] = job.host.ip if job.host else ""
    return d


@router.get("/", response_model=List[JobOut])
async def list_jobs(
    status: Optional[str] = None,
    host_id: Optional[int] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(PatchJob).options(selectinload(PatchJob.host)).order_by(desc(PatchJob.created_at))
    if status:
        q = q.where(PatchJob.status == JobStatus(status))
    if host_id:
        q = q.where(PatchJob.host_id == host_id)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return [_job_to_out(j) for j in result.scalars().all()]


@router.get("/stats")
async def job_stats(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    total = await db.scalar(select(func.count(PatchJob.id)))
    running = await db.scalar(select(func.count(PatchJob.id)).where(PatchJob.status == JobStatus.running))
    success = await db.scalar(select(func.count(PatchJob.id)).where(PatchJob.status == JobStatus.success))
    failed = await db.scalar(select(func.count(PatchJob.id)).where(PatchJob.status == JobStatus.failed))
    pending = await db.scalar(select(func.count(PatchJob.id)).where(PatchJob.status == JobStatus.pending))
    rolled_back = await db.scalar(select(func.count(PatchJob.id)).where(PatchJob.status == JobStatus.rolled_back))
    return {
        "total": total,
        "running": running,
        "success": success,
        "failed": failed,
        "pending": pending,
        "rolled_back": rolled_back,
    }


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(PatchJob).options(selectinload(PatchJob.host)).where(PatchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_to_out(job)


@router.post("/", response_model=JobOut)
async def create_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    # Validate host exists
    result = await db.execute(select(Host).where(Host.id == body.host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Host not found")

    job = PatchJob(
        host_id=body.host_id,
        action=PatchAction(body.action),
        status=JobStatus.pending,
        packages=body.packages,
        hold_packages=body.hold_packages,
        dry_run=body.dry_run,
        auto_snapshot=body.auto_snapshot,
        auto_rollback=body.auto_rollback,
        initiated_by=user.username,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    # Eagerly load host
    result = await db.execute(select(PatchJob).options(selectinload(PatchJob.host)).where(PatchJob.id == job.id))
    job = result.scalar_one()
    return _job_to_out(job)


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(PatchJob).where(PatchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    await db.delete(job)
    return {"ok": True}
