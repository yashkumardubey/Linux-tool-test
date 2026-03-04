#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "=== Users ==="
curl -s http://localhost:8000/api/users/ -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json; users=json.load(sys.stdin); print(f"{len(users)} users: {[u[\"username\"]+\"(\"+u[\"role\"]+\")\" for u in users]}")'

echo "=== License ==="
curl -s http://localhost:8000/api/license/status -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f"Status: {d[\"status\"]}, Days left: {d.get(\"days_remaining\",\"?\")}")'

echo "=== Git Repos ==="
curl -s http://localhost:8000/api/git/repos -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json; repos=json.load(sys.stdin); print(f"{len(repos)} repos: {[r[\"name\"]+\"(\"+r[\"provider\"]+\")\" for r in repos]}")'

echo "=== CI/CD Pipelines ==="
curl -s http://localhost:8000/api/cicd/pipelines -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json; p=json.load(sys.stdin); print(f"{len(p)} pipelines: {[x[\"name\"] for x in p]}")'

echo "=== CI/CD Builds ==="
curl -s http://localhost:8000/api/cicd/builds -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json; b=json.load(sys.stdin); print(f"{len(b)} builds")'

echo "=== Permissions (admin) ==="
curl -s http://localhost:8000/api/auth/permissions-matrix -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json; d=json.load(sys.stdin); feats=d["features"]; print(f"{len(feats)} features: {feats}")'
