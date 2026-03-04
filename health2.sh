#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "=== Users ==="
curl -s http://localhost:8000/api/users/ -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
users=json.load(sys.stdin)
names = [u["username"]+"("+u["role"]+")" for u in users]
print(str(len(users)) + " users: " + str(names))
'

echo "=== License ==="
curl -s http://localhost:8000/api/license/status -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
d=json.load(sys.stdin)
print("Status: " + d["status"] + ", Days left: " + str(d.get("days_remaining","?")))
'

echo "=== Git Repos ==="
curl -s http://localhost:8000/api/git/repos -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
repos=json.load(sys.stdin)
names = [r["name"]+"("+r["provider"]+")" for r in repos]
print(str(len(repos)) + " repos: " + str(names))
'

echo "=== CI/CD Pipelines ==="
curl -s http://localhost:8000/api/cicd/pipelines -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
p=json.load(sys.stdin)
names = [x["name"] for x in p]
print(str(len(p)) + " pipelines: " + str(names))
'

echo "=== CI/CD Builds ==="
curl -s http://localhost:8000/api/cicd/builds -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
b=json.load(sys.stdin)
print(str(len(b)) + " builds")
'

echo "=== RBAC Features ==="
curl -s http://localhost:8000/api/auth/permissions-matrix -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
d=json.load(sys.stdin)
print(str(len(d.get("features",[]))) + " features: " + str(d.get("features",[])))
'
