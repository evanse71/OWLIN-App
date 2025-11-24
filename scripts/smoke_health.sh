#!/usr/bin/env bash
set -e

# OWLIN Health Smoke Test
# One-command validation of all health banner features

ok() { echo "✅ $1"; }
bad() { echo "❌ $1"; exit 1; }

echo "🔍 OWLIN Health Smoke Test"
echo "=========================="

# Health endpoint
curl -fsS http://127.0.0.1:8000/api/health >/dev/null && ok "health 200" || bad "health endpoint down"

# Deep link (SPA fallback)
curl -I -s http://127.0.0.1:8000/dashboard | grep -q "200" && ok "deep link 200" || bad "deep link failed"

# Upload functionality
printf "%s" "%PDF-1.4\n%%EOF" > /tmp/t.pdf
curl -fsS -F "file=@/tmp/t.pdf" http://127.0.0.1:8000/api/upload >/dev/null && ok "upload ok" || bad "upload failed"

# Non-PDF rejection (400)
echo "hello" > /tmp/no.pdf
test "$(curl -s -o /dev/null -w "%{http_code}" -F "file=@/tmp/no.pdf" http://127.0.0.1:8000/api/upload)" = "400" && ok "non-pdf 400" || bad "non-pdf not rejected"

# Oversize rejection (413)
dd if=/dev/zero of=/tmp/big.pdf bs=1M count=30 >/dev/null 2>&1
test "$(curl -s -o /dev/null -w "%{http_code}" -F "file=@/tmp/big.pdf" http://127.0.0.1:8000/api/upload)" = "413" && ok "oversize 413" || bad "oversize not rejected"

echo ""
echo "🎉 All health checks PASSED!"
echo "Health banner is bulletproof! 🛡️"
