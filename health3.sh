#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "=== Users (raw) ==="
curl -s http://localhost:8000/api/users/ -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
d=json.load(sys.stdin)
if isinstance(d, list):
    print(str(len(d)) + " users")
    for u in d[:5]:
        if isinstance(u, dict):
            print("  " + u.get("username","?") + " (" + u.get("role","?") + ")")
        else:
            print("  item type: " + str(type(u)))
elif isinstance(d, dict):
    users = d.get("users", d.get("items", [d]))
    print(str(len(users)) + " users")
    for u in users[:5]:
        print("  " + u.get("username","?") + " (" + u.get("role","?") + ")")
'

echo "=== License (raw) ==="
curl -s http://localhost:8000/api/license/status -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
d=json.load(sys.stdin)
print(str(d)[:300])
'

echo "=== RBAC (raw) ==="
curl -s http://localhost:8000/api/auth/permissions-matrix -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
d=json.load(sys.stdin)
print(str(list(d.keys()))[:300])
'
