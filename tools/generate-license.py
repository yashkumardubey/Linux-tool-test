#!/usr/bin/env python3
"""
PatchMaster — License Key Generator
Run this on your admin machine to generate license keys for customers.

Usage:
    python generate-license.py --plan 1-year --customer "Acme Corp"
    python generate-license.py --plan testing --customer "Demo User"
    python generate-license.py --plan 5-year --customer "Enterprise Inc" --secret MY_KEY
"""
import argparse
import base64
import hashlib
import hmac
import json
import sys
from datetime import datetime, timedelta

# Default signing secret — override with --secret or LICENSE_SIGN_KEY env var
DEFAULT_SIGN_KEY = "PatchMaster-License-SignKey-2026-Secure"

PLANS = {
    "testing":  {"days": 30,   "label": "Testing (1 Month)"},
    "1-year":   {"days": 365,  "label": "Standard (1 Year)"},
    "2-year":   {"days": 730,  "label": "Professional (2 Years)"},
    "5-year":   {"days": 1825, "label": "Enterprise (5 Years)"},
}


def generate_license(plan: str, customer: str, sign_key: str) -> str:
    """Generate a signed license key."""
    if plan not in PLANS:
        print(f"Error: Invalid plan '{plan}'. Choose from: {', '.join(PLANS.keys())}")
        sys.exit(1)

    now = datetime.utcnow()
    expires = now + timedelta(days=PLANS[plan]["days"])

    payload = {
        "v": 1,
        "plan": plan,
        "plan_label": PLANS[plan]["label"],
        "customer": customer,
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_hosts": 0,  # 0 = unlimited
    }

    # Encode payload
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode().rstrip("=")

    # Sign with HMAC-SHA256
    signature = hmac.new(
        sign_key.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()

    # License format: PM1-<payload>.<signature>
    license_key = f"PM1-{payload_b64}.{signature}"
    return license_key


def main():
    parser = argparse.ArgumentParser(description="PatchMaster License Generator")
    parser.add_argument("--plan", required=True, choices=PLANS.keys(),
                        help="License plan: testing, 1-year, 2-year, 5-year")
    parser.add_argument("--customer", required=True, help="Customer name / org")
    parser.add_argument("--secret", default=DEFAULT_SIGN_KEY,
                        help="Signing secret (must match LICENSE_SIGN_KEY on the server)")
    args = parser.parse_args()

    license_key = generate_license(args.plan, args.customer, args.secret)

    # Decode for display
    parts = license_key.split("-", 1)[1]
    payload_b64 = parts.rsplit(".", 1)[0]
    # Add padding
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))

    print()
    print("=" * 60)
    print("  PatchMaster — License Key Generated")
    print("=" * 60)
    print(f"  Customer:    {payload['customer']}")
    print(f"  Plan:        {payload['plan_label']}")
    print(f"  Issued:      {payload['issued_at']}")
    print(f"  Expires:     {payload['expires_at']}")
    print("=" * 60)
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
    print(f'      -d \'{{"license_key": "{license_key[:40]}..."}}\'')
    print()


if __name__ == "__main__":
    main()
