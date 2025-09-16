#!/usr/bin/env bash
set -euo pipefail

API="http://localhost:8001/health"
DOCS="http://localhost:8001/docs"
APP="http://localhost:3000"

echo "==> Checking backend: $API"
RESP=$(curl -sS "$API" || true)
echo "Backend /health → $RESP"
echo "$RESP" | grep -q '"status":"ok"' || { echo "FAIL: backend not healthy"; exit 1; }

echo "==> Checking OpenAPI docs: $DOCS"
curl -sS "$DOCS" >/dev/null || { echo "FAIL: /docs unreachable"; exit 1; }

echo "==> Checking frontend: $APP"
curl -sSI "$APP" | head -n1 || { echo "WARN: frontend not ready yet"; exit 0; }
