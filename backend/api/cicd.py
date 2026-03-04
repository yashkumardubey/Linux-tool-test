"""CI/CD Pipeline API — Jenkins, GitLab, GitHub Actions webhook integration."""
import hashlib
import hmac
import secrets
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user, require_role
from models.db_models import CICDPipeline, CICDBuild

router = APIRouter(prefix="/api/cicd", tags=["cicd"])

# ── Pydantic schemas ──

class PipelineCreate(BaseModel):
    name: str
    description: str = ""
    tool: str  # jenkins, gitlab, github, custom
    server_url: str
    auth_type: str = "token"
    auth_credentials: dict = {}
    job_path: str = ""
    script_type: str = "groovy"
    script_content: str = ""
    trigger_events: list = []

class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    server_url: Optional[str] = None
    auth_type: Optional[str] = None
    auth_credentials: Optional[dict] = None
    job_path: Optional[str] = None
    script_type: Optional[str] = None
    script_content: Optional[str] = None
    trigger_events: Optional[list] = None
    status: Optional[str] = None

class PipelineOut(BaseModel):
    id: int
    name: str
    description: str
    tool: str
    server_url: str
    auth_type: str
    job_path: str
    script_type: str
    script_content: str
    webhook_secret: str
    webhook_url: str
    trigger_events: list
    status: str
    last_triggered: Optional[str]
    created_by: str
    created_at: str
    build_count: int = 0
    last_build_status: Optional[str] = None

class BuildOut(BaseModel):
    id: int
    pipeline_id: int
    pipeline_name: str
    build_number: int
    status: str
    trigger_type: str
    trigger_info: dict
    duration_seconds: Optional[int]
    output: str
    external_url: str
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str

class TriggerRequest(BaseModel):
    parameters: dict = {}


# ── Helpers ──

def _pipeline_to_dict(p: CICDPipeline, build_count: int = 0, last_status: str = None, base_url: str = "") -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "tool": p.tool,
        "server_url": p.server_url,
        "auth_type": p.auth_type,
        "job_path": p.job_path,
        "script_type": p.script_type,
        "script_content": p.script_content,
        "webhook_secret": p.webhook_secret,
        "webhook_url": f"{base_url}/api/cicd/webhook/{p.id}",
        "trigger_events": p.trigger_events or [],
        "status": p.status or "active",
        "last_triggered": p.last_triggered.isoformat() if p.last_triggered else None,
        "created_by": p.created_by or "",
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "build_count": build_count,
        "last_build_status": last_status,
    }


def _build_to_dict(b: CICDBuild, pipeline_name: str = "") -> dict:
    return {
        "id": b.id,
        "pipeline_id": b.pipeline_id,
        "pipeline_name": pipeline_name,
        "build_number": b.build_number,
        "status": b.status or "pending",
        "trigger_type": b.trigger_type or "manual",
        "trigger_info": b.trigger_info or {},
        "duration_seconds": b.duration_seconds,
        "output": b.output or "",
        "external_url": b.external_url or "",
        "started_at": b.started_at.isoformat() if b.started_at else None,
        "completed_at": b.completed_at.isoformat() if b.completed_at else None,
        "created_at": b.created_at.isoformat() if b.created_at else "",
    }


def _build_jenkins_headers(pipeline: CICDPipeline) -> dict:
    """Build auth headers for Jenkins API calls."""
    headers = {}
    creds = pipeline.auth_credentials or {}
    if pipeline.auth_type == "token" and creds.get("user") and creds.get("token"):
        import base64
        auth_str = f"{creds['user']}:{creds['token']}"
        headers["Authorization"] = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
    elif pipeline.auth_type == "basic" and creds.get("user") and creds.get("password"):
        import base64
        auth_str = f"{creds['user']}:{creds['password']}"
        headers["Authorization"] = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
    elif pipeline.auth_type == "token" and creds.get("token"):
        headers["Authorization"] = f"Bearer {creds['token']}"
    return headers


# ── Pipeline CRUD ──

@router.get("/pipelines")
async def list_pipelines(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all CI/CD pipelines with build stats."""
    result = await db.execute(select(CICDPipeline).order_by(CICDPipeline.created_at.desc()))
    pipelines = result.scalars().all()

    base_url = str(request.base_url).rstrip("/")
    out = []
    for p in pipelines:
        # Get build count and last status
        count_result = await db.execute(
            select(func.count(CICDBuild.id)).where(CICDBuild.pipeline_id == p.id)
        )
        build_count = count_result.scalar() or 0

        last_build = await db.execute(
            select(CICDBuild).where(CICDBuild.pipeline_id == p.id)
            .order_by(CICDBuild.created_at.desc()).limit(1)
        )
        lb = last_build.scalars().first()
        last_status = lb.status if lb else None

        out.append(_pipeline_to_dict(p, build_count, last_status, base_url))
    return out


@router.post("/pipelines", status_code=201)
async def create_pipeline(
    body: PipelineCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "operator")),
):
    """Create a new CI/CD pipeline."""
    if body.tool not in ("jenkins", "gitlab", "github", "custom"):
        raise HTTPException(400, "tool must be one of: jenkins, gitlab, github, custom")
    if body.script_type not in ("groovy", "yaml", "shell"):
        raise HTTPException(400, "script_type must be one of: groovy, yaml, shell")

    webhook_secret = secrets.token_hex(24)

    pipeline = CICDPipeline(
        name=body.name,
        description=body.description,
        tool=body.tool,
        server_url=body.server_url.rstrip("/"),
        auth_type=body.auth_type,
        auth_credentials=body.auth_credentials,
        job_path=body.job_path,
        script_type=body.script_type,
        script_content=body.script_content,
        webhook_secret=webhook_secret,
        trigger_events=body.trigger_events,
        status="active",
        created_by=user.username,
    )
    db.add(pipeline)
    await db.flush()
    await db.refresh(pipeline)

    base_url = str(request.base_url).rstrip("/")
    return _pipeline_to_dict(pipeline, 0, None, base_url)


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(
    pipeline_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get a single pipeline with details."""
    result = await db.execute(select(CICDPipeline).where(CICDPipeline.id == pipeline_id))
    pipeline = result.scalars().first()
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")

    count_result = await db.execute(
        select(func.count(CICDBuild.id)).where(CICDBuild.pipeline_id == pipeline_id)
    )
    build_count = count_result.scalar() or 0

    last_build = await db.execute(
        select(CICDBuild).where(CICDBuild.pipeline_id == pipeline_id)
        .order_by(CICDBuild.created_at.desc()).limit(1)
    )
    lb = last_build.scalars().first()

    base_url = str(request.base_url).rstrip("/")
    return _pipeline_to_dict(pipeline, build_count, lb.status if lb else None, base_url)


@router.put("/pipelines/{pipeline_id}")
async def update_pipeline(
    pipeline_id: int,
    body: PipelineUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "operator")),
):
    """Update a CI/CD pipeline."""
    result = await db.execute(select(CICDPipeline).where(CICDPipeline.id == pipeline_id))
    pipeline = result.scalars().first()
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")

    for field in ("name", "description", "server_url", "auth_type", "auth_credentials",
                  "job_path", "script_type", "script_content", "trigger_events", "status"):
        val = getattr(body, field, None)
        if val is not None:
            if field == "server_url":
                val = val.rstrip("/")
            setattr(pipeline, field, val)

    pipeline.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(pipeline)

    base_url = str(request.base_url).rstrip("/")
    return _pipeline_to_dict(pipeline, 0, None, base_url)


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Delete a pipeline and all its builds."""
    result = await db.execute(select(CICDPipeline).where(CICDPipeline.id == pipeline_id))
    pipeline = result.scalars().first()
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")
    await db.delete(pipeline)
    return {"ok": True}


# ── Trigger builds ──

@router.post("/pipelines/{pipeline_id}/trigger")
async def trigger_build(
    pipeline_id: int,
    body: TriggerRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "operator")),
):
    """Manually trigger a pipeline build via Jenkins/GitLab API."""
    result = await db.execute(select(CICDPipeline).where(CICDPipeline.id == pipeline_id))
    pipeline = result.scalars().first()
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")
    if pipeline.status != "active":
        raise HTTPException(400, "Pipeline is not active")

    # Get next build number
    max_num = await db.execute(
        select(func.coalesce(func.max(CICDBuild.build_number), 0))
        .where(CICDBuild.pipeline_id == pipeline_id)
    )
    next_num = (max_num.scalar() or 0) + 1

    build = CICDBuild(
        pipeline_id=pipeline_id,
        build_number=next_num,
        status="pending",
        trigger_type="manual",
        trigger_info={"triggered_by": user.username, "parameters": body.parameters},
        started_at=datetime.utcnow(),
    )
    db.add(build)
    pipeline.last_triggered = datetime.utcnow()
    await db.flush()
    await db.refresh(build)

    # Attempt to trigger remote CI system
    external_url = ""
    try:
        if pipeline.tool == "jenkins":
            external_url = await _trigger_jenkins(pipeline, body.parameters)
            build.status = "running"
            build.external_url = external_url
        elif pipeline.tool in ("gitlab", "github"):
            external_url = await _trigger_generic_webhook(pipeline, body.parameters)
            build.status = "running"
            build.external_url = external_url
        else:
            build.status = "running"
    except Exception as exc:
        build.status = "failed"
        build.output = f"Trigger failed: {str(exc)}"
        build.completed_at = datetime.utcnow()

    await db.flush()
    await db.refresh(build)
    return _build_to_dict(build, pipeline.name)


async def _trigger_jenkins(pipeline: CICDPipeline, params: dict) -> str:
    """Trigger a Jenkins job and return the build URL."""
    headers = _build_jenkins_headers(pipeline)
    job_path = pipeline.job_path.strip("/")
    base = pipeline.server_url

    # Jenkins build URL — with or without parameters
    if params:
        url = f"{base}/job/{job_path}/buildWithParameters"
    else:
        url = f"{base}/job/{job_path}/build"

    # Get crumb for CSRF protection
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            crumb_resp = await client.get(f"{base}/crumbIssuer/api/json", headers=headers)
            if crumb_resp.status_code == 200:
                crumb_data = crumb_resp.json()
                headers[crumb_data["crumbRequestField"]] = crumb_data["crumb"]
    except Exception:
        pass  # Some Jenkins instances don't require crumbs

    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        resp = await client.post(url, headers=headers, data=params if params else None)
        if resp.status_code not in (200, 201, 302):
            raise Exception(f"Jenkins returned HTTP {resp.status_code}: {resp.text[:200]}")
        # Return the queue/build URL
        location = resp.headers.get("Location", "")
        if location:
            return location
        return f"{base}/job/{job_path}/"


async def _trigger_generic_webhook(pipeline: CICDPipeline, params: dict) -> str:
    """Trigger via generic webhook POST."""
    headers = _build_jenkins_headers(pipeline)
    headers["Content-Type"] = "application/json"
    import json
    payload = {
        "ref": params.get("branch", "main"),
        "variables": params,
    }
    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        resp = await client.post(pipeline.server_url, headers=headers, json=payload)
        if resp.status_code not in (200, 201, 202):
            raise Exception(f"Webhook returned HTTP {resp.status_code}: {resp.text[:200]}")
    return pipeline.server_url


# ── Build history ──

@router.get("/builds")
async def list_builds(
    pipeline_id: int = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List builds, optionally filtered by pipeline."""
    q = select(CICDBuild).order_by(CICDBuild.created_at.desc()).limit(min(limit, 200))
    if pipeline_id:
        q = q.where(CICDBuild.pipeline_id == pipeline_id)

    result = await db.execute(q)
    builds = result.scalars().all()

    # Get pipeline names
    pipe_ids = {b.pipeline_id for b in builds}
    names = {}
    if pipe_ids:
        pr = await db.execute(select(CICDPipeline).where(CICDPipeline.id.in_(pipe_ids)))
        for p in pr.scalars().all():
            names[p.id] = p.name

    return [_build_to_dict(b, names.get(b.pipeline_id, "")) for b in builds]


@router.get("/builds/{build_id}")
async def get_build(
    build_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await db.execute(select(CICDBuild).where(CICDBuild.id == build_id))
    build = result.scalars().first()
    if not build:
        raise HTTPException(404, "Build not found")
    pr = await db.execute(select(CICDPipeline).where(CICDPipeline.id == build.pipeline_id))
    pipe = pr.scalars().first()
    return _build_to_dict(build, pipe.name if pipe else "")


# ── Incoming webhook (from Jenkins / GitLab / GitHub) ──

@router.post("/webhook/{pipeline_id}")
async def receive_webhook(
    pipeline_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive webhook callback from Jenkins/GitLab/GitHub.
    Validates signature if webhook_secret is set.
    Creates or updates a build record.
    """
    result = await db.execute(select(CICDPipeline).where(CICDPipeline.id == pipeline_id))
    pipeline = result.scalars().first()
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")

    body_bytes = await request.body()
    body_text = body_bytes.decode("utf-8", errors="replace")

    # Validate webhook signature if secret is set
    if pipeline.webhook_secret:
        # Check for Jenkins, GitLab, or GitHub signature headers
        sig_header = (
            request.headers.get("X-Hub-Signature-256")       # GitHub
            or request.headers.get("X-Gitlab-Token")          # GitLab
            or request.headers.get("X-Jenkins-Signature")     # Jenkins custom
        )
        if sig_header:
            if sig_header.startswith("sha256="):
                # GitHub-style HMAC
                expected = "sha256=" + hmac.new(
                    pipeline.webhook_secret.encode(), body_bytes, hashlib.sha256
                ).hexdigest()
                if not hmac.compare_digest(sig_header, expected):
                    raise HTTPException(403, "Invalid webhook signature")
            elif sig_header == pipeline.webhook_secret:
                pass  # GitLab token match
            else:
                raise HTTPException(403, "Invalid webhook signature")

    # Parse payload
    try:
        import json
        payload = json.loads(body_text)
    except Exception:
        payload = {"raw": body_text[:2000]}

    # Determine build status from payload
    build_status = "success"
    build_number = 0
    external_url = ""
    output = ""

    # Jenkins payload
    if "build" in payload:
        b = payload["build"]
        jenkins_status = b.get("status", b.get("phase", ""))
        if jenkins_status in ("SUCCESS", "COMPLETED"):
            build_status = "success"
        elif jenkins_status in ("FAILURE", "FAILED"):
            build_status = "failed"
        elif jenkins_status in ("STARTED", "RUNNING"):
            build_status = "running"
        elif jenkins_status in ("ABORTED",):
            build_status = "aborted"
        else:
            build_status = "running"
        build_number = b.get("number", 0)
        external_url = b.get("full_url", b.get("url", ""))
        output = f"Jenkins build #{build_number} — {jenkins_status}"

    # GitHub Actions payload
    elif "workflow_run" in payload:
        wr = payload["workflow_run"]
        conclusion = wr.get("conclusion", "")
        if conclusion == "success":
            build_status = "success"
        elif conclusion == "failure":
            build_status = "failed"
        elif conclusion == "cancelled":
            build_status = "aborted"
        else:
            build_status = "running"
        build_number = wr.get("run_number", 0)
        external_url = wr.get("html_url", "")
        output = f"GitHub Actions run #{build_number} — {conclusion or 'in_progress'}"

    # GitLab pipeline payload
    elif "object_attributes" in payload and "pipeline" in payload.get("object_kind", ""):
        oa = payload["object_attributes"]
        gl_status = oa.get("status", "")
        if gl_status == "success":
            build_status = "success"
        elif gl_status == "failed":
            build_status = "failed"
        elif gl_status == "canceled":
            build_status = "aborted"
        else:
            build_status = "running"
        build_number = oa.get("id", 0)
        external_url = oa.get("url", "")
        output = f"GitLab pipeline #{build_number} — {gl_status}"

    else:
        output = f"Webhook received: {body_text[:500]}"

    # Check if we already have a build with this number
    existing = None
    if build_number:
        er = await db.execute(
            select(CICDBuild).where(
                CICDBuild.pipeline_id == pipeline_id,
                CICDBuild.build_number == build_number,
            )
        )
        existing = er.scalars().first()

    now = datetime.utcnow()
    if existing:
        existing.status = build_status
        existing.output = output
        existing.external_url = external_url or existing.external_url
        if build_status in ("success", "failed", "aborted"):
            existing.completed_at = now
            if existing.started_at:
                existing.duration_seconds = int((now - existing.started_at).total_seconds())
        elif build_status == "running" and not existing.started_at:
            existing.started_at = now
        build_record = existing
    else:
        max_num = await db.execute(
            select(func.coalesce(func.max(CICDBuild.build_number), 0))
            .where(CICDBuild.pipeline_id == pipeline_id)
        )
        fallback_num = (max_num.scalar() or 0) + 1
        build_record = CICDBuild(
            pipeline_id=pipeline_id,
            build_number=build_number or fallback_num,
            status=build_status,
            trigger_type="webhook",
            trigger_info={"source": pipeline.tool, "headers": dict(request.headers)},
            output=output,
            external_url=external_url,
            started_at=now if build_status == "running" else None,
            completed_at=now if build_status in ("success", "failed", "aborted") else None,
        )
        db.add(build_record)

    pipeline.last_triggered = now
    await db.flush()
    return {"ok": True, "build_status": build_status}


# ── Test connection ──

@router.post("/pipelines/{pipeline_id}/test")
async def test_connection(
    pipeline_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "operator")),
):
    """Test connectivity to the CI/CD server."""
    result = await db.execute(select(CICDPipeline).where(CICDPipeline.id == pipeline_id))
    pipeline = result.scalars().first()
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")

    try:
        headers = _build_jenkins_headers(pipeline)
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            if pipeline.tool == "jenkins":
                url = f"{pipeline.server_url}/api/json"
            else:
                url = pipeline.server_url
            resp = await client.get(url, headers=headers)
            return {
                "ok": resp.status_code < 400,
                "status_code": resp.status_code,
                "message": f"Connected — HTTP {resp.status_code}",
            }
    except Exception as e:
        return {"ok": False, "status_code": 0, "message": f"Connection failed: {str(e)}"}


# ── Script templates ──

@router.get("/templates")
async def get_script_templates(user=Depends(get_current_user)):
    """Return starter pipeline script templates."""
    return {
        "groovy": {
            "label": "Jenkins Declarative Pipeline (Groovy)",
            "content": """pipeline {
    agent any
    environment {
        PATCHMASTER_URL = 'http://YOUR_SERVER:8000'
    }
    stages {
        stage('Pre-Patch Check') {
            steps {
                sh '''
                    curl -s $PATCHMASTER_URL/api/health
                    echo "PatchMaster is reachable"
                '''
            }
        }
        stage('Run Patches') {
            steps {
                sh '''
                    curl -s -X POST $PATCHMASTER_URL/api/jobs/ \\
                        -H "Authorization: Bearer $PM_TOKEN" \\
                        -H "Content-Type: application/json" \\
                        -d '{"host_id": 1, "action": "upgrade", "dry_run": false}'
                '''
            }
        }
        stage('Verify') {
            steps {
                sh '''
                    curl -s $PATCHMASTER_URL/api/compliance/ \\
                        -H "Authorization: Bearer $PM_TOKEN"
                '''
            }
        }
    }
    post {
        success {
            echo 'Patch pipeline completed successfully!'
        }
        failure {
            echo 'Patch pipeline failed — check PatchMaster logs.'
        }
    }
}""",
        },
        "yaml": {
            "label": "GitLab CI / GitHub Actions (YAML)",
            "content": """# GitLab CI / GitHub Actions Pipeline
name: PatchMaster CI/CD

on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * SAT'  # Every Saturday at 2 AM

env:
  PATCHMASTER_URL: http://YOUR_SERVER:8000
  PM_TOKEN: ${{ secrets.PATCHMASTER_TOKEN }}

jobs:
  patch-management:
    runs-on: ubuntu-latest
    steps:
      - name: Health Check
        run: |
          curl -sf $PATCHMASTER_URL/api/health
          echo "PatchMaster is reachable"

      - name: Pre-Patch Snapshot
        run: |
          curl -s -X POST $PATCHMASTER_URL/api/jobs/ \\
            -H "Authorization: Bearer $PM_TOKEN" \\
            -H "Content-Type: application/json" \\
            -d '{"host_id": 1, "action": "snapshot"}'

      - name: Execute Patches
        run: |
          curl -s -X POST $PATCHMASTER_URL/api/jobs/ \\
            -H "Authorization: Bearer $PM_TOKEN" \\
            -H "Content-Type: application/json" \\
            -d '{"host_id": 1, "action": "upgrade", "auto_snapshot": true}'

      - name: Compliance Report
        run: |
          curl -s $PATCHMASTER_URL/api/compliance/ \\
            -H "Authorization: Bearer $PM_TOKEN" | jq .
""",
        },
        "shell": {
            "label": "Shell Script",
            "content": """#!/bin/bash
# PatchMaster CI/CD Shell Script
set -euo pipefail

PATCHMASTER_URL="${PATCHMASTER_URL:-http://localhost:8000}"
PM_TOKEN="${PM_TOKEN:-}"

echo "=== PatchMaster CI/CD Pipeline ==="
echo "Server: $PATCHMASTER_URL"
echo "Time: $(date -u)"

# Health check
echo "--- Health Check ---"
curl -sf "$PATCHMASTER_URL/api/health" || { echo "FAIL: PatchMaster unreachable"; exit 1; }

# Pre-patch snapshot
echo "--- Creating Snapshot ---"
curl -s -X POST "$PATCHMASTER_URL/api/jobs/" \\
    -H "Authorization: Bearer $PM_TOKEN" \\
    -H "Content-Type: application/json" \\
    -d '{"host_id": 1, "action": "snapshot"}' | jq .

# Execute patches
echo "--- Executing Patches ---"
curl -s -X POST "$PATCHMASTER_URL/api/jobs/" \\
    -H "Authorization: Bearer $PM_TOKEN" \\
    -H "Content-Type: application/json" \\
    -d '{"host_id": 1, "action": "upgrade", "auto_snapshot": true, "auto_rollback": true}' | jq .

# Check compliance
echo "--- Compliance Check ---"
curl -s "$PATCHMASTER_URL/api/compliance/" \\
    -H "Authorization: Bearer $PM_TOKEN" | jq .

echo "=== Pipeline Complete ==="
""",
        },
    }
