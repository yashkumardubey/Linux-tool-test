"""Monitoring API — service status, enforcement, install/start/stop."""
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user, require_role
from models.db_models import User, UserRole
from license import get_license_info
import monitoring_manager as mm

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])


@router.get("/status")
async def monitoring_status(user: User = Depends(get_current_user)):
    """Get monitoring service status + license feature check."""
    info = get_license_info()
    features = info.get("features", [])
    has_monitoring = "monitoring" in features
    tier = info.get("tier", "")
    tier_label = info.get("tier_label", "")

    services = mm.get_status()

    return {
        "licensed": has_monitoring,
        "tier": tier,
        "tier_label": tier_label,
        "min_tier": "standard",
        "services": services,
    }


@router.post("/enforce")
async def enforce_monitoring(user=Depends(require_role(UserRole.admin))):
    """Enforce monitoring services based on current license.
    - Licensed (standard+): install if needed, start all.
    - Not licensed (basic): stop all monitoring services.
    """
    info = get_license_info(force_refresh=True)
    features = info.get("features", [])
    result = mm.enforce_license(features)
    has_monitoring = "monitoring" in features
    return {
        "licensed": has_monitoring,
        "tier": info.get("tier", ""),
        "action": "started" if has_monitoring else "stopped",
        "services": result,
    }


@router.post("/install")
async def install_monitoring(user=Depends(require_role(UserRole.admin))):
    """Install all monitoring services (requires standard+ license)."""
    info = get_license_info()
    if "monitoring" not in info.get("features", []):
        raise HTTPException(
            403,
            "Monitoring requires Standard tier or above. Upgrade your license."
        )
    result = mm.install_services("all")
    return {"action": "install", "result": result}


@router.post("/start")
async def start_monitoring(user=Depends(require_role(UserRole.admin))):
    """Start all monitoring services (requires standard+ license)."""
    info = get_license_info()
    if "monitoring" not in info.get("features", []):
        raise HTTPException(
            403,
            "Monitoring requires Standard tier or above. Upgrade your license."
        )
    result = mm.start_services("all")
    return {"action": "start", "result": result}


@router.post("/stop")
async def stop_monitoring(user=Depends(require_role(UserRole.admin))):
    """Stop all monitoring services."""
    result = mm.stop_services("all")
    return {"action": "stop", "result": result}
