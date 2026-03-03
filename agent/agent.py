#!/usr/bin/env python3
"""PatchMaster Agent - Full patch management with snapshot/rollback, offline install, package comparison."""

import argparse
import logging
import os
import shutil
import subprocess
import time
import json
import glob
import re
from datetime import datetime
from flask import Flask, jsonify, request
from prometheus_client import start_http_server, Gauge
from logging.handlers import RotatingFileHandler

# --- Config ---
LOG_DIR = '/var/log/patch-agent'
SNAPSHOT_DIR = '/var/lib/patch-agent/snapshots'
OFFLINE_DIR = '/var/lib/patch-agent/offline-debs'

for d in [LOG_DIR, SNAPSHOT_DIR, OFFLINE_DIR]:
    os.makedirs(d, exist_ok=True)

logger = logging.getLogger("patch-agent")
logger.setLevel(logging.INFO)
fh = RotatingFileHandler(os.path.join(LOG_DIR, 'agent.log'), maxBytes=5*1024*1024, backupCount=5)
fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh.setFormatter(fmt)
logger.addHandler(fh)
console = logging.StreamHandler()
console.setFormatter(fmt)
logger.addHandler(console)

app = Flask(__name__)

JOB_STATUS = {"state": "idle", "last_result": None}
JOB_HISTORY = []

patch_gauge = Gauge("patch_job_status", "0=idle,1=running,2=success,3=failure")
last_patch_ts = Gauge("last_patch_timestamp", "Last patch epoch")


def run_cmd(cmd, timeout=3600):
    logger.info("CMD: %s", " ".join(cmd) if isinstance(cmd, list) else cmd)
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired:
        return -1, "Command timed out"
    except Exception as e:
        return -1, str(e)


def record_job(entry):
    entry["ts"] = time.time()
    entry["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    JOB_HISTORY.insert(0, entry)
    if len(JOB_HISTORY) > 500:
        JOB_HISTORY.pop()


# === PACKAGE LISTING ===

@app.route("/packages/installed")
def packages_installed():
    rc, out = run_cmd(["dpkg-query", "-W", "-f", "${Package}\t${Version}\t${Status}\n"], timeout=30)
    if rc != 0:
        return jsonify({"error": "dpkg-query failed", "output": out}), 500
    packages = []
    for line in out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and "installed" in parts[2].lower():
            packages.append({"name": parts[0], "version": parts[1], "status": parts[2].strip()})
    return jsonify({"packages": packages, "count": len(packages)})


@app.route("/packages/refresh", methods=["POST"])
def packages_refresh():
    """Run apt-get update to refresh package cache. Requires internet on agent."""
    rc, out = run_cmd(["apt-get", "update", "-qq"], timeout=120)
    return jsonify({"success": rc == 0, "output": out})


@app.route("/packages/upgradable")
def packages_upgradable():
    # Don't run apt-get update — agent may have no internet
    rc, out = run_cmd(["apt", "list", "--upgradable"], timeout=30)
    if rc != 0:
        return jsonify({"error": "apt list failed", "output": out}), 500
    packages = []
    for line in out.strip().splitlines():
        # Skip non-package lines (warnings, headers, blanks)
        if not line.strip() or line.startswith("Listing") or line.startswith("WARNING"):
            continue
        # Valid lines look like: package/source version arch [upgradable from: old_version]
        if "/" not in line:
            continue
        try:
            name_src = line.split("/")[0].strip()
            rest = line.split(" ")
            candidate = rest[1] if len(rest) > 1 else ""
            current = ""
            if "[upgradable from:" in line:
                current = line.split("[upgradable from:")[1].strip(" ]")
            packages.append({"name": name_src, "current_version": current, "available_version": candidate})
        except (IndexError, ValueError):
            continue
    return jsonify({"packages": packages, "count": len(packages)})


@app.route("/packages/uris", methods=["POST"])
def packages_uris():
    """Return download URIs for specified packages using apt-get --print-uris (works offline from cache)."""
    data = request.get_json(silent=True) or {}
    pkg_names = data.get("packages", [])
    if pkg_names:
        cmd = ["apt-get", "--print-uris", "-y", "install"] + pkg_names
    else:
        cmd = ["apt-get", "--print-uris", "-y", "upgrade"]
    rc, out = run_cmd(cmd, timeout=60)
    uris = []
    for line in out.strip().splitlines():
        # URI lines look like: 'http://archive.ubuntu.com/.../pkg_ver_arch.deb' pkg_ver_arch.deb 12345 SHA256:...
        line = line.strip()
        if not line.startswith("'") or not ".deb" in line:
            continue
        parts = line.split(" ")
        if len(parts) >= 3:
            url = parts[0].strip("'")
            filename = parts[1]
            size = parts[2] if len(parts) > 2 else "0"
            uris.append({"url": url, "filename": filename, "size": size})
    return jsonify({"uris": uris, "count": len(uris)})


# === SNAPSHOTS (dpkg-based, no LVM needed) ===

def _create_snapshot(name=None):
    if not name:
        name = f"snap-{int(time.time())}"
    snap_dir = os.path.join(SNAPSHOT_DIR, name)
    os.makedirs(snap_dir, exist_ok=True)
    result = {"name": name, "path": snap_dir, "success": False, "details": {}}
    try:
        rc, out = run_cmd(["dpkg-query", "-W", "-f", "${Package}=${Version}\n"])
        if rc == 0:
            with open(os.path.join(snap_dir, "packages.txt"), "w") as f:
                f.write(out)
            result["details"]["packages_count"] = len(out.strip().splitlines())
        rc2, out2 = run_cmd(["dpkg", "--get-selections"])
        if rc2 == 0:
            with open(os.path.join(snap_dir, "selections.txt"), "w") as f:
                f.write(out2)
        sources_dir = os.path.join(snap_dir, "sources")
        os.makedirs(sources_dir, exist_ok=True)
        if os.path.exists("/etc/apt/sources.list"):
            shutil.copy2("/etc/apt/sources.list", sources_dir)
        if os.path.isdir("/etc/apt/sources.list.d"):
            for sf in os.listdir("/etc/apt/sources.list.d"):
                shutil.copy2(os.path.join("/etc/apt/sources.list.d", sf), sources_dir)
        meta = {"name": name, "created": datetime.now().isoformat(), "packages_count": result["details"].get("packages_count", 0)}
        with open(os.path.join(snap_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        result["success"] = True
        result["created"] = meta["created"]
        logger.info("Snapshot '%s' created with %d packages", name, meta["packages_count"])
    except Exception as e:
        result["error"] = str(e)
        logger.error("Snapshot creation failed: %s", e)
    record_job({"type": "snapshot", **result})
    return result


def _rollback_snapshot(name):
    snap_dir = os.path.join(SNAPSHOT_DIR, name)
    result = {"name": name, "success": False, "steps": []}
    if not os.path.isdir(snap_dir):
        result["error"] = f"Snapshot '{name}' not found"
        return result
    try:
        selections_file = os.path.join(snap_dir, "selections.txt")
        packages_file = os.path.join(snap_dir, "packages.txt")
        if not os.path.exists(selections_file):
            result["error"] = "No selections file in snapshot"
            return result
        with open(selections_file, "r") as f:
            sel_data = f.read()
        proc = subprocess.run(["dpkg", "--set-selections"], input=sel_data, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        result["steps"].append({"step": "set-selections", "rc": proc.returncode, "output": proc.stdout[:500]})
        rc, out = run_cmd(["apt-get", "dselect-upgrade", "-y", "--allow-downgrades"], timeout=600)
        result["steps"].append({"step": "dselect-upgrade", "rc": rc, "output": out[:1000]})
        if rc == 0:
            result["success"] = True
            logger.info("Rollback to '%s' completed", name)
        else:
            if os.path.exists(packages_file):
                with open(packages_file) as f:
                    pkgs = [l.strip() for l in f if l.strip()]
                for i in range(0, len(pkgs), 50):
                    batch = pkgs[i:i+50]
                    rc3, out3 = run_cmd(["apt-get", "install", "-y", "--allow-downgrades"] + batch, timeout=300)
                result["steps"].append({"step": "version-pinned-install", "rc": rc3})
                result["success"] = (rc3 == 0)
    except Exception as e:
        result["error"] = str(e)
    record_job({"type": "rollback", **result})
    return result


@app.route("/snapshot/create", methods=["POST"])
def api_create_snapshot():
    data = request.get_json(silent=True) or {}
    result = _create_snapshot(data.get("name"))
    return jsonify(result), 200 if result["success"] else 500


@app.route("/snapshot/list", methods=["GET"])
def api_list_snapshots():
    snapshots = []
    if os.path.isdir(SNAPSHOT_DIR):
        for name in sorted(os.listdir(SNAPSHOT_DIR), reverse=True):
            meta_file = os.path.join(SNAPSHOT_DIR, name, "meta.json")
            if os.path.exists(meta_file):
                with open(meta_file) as f:
                    snapshots.append(json.load(f))
            else:
                snapshots.append({"name": name, "created": "unknown"})
    return jsonify({"snapshots": snapshots, "count": len(snapshots)})


@app.route("/snapshot/rollback", methods=["POST"])
def api_rollback_snapshot():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "snapshot name required"}), 400
    result = _rollback_snapshot(name)
    return jsonify(result), 200 if result["success"] else 500


@app.route("/snapshot/delete", methods=["POST"])
def api_delete_snapshot():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "snapshot name required"}), 400
    snap_dir = os.path.join(SNAPSHOT_DIR, name)
    if os.path.isdir(snap_dir):
        shutil.rmtree(snap_dir)
        return jsonify({"deleted": True, "name": name})
    return jsonify({"error": "snapshot not found"}), 404


# === PATCH EXECUTION with snapshot + rollback ===

@app.route("/patch/execute", methods=["POST"])
def execute_patch():
    if JOB_STATUS["state"] == "running":
        return jsonify({"error": "another job is running"}), 409
    data = request.get_json(silent=True) or {}
    # Sanitize package names — only allow valid dpkg names (alphanumeric, -, ., +)
    _valid_pkg = re.compile(r'^[a-z0-9][a-z0-9.+\-]+$')
    packages = [p.strip() for p in data.get("packages", []) if isinstance(p, str) and _valid_pkg.match(p.strip())]
    hold = [h.strip() for h in data.get("hold", []) if isinstance(h, str) and _valid_pkg.match(h.strip())]
    dry_run = data.get("dry_run", False)
    auto_snapshot = data.get("auto_snapshot", True)
    auto_rollback = data.get("auto_rollback", True)
    JOB_STATUS["state"] = "running"
    patch_gauge.set(1)
    result = {"success": False, "snapshot": None, "patch_output": "", "rollback": None, "dry_run": dry_run}
    try:
        if auto_snapshot and not dry_run:
            snap_result = _create_snapshot(f"pre-patch-{int(time.time())}")
            result["snapshot"] = snap_result
        held = []
        for pkg in hold:
            run_cmd(["apt-mark", "hold", pkg])
            held.append(pkg)
        rc, out = run_cmd(["apt-get", "update", "-qq"], timeout=120)
        result["patch_output"] += out
        if dry_run:
            cmd = (["apt-get", "-s", "install"] + packages) if packages else ["apt-get", "-s", "upgrade"]
        else:
            cmd = (["apt-get", "-y", "install"] + packages) if packages else ["apt-get", "-y", "upgrade"]
        rc2, out2 = run_cmd(cmd, timeout=600)
        result["patch_output"] += out2
        patch_success = (rc2 == 0)
        for pkg in held:
            run_cmd(["apt-mark", "unhold", pkg])
        if not patch_success and auto_rollback and not dry_run:
            if result.get("snapshot", {}).get("success"):
                rb = _rollback_snapshot(result["snapshot"]["name"])
                result["rollback"] = rb
        result["success"] = patch_success
        JOB_STATUS["state"] = "idle"
        JOB_STATUS["last_result"] = result
        patch_gauge.set(2 if patch_success else 3)
        if patch_success:
            last_patch_ts.set(time.time())
        record_job({"type": "patch", **result})
        return jsonify(result)
    except Exception as e:
        JOB_STATUS["state"] = "idle"
        result["error"] = str(e)
        patch_gauge.set(3)
        record_job({"type": "patch", **result})
        return jsonify(result), 500


# === OFFLINE PATCHING ===

@app.route("/offline/upload", methods=["POST"])
def offline_upload():
    files = request.files.getlist("file")
    if not files:
        return jsonify({"error": "no files provided"}), 400
    saved = []
    for f in files:
        if not f.filename.endswith(".deb"):
            continue
        dest = os.path.join(OFFLINE_DIR, f.filename)
        f.save(dest)
        saved.append(f.filename)
    return jsonify({"uploaded": saved, "count": len(saved), "path": OFFLINE_DIR})


@app.route("/offline/list", methods=["GET"])
def offline_list():
    debs = []
    if os.path.isdir(OFFLINE_DIR):
        for f in sorted(os.listdir(OFFLINE_DIR)):
            if f.endswith(".deb"):
                fpath = os.path.join(OFFLINE_DIR, f)
                debs.append({"name": f, "size": os.path.getsize(fpath), "size_mb": round(os.path.getsize(fpath)/1048576, 2)})
    return jsonify({"debs": debs, "count": len(debs)})


@app.route("/offline/install", methods=["POST"])
def offline_install():
    if JOB_STATUS["state"] == "running":
        return jsonify({"error": "another job is running"}), 409
    data = request.get_json(silent=True) or {}
    auto_snapshot = data.get("auto_snapshot", True)
    auto_rollback = data.get("auto_rollback", True)
    selected = data.get("files", [])
    if selected:
        deb_files = [os.path.join(OFFLINE_DIR, f) for f in selected if os.path.exists(os.path.join(OFFLINE_DIR, f))]
    else:
        deb_files = glob.glob(os.path.join(OFFLINE_DIR, "*.deb"))
    if not deb_files:
        return jsonify({"error": "no .deb files found"}), 400
    JOB_STATUS["state"] = "running"
    patch_gauge.set(1)
    result = {"success": False, "snapshot": None, "install_output": "", "rollback": None, "files": [os.path.basename(f) for f in deb_files]}
    try:
        if auto_snapshot:
            snap = _create_snapshot(f"pre-offline-{int(time.time())}")
            result["snapshot"] = snap
        rc, out = run_cmd(["dpkg", "-i"] + deb_files, timeout=300)
        result["install_output"] += out
        if rc != 0:
            rc2, out2 = run_cmd(["apt-get", "-f", "-y", "install"], timeout=120)
            result["install_output"] += out2
            ok = (rc2 == 0)
        else:
            ok = True
        if not ok and auto_rollback and result.get("snapshot", {}).get("success"):
            rb = _rollback_snapshot(result["snapshot"]["name"])
            result["rollback"] = rb
        result["success"] = ok
        JOB_STATUS["state"] = "idle"
        JOB_STATUS["last_result"] = result
        patch_gauge.set(2 if ok else 3)
        if ok:
            last_patch_ts.set(time.time())
        record_job({"type": "offline_install", **result})
        return jsonify(result)
    except Exception as e:
        JOB_STATUS["state"] = "idle"
        result["error"] = str(e)
        patch_gauge.set(3)
        record_job({"type": "offline_install", **result})
        return jsonify(result), 500


@app.route("/offline/clear", methods=["POST"])
def offline_clear():
    removed = []
    for f in glob.glob(os.path.join(OFFLINE_DIR, "*.deb")):
        os.remove(f)
        removed.append(os.path.basename(f))
    return jsonify({"cleared": removed, "count": len(removed)})


# === BASIC ROUTES ===

@app.route("/health")
def health():
    return jsonify({"status": "ok", "state": JOB_STATUS["state"]})

@app.route("/status")
def status():
    return jsonify(JOB_STATUS)

@app.route("/history")
def history():
    return jsonify({"history": JOB_HISTORY[:100]})


def main(port=8080, metrics_port=9100):
    start_http_server(metrics_port)
    logger.info("Agent starting on port %s", port)
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--metrics-port", type=int, default=9100)
    args = parser.parse_args()
    main(port=args.port, metrics_port=args.metrics_port)
