#!/usr/bin/env bash
set -euo pipefail

echo "🔍 OWLIN E2E Smoke Test"
echo "======================="

# Test 1: Backend health check
echo "▶ Backend health"
if curl -sf http://127.0.0.1:8000/api/health | grep -q '"status":"ok"'; then
    echo "✅ Backend health: OK"
else
    echo "❌ Backend health: FAILED"
    echo "   Make sure backend is running: uvicorn backend.main:app --host 0.0.0.0 --port 8000"
    exit 1
fi

# Test 2: Upload sample PDF
echo "▶ Upload sample PDF"
TEST_FILE="/tmp/owlin_smoke.pdf"

# Create a minimal PDF for testing
printf '%s' "%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Count 0 >>
endobj
trailer << /Root 1 0 R >>
%%EOF" > "$TEST_FILE"

# Test upload endpoint
if curl -sf -X POST http://127.0.0.1:8000/api/upload -F "file=@$TEST_FILE" | grep -q '"ok":true'; then
    echo "✅ Upload test: OK"
else
    echo "❌ Upload test: FAILED"
    echo "   Check backend logs for upload errors"
    exit 1
fi

# Test 3: CORS configuration
echo "▶ CORS configuration"
if curl -sf -X OPTIONS http://127.0.0.1:8000/api/health \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type" | grep -q "Access-Control-Allow-Origin"; then
    echo "✅ CORS test: OK"
else
    echo "❌ CORS test: FAILED"
    echo "   Check CORS configuration in backend"
    exit 1
fi

# Cleanup
rm -f "$TEST_FILE"

echo ""
echo "🎉 All E2E smoke tests passed!"
echo "✅ Backend health: OK"
echo "✅ Upload endpoint: OK" 
echo "✅ CORS configuration: OK"
echo ""
echo "The upload path is working end-to-end!"
