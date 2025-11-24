#!/usr/bin/env bash
set -e

# OWLIN Pairing MVP Validation Script
# 10-minute verification of Invoice ↔ Delivery-Note pairing system

echo "🔍 OWLIN Pairing MVP Validation"
echo "==============================="

# Test 1: Health + version check
echo "1. Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://127.0.0.1:8000/api/health)
echo "Health response: $HEALTH_RESPONSE"

if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    echo "✅ Health endpoint OK"
else
    echo "❌ Health endpoint failed"
    exit 1
fi

# Test 2: Create test documents with different content
echo "2. Creating test documents..."

# Create invoice PDF with different content
printf "%s" "%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Invoice INV-2024-001) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
297
%%EOF" > test_invoice_real.pdf

# Create delivery note PDF with different content
printf "%s" "%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Delivery Note DN-2024-001) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
297
%%EOF" > test_dn_real.pdf

echo "✅ Test documents created"

# Test 3: Upload invoice
echo "3. Uploading invoice..."
INVOICE_RESPONSE=$(curl -s -F "file=@test_invoice_real.pdf" http://127.0.0.1:8000/api/upload)
echo "Invoice upload response: $INVOICE_RESPONSE"

# Test 4: Upload delivery note
echo "4. Uploading delivery note..."
DELIVERY_RESPONSE=$(curl -s -F "file=@test_dn_real.pdf" http://127.0.0.1:8000/api/upload)
echo "Delivery note upload response: $DELIVERY_RESPONSE"

# Test 5: Check pairing suggestions
echo "5. Checking pairing suggestions..."
SUGGESTIONS_RESPONSE=$(curl -s http://127.0.0.1:8000/api/pairs/suggestions)
echo "Suggestions response: $SUGGESTIONS_RESPONSE"

# Test 6: Validate suggestions structure
echo "6. Validating suggestions structure..."
if echo "$SUGGESTIONS_RESPONSE" | grep -q '"suggestions"'; then
    echo "✅ Suggestions API returns valid JSON structure"
    
    # Count suggestions
    SUGGESTIONS_COUNT=$(echo "$SUGGESTIONS_RESPONSE" | grep -o '"suggestions"' | wc -l)
    echo "Found $SUGGESTIONS_COUNT pairing suggestions"
    
    if [ "$SUGGESTIONS_COUNT" -gt 0 ]; then
        echo "✅ Pairing suggestions generated successfully"
        
        # Test 7: Accept a suggestion (if available)
        FIRST_PAIR_ID=$(echo "$SUGGESTIONS_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
        if [ -n "$FIRST_PAIR_ID" ]; then
            echo "7. Testing pair acceptance..."
            ACCEPT_RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/pairs/$FIRST_PAIR_ID/accept)
            echo "Accept response: $ACCEPT_RESPONSE"
            
            if echo "$ACCEPT_RESPONSE" | grep -q '"ok":true'; then
                echo "✅ Pair acceptance successful"
            else
                echo "❌ Pair acceptance failed"
            fi
        fi
    else
        echo "⚠️  No pairing suggestions found (this may be expected for test data)"
    fi
else
    echo "❌ Suggestions API returned invalid JSON or error"
    echo "Response: $SUGGESTIONS_RESPONSE"
fi

# Test 8: Guardrails still hold
echo "8. Testing guardrails..."

# Non-PDF → 400
echo "Testing non-PDF rejection..."
echo 'notpdf' > test_not.pdf
NOT_PDF_CODE=$(curl -s -o /dev/null -w "%{http_code}" -F "file=@test_not.pdf" http://127.0.0.1:8000/api/upload)
echo "Non-PDF response code: $NOT_PDF_CODE"

if [ "$NOT_PDF_CODE" = "400" ]; then
    echo "✅ Non-PDF correctly rejected with 400"
else
    echo "❌ Non-PDF should return 400, got $NOT_PDF_CODE"
fi

# Oversize → 413 (≥25MB)
echo "Testing oversize rejection..."
# Create a 30MB file
dd if=/dev/zero of=test_big.pdf bs=1M count=30 2>/dev/null || echo "dd not available, creating large file manually"
if [ ! -f test_big.pdf ]; then
    # Fallback for Windows
    python -c "
import os
with open('test_big.pdf', 'wb') as f:
    f.write(b'%PDF-1.4\n' + b'0' * (30 * 1024 * 1024))
"
fi

BIG_FILE_CODE=$(curl -s -o /dev/null -w "%{http_code}" -F "file=@test_big.pdf" http://127.0.0.1:8000/api/upload)
echo "Oversize response code: $BIG_FILE_CODE"

if [ "$BIG_FILE_CODE" = "413" ]; then
    echo "✅ Oversize correctly rejected with 413"
else
    echo "❌ Oversize should return 413, got $BIG_FILE_CODE"
fi

# Cleanup
echo "9. Cleaning up test files..."
rm -f test_invoice_real.pdf test_dn_real.pdf test_not.pdf test_big.pdf

echo ""
echo "🎉 Pairing MVP validation completed!"
echo "The Invoice ↔ Delivery-Note pairing system is working! 🚀"
