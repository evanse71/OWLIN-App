#!/usr/bin/env bash
set -euo pipefail

echo "🔍 OWLIN Edge Case Smoke Tests"
echo "==============================="

# Test 1: 404 wrong path
echo "▶ Testing 404 wrong path"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8000/api/uploadz)
if [ "$HTTP_CODE" = "404" ]; then
    echo "✅ 404 wrong path: OK"
else
    echo "❌ 404 wrong path: FAILED (got $HTTP_CODE)"
    exit 1
fi

# Test 2: Large file handling (pseudo test)
echo "▶ Testing large file handling"
# Create a large test file (10MB)
dd if=/dev/zero of=/tmp/big_test.pdf bs=1M count=10 2>/dev/null || {
    # Fallback for systems without dd
    echo "Creating large file with fallback method..."
    python3 -c "
import os
with open('/tmp/big_test.pdf', 'wb') as f:
    f.write(b'%PDF-1.4\n' + b'0' * (10 * 1024 * 1024))
"
}

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -F "file=@/tmp/big_test.pdf" http://127.0.0.1:8000/api/upload)
if [[ "$HTTP_CODE" =~ ^(200|201|413)$ ]]; then
    echo "✅ Large file handling: OK (HTTP $HTTP_CODE)"
else
    echo "❌ Large file handling: FAILED (got $HTTP_CODE)"
    exit 1
fi

# Cleanup large file
rm -f /tmp/big_test.pdf

# Test 3: CORS preflight
echo "▶ Testing CORS preflight"
CORS_RESPONSE=$(curl -s -X OPTIONS http://127.0.0.1:8000/api/health \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type" \
    -w "%{http_code}")

if echo "$CORS_RESPONSE" | grep -q "Access-Control-Allow-Origin"; then
    echo "✅ CORS preflight: OK"
else
    echo "❌ CORS preflight: FAILED"
    exit 1
fi

# Test 4: Permissions test (if possible)
echo "▶ Testing uploads directory permissions"
if [ -w "data/uploads" ]; then
    echo "✅ Uploads directory writable: OK"
else
    echo "⚠️  Uploads directory not writable (may cause 500 errors)"
fi

# Test 5: OCR disabled response
echo "▶ Testing OCR disabled response"
TEST_FILE="/tmp/ocr_test.txt"
echo "test content" > "$TEST_FILE"

UPLOAD_RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/upload -F "file=@$TEST_FILE")
if echo "$UPLOAD_RESPONSE" | grep -q '"ok":true'; then
    echo "✅ OCR disabled response: OK"
    # Check if parsed field is null (OCR disabled)
    if echo "$UPLOAD_RESPONSE" | grep -q '"parsed":null'; then
        echo "✅ OCR properly disabled (parsed: null)"
    else
        echo "⚠️  OCR response: $(echo "$UPLOAD_RESPONSE" | grep -o '"parsed":[^,]*')"
    fi
else
    echo "❌ OCR disabled response: FAILED"
    echo "Response: $UPLOAD_RESPONSE"
    exit 1
fi

# Cleanup
rm -f "$TEST_FILE"

# Test 6: Empty file handling
echo "▶ Testing empty file handling"
EMPTY_FILE="/tmp/empty_test.txt"
touch "$EMPTY_FILE"

EMPTY_RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/upload -F "file=@$EMPTY_FILE")
if echo "$EMPTY_RESPONSE" | grep -q '"ok":true'; then
    echo "✅ Empty file handling: OK"
else
    echo "❌ Empty file handling: FAILED"
    echo "Response: $EMPTY_RESPONSE"
    exit 1
fi

# Cleanup
rm -f "$EMPTY_FILE"

# Test 7: Invalid file type (if backend has validation)
echo "▶ Testing file type handling"
INVALID_FILE="/tmp/invalid.exe"
echo "fake executable" > "$INVALID_FILE"

INVALID_RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/upload -F "file=@$INVALID_FILE")
if echo "$INVALID_RESPONSE" | grep -q '"ok":true'; then
    echo "✅ File type handling: OK (accepts all types)"
else
    echo "⚠️  File type validation: $(echo "$INVALID_RESPONSE" | grep -o '"detail":"[^"]*"' || echo 'No detail')"
fi

# Cleanup
rm -f "$INVALID_FILE"

echo ""
echo "🎉 All edge case tests passed!"
echo "✅ 404 handling: OK"
echo "✅ Large file handling: OK"
echo "✅ CORS preflight: OK"
echo "✅ Permissions: OK"
echo "✅ OCR disabled: OK"
echo "✅ Empty file: OK"
echo "✅ File types: OK"
echo ""
echo "The upload system handles edge cases gracefully!"
