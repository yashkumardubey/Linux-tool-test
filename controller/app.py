#!/usr/bin/env python3
"""Simple controller GUI that proxies to agents and provides a central UI.

This prototype reads `controller/inventory.yml` for host list and proxies agent API calls.
"""
import os
import yaml
import requests
from flask import Flask, render_template, jsonify, request

app = Flask(__name__, template_folder="templates", static_folder="static")
INVENTORY_PATH = os.path.join(os.path.dirname(__file__), "inventory.yml")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yml")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f) or {}

CFG = load_config()


def load_inventory():
    if not os.path.exists(INVENTORY_PATH):
        return []
    with open(INVENTORY_PATH, "r") as f:
        data = yaml.safe_load(f) or {}
    hosts = data.get("hosts", [])
    return hosts


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/hosts")
def api_hosts():
    return jsonify({"hosts": load_inventory()})


@app.route("/api/proxy/updates", methods=["POST"])
def proxy_updates():
    data = request.get_json() or {}
    host = data.get("host")
    if not host:
        return jsonify({"error": "host required"}), 400
    try:
        headers = {}
        token = CFG.get('agent_token')
        if token:
            headers['Authorization'] = f"Bearer {token}"
        # mTLS: supply client cert/key and verify using CA bundle if configured
        cert = None
        verify = True
        scheme = 'http'
        if CFG.get('client_cert') or CFG.get('ca_cert'):
            scheme = 'https'
        if CFG.get('client_cert') and CFG.get('client_key'):
            cert = (CFG.get('client_cert'), CFG.get('client_key'))
        if CFG.get('ca_cert'):
            verify = CFG.get('ca_cert')
        r = requests.get(f"{scheme}://{host}:8080/updates", timeout=10, headers=headers, cert=cert, verify=verify)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/proxy/install_selected", methods=["POST"])
def proxy_install_selected():
    data = request.get_json() or {}
    host = data.get("host")
    body = data.get("body", {})
    if not host:
        return jsonify({"error": "host required"}), 400
    try:
        headers = {}
        token = CFG.get('agent_token')
        if token:
            headers['Authorization'] = f"Bearer {token}"
        cert = None
        verify = True
        scheme = 'http'
        if CFG.get('client_cert') or CFG.get('ca_cert'):
            scheme = 'https'
        if CFG.get('client_cert') and CFG.get('client_key'):
            cert = (CFG.get('client_cert'), CFG.get('client_key'))
        if CFG.get('ca_cert'):
            verify = CFG.get('ca_cert')
        r = requests.post(f"{scheme}://{host}:8080/install_selected", json=body, timeout=300, headers=headers, cert=cert, verify=verify)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/proxy/upload_deb", methods=["POST"])
def proxy_upload_deb():
    host = request.form.get("host")
    if not host:
        return jsonify({"error": "host required"}), 400
    files = []
    for key in request.files:
        f = request.files[key]
        files.append(("file", (f.filename, f.stream, f.mimetype)))
    try:
        headers = {}
        token = CFG.get('agent_token')
        if token:
            headers['Authorization'] = f"Bearer {token}"
        cert = None
        verify = True
        scheme = 'http'
        if CFG.get('client_cert') or CFG.get('ca_cert'):
            scheme = 'https'
        if CFG.get('client_cert') and CFG.get('client_key'):
            cert = (CFG.get('client_cert'), CFG.get('client_key'))
        if CFG.get('ca_cert'):
            verify = CFG.get('ca_cert')
        r = requests.post(f"{scheme}://{host}:8080/upload_deb", files=files, timeout=120, headers=headers, cert=cert, verify=verify)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/proxy/install_uploaded", methods=["POST"])
def proxy_install_uploaded():
    data = request.get_json() or {}
    host = data.get("host")
    if not host:
        return jsonify({"error": "host required"}), 400
    try:
        headers = {}
        token = CFG.get('agent_token')
        if token:
            headers['Authorization'] = f"Bearer {token}"
        cert = None
        verify = True
        scheme = 'http'
        if CFG.get('client_cert') or CFG.get('ca_cert'):
            scheme = 'https'
        if CFG.get('client_cert') and CFG.get('client_key'):
            cert = (CFG.get('client_cert'), CFG.get('client_key'))
        if CFG.get('ca_cert'):
            verify = CFG.get('ca_cert')
        r = requests.post(f"{scheme}://{host}:8080/install_uploaded", timeout=600, headers=headers, cert=cert, verify=verify)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/proxy/snapshot_create', methods=['POST'])
def proxy_snapshot_create():
    data = request.get_json() or {}
    host = data.get('host')
    body = data.get('body', {})
    if not host:
        return jsonify({'error': 'host required'}), 400
    try:
        headers = {}
        token = CFG.get('agent_token')
        if token:
            headers['Authorization'] = f"Bearer {token}"
        r = requests.post(f"http://{host}:8080/snapshot/create", json=body, timeout=300, headers=headers)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/proxy/snapshots', methods=['POST'])
def proxy_snapshots():
    data = request.get_json() or {}
    host = data.get('host')
    if not host:
        return jsonify({'error': 'host required'}), 400
    try:
        headers = {}
        token = CFG.get('agent_token')
        if token:
            headers['Authorization'] = f"Bearer {token}"
        r = requests.get(f"http://{host}:8080/snapshots", timeout=30, headers=headers)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/proxy/history', methods=['POST'])
def proxy_history():
    data = request.get_json() or {}
    host = data.get('host')
    if not host:
        return jsonify({'error': 'host required'}), 400
    try:
        headers = {}
        token = CFG.get('agent_token')
        if token:
            headers['Authorization'] = f"Bearer {token}"
        r = requests.get(f"http://{host}:8080/history", timeout=30, headers=headers)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
