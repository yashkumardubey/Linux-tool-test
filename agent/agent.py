#!/usr/bin/env python3
"""Minimal patch agent prototype.

- Exposes a small REST API to trigger a patch job and view status.
- Exposes Prometheus metrics at /metrics.

This is a prototype: production use requires hardening, proper auth (mTLS/tokens),
robust error handling, and snapshot integration.
"""

import argparse
import logging
import ssl
import pwd
import grp
import stat
import shutil
import subprocess
import threading
import time
from flask import Flask, jsonify, request
from prometheus_client import start_http_server, Gauge
import os
from functools import wraps

LOG_DIR = '/var/log/patch-agent'
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("patch-agent")
logger.setLevel(logging.INFO)
from logging.handlers import RotatingFileHandler
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

# Prometheus metrics
patch_job_gauge = Gauge("patch_job_status", "Patch job status (0=idle,1=running,2=success,3=failure)")
last_patch_ts = Gauge("last_patch_timestamp", "Last patch completion epoch seconds")


def run_command(cmd, timeout=3600):
    logger.info("Running: %s", " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = []
    try:
        for line in proc.stdout:
            logger.info(line.rstrip())
            out.append(line)
        rc = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        rc = -1
    return rc, "".join(out)


def drop_privileges(user_name: str):
    try:
        pw = pwd.getpwnam(user_name)
    except KeyError:
        logger.warning('User %s not found; skipping privilege drop', user_name)
        return
    uid = pw.pw_uid
    gid = pw.pw_gid
    logger.info('Dropping privileges to %s (%d:%d)', user_name, uid, gid)
    os.setgid(gid)
    os.setuid(uid)
    os.environ['HOME'] = pw.pw_dir



def record_job(entry):
    try:
        JOB_HISTORY.insert(0, {**entry, "ts": time.time()})
        # cap history
        if len(JOB_HISTORY) > 200:
            JOB_HISTORY.pop()
    except Exception:
        pass


def require_token(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        token = os.environ.get('AGENT_TOKEN')
        if token:
            auth = request.headers.get('Authorization', '')
            if not auth.startswith('Bearer ' + token):
                return jsonify({'error': 'missing/invalid token'}), 401
        return f(*args, **kwargs)
    return wrapped


def perform_patch_job(dry_run=False):
    JOB_STATUS["state"] = "running"
    patch_job_gauge.set(1)
    try:
        # Placeholder: snapshot should be created here (LVM/Btrfs/ZFS/hypervisor)
        logger.info("[PATCH] Pre-checks and snapshot step (placeholder)")

        # Assume internal mirror is configured in /etc/apt/sources.list.d/internal-mirror.list
        if dry_run:
            logger.info("Dry run: apt update && apt -s upgrade")
            rc, out = run_command(["/usr/bin/sudo", "apt-get", "update"])  # update package metadata
            rc2, out2 = run_command(["/usr/bin/sudo", "apt-get", "-s", "upgrade"])  # simulation
            success = (rc == 0)
        else:
            rc, out = run_command(["/usr/bin/sudo", "apt-get", "update"])  # update package metadata
            if rc != 0:
                raise RuntimeError("apt-get update failed")
            rc2, out2 = run_command(["/usr/bin/sudo", "apt-get", "-y", "upgrade"])  # perform upgrades
            success = (rc2 == 0)

        if success:
            JOB_STATUS["state"] = "idle"
            JOB_STATUS["last_result"] = {"success": True, "out": out + out2}
            patch_job_gauge.set(2)
            last_patch_ts.set(time.time())
            return True, JOB_STATUS["last_result"]
        else:
            JOB_STATUS["state"] = "idle"
            JOB_STATUS["last_result"] = {"success": False, "out": out + out2}
            patch_job_gauge.set(3)
            return False, JOB_STATUS["last_result"]
    except Exception as e:
        JOB_STATUS["state"] = "idle"
        JOB_STATUS["last_result"] = {"success": False, "error": str(e)}
        patch_job_gauge.set(3)
        return False, JOB_STATUS["last_result"]


@app.route("/health")
def health():
    return jsonify({"status": "ok", "state": JOB_STATUS["state"]})


@app.route("/status")
def status():
    return jsonify(JOB_STATUS)


@app.route("/run_patch", methods=["POST"])
def run_patch():
    data = request.get_json(silent=True) or {}
    dry = bool(data.get("dry_run", False))
    if JOB_STATUS["state"] == "running":
        return jsonify({"error": "another job is running"}), 409

    def worker():
        perform_patch_job(dry_run=dry)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return jsonify({"started": True, "dry_run": dry})


@app.route("/updates", methods=["GET"])
def list_updates():
    """Return list of upgradable packages (name, candidate).

    Uses `apt list --upgradable` and parses the output. Requires apt on host.
    """
    try:
        rc, out = run_command(["/usr/bin/apt", "list", "--upgradable"], timeout=30)
        if rc != 0:
            return jsonify({"error": "apt list failed", "output": out}), 500
        lines = out.splitlines()
        pkgs = []
        for line in lines:
            # skip header lines
            if line.startswith("Listing...") or not line.strip():
                continue
            # format: pkg/version arch [upgradable from: old]
            parts = line.split()
            namever = parts[0]
            if '/' in namever:
                name = namever.split('/')[0]
            else:
                name = namever
            candidate = namever.split('/')[1] if '/' in namever else ''
            # try to parse current version from tail
            current = None
            if "[upgradable from:" in line:
                try:
                    current = line.split('[upgradable from:')[1].strip(' ]')
                except Exception:
                    current = None
            pkgs.append({"name": name, "candidate": candidate, "current": current})
        return jsonify({"upgradable": pkgs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/upload_deb", methods=["POST"])
def upload_deb():
    files = request.files.getlist('file')
    saved = []
    saved_dir = "/tmp/patch_agent_debs"
    import os
    os.makedirs(saved_dir, exist_ok=True)
    for f in files:
        dest = os.path.join(saved_dir, f.filename)
        f.save(dest)
        saved.append(dest)
    return jsonify({"saved": saved})


@app.route("/install_uploaded", methods=["POST"])
def install_uploaded():
    """Install uploaded .deb files previously placed via /upload_deb"""
    saved_dir = "/tmp/patch_agent_debs"
    import os
    if not os.path.isdir(saved_dir):
        return jsonify({"error": "no uploaded packages"}), 400
    files = [os.path.join(saved_dir, f) for f in os.listdir(saved_dir) if f.endswith('.deb')]
    if not files:
        return jsonify({"error": "no .deb files found"}), 400
    JOB_STATUS["state"] = "running"
    patch_job_gauge.set(1)
    try:
        # install debs
        rc, out = run_command(["/usr/bin/sudo", "/usr/bin/dpkg", "-i"] + files)
        if rc != 0:
            # try to fix deps
            rc2, out2 = run_command(["/usr/bin/sudo", "/usr/bin/apt-get", "-f", "-y", "install"])
            success = (rc2 == 0)
            out += out2
        else:
            success = True
        JOB_STATUS["state"] = "idle"
        JOB_STATUS["last_result"] = {"success": success, "out": out}
        patch_job_gauge.set(2 if success else 3)
        if success:
            last_patch_ts.set(time.time())
        return jsonify(JOB_STATUS["last_result"])
    except Exception as e:
        JOB_STATUS["state"] = "idle"
        JOB_STATUS["last_result"] = {"success": False, "error": str(e)}
        patch_job_gauge.set(3)
        return jsonify(JOB_STATUS["last_result"]), 500


@app.route("/install_selected", methods=["POST"])
def install_selected():
    """Install selected packages or perform full upgrade with exclusions.

    JSON body:
    {
      "packages": ["pkg1", "pkg2"],   # optional, if empty do full upgrade
      "hold": ["postgresql", "pgpool2"]  # packages to hold/ exclude during upgrade
    }
    """
    data = request.get_json(silent=True) or {}
    packages = data.get('packages', []) or []
    hold = data.get('hold', []) or []
    if JOB_STATUS["state"] == "running":
        return jsonify({"error": "another job is running"}), 409

    JOB_STATUS["state"] = "running"
    patch_job_gauge.set(1)
    try:
        # hold packages
        held = []
        for pkg in hold:
            run_command(["/usr/bin/sudo", "/usr/bin/apt-mark", "hold", pkg])
            held.append(pkg)

        # update cache
        rc, out = run_command(["/usr/bin/sudo", "apt-get", "update"])
        if rc != 0:
            raise RuntimeError("apt-get update failed: " + out)

        if packages:
            cmd = ["/usr/bin/sudo", "apt-get", "-y", "install"] + packages
        else:
            cmd = ["/usr/bin/sudo", "apt-get", "-y", "upgrade"]

        rc2, out2 = run_command(cmd)
        success = (rc2 == 0)

        # unhold packages
        for pkg in held:
            run_command(["/usr/bin/sudo", "/usr/bin/apt-mark", "unhold", pkg])

        JOB_STATUS["state"] = "idle"
        JOB_STATUS["last_result"] = {"success": success, "out": out + out2}
        patch_job_gauge.set(2 if success else 3)
        if success:
            last_patch_ts.set(time.time())
        return jsonify(JOB_STATUS["last_result"])
    except Exception as e:
        # try to unhold on error
        for pkg in hold:
            run_command(["/usr/bin/sudo", "/usr/bin/apt-mark", "unhold", pkg])
        JOB_STATUS["state"] = "idle"
        JOB_STATUS["last_result"] = {"success": False, "error": str(e)}
        patch_job_gauge.set(3)
        return jsonify(JOB_STATUS["last_result"]), 500


@app.route('/snapshots', methods=['GET'])
@require_token
def list_snapshots():
    """Return in-memory snapshot records (prototype)."""
    # In a real system this should query snapshot backend or a persistent store
    snaps = [s for s in JOB_HISTORY if s.get('type') == 'snapshot']
    return jsonify({'snapshots': snaps})


@app.route('/snapshot/create', methods=['POST'])
@require_token
def create_snapshot():
    data = request.get_json(silent=True) or {}
    name = data.get('name') or f"snap-{int(time.time())}"
    method = data.get('method', 'lvm')
    # Prototype: attempt LVM snapshot if present, otherwise fallback placeholder
    entry = {'type': 'snapshot', 'name': name, 'method': method, 'success': False}
    # detect LVM logical volumes (simple heuristic)
    try:
        rc, out = run_command(['/sbin/lvs', '--noheadings', '-o', 'lv_path'])
        if rc == 0 and out.strip():
            lv = out.splitlines()[0].strip()
            snap_name = name
            cmd = ['/usr/bin/sudo', '/sbin/lvcreate', '-L', '1G', '-s', '-n', snap_name, lv]
            rc2, out2 = run_command(cmd)
            entry['cmd'] = ' '.join(cmd)
            entry['out'] = out2
            entry['success'] = (rc2 == 0)
        else:
            # fallback: store placeholder record
            entry['out'] = 'no LVM detected; snapshot not created (prototype)'
            entry['success'] = False
    except Exception as e:
        entry['out'] = str(e)
        entry['success'] = False

    record_job(entry)
    return jsonify(entry)


@app.route('/snapshot/rollback', methods=['POST'])
@require_token
def rollback_snapshot():
    data = request.get_json(silent=True) or {}
    name = data.get('name')
    if not name:
        return jsonify({'error': 'snapshot name required'}), 400
    # Prototype: attempt to remove snapshot and activate (real rollback requires careful steps)
    entry = {'type': 'rollback', 'name': name, 'success': False}
    try:
        # Try LVM rollback sequence (high-level prototype):
        # 1) find snapshot lv path
        rc, out = run_command(['/sbin/lvs', '--noheadings', '-o', 'lv_name,vg_name'])
        if rc == 0:
            found = False
            for l in out.splitlines():
                parts = l.split()
                if parts and parts[0] == name:
                    found = True
                    vg = parts[1]
                    snap_path = f"/dev/{vg}/{name}"
                    # In many cases rollback requires deactivating origin, removing, restoring, etc.
                    entry['out'] = f"found snapshot {snap_path}; manual rollback required (prototype)"
                    entry['success'] = False
                    break
            if not found:
                entry['out'] = 'snapshot not found'
                entry['success'] = False
        else:
            entry['out'] = 'cannot list lvs'
            entry['success'] = False
    except Exception as e:
        entry['out'] = str(e)
        entry['success'] = False

    record_job(entry)
    return jsonify(entry)


@app.route('/history', methods=['GET'])
@require_token
def history():
    return jsonify({'history': JOB_HISTORY})


def main(dev_server=False, port=8080, metrics_port=9100):
    # start prometheus metrics server on separate port
    start_http_server(metrics_port)
    logger.info("Prometheus metrics available on port %s", metrics_port)
    # Optionally drop privileges if AGENT_RUN_AS_USER is set and we're root
    run_as = os.environ.get('AGENT_RUN_AS_USER')
    if run_as and os.geteuid() == 0:
        # ensure log dir ownership
        try:
            pw = pwd.getpwnam(run_as)
            shutil.chown(LOG_DIR, user=pw.pw_name, group=pw.pw_name)
        except Exception:
            pass
        drop_privileges(run_as)

    # Configure SSL / mTLS if certs provided
    certfile = os.environ.get('AGENT_CERTFILE')
    keyfile = os.environ.get('AGENT_KEYFILE')
    ca_bundle = os.environ.get('AGENT_CABUNDLE')
    if certfile and keyfile:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        if ca_bundle:
            context.load_verify_locations(cafile=ca_bundle)
            context.verify_mode = ssl.CERT_REQUIRED
        ssl_context = context
    else:
        ssl_context = None

    # For prototype we use Flask's built-in server; in production use gunicorn behind a reverse-proxy.
    app.run(host="0.0.0.0", port=port, ssl_context=ssl_context)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev-server", action="store_true")
    parser.add_argument("--metrics-port", type=int, default=9100)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    main(dev_server=args.dev_server, port=args.port, metrics_port=args.metrics_port)
