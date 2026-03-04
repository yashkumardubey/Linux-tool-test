#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "=== Users raw ==="
curl -s http://localhost:8000/api/users -H "Authorization: Bearer $TOKEN" | head -c 500

echo ""
echo "=== RBAC raw ==="
curl -s http://localhost:8000/api/auth/rbac/matrix -H "Authorization: Bearer $TOKEN" | head -c 500

echo ""
echo "=== DB tables ==="
echo root | sudo -S -u postgres psql -d patchmaster -c "SELECT tablename FROM pg_tables WHERE schemaname='public';" 2>/dev/null | grep -v 'password\|row'
