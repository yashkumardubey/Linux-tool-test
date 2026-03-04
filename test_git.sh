#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
echo "=== Token: ${TOKEN:0:20}... ==="

echo "=== Create repo ==="
curl -s -X POST http://localhost:8000/api/git/repos \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"test-repo","provider":"github","repo_full_name":"torvalds/linux","default_branch":"master","auth_token":""}'

echo ""
echo "=== List repos ==="
curl -s http://localhost:8000/api/git/repos -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "=== Test connection repo 1 ==="
curl -s -X POST http://localhost:8000/api/git/repos/1/test -H "Authorization: Bearer $TOKEN"

echo ""
echo "=== Frontend check ==="
curl -s -o /dev/null -w 'Frontend HTTP %{http_code}\n' http://localhost:3000

echo ""
echo "=== DONE ==="
