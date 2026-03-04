"""
PatchMaster — License validation module.
Validates signed license keys and checks expiry.
"""
import base64
import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

LICENSE_SIGN_KEY = os.getenv(
    "LICENSE_SIGN_KEY", "PatchMaster-License-SignKey-2026-Secure"
)
LICENSE_FILE = os.getenv(
    "LICENSE_FILE", os.path.join(os.getenv("INSTALL_DIR", "/opt/patchmaster"), "license.key")
)

# Cached license state
_cached_license: Optional[dict] = None
_cache_time: Optional[datetime] = None
_CACHE_TTL_SECONDS = 60  # Re-read file every 60s


class LicenseError(Exception):
    """Raised when the license is invalid or expired."""
    pass


def _verify_signature(payload_b64: str, signature: str) -> bool:
    """Verify HMAC-SHA256 signature."""
    expected = hmac.new(
        LICENSE_SIGN_KEY.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def decode_license(license_key: str) -> dict:
    """Decode and verify a license key string. Returns the payload dict."""
    if not license_key or not license_key.startswith("PM1-"):
        raise LicenseError("Invalid license key format")

    body = license_key[4:]  # strip PM1-
    if "." not in body:
        raise LicenseError("Invalid license key format")

    payload_b64, signature = body.rsplit(".", 1)

    # Verify signature
    if not _verify_signature(payload_b64, signature):
        raise LicenseError("License key signature verification failed")

    # Decode payload
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64_padded = payload_b64 + "=" * padding
    else:
        payload_b64_padded = payload_b64

    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64_padded))
    except Exception:
        raise LicenseError("License key payload is corrupted")

    # Validate required fields
    for field in ("plan", "customer", "issued_at", "expires_at"):
        if field not in payload:
            raise LicenseError(f"License key missing required field: {field}")

    return payload


def read_license_file() -> Optional[str]:
    """Read the license key from the license file."""
    path = Path(LICENSE_FILE)
    if path.is_file():
        content = path.read_text().strip()
        if content:
            return content
    return None


def get_license_info(force_refresh: bool = False) -> dict:
    """
    Get the current license status. Returns a dict with:
      - valid: bool
      - expired: bool
      - plan, customer, issued_at, expires_at, days_remaining, etc.
      - error: str (if invalid)
    """
    global _cached_license, _cache_time

    now = datetime.utcnow()

    # Use cache if fresh
    if (
        not force_refresh
        and _cached_license is not None
        and _cache_time is not None
        and (now - _cache_time).total_seconds() < _CACHE_TTL_SECONDS
    ):
        # Recheck expiry from cache
        info = _cached_license.copy()
        if info.get("valid") and info.get("expires_at_dt"):
            info["expired"] = now >= info["expires_at_dt"]
            info["days_remaining"] = max(0, (info["expires_at_dt"] - now).days)
        return info

    license_key = read_license_file()

    if not license_key:
        info = {
            "valid": False,
            "expired": False,
            "activated": False,
            "error": "No license key found. Activate a license to use PatchMaster.",
        }
        _cached_license = info
        _cache_time = now
        return info

    try:
        payload = decode_license(license_key)
    except LicenseError as e:
        info = {
            "valid": False,
            "expired": False,
            "activated": True,
            "error": str(e),
        }
        _cached_license = info
        _cache_time = now
        return info

    expires_at = datetime.strptime(payload["expires_at"], "%Y-%m-%dT%H:%M:%SZ")
    issued_at = datetime.strptime(payload["issued_at"], "%Y-%m-%dT%H:%M:%SZ")
    is_expired = now >= expires_at
    days_remaining = max(0, (expires_at - now).days)

    info = {
        "valid": True,
        "expired": is_expired,
        "activated": True,
        "plan": payload.get("plan", "unknown"),
        "plan_label": payload.get("plan_label", payload.get("plan", "Unknown")),
        "customer": payload.get("customer", "Unknown"),
        "issued_at": payload["issued_at"],
        "expires_at": payload["expires_at"],
        "expires_at_dt": expires_at,
        "issued_at_dt": issued_at,
        "days_remaining": days_remaining,
        "max_hosts": payload.get("max_hosts", 0),
    }

    _cached_license = info
    _cache_time = now
    return info


def invalidate_cache():
    """Force next call to re-read the license file."""
    global _cached_license, _cache_time
    _cached_license = None
    _cache_time = None


def is_license_active() -> bool:
    """Quick check: is the license valid and not expired?"""
    info = get_license_info()
    return info.get("valid", False) and not info.get("expired", True)
