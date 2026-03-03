import time
import requests
import socket
import platform
import os
import json
import subprocess


def get_real_ip():
    """Get the real network IP using ip-route (most reliable on Linux/WSL)."""
    # Method 1 (best): 'ip route get' returns the actual source IP for external traffic
    try:
        out = subprocess.check_output(["ip", "route", "get", "1.1.1.1"], text=True, timeout=5)
        # Look for 'src <IP>' pattern
        parts = out.split()
        for i, token in enumerate(parts):
            if token == "src" and i + 1 < len(parts):
                ip = parts[i + 1].split("/")[0]
                if ip and not ip.startswith("127."):
                    return ip
    except Exception:
        pass
    # Method 2: UDP socket trick
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    # Method 3: hostname -I, take first non-loopback
    try:
        out = subprocess.check_output(["hostname", "-I"], text=True, timeout=5).strip()
        for candidate in out.split():
            if candidate.count(".") == 3 and not candidate.startswith("127."):
                return candidate
    except Exception:
        pass
    # Fallback
    ip = socket.gethostbyname(socket.gethostname())
    if "/" in ip:
        ip = ip.split("/")[0]
    return ip


def get_os_info():
    """Get distro name and version from /etc/os-release (e.g. 'Ubuntu 24.04')."""
    try:
        info = {}
        with open("/etc/os-release") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, _, val = line.partition("=")
                    info[key] = val.strip('"')
        name = info.get("NAME", info.get("ID", "Linux"))
        version = info.get("VERSION_ID", info.get("VERSION", ""))
        return name, version
    except Exception:
        return platform.system(), platform.version()


def get_inventory():
    os_name, os_version = get_os_info()
    return {
        "hostname": socket.gethostname(),
        "os": os_name,
        "os_version": os_version,
        "kernel": platform.release(),
        "arch": platform.machine(),
        "ip": get_real_ip(),
    }

def register(controller_url, token=None):
    inv = get_inventory()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.post(f"{controller_url}/api/register", json=inv, headers=headers, timeout=10)
        if r.status_code == 200:
            print("Registered successfully.")
            return r.json().get("agent_token")
        else:
            print(f"Registration failed: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Registration error: {e}")
    return None

def heartbeat(controller_url, agent_token):
    inv = get_inventory()
    headers = {"Authorization": f"Bearer {agent_token}"}
    try:
        r = requests.post(f"{controller_url}/api/heartbeat", json=inv, headers=headers, timeout=10)
        if r.status_code == 200:
            print("Heartbeat sent.")
        else:
            print(f"Heartbeat failed: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Heartbeat error: {e}")

def main():
    controller_url = os.environ.get("CONTROLLER_URL", "http://localhost:8000")
    token_path = "/etc/patch-agent/token"
    agent_token = None
    if os.path.exists(token_path):
        with open(token_path) as f:
            agent_token = f.read().strip()
    else:
        agent_token = register(controller_url)
        if agent_token:
            try:
                os.makedirs("/etc/patch-agent", exist_ok=True)
                with open(token_path, "w") as f:
                    f.write(agent_token)
            except PermissionError:
                print(f"Warning: Cannot write token to {token_path} (permission denied). Running without persistent token.")
    while True:
        if agent_token:
            heartbeat(controller_url, agent_token)
        time.sleep(60)

if __name__ == "__main__":
    main()
