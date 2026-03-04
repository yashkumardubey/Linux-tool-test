#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "=== Users ==="
curl -s http://localhost:8000/api/auth/users -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
d=json.load(sys.stdin)
for u in d:
    print("  " + u["username"] + " (" + u["role"] + ")")
print("Total: " + str(len(d)))
'

echo "=== License ==="
curl -s http://localhost:8000/api/license/status -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
d=json.load(sys.stdin)
print("  Valid: " + str(d["valid"]) + ", Plan: " + d["plan"] + ", Days left: " + str(d["days_remaining"]))
'

echo "=== Git Repos ==="
curl -s http://localhost:8000/api/git/repos -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
repos=json.load(sys.stdin)
for r in repos:
    stars = r.get("repo_meta",{}).get("stars","")
    print("  " + r["name"] + " (" + r["provider"] + ") - " + r["repo_full_name"] + " [stars: " + str(stars) + "]")
print("Total: " + str(len(repos)))
'

echo "=== CI/CD ==="
curl -s http://localhost:8000/api/cicd/pipelines -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
p=json.load(sys.stdin)
for x in p:
    print("  " + x["name"] + " (" + x["tool"] + ") - " + x["status"])
print("Pipelines: " + str(len(p)))
'
curl -s http://localhost:8000/api/cicd/builds -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
b=json.load(sys.stdin)
print("Builds: " + str(len(b)))
'

echo "=== Role Defaults ==="
curl -s http://localhost:8000/api/auth/role-defaults -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
d=json.load(sys.stdin)
feats = d.get("features",[])
print("  Features (" + str(len(feats)) + "): " + ", ".join(feats))
'

echo "=== Frontend ==="
curl -s -o /dev/null -w "  HTTP %{http_code}" http://localhost:3000
echo ""
echo "=== ALL OK ==="
