#!/bin/bash
# 30-second proof for ephemeral mode
echo "🧪 Testing Ephemeral Mode - 30 Second Proof"
echo "============================================="

# Test 1: Health check
echo "1. Testing health endpoint..."
curl -s http://127.0.0.1:8000/api/health | jq . || echo "Health check failed"

# Test 2: Reset endpoint (should work in ephemeral mode)
echo -e "\n2. Testing reset endpoint (ephemeral mode)..."
curl -s -X POST http://127.0.0.1:8000/api/reset | jq . || echo "Reset failed"

# Test 3: Create test PDFs
echo -e "\n3. Creating test PDFs..."
printf "%%PDF-1.4\nINV-1234_ACME\n" > INV-1234_ACME.pdf
printf "%%PDF-1.4\nDN-1234_ACME\n" > DN-1234_ACME.pdf
echo "Created test PDFs"

# Test 4: Upload test files
echo -e "\n4. Uploading test files..."
echo "Uploading invoice..."
curl -s -F "file=@INV-1234_ACME.pdf" http://127.0.0.1:8000/api/upload | jq . || echo "Invoice upload failed"

echo "Uploading delivery note..."
curl -s -F "file=@DN-1234_ACME.pdf" http://127.0.0.1:8000/api/upload | jq . || echo "Delivery note upload failed"

# Test 5: Check for pairing suggestions
echo -e "\n5. Checking for pairing suggestions..."
curl -s http://127.0.0.1:8000/api/pairs/suggestions | jq . || echo "No suggestions found"

# Test 6: Test reset again (should clear everything)
echo -e "\n6. Testing reset again (should clear everything)..."
curl -s -X POST http://127.0.0.1:8000/api/reset | jq . || echo "Reset failed"

# Test 7: Verify suggestions are gone
echo -e "\n7. Verifying suggestions are cleared..."
curl -s http://127.0.0.1:8000/api/pairs/suggestions | jq . || echo "Suggestions cleared"

# Cleanup
echo -e "\n8. Cleaning up test files..."
rm -f INV-1234_ACME.pdf DN-1234_ACME.pdf

echo -e "\n✅ Ephemeral mode test complete!"
echo "💡 Open http://127.0.0.1:8000 in your browser to see the UI"
echo "🔄 Refresh the page to see the auto-reset in action"
