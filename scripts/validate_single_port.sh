#!/usr/bin/env bash
set -euo pipefail

echo "🚀 OWLIN 60-Second Validation"
echo "=============================="

# 1) Boot single-port demo
echo "1️⃣  Starting single-port demo..."
VITE_API_BASE_URL=http://127.0.0.1:8000 OWLIN_SINGLE_PORT=1 bash scripts/run_single_port.sh &
DEMO_PID=$!

# Wait for startup
echo "   Waiting for startup..."
sleep 5

# 2) Prove UI + API + Upload
echo "2️⃣  Running smoke tests..."
bash scripts/smoke_single_port.sh

# 3) Deep-link sanity (served by SPA fallback)
echo "3️⃣  Testing deep links..."
DASHBOARD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/dashboard)
INVOICES_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/invoices)

if [ "$DASHBOARD_STATUS" = "200" ] && [ "$INVOICES_STATUS" = "200" ]; then
    echo "   ✅ Deep links working (SPA fallback)"
else
    echo "   ❌ Deep links failed (Dashboard: $DASHBOARD_STATUS, Invoices: $INVOICES_STATUS)"
    exit 1
fi

# 4) Test API endpoints
echo "4️⃣  Testing API endpoints..."
curl -sf http://127.0.0.1:8000/api/health | grep -q '"status":"ok"'
echo "   ✅ API health check passed"

# 5) Test file upload with OCR
echo "5️⃣  Testing file upload with OCR..."
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

UPLOAD_RESPONSE=$(curl -sf -X POST http://127.0.0.1:8000/api/upload -F "file=@$TMPPDF")
if echo "$UPLOAD_RESPONSE" | grep -q '"ok":true'; then
    echo "   ✅ File upload working"
    if echo "$UPLOAD_RESPONSE" | grep -q '"ocr"'; then
        echo "   ✅ OCR data included in response"
    else
        echo "   ⚠️  OCR data not found (expected for mock)"
    fi
else
    echo "   ❌ File upload failed"
    exit 1
fi

rm -f "$TMPPDF"

# 6) Check log files
echo "6️⃣  Checking log files..."
if [ -f "data/logs/app.log" ]; then
    echo "   ✅ Log files created"
    echo "   📝 Recent logs:"
    tail -3 data/logs/app.log | sed 's/^/     /'
else
    echo "   ⚠️  Log files not found"
fi

echo ""
echo "🎉 60-second validation COMPLETE!"
echo "   Frontend: http://127.0.0.1:8000"
echo "   API: http://127.0.0.1:8000/api/health"
echo "   Logs: data/logs/app.log"
echo ""
echo "💡 To stop the demo: kill $DEMO_PID"
