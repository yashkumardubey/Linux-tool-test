#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "=== List repos ==="
curl -s http://localhost:8000/api/git/repos -H "Authorization: Bearer $TOKEN"

echo ""
echo "=== Test connection repo 1 ==="
curl -s -X POST http://localhost:8000/api/git/repos/1/test -H "Authorization: Bearer $TOKEN"

echo ""
echo "=== Branches repo 1 ==="
curl -s http://localhost:8000/api/git/repos/1/branches -H "Authorization: Bearer $TOKEN"

echo ""
echo "=== Commits repo 1 ==="
curl -s 'http://localhost:8000/api/git/repos/1/commits?branch=master' -H "Authorization: Bearer $TOKEN"

echo ""
echo "=== Tags repo 1 ==="
curl -s http://localhost:8000/api/git/repos/1/tags -H "Authorization: Bearer $TOKEN"

echo ""
echo "=== DONE ==="
