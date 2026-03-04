#!/usr/bin/env python3
"""
PatchMaster — License Key Generator (v2)
Generates tier-based, version-compatible license keys.

License Tiers:
  basic      — Patching + basic monitoring
  standard   — Basic + advanced monitoring, compliance, CVE, audit
  devops     — Standard + CI/CD, Git integration
  enterprise — All features enabled

Duration Plans:
  testing — 30 days (all features unlocked for evaluation)
  1-year  — 365 days
  2-year  — 730 days
  5-year  — 1825 days

Usage:
    python generate-license.py --tier standard --plan 1-year --customer "Acme Corp"
    python generate-license.py --tier enterprise --plan 5-year --customer "Big Corp"
    python generate-license.py --tier basic --plan 1-year --customer "Small Co" --max-hosts 50
    python generate-license.py --plan testing --customer "Demo User"
"""
import argparse
import base64
import hashlib
import hmac
import json
import sys
import uuid
from datetime import datetime, timedelta

DEFAULT_SIGN_KEY = "PatchMaster-License-SignKey-2026-Secure"

PLANS = {
    "testing": {"days": 30,   "label": "Testing (1 Month)"},
    "1-year":  {"days": 365,  "label": "1 Year"},
    "2-year":  {"days": 730,  "label": "2 Years"},
    "5-year":  {"days": 1825, "label": "5 Years"},
}

TIERS = {
    "basic": {
        "label": "Basic",
        "description": "Patching + Basic Monitoring",
        "features": [
            "dashboard", "hosts", "groups", "patches", "snapshots",
            "compare", "offline", "schedules", "jobs", "onboarding",
        ],
    },
    "standard": {
        "label": "Standard",
        "description": "Basic + Advanced Monitoring, Compliance, CVE, Audit",
        "features": [
            "dashboard", "hosts", "groups", "patches", "snapshots",
            "compare", "offline", "schedules", "jobs", "onboarding",
            "compliance", "cve", "audit", "notifications", "users",
            "monitoring",
        ],
    },
    "devops": {
        "label": "DevOps",
        "description": "Standard + CI/CD Pipelines, Git Integration",
        "features": [
            "dashboard", "hosts", "groups", "patches", "snapshots",
            "compare", "offline", "schedules", "jobs", "onboarding",
            "compliance", "cve", "audit", "notifications", "users",
            "cicd", "git", "monitoring",
        ],
    },
    "enterprise": {
        "label": "Enterprise",
        "description": "All Features Enabled",
        "features": [
            "dashboard", "compliance", "hosts", "groups", "patches", "snapshots",
            "compare", "offline", "schedules", "cve", "jobs", "audit",
            "notifications", "users", "license", "cicd", "git", "onboarding",
            "settings", "monitoring",
        ],
    },
}

TOOL_VERSION = "2.0"
VERSION_COMPAT = "2.x"


def generate_license(tier: str, plan: str, customer: str, sign_key: str, max_hosts: int = 0) -> str:
    """Generate a signed license key with tier and version info."""
    if plan not in PLANS:
        print(f"Error: Invalid plan '{plan}'. Choose: {', '.join(PLANS.keys())}")
        sys.exit(1)

    effective_tier = "enterprise" if plan == "testing" else tier
    if effective_tier not in TIERS:
        print(f"Error: Invalid tier '{effective_tier}'. Choose: {', '.join(TIERS.keys())}")
        sys.exit(1)

    now = datetime.utcnow()
    expires = now + timedelta(days=PLANS[plan]["days"])

    payload = {
        "v": 2,
        "license_id": str(uuid.uuid4())[:8],
        "tier": effective_tier,
        "tier_label": TIERS[effective_tier]["label"],
        "features": TIERS[effective_tier]["features"],
        "plan": plan,
        "plan_label": f"{TIERS[effective_tier]['label']} ({PLANS[plan]['label']})",
        "customer": customer,
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_hosts": max_hosts,
        "version_compat": VERSION_COMPAT,
        "tool_version": TOOL_VERSION,
    }

    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode().rstrip("=")

    signature = hmac.new(
        sign_key.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()

    return f"PM1-{payload_b64}.{signature}"


def main():
    parser = argparse.ArgumentParser(
        description="PatchMaster License Generator v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Tier Feature Matrix:
  basic      — Patching, hosts, groups, snapshots, schedules, jobs, basic monitoring
  standard   — Basic + compliance, CVE, audit, notifications, offline
  devops     — Standard + CI/CD pipelines, Git integration
  enterprise — All features including user management & license admin

Examples:
  python generate-license.py --tier basic --plan 1-year --customer "Small Co"
  python generate-license.py --tier standard --plan 2-year --customer "Mid Corp"
  python generate-license.py --tier devops --plan 1-year --customer "Dev Team"
  python generate-license.py --tier enterprise --plan 5-year --customer "Big Corp"
  python generate-license.py --plan testing --customer "Demo User"
        """,
    )
    parser.add_argument("--tier", choices=TIERS.keys(), default="enterprise",
                        help="License tier (default: enterprise). Ignored for testing plan.")
    parser.add_argument("--plan", required=True, choices=PLANS.keys(),
                        help="Duration: testing, 1-year, 2-year, 5-year")
    parser.add_argument("--customer", required=True, help="Customer / organization name")
    parser.add_argument("--max-hosts", type=int, default=0,
                        help="Maximum managed hosts (0 = unlimited)")
    parser.add_argument("--secret", default=DEFAULT_SIGN_KEY,
                        help="Signing secret (must match LICENSE_SIGN_KEY on server)")
    args = parser.parse_args()

    license_key = generate_license(args.tier, args.plan, args.customer, args.secret, args.max_hosts)

    # Decode for display
    body = license_key[4:]
    payload_b64 = body.rsplit(".", 1)[0]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))

    tier_info = TIERS[payload["tier"]]

    print()
    print("=" * 64)
    print("  PatchMaster — License Key Generated (v2)")
    print("=" * 64)
    print(f"  License ID:    {payload['license_id']}")
    print(f"  Customer:      {payload['customer']}")
    print(f"  Tier:          {payload['tier_label']} ({payload['tier']})")
    print(f"  Description:   {tier_info['description']}")
    print(f"  Plan:          {payload['plan_label']}")
    print(f"  Issued:        {payload['issued_at']}")
    print(f"  Expires:       {payload['expires_at']}")
    print(f"  Max Hosts:     {'Unlimited' if payload['max_hosts'] == 0 else payload['max_hosts']}")
    print(f"  Version:       {payload['tool_version']} (compatible: {payload['version_compat']})")
    print("-" * 64)
    print(f"  Features ({len(payload['features'])}):")
    for i in range(0, len(payload['features']), 4):
        row = payload['features'][i:i+4]
        print(f"    {', '.join(row)}")
    print("=" * 64)
    print()
    print("LICENSE KEY:")
    print(license_key)
    print()
    print("ACTIVATION:")
    print("  Option 1: Place in /opt/patchmaster/license.key")
    print("  Option 2: Use the PatchMaster Web UI → Settings → License")
    print("  Option 3: API call:")
    print(f'    curl -X POST http://SERVER:8000/api/license/activate \\')
    print(f'      -H "Content-Type: application/json" \\')
    print(f'      -d \'{{"license_key": "{license_key[:50]}..."}}\'')
    print()


if __name__ == "__main__":
    main()
