# Runbook: Offline Patch Management Demo

This runbook describes how to operate the offline patching prototype entirely within Docker
and optionally via a Vagrant VM.  It covers provisioning, day‑to‑day tasks, and teardown.

## Prerequisites

- Docker Engine & docker-compose
- Optional: VirtualBox & Vagrant for the VM demo
- Ports 5000, 8080, 9080, 9090, 3000, 9100, 9101 available on host

## Starting the Demo

The `Makefile` simplifies commands.  Always wipe any previously‑generated certs before
regenerating to ensure the new SAN configuration is applied:

```sh
rm -rf certs   # remove old certificates
make demo      # build images, generate fresh certs, and launch everything
```

or manually:

```sh
./docker/start_all.sh
```

This performs:

1. `./scripts/generate_certs.sh certs` – create a CA and server/client certs.  The
   script now generates certificates with subjectAltName entries for `agent`,
   `patch-agent.local`, `localhost`, and `127.0.0.1` so that hostname verification passes
   when the controller connects to the agent container by its Docker service name.
2. Update `controller/config.yml` with client cert/key and CA path.
3. Build Docker images for agent, controller, prometheus, grafana, linuxhost.
4. `docker-compose up -d` to launch services.
5. Perform two quick API calls via controller to ensure connectivity.

## Viewing the UI

- Controller: http://localhost:5000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (default credentials `admin/admin`)

## Managing Targets

By default the controller inventory contains:

```yaml
hosts:
  - name: localhost
    host: agent
    groups: [all]
  - name: linuxhost
    host: linuxhost
    groups: [all]
```

Add/remove entries here or via the controller UI dropdown.  Each host can be reached via the
internal Docker network name (e.g. `linuxhost`).  You can run additional host containers by
copying the `linuxhost` service in `docker-compose.yml`.

### Example: add a third container

```yaml
  linuxhost2:
    build:
      context: .
      dockerfile: ./docker/linuxhost/Dockerfile
    ports:
      - "9180:8080"
      - "9102:9100"
``` 

Then update `controller/config.yml` with `linuxhost2`.

## Common Operations

### List available updates

```sh
curl -sS -X POST http://localhost:5000/api/proxy/updates \
    -H 'Content-Type: application/json' \
    -d '{"host":"linuxhost"}' | jq .
```

### Trigger an upgrade (dry-run)

```sh
curl -sS -X POST http://localhost:5000/api/proxy/install_selected \
    -H 'Content-Type: application/json' \
    -d '{"host":"linuxhost","body":{"packages":[],"hold":["postgresql"]}}' | jq .
```

### Create a snapshot

```sh
curl -sS -X POST http://localhost:5000/api/proxy/snapshot_create \
    -H 'Content-Type: application/json' \
    -d '{"host":"linuxhost","body":{"name":"canary"}}' | jq .
```

### View job history

```sh
curl -sS -X POST http://localhost:5000/api/proxy/history \
    -H 'Content-Type: application/json' \
    -d '{"host":"linuxhost"}' | jq .
```

Note: snapshots and rollback are simple prototypes; they will not function inside these
containers since no LVM volume exists.  Use the Vagrant VM or real systems for snapshot tests.

## Vagrant VM Demo

A separate lab VM can be provisioned with:

```sh
vagrant up
```

It installs the agent, configures certs, and starts the service via systemd.  The Vagrantfile now
creates a private network (`192.168.122.10`) and forwards ports 8080/9100 to the host, so you
can reach the agent either via `localhost:8080` or the VM address.

### Troubleshooting connectivity

If the controller UI shows timeouts when targeting `192.168.122.10`:

1. confirm the VM is up and agent service running:
   ```sh
   vagrant ssh -c 'systemctl status patch-agent'
   ```
2. test from the host that the port is reachable:
   ```sh
   curl -v --cacert certs/ca.crt \  
        --cert certs/client.crt --key certs/client.key \
        https://192.168.122.10:8080/health
   # or use http if you skipped TLS
   curl http://127.0.0.1:8080/health
   ```
3. check that firewall inside VM isn’t blocking (UFW/iptables).  disable if necessary:
   ```sh
   vagrant ssh -c 'sudo ufw disable'
   ```
4. if using a non‑privileged network (e.g. libvirt NAT), make sure the host can reach the IP
   - on Windows/WSL you may need to create a host‑only adapter or use the forwarded port instead

Once connectivity is restored, the controller will be able to call `/updates`, `/install_selected`,
`/snapshots` etc. without timeout errors.


## Cleanup

```sh
make clean   # stops containers, removes volumes, deletes certs
```

For the VM:

```sh
vagrant destroy -f
```

## Production Notes

- The controller and agent images here are prototypes; for production rebuild them with
  proper base images, hardened configurations, and signed packages.
- Use Docker secrets or a vault to manage TLS keys instead of volume mounts.
- Replace the Flask dev server with gunicorn/nginx in production.
- Move inventory to a persistent store and secure the controller UI with authentication.

---

This runbook should enable any operator to fully exercise the patching prototype entirely
within Docker, fulfilling the "everything automated" requirement.  Additional tasks such as
snapshot testing on physical hosts and integration with an existing Ansible infrastructure
are outside the scope of this document.
