from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# In-memory DB for demo
jobs_db = []

class Job(BaseModel):
    id: int
    name: str
    status: str
    scheduled_time: str

@router.get("/", response_model=List[Job])
def list_jobs():
    return jobs_db

@router.post("/", response_model=Job)
def add_job(job: Job):
    jobs_db.append(job)
    return job

@router.delete("/{job_id}")
def delete_job(job_id: int):
    global jobs_db
    jobs_db = [j for j in jobs_db if j.id != job_id]
    return {"ok": True}

@router.put("/{job_id}", response_model=Job)
def update_job(job_id: int, job: Job):
    for i, j in enumerate(jobs_db):
        if j.id == job_id:
            jobs_db[i] = job
            return job
    raise HTTPException(status_code=404, detail="Job not found")
