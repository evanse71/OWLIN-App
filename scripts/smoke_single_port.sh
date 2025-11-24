#!/usr/bin/env bash
set -euo pipefail

echo "🧪 OWLIN Single-Port Smoke Test"
echo "==============================="

# 1) Root serves UI
echo "1️⃣  Testing frontend serving..."
curl -sS http://127.0.0.1:8000 | grep -qi "<!doctype html"
echo "   ✅ Frontend HTML served"

# 2) Health ok
echo "2️⃣  Testing API health..."
curl -sf http://127.0.0.1:8000/api/health | grep -q '"status":"ok"'
echo "   ✅ API health check passed"

# 3) Upload works
echo "3️⃣  Testing file upload..."
TMPPDF="$(mktemp).pdf"
printf '%s' '%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Count 0 >>
endobj
trailer << /Root 1 0 R >>
%%EOF' > "$TMPPDF"
curl -sf -X POST http://127.0.0.1:8000/api/upload -F "file=@$TMPPDF" | grep -q '"ok":'
echo "   ✅ File upload working"

# Cleanup
rm -f "$TMPPDF"

echo ""
echo "🎉 Single-port smoke test PASSED!"
echo "   Frontend: http://127.0.0.1:8000"
echo "   API: http://127.0.0.1:8000/api/health"
