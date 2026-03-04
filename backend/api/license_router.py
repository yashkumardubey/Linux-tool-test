"""License management API — view status, activate, deactivate, tier info."""
import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from auth import get_current_user, require_role
from models.db_models import UserRole
from license import (
    get_license_info,
    decode_license,
    invalidate_cache,
    LicenseError,
    LICENSE_FILE,
    TIER_FEATURES,
    TIER_LABELS,
    ALL_FEATURES,
)

router = APIRouter(prefix="/api/license", tags=["License"])


class ActivateRequest(BaseModel):
    license_key: str


class LicenseResponse(BaseModel):
    valid: bool
    expired: bool
    activated: bool
    plan: str = ""
    plan_label: str = ""
    customer: str = ""
    issued_at: str = ""
    expires_at: str = ""
    days_remaining: int = 0
    max_hosts: int = 0
    tier: str = ""
    tier_label: str = ""
    features: List[str] = []
    license_id: str = ""
    version_compat: str = ""
    tool_version: str = ""
    error: str = ""


@router.get("/status", response_model=LicenseResponse)
async def license_status():
    """Get current license status. No auth required — frontend needs this."""
    info = get_license_info(force_refresh=True)
    return LicenseResponse(
        valid=info.get("valid", False),
        expired=info.get("expired", False),
        activated=info.get("activated", False),
        plan=info.get("plan", ""),
        plan_label=info.get("plan_label", ""),
        customer=info.get("customer", ""),
        issued_at=info.get("issued_at", ""),
        expires_at=info.get("expires_at", ""),
        days_remaining=info.get("days_remaining", 0),
        max_hosts=info.get("max_hosts", 0),
        tier=info.get("tier", ""),
        tier_label=info.get("tier_label", ""),
        features=info.get("features", []),
        license_id=info.get("license_id", ""),
        version_compat=info.get("version_compat", ""),
        tool_version=info.get("tool_version", ""),
        error=info.get("error", ""),
    )


@router.post("/activate", response_model=LicenseResponse)
async def activate_license(req: ActivateRequest, user=Depends(require_role(UserRole.admin))):

    key = req.license_key.strip()
    if not key:
        raise HTTPException(400, "License key cannot be empty")

    # Validate before saving
    try:
        payload = decode_license(key)
    except LicenseError as e:
        raise HTTPException(400, f"Invalid license key: {e}")

    # Write to file
    license_path = Path(LICENSE_FILE)
    license_path.parent.mkdir(parents=True, exist_ok=True)
    license_path.write_text(key)

    # Clear cache
    invalidate_cache()

    info = get_license_info(force_refresh=True)
    return LicenseResponse(
        valid=info.get("valid", False),
        expired=info.get("expired", False),
        activated=info.get("activated", False),
        plan=info.get("plan", ""),
        plan_label=info.get("plan_label", ""),
        customer=info.get("customer", ""),
        issued_at=info.get("issued_at", ""),
        expires_at=info.get("expires_at", ""),
        days_remaining=info.get("days_remaining", 0),
        max_hosts=info.get("max_hosts", 0),
        tier=info.get("tier", ""),
        tier_label=info.get("tier_label", ""),
        features=info.get("features", []),
        license_id=info.get("license_id", ""),
        version_compat=info.get("version_compat", ""),
        tool_version=info.get("tool_version", ""),
        error=info.get("error", ""),
    )


@router.delete("/deactivate")
async def deactivate_license(user=Depends(require_role(UserRole.admin))):

    license_path = Path(LICENSE_FILE)
    if license_path.is_file():
        license_path.unlink()

    invalidate_cache()
    return {"detail": "License deactivated"}


@router.get("/tiers")
async def list_tiers():
    """Return all tier definitions and their features (public, no auth)."""
    tiers = []
    for key in ("basic", "standard", "devops", "enterprise"):
        tiers.append({
            "tier": key,
            "label": TIER_LABELS.get(key, key.title()),
            "features": TIER_FEATURES.get(key, []),
            "feature_count": len(TIER_FEATURES.get(key, [])),
        })
    return {"tiers": tiers, "all_features": ALL_FEATURES}
