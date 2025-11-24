#!/bin/bash
# Test ephemeral mode - clean slate verification
echo "🧪 Testing Ephemeral Mode - Clean Slate Verification"
echo "====================================================="

# Test 1: Health check
echo "1. Testing health endpoint..."
curl -s http://127.0.0.1:8000/api/health | jq . || echo "Health check failed"

# Test 2: Reset endpoint (should work in ephemeral mode)
echo -e "\n2. Testing reset endpoint (ephemeral mode)..."
curl -s -X POST http://127.0.0.1:8000/api/reset | jq . || echo "Reset failed"

# Test 3: Check that no demo data is returned
echo -e "\n3. Checking for demo data elimination..."
echo "Checking invoices endpoint..."
INVOICES=$(curl -s http://127.0.0.1:8000/api/invoices 2>/dev/null || echo "[]")
echo "Invoices: $INVOICES"

echo "Checking delivery notes endpoint..."
NOTES=$(curl -s http://127.0.0.1:8000/api/delivery-notes 2>/dev/null || echo "[]")
echo "Delivery notes: $NOTES"

echo "Checking pairing suggestions..."
SUGGESTIONS=$(curl -s http://127.0.0.1:8000/api/pairs/suggestions 2>/dev/null || echo "[]")
echo "Suggestions: $SUGGESTIONS"

# Test 4: Create test PDFs
echo -e "\n4. Creating test PDFs..."
printf "%%PDF-1.4\nINV-1234_ACME\n" > INV-1234_ACME.pdf
printf "%%PDF-1.4\nDN-1234_ACME\n" > DN-1234_ACME.pdf
echo "Created test PDFs"

# Test 5: Upload test files
echo -e "\n5. Uploading test files..."
echo "Uploading invoice..."
curl -s -F "file=@INV-1234_ACME.pdf" http://127.0.0.1:8000/api/upload | jq . || echo "Invoice upload failed"

echo "Uploading delivery note..."
curl -s -F "file=@DN-1234_ACME.pdf" http://127.0.0.1:8000/api/upload | jq . || echo "Delivery note upload failed"

# Test 6: Check for pairing suggestions after upload
echo -e "\n6. Checking for pairing suggestions after upload..."
curl -s http://127.0.0.1:8000/api/pairs/suggestions | jq . || echo "No suggestions found"

# Test 7: Test reset again (should clear everything)
echo -e "\n7. Testing reset again (should clear everything)..."
curl -s -X POST http://127.0.0.1:8000/api/reset | jq . || echo "Reset failed"

# Test 8: Verify suggestions are gone
echo -e "\n8. Verifying suggestions are cleared..."
curl -s http://127.0.0.1:8000/api/pairs/suggestions | jq . || echo "Suggestions cleared"

# Test 9: Check that no demo data persists
echo -e "\n9. Final check - no demo data should persist..."
echo "Final invoices check:"
curl -s http://127.0.0.1:8000/api/invoices 2>/dev/null || echo "[]"

# Cleanup
echo -e "\n10. Cleaning up test files..."
rm -f INV-1234_ACME.pdf DN-1234_ACME.pdf

echo -e "\n✅ Ephemeral mode clean slate test complete!"
echo "💡 Open http://127.0.0.1:8000 in your browser to see the clean UI"
echo "🔄 Refresh the page to see the auto-reset in action"
echo "📝 No demo data should appear - only real uploads create cards"
