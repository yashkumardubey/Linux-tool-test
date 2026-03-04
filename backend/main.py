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
from api.metrics import router as metrics_router, MetricsMiddleware
from api.zabbix import router as zabbix_router
from api.license_router import router as license_router
from license import get_license_info


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="PatchMaster", version="2.0.0", lifespan=lifespan)

# ── License enforcement middleware ──
# Blocks all API requests (except license & health endpoints) when license is
# missing or expired.
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class LicenseMiddleware(BaseHTTPMiddleware):
    # Paths that work without a valid license
    EXEMPT_PATHS = (
        "/api/health",
        "/api/license/",
        "/api/auth/login",
        "/api/auth/register",
        "/docs",
        "/openapi.json",
        "/static/",
        "/metrics",
    )

    async def dispatch(self, request, call_next):
        path = request.url.path
        # Allow exempt paths
        if any(path.startswith(p) for p in self.EXEMPT_PATHS):
            return await call_next(request)
        # Check license
        info = get_license_info()
        if not info.get("activated", False):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "No license activated. Please activate a license to use PatchMaster.",
                    "license_status": "not_activated",
                },
            )
        if info.get("expired", True):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"License expired on {info.get('expires_at', 'unknown')}. Please renew.",
                    "license_status": "expired",
                },
            )
        return await call_next(request)


app.add_middleware(LicenseMiddleware)

# Prometheus request metrics middleware
app.add_middleware(MetricsMiddleware)

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
# Prometheus metrics
app.include_router(metrics_router)
# Zabbix integration
app.include_router(zabbix_router)
# License management
app.include_router(license_router)
