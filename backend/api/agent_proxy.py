"""Backend proxy API — forwards commands from UI to agent machines."""
import httpx
import os
import tempfile
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from api.hosts import hosts_db

router = APIRouter(prefix="/api/agent", tags=["agent-proxy"])

AGENT_PORT = 8080
TIMEOUT = 30.0
logger = logging.getLogger("agent-proxy")


def _agent_url(ip: str, path: str) -> str:
    return f"http://{ip}:{AGENT_PORT}{path}"


async def _get(ip: str, path: str):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(_agent_url(ip, path))
            return r.json()
    except Exception as e:
        raise HTTPException(502, f"Agent {ip} unreachable: {e}")


async def _post(ip: str, path: str, json_body: dict = None):
    try:
        async with httpx.AsyncClient(timeout=120.0) as c:
            r = await c.post(_agent_url(ip, path), json=json_body or {})
            return r.json()
    except Exception as e:
        raise HTTPException(502, f"Agent {ip} unreachable: {e}")


# --- Package info ---
@router.get("/{host_ip}/packages/installed")
async def proxy_installed(host_ip: str):
    return await _get(host_ip, "/packages/installed")


@router.get("/{host_ip}/packages/upgradable")
async def proxy_upgradable(host_ip: str):
    return await _get(host_ip, "/packages/upgradable")


@router.post("/{host_ip}/packages/refresh")
async def proxy_refresh(host_ip: str):
    return await _post(host_ip, "/packages/refresh")


# --- Snapshots ---
@router.get("/{host_ip}/snapshot/list")
async def proxy_snap_list(host_ip: str):
    return await _get(host_ip, "/snapshot/list")


@router.post("/{host_ip}/snapshot/create")
async def proxy_snap_create(host_ip: str, body: dict = {}):
    return await _post(host_ip, "/snapshot/create", body)


@router.post("/{host_ip}/snapshot/rollback")
async def proxy_snap_rollback(host_ip: str, body: dict = {}):
    return await _post(host_ip, "/snapshot/rollback", body)


@router.post("/{host_ip}/snapshot/delete")
async def proxy_snap_delete(host_ip: str, body: dict = {}):
    return await _post(host_ip, "/snapshot/delete", body)


# --- Patch execution ---
@router.post("/{host_ip}/patch/execute")
async def proxy_patch(host_ip: str, body: dict = {}):
    return await _post(host_ip, "/patch/execute", body)


# --- Offline ---
@router.get("/{host_ip}/offline/list")
async def proxy_offline_list(host_ip: str):
    return await _get(host_ip, "/offline/list")


@router.post("/{host_ip}/offline/install")
async def proxy_offline_install(host_ip: str, body: dict = {}):
    return await _post(host_ip, "/offline/install", body)


@router.post("/{host_ip}/offline/clear")
async def proxy_offline_clear(host_ip: str):
    return await _post(host_ip, "/offline/clear")


# --- Status / history ---
@router.get("/{host_ip}/health")
async def proxy_health(host_ip: str):
    return await _get(host_ip, "/health")


@router.get("/{host_ip}/status")
async def proxy_status(host_ip: str):
    return await _get(host_ip, "/status")


@router.get("/{host_ip}/history")
async def proxy_history(host_ip: str):
    return await _get(host_ip, "/history")


# --- Server-side package download + push ---
@router.post("/{host_ip}/packages/uris")
async def proxy_uris(host_ip: str, body: dict = {}):
    return await _post(host_ip, "/packages/uris", body)


@router.post("/{host_ip}/patch/server-patch")
async def server_patch(host_ip: str, body: dict = {}):
    """
    Full server-side patching workflow for air-gapped agents:
    1. Get download URIs from agent (reads its local apt cache)
    2. Server downloads .deb files (server has internet)
    3. Server pushes .debs to agent's offline endpoint
    4. Agent installs with dpkg -i (snapshot + rollback protection)
    """
    packages = body.get("packages", [])
    hold = body.get("hold", [])
    auto_snapshot = body.get("auto_snapshot", True)
    auto_rollback = body.get("auto_rollback", True)
    dry_run = body.get("dry_run", False)

    result = {
        "success": False,
        "phase": "init",
        "uris_count": 0,
        "downloaded": [],
        "download_failed": [],
        "pushed": 0,
        "install_result": None,
        "dry_run": dry_run,
    }

    try:
        # Step 1: Get download URIs from agent
        result["phase"] = "getting_uris"
        uris_data = await _post(host_ip, "/packages/uris", {"packages": packages})
        uris = uris_data.get("uris", [])
        result["uris_count"] = len(uris)

        if not uris:
            result["phase"] = "done"
            result["success"] = True
            result["message"] = "No packages to download — system may already be up to date"
            return result

        if dry_run:
            result["phase"] = "done"
            result["success"] = True
            result["message"] = f"DRY RUN: Would download {len(uris)} packages and install on agent"
            result["packages_to_download"] = [u["filename"] for u in uris]
            return result

        # Step 2: Download .debs on the server
        result["phase"] = "downloading"
        tmp_dir = tempfile.mkdtemp(prefix="patchmaster-debs-")
        downloaded_files = []

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            for uri in uris:
                url = uri["url"]
                fname = uri["filename"]
                if not fname.endswith(".deb"):
                    continue
                try:
                    r = await client.get(url)
                    if r.status_code == 200:
                        path = os.path.join(tmp_dir, fname)
                        with open(path, "wb") as f:
                            f.write(r.content)
                        downloaded_files.append(path)
                        result["downloaded"].append(fname)
                    else:
                        result["download_failed"].append({"file": fname, "status": r.status_code})
                except Exception as e:
                    result["download_failed"].append({"file": fname, "error": str(e)})

        if not downloaded_files:
            result["phase"] = "download_failed"
            result["message"] = "Failed to download any packages"
            return result

        # Step 3: Push .debs to agent's offline upload
        result["phase"] = "pushing_to_agent"
        agent_url = _agent_url(host_ip, "/offline/upload")
        async with httpx.AsyncClient(timeout=300.0) as client:
            files_to_send = []
            for fpath in downloaded_files:
                fname = os.path.basename(fpath)
                files_to_send.append(("file", (fname, open(fpath, "rb"), "application/octet-stream")))

            r = await client.post(agent_url, files=files_to_send)

            # Close file handles
            for _, (_, fh, _) in files_to_send:
                fh.close()

            if r.status_code != 200:
                result["phase"] = "push_failed"
                result["message"] = f"Failed to upload .debs to agent: {r.text}"
                return result

            upload_result = r.json()
            result["pushed"] = upload_result.get("count", 0)

        # Step 4: Trigger offline install on agent
        result["phase"] = "installing"
        install_data = {
            "auto_snapshot": auto_snapshot,
            "auto_rollback": auto_rollback,
        }
        install_result = await _post(host_ip, "/offline/install", install_data)
        result["install_result"] = install_result
        result["success"] = install_result.get("success", False)
        result["phase"] = "done"

        # Cleanup temp files
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

        return result

    except HTTPException:
        raise
    except Exception as e:
        result["phase"] = "error"
        result["error"] = str(e)
        return result
