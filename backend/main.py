import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from api.auth_api import router as auth_router
from api.register_v2 import router as register_router
from api.hosts_v2 import router as hosts_router
from api.jobs_v2 import router as jobs_router
from api.agent_proxy import router as agent_proxy_router
from api.groups import router as groups_router, tags_router
from api.schedules import router as schedules_router
from api.audit import router as audit_router
from api.compliance import router as compliance_router
from api.cve import router as cve_router
from api.notifications import router as notifications_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="PatchMaster", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (for agent .deb download)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Auth & Users
app.include_router(auth_router)
# Agent registration & heartbeat
app.include_router(register_router)
# Host management
app.include_router(hosts_router)
# Patch jobs
app.include_router(jobs_router)
# Agent proxy (forward commands to agents)
app.include_router(agent_proxy_router)
# Host groups & tags
app.include_router(groups_router)
app.include_router(tags_router)
# Patch scheduling
app.include_router(schedules_router)
# Audit trail
app.include_router(audit_router)
# Compliance dashboard
app.include_router(compliance_router)
# CVE tracking
app.include_router(cve_router)
# Notifications
app.include_router(notifications_router)
