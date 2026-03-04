#!/usr/bin/env python3
"""
PatchMaster — Customer & License Management Tool
Standalone Flask app for vendor-side customer tracking, purchase management,
license generation, and version control.

Usage:
    python app.py                      # runs on http://localhost:5050
    python app.py --port 5050          # custom port
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, session, g,
)

# ── App Setup ──────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("CM_SECRET_KEY", secrets.token_hex(32))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "customers.db")

# ── License constants (must match PatchMaster) ─────────────────
DEFAULT_SIGN_KEY = "PatchMaster-License-SignKey-2026-Secure"
TOOL_VERSION = "2.0"
VERSION_COMPAT = "2.x"

PLANS = {
    "testing": {"days": 30, "label": "Testing (1 Month)", "price": 0},
    "1-year":  {"days": 365, "label": "1 Year", "price": 999},
    "2-year":  {"days": 730, "label": "2 Years", "price": 1799},
    "5-year":  {"days": 1825, "label": "5 Years", "price": 3999},
}

TIERS = {
    "basic": {
        "label": "Basic",
        "description": "Patching + Basic Monitoring",
        "price_mult": 1.0,
        "features": [
            "dashboard", "hosts", "groups", "patches", "snapshots",
            "compare", "offline", "schedules", "jobs", "onboarding",
        ],
    },
    "standard": {
        "label": "Standard",
        "description": "Basic + Advanced Monitoring, Compliance, CVE, Audit",
        "price_mult": 2.0,
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
        "price_mult": 3.0,
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
        "price_mult": 5.0,
        "features": [
            "dashboard", "compliance", "hosts", "groups", "patches", "snapshots",
            "compare", "offline", "schedules", "cve", "jobs", "audit",
            "notifications", "users", "license", "cicd", "git", "onboarding",
            "settings", "monitoring",
        ],
    },
}


# ── Database ───────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.template_filter("from_json")
def from_json_filter(s):
    try:
        return json.loads(s)
    except Exception:
        return []


@app.context_processor
def inject_now():
    return {"now": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}


def init_db():
    """Create tables if they don't exist."""
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL,
            company     TEXT    NOT NULL DEFAULT '',
            phone       TEXT    NOT NULL DEFAULT '',
            address     TEXT    NOT NULL DEFAULT '',
            notes       TEXT    NOT NULL DEFAULT '',
            status      TEXT    NOT NULL DEFAULT 'active',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id     INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            tier            TEXT    NOT NULL,
            plan            TEXT    NOT NULL,
            max_hosts       INTEGER NOT NULL DEFAULT 0,
            amount          REAL    NOT NULL DEFAULT 0,
            currency        TEXT    NOT NULL DEFAULT 'USD',
            payment_method  TEXT    NOT NULL DEFAULT '',
            payment_ref     TEXT    NOT NULL DEFAULT '',
            status          TEXT    NOT NULL DEFAULT 'completed',
            notes           TEXT    NOT NULL DEFAULT '',
            purchased_at    TEXT    NOT NULL DEFAULT (datetime('now')),
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS licenses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id     INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
            customer_id     INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            license_id      TEXT    NOT NULL UNIQUE,
            license_key     TEXT    NOT NULL,
            tier            TEXT    NOT NULL,
            plan            TEXT    NOT NULL,
            features        TEXT    NOT NULL DEFAULT '[]',
            max_hosts       INTEGER NOT NULL DEFAULT 0,
            tool_version    TEXT    NOT NULL DEFAULT '2.0',
            version_compat  TEXT    NOT NULL DEFAULT '2.x',
            issued_at       TEXT    NOT NULL,
            expires_at      TEXT    NOT NULL,
            is_revoked      INTEGER NOT NULL DEFAULT 0,
            revoked_at      TEXT,
            revoke_reason   TEXT    NOT NULL DEFAULT '',
            activated       INTEGER NOT NULL DEFAULT 0,
            activated_at    TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tool_versions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            version         TEXT    NOT NULL UNIQUE,
            codename        TEXT    NOT NULL DEFAULT '',
            release_date    TEXT    NOT NULL,
            changelog       TEXT    NOT NULL DEFAULT '',
            min_tier        TEXT    NOT NULL DEFAULT 'basic',
            is_latest       INTEGER NOT NULL DEFAULT 0,
            download_url    TEXT    NOT NULL DEFAULT '',
            file_hash       TEXT    NOT NULL DEFAULT '',
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            action      TEXT    NOT NULL,
            entity_type TEXT    NOT NULL DEFAULT '',
            entity_id   INTEGER,
            details     TEXT    NOT NULL DEFAULT '',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    db.commit()
    db.close()


def log_activity(action, entity_type="", entity_id=None, details=""):
    db = get_db()
    db.execute(
        "INSERT INTO activity_log (action, entity_type, entity_id, details) VALUES (?,?,?,?)",
        (action, entity_type, entity_id, details),
    )
    db.commit()


# ── License Generation ─────────────────────────────────────────
def generate_license_key(tier, plan, customer, max_hosts=0, sign_key=DEFAULT_SIGN_KEY):
    """Generate a signed PatchMaster license key. Returns (key, payload)."""
    effective_tier = "enterprise" if plan == "testing" else tier
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

    key = f"PM1-{payload_b64}.{signature}"
    return key, payload


# ── Auth (simple session-based) ────────────────────────────────
ADMIN_USER = os.environ.get("CM_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("CM_ADMIN_PASS", "admin123")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if hmac.compare_digest(username, ADMIN_USER) and hmac.compare_digest(password, ADMIN_PASS):
            session["logged_in"] = True
            session["user"] = username
            flash("Logged in successfully.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


# ── Dashboard ──────────────────────────────────────────────────
@app.route("/")
@login_required
def dashboard():
    db = get_db()
    stats = {
        "total_customers": db.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
        "active_customers": db.execute("SELECT COUNT(*) FROM customers WHERE status='active'").fetchone()[0],
        "total_purchases": db.execute("SELECT COUNT(*) FROM purchases").fetchone()[0],
        "total_revenue": db.execute("SELECT COALESCE(SUM(amount),0) FROM purchases WHERE status='completed'").fetchone()[0],
        "total_licenses": db.execute("SELECT COUNT(*) FROM licenses").fetchone()[0],
        "active_licenses": db.execute("SELECT COUNT(*) FROM licenses WHERE is_revoked=0 AND expires_at > datetime('now')").fetchone()[0],
        "expired_licenses": db.execute("SELECT COUNT(*) FROM licenses WHERE is_revoked=0 AND expires_at <= datetime('now')").fetchone()[0],
        "revoked_licenses": db.execute("SELECT COUNT(*) FROM licenses WHERE is_revoked=1").fetchone()[0],
    }
    # Tier distribution
    tier_dist = db.execute(
        "SELECT tier, COUNT(*) as cnt FROM licenses WHERE is_revoked=0 GROUP BY tier"
    ).fetchall()
    # Recent activity
    recent = db.execute(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 15"
    ).fetchall()
    # Recent purchases
    recent_purchases = db.execute("""
        SELECT p.*, c.name as customer_name, c.company
        FROM purchases p JOIN customers c ON p.customer_id = c.id
        ORDER BY p.purchased_at DESC LIMIT 10
    """).fetchall()
    return render_template("dashboard.html", stats=stats, tier_dist=tier_dist,
                           recent=recent, recent_purchases=recent_purchases,
                           tiers=TIERS, plans=PLANS)


# ── Customers ──────────────────────────────────────────────────
@app.route("/customers")
@login_required
def customers_list():
    db = get_db()
    search = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "")
    query = """
        SELECT c.*,
               COUNT(DISTINCT p.id) as purchase_count,
               COUNT(DISTINCT l.id) as license_count,
               COALESCE(SUM(p.amount), 0) as total_spent
        FROM customers c
        LEFT JOIN purchases p ON c.id = p.customer_id
        LEFT JOIN licenses l ON c.id = l.customer_id AND l.is_revoked = 0
    """
    params = []
    wheres = []
    if search:
        wheres.append("(c.name LIKE ? OR c.email LIKE ? OR c.company LIKE ?)")
        params.extend([f"%{search}%"] * 3)
    if status_filter:
        wheres.append("c.status = ?")
        params.append(status_filter)
    if wheres:
        query += " WHERE " + " AND ".join(wheres)
    query += " GROUP BY c.id ORDER BY c.created_at DESC"
    customers = db.execute(query, params).fetchall()
    return render_template("customers.html", customers=customers, search=search,
                           status_filter=status_filter)


@app.route("/customers/new", methods=["GET", "POST"])
@login_required
def customer_new():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO customers (name, email, company, phone, address, notes) VALUES (?,?,?,?,?,?)",
            (
                request.form["name"].strip(),
                request.form["email"].strip(),
                request.form.get("company", "").strip(),
                request.form.get("phone", "").strip(),
                request.form.get("address", "").strip(),
                request.form.get("notes", "").strip(),
            ),
        )
        db.commit()
        cust_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        log_activity("customer.created", "customer", cust_id,
                     f"Created customer: {request.form['name'].strip()}")
        flash("Customer created successfully.", "success")
        return redirect(url_for("customer_detail", cid=cust_id))
    return render_template("customer_form.html", customer=None, tiers=TIERS, plans=PLANS)


@app.route("/customers/<int:cid>")
@login_required
def customer_detail(cid):
    db = get_db()
    customer = db.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for("customers_list"))
    purchases = db.execute(
        "SELECT * FROM purchases WHERE customer_id = ? ORDER BY purchased_at DESC", (cid,)
    ).fetchall()
    licenses = db.execute(
        "SELECT * FROM licenses WHERE customer_id = ? ORDER BY created_at DESC", (cid,)
    ).fetchall()
    return render_template("customer_detail.html", customer=customer,
                           purchases=purchases, licenses=licenses,
                           tiers=TIERS, plans=PLANS)


@app.route("/customers/<int:cid>/edit", methods=["GET", "POST"])
@login_required
def customer_edit(cid):
    db = get_db()
    customer = db.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for("customers_list"))
    if request.method == "POST":
        db.execute("""
            UPDATE customers SET name=?, email=?, company=?, phone=?, address=?,
                   notes=?, status=?, updated_at=datetime('now')
            WHERE id=?
        """, (
            request.form["name"].strip(),
            request.form["email"].strip(),
            request.form.get("company", "").strip(),
            request.form.get("phone", "").strip(),
            request.form.get("address", "").strip(),
            request.form.get("notes", "").strip(),
            request.form.get("status", "active"),
            cid,
        ))
        db.commit()
        log_activity("customer.updated", "customer", cid,
                     f"Updated customer: {request.form['name'].strip()}")
        flash("Customer updated.", "success")
        return redirect(url_for("customer_detail", cid=cid))
    return render_template("customer_form.html", customer=customer, tiers=TIERS, plans=PLANS)


# ── Purchases ──────────────────────────────────────────────────
@app.route("/purchases")
@login_required
def purchases_list():
    db = get_db()
    tier_filter = request.args.get("tier", "")
    plan_filter = request.args.get("plan", "")
    query = """
        SELECT p.*, c.name as customer_name, c.company
        FROM purchases p JOIN customers c ON p.customer_id = c.id
    """
    params = []
    wheres = []
    if tier_filter:
        wheres.append("p.tier = ?")
        params.append(tier_filter)
    if plan_filter:
        wheres.append("p.plan = ?")
        params.append(plan_filter)
    if wheres:
        query += " WHERE " + " AND ".join(wheres)
    query += " ORDER BY p.purchased_at DESC"
    purchases = db.execute(query, params).fetchall()
    return render_template("purchases.html", purchases=purchases, tiers=TIERS,
                           plans=PLANS, tier_filter=tier_filter, plan_filter=plan_filter)


@app.route("/purchases/new", methods=["GET", "POST"])
@login_required
def purchase_new():
    db = get_db()
    if request.method == "POST":
        customer_id = int(request.form["customer_id"])
        tier = request.form["tier"]
        plan = request.form["plan"]
        max_hosts = int(request.form.get("max_hosts", 0))
        amount = float(request.form.get("amount", 0))
        payment_method = request.form.get("payment_method", "").strip()
        payment_ref = request.form.get("payment_ref", "").strip()
        notes = request.form.get("notes", "").strip()

        # Validate
        customer = db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not customer:
            flash("Customer not found.", "danger")
            return redirect(url_for("purchase_new"))
        if tier not in TIERS or plan not in PLANS:
            flash("Invalid tier or plan.", "danger")
            return redirect(url_for("purchase_new"))

        # Create purchase
        db.execute("""
            INSERT INTO purchases (customer_id, tier, plan, max_hosts, amount,
                                   currency, payment_method, payment_ref, notes)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (customer_id, tier, plan, max_hosts, amount, "USD",
              payment_method, payment_ref, notes))
        db.commit()
        purchase_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Auto-generate license key
        key, payload = generate_license_key(tier, plan, customer["name"], max_hosts)
        db.execute("""
            INSERT INTO licenses (purchase_id, customer_id, license_id, license_key,
                                  tier, plan, features, max_hosts, tool_version,
                                  version_compat, issued_at, expires_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            purchase_id, customer_id, payload["license_id"], key,
            payload["tier"], plan, json.dumps(payload["features"]),
            max_hosts, TOOL_VERSION, VERSION_COMPAT,
            payload["issued_at"], payload["expires_at"],
        ))
        db.commit()

        log_activity("purchase.created", "purchase", purchase_id,
                     f"{customer['name']} — {TIERS[tier]['label']} / {PLANS[plan]['label']} (${amount})")
        log_activity("license.generated", "license", None,
                     f"License {payload['license_id']} for {customer['name']}")

        flash(f"Purchase recorded & license generated (ID: {payload['license_id']}).", "success")
        return redirect(url_for("customer_detail", cid=customer_id))

    customers = db.execute("SELECT id, name, company FROM customers WHERE status='active' ORDER BY name").fetchall()
    return render_template("purchase_form.html", customers=customers, tiers=TIERS, plans=PLANS)


# ── Licenses ───────────────────────────────────────────────────
@app.route("/licenses")
@login_required
def licenses_list():
    db = get_db()
    status_filter = request.args.get("status", "")
    tier_filter = request.args.get("tier", "")
    query = """
        SELECT l.*, c.name as customer_name, c.company
        FROM licenses l JOIN customers c ON l.customer_id = c.id
    """
    params = []
    wheres = []
    if status_filter == "active":
        wheres.append("l.is_revoked = 0 AND l.expires_at > datetime('now')")
    elif status_filter == "expired":
        wheres.append("l.is_revoked = 0 AND l.expires_at <= datetime('now')")
    elif status_filter == "revoked":
        wheres.append("l.is_revoked = 1")
    if tier_filter:
        wheres.append("l.tier = ?")
        params.append(tier_filter)
    if wheres:
        query += " WHERE " + " AND ".join(wheres)
    query += " ORDER BY l.created_at DESC"
    licenses = db.execute(query, params).fetchall()
    return render_template("licenses.html", licenses=licenses, tiers=TIERS,
                           status_filter=status_filter, tier_filter=tier_filter)


@app.route("/licenses/<int:lid>")
@login_required
def license_detail(lid):
    db = get_db()
    lic = db.execute("""
        SELECT l.*, c.name as customer_name, c.company, c.email as customer_email
        FROM licenses l JOIN customers c ON l.customer_id = c.id
        WHERE l.id = ?
    """, (lid,)).fetchone()
    if not lic:
        flash("License not found.", "danger")
        return redirect(url_for("licenses_list"))
    features = json.loads(lic["features"]) if lic["features"] else []
    return render_template("license_detail.html", lic=lic, features=features, tiers=TIERS)


@app.route("/licenses/<int:lid>/revoke", methods=["POST"])
@login_required
def license_revoke(lid):
    db = get_db()
    reason = request.form.get("reason", "").strip()
    db.execute("""
        UPDATE licenses SET is_revoked=1, revoked_at=datetime('now'), revoke_reason=?
        WHERE id=?
    """, (reason, lid))
    db.commit()
    lic = db.execute("SELECT license_id, customer_id FROM licenses WHERE id=?", (lid,)).fetchone()
    log_activity("license.revoked", "license", lid,
                 f"License {lic['license_id']} revoked: {reason}")
    flash("License revoked.", "warning")
    return redirect(url_for("license_detail", lid=lid))


@app.route("/licenses/<int:lid>/copy-key")
@login_required
def license_copy_key(lid):
    db = get_db()
    lic = db.execute("SELECT license_key FROM licenses WHERE id=?", (lid,)).fetchone()
    if lic:
        return jsonify({"key": lic["license_key"]})
    return jsonify({"error": "Not found"}), 404


# ── Re-generate license (same purchase, new key) ──────────────
@app.route("/licenses/<int:lid>/regenerate", methods=["POST"])
@login_required
def license_regenerate(lid):
    db = get_db()
    old = db.execute("""
        SELECT l.*, c.name as customer_name
        FROM licenses l JOIN customers c ON l.customer_id = c.id
        WHERE l.id = ?
    """, (lid,)).fetchone()
    if not old:
        flash("License not found.", "danger")
        return redirect(url_for("licenses_list"))

    # Revoke old
    db.execute("UPDATE licenses SET is_revoked=1, revoked_at=datetime('now'), revoke_reason='Regenerated' WHERE id=?", (lid,))

    # Generate new
    key, payload = generate_license_key(old["tier"], old["plan"], old["customer_name"], old["max_hosts"])
    db.execute("""
        INSERT INTO licenses (purchase_id, customer_id, license_id, license_key,
                              tier, plan, features, max_hosts, tool_version,
                              version_compat, issued_at, expires_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        old["purchase_id"], old["customer_id"], payload["license_id"], key,
        payload["tier"], old["plan"], json.dumps(payload["features"]),
        old["max_hosts"], TOOL_VERSION, VERSION_COMPAT,
        payload["issued_at"], payload["expires_at"],
    ))
    db.commit()
    new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    log_activity("license.regenerated", "license", new_id,
                 f"Regenerated from {old['license_id']} → {payload['license_id']}")
    flash(f"New license generated (ID: {payload['license_id']}). Old key revoked.", "success")
    return redirect(url_for("license_detail", lid=new_id))


# ── Tool Versions ──────────────────────────────────────────────
@app.route("/versions")
@login_required
def versions_list():
    db = get_db()
    versions = db.execute("SELECT * FROM tool_versions ORDER BY release_date DESC").fetchall()
    return render_template("versions.html", versions=versions, tiers=TIERS)


@app.route("/versions/new", methods=["GET", "POST"])
@login_required
def version_new():
    if request.method == "POST":
        db = get_db()
        version = request.form["version"].strip()
        is_latest = 1 if request.form.get("is_latest") else 0
        if is_latest:
            db.execute("UPDATE tool_versions SET is_latest=0")
        db.execute("""
            INSERT INTO tool_versions (version, codename, release_date, changelog,
                                       min_tier, is_latest, download_url, file_hash)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            version,
            request.form.get("codename", "").strip(),
            request.form["release_date"].strip(),
            request.form.get("changelog", "").strip(),
            request.form.get("min_tier", "basic"),
            is_latest,
            request.form.get("download_url", "").strip(),
            request.form.get("file_hash", "").strip(),
        ))
        db.commit()
        log_activity("version.created", "version", None, f"Version {version} added")
        flash(f"Version {version} added.", "success")
        return redirect(url_for("versions_list"))
    return render_template("version_form.html", version=None, tiers=TIERS)


@app.route("/versions/<int:vid>/edit", methods=["GET", "POST"])
@login_required
def version_edit(vid):
    db = get_db()
    ver = db.execute("SELECT * FROM tool_versions WHERE id=?", (vid,)).fetchone()
    if not ver:
        flash("Version not found.", "danger")
        return redirect(url_for("versions_list"))
    if request.method == "POST":
        is_latest = 1 if request.form.get("is_latest") else 0
        if is_latest:
            db.execute("UPDATE tool_versions SET is_latest=0")
        db.execute("""
            UPDATE tool_versions SET version=?, codename=?, release_date=?, changelog=?,
                   min_tier=?, is_latest=?, download_url=?, file_hash=?
            WHERE id=?
        """, (
            request.form["version"].strip(),
            request.form.get("codename", "").strip(),
            request.form["release_date"].strip(),
            request.form.get("changelog", "").strip(),
            request.form.get("min_tier", "basic"),
            is_latest,
            request.form.get("download_url", "").strip(),
            request.form.get("file_hash", "").strip(),
            vid,
        ))
        db.commit()
        flash("Version updated.", "success")
        return redirect(url_for("versions_list"))
    return render_template("version_form.html", version=ver, tiers=TIERS)


# ── Activity Log ───────────────────────────────────────────────
@app.route("/activity")
@login_required
def activity_log():
    db = get_db()
    logs = db.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 200").fetchall()
    return render_template("activity.html", logs=logs)


# ── Reports / Analytics ───────────────────────────────────────
@app.route("/reports")
@login_required
def reports():
    db = get_db()
    # Revenue by month
    revenue_monthly = db.execute("""
        SELECT strftime('%Y-%m', purchased_at) as month, SUM(amount) as total
        FROM purchases WHERE status='completed'
        GROUP BY month ORDER BY month DESC LIMIT 12
    """).fetchall()
    # Revenue by tier
    revenue_tier = db.execute("""
        SELECT tier, SUM(amount) as total, COUNT(*) as cnt
        FROM purchases WHERE status='completed'
        GROUP BY tier
    """).fetchall()
    # Licenses by status
    lic_active = db.execute("SELECT COUNT(*) FROM licenses WHERE is_revoked=0 AND expires_at > datetime('now')").fetchone()[0]
    lic_expired = db.execute("SELECT COUNT(*) FROM licenses WHERE is_revoked=0 AND expires_at <= datetime('now')").fetchone()[0]
    lic_revoked = db.execute("SELECT COUNT(*) FROM licenses WHERE is_revoked=1").fetchone()[0]
    # Expiring soon (within 30 days)
    expiring = db.execute("""
        SELECT l.*, c.name as customer_name, c.company
        FROM licenses l JOIN customers c ON l.customer_id = c.id
        WHERE l.is_revoked=0 AND l.expires_at > datetime('now')
          AND l.expires_at <= datetime('now', '+30 days')
        ORDER BY l.expires_at ASC
    """).fetchall()
    return render_template("reports.html",
                           revenue_monthly=revenue_monthly, revenue_tier=revenue_tier,
                           lic_active=lic_active, lic_expired=lic_expired,
                           lic_revoked=lic_revoked, expiring=expiring,
                           tiers=TIERS, plans=PLANS)


# ── API endpoints for external integration ─────────────────────
@app.route("/api/stats")
@login_required
def api_stats():
    db = get_db()
    return jsonify({
        "customers": db.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
        "purchases": db.execute("SELECT COUNT(*) FROM purchases").fetchone()[0],
        "licenses": db.execute("SELECT COUNT(*) FROM licenses").fetchone()[0],
        "active_licenses": db.execute(
            "SELECT COUNT(*) FROM licenses WHERE is_revoked=0 AND expires_at > datetime('now')"
        ).fetchone()[0],
        "revenue": db.execute("SELECT COALESCE(SUM(amount),0) FROM purchases WHERE status='completed'").fetchone()[0],
    })


# ── Main ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PatchMaster Customer Manager")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    init_db()
    print(f"\n  PatchMaster Customer Manager")
    print(f"  http://{args.host}:{args.port}")
    print(f"  Login: {ADMIN_USER} / {'*' * len(ADMIN_PASS)}\n")
    app.run(host=args.host, port=args.port, debug=args.debug)
