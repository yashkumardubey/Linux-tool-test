<<<<<<< HEAD
Demo and packaging
- `Vagrantfile` and `scripts/vagrant_provision.sh` — spin up an Ubuntu VM and provision the agent for an end-to-end demo.
- `packaging/build_deb.sh` — build a simple `.deb` package for the agent (prototype).
- `scripts/run_integration_demo.sh` — CI/demo script that waits for agent and triggers a dry-run.
How to run the Vagrant demo (local machine with VirtualBox):

1. Generate certs on host:

```bash
./scripts/generate_certs.sh certs
```

2. Start the VM and provision:

```bash
vagrant up
```

3. Access the controller UI on http://127.0.0.1:5000 and use the demo host `127.0.0.1` (the Vagrantfile forwards ports).

Packaging:

```bash
cd packaging
./build_deb.sh 0.1.0
```

CI notes:
- The integration job in `.github/workflows/ci.yml` expects a self-hosted runner labeled `vm-runner` capable of running VirtualBox/Vagrant. Adjust the workflow for your preferred virtualization backend (LXD/libvirt/VMware).
# Offline Patch Management Prototype (Ubuntu)

This repository contains a minimal prototype for an offline patch management solution targeting Ubuntu/Debian:

- `agent/agent.py` — minimal Python agent (REST + metrics) that runs patch jobs.
- `agent/requirements.txt` — Python dependencies.
- `systemd/patch-agent.service` — example systemd unit for the agent.
- `ansible/playbooks/ubuntu_offline_patch.yml` — sample Ansible playbook to run offline patching.
- `scripts/mirror_apt_sync.sh` — template script to sync Ubuntu repositories to an internal mirror.
- `prometheus/exporter.py` — simple example of pushing job status metrics.

Quick start (development):

1. Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r agent/requirements.txt
```

2. Run the agent (dev):

```bash
python agent/agent.py --dev-server
```

3. Run the sample Ansible playbook from your control host (customize inventory and local mirror URL):

```bash
ansible-playbook -i inventory ansible/playbooks/ubuntu_offline_patch.yml
```

New agent endpoints:

- `GET /updates` — list available upgradable packages on the host.
- `POST /install_selected` — body accepts `packages` (list) and `hold` (list) to install selected packages or run a full upgrade while holding/excluding specific packages (e.g., `postgresql`).
- `POST /upload_deb` — multipart upload of local `.deb` files (field name `file`).
- `POST /install_uploaded` — install previously uploaded `.deb` files.

Example Ansible usage:

Define `selected_packages` in your playbook/inventory to install only certain packages. To exclude DB packages, the playbook will add `db_exclude_packages` to the `hold` list for hosts in the `db` group.

For offline package installation (e.g., `ntp`): upload the `.deb` to the target and call `/install_uploaded`, or include `ntp` in `selected_packages` if it's available in your internal mirror.

Auth & snapshots
- The agent supports simple token auth: set `AGENT_TOKEN` on the target host and configure `controller/config.yml` `agent_token` to match.
- New snapshot endpoints: `POST /snapshot/create`, `POST /snapshot/rollback`, `GET /snapshots`, and `GET /history`. These are prototypes that attempt LVM snapshots if LVM is present; production rollbacks require careful validation and automated tests.

Ansible roles
- `ansible/roles/snapshot` — call `/snapshot/create` and save the returned name as `latest_snapshot` fact.
- `ansible/roles/rollback` — call `/snapshot/rollback` with `snapshot_name`.

Security note: this prototype uses token auth for simplicity. For production, use mTLS between controller and agents, signed packages, least-privilege agent users, and additional hardening.

Next steps: wire the agent to your controller, configure the internal apt mirror, and test snapshot+rollback on a staging node.
=======
# Linux-tool-test
>>>>>>> a50e16c27776450e10ebd93b01eff5ea99a2e689
