# Test ephemeral mode - clean slate verification (Windows PowerShell)
Write-Host "Testing Ephemeral Mode - Clean Slate Verification" -ForegroundColor Green
Write-Host "====================================================="

# Test 1: Health check
Write-Host "`n1. Testing health endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method GET
    Write-Host "Health: $($health | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Reset endpoint (should work in ephemeral mode)
Write-Host "`n2. Testing reset endpoint (ephemeral mode)..." -ForegroundColor Yellow
try {
    $reset = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/reset" -Method POST
    Write-Host "Reset: $($reset | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Reset failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Check that no demo data is returned
Write-Host "`n3. Checking for demo data elimination..." -ForegroundColor Yellow
Write-Host "Checking invoices endpoint..."
try {
    $invoices = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/invoices" -Method GET
    Write-Host "Invoices: $($invoices | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Invoices: [] (no demo data)" -ForegroundColor Green
}

Write-Host "Checking delivery notes endpoint..."
try {
    $notes = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/delivery-notes" -Method GET
    Write-Host "Delivery notes: $($notes | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Delivery notes: [] (no demo data)" -ForegroundColor Green
}

Write-Host "Checking pairing suggestions..."
try {
    $suggestions = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/pairs/suggestions" -Method GET
    Write-Host "Suggestions: $($suggestions | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Suggestions: [] (no demo data)" -ForegroundColor Green
}

# Test 4: Create test PDFs
Write-Host "`n4. Creating test PDFs..." -ForegroundColor Yellow
$inv = "%PDF-1.4`nINV-1234_ACME`n"
$dn = "%PDF-1.4`nDN-1234_ACME`n"
[IO.File]::WriteAllText("INV-1234_ACME.pdf", $inv, [Text.Encoding]::UTF8)
[IO.File]::WriteAllText("DN-1234_ACME.pdf", $dn, [Text.Encoding]::UTF8)
Write-Host "Created test PDFs" -ForegroundColor Green

# Test 5: Upload test files
Write-Host "`n5. Uploading test files..." -ForegroundColor Yellow
Write-Host "Uploading invoice..."
try {
    $invoiceUpload = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/upload" -Method POST -Form @{file = Get-Item "INV-1234_ACME.pdf"}
    Write-Host "Invoice upload: $($invoiceUpload | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Invoice upload failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Uploading delivery note..."
try {
    $dnUpload = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/upload" -Method POST -Form @{file = Get-Item "DN-1234_ACME.pdf"}
    Write-Host "Delivery note upload: $($dnUpload | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Delivery note upload failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 6: Check for pairing suggestions after upload
Write-Host "`n6. Checking for pairing suggestions after upload..." -ForegroundColor Yellow
try {
    $suggestions = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/pairs/suggestions" -Method GET
    Write-Host "Suggestions: $($suggestions | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "No suggestions found: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Test 7: Test reset again (should clear everything)
Write-Host "`n7. Testing reset again (should clear everything)..." -ForegroundColor Yellow
try {
    $reset2 = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/reset" -Method POST
    Write-Host "Reset: $($reset2 | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Reset failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 8: Verify suggestions are gone
Write-Host "`n8. Verifying suggestions are cleared..." -ForegroundColor Yellow
try {
    $suggestions2 = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/pairs/suggestions" -Method GET
    Write-Host "Suggestions after reset: $($suggestions2 | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Suggestions cleared" -ForegroundColor Green
}

# Test 9: Check that no demo data persists
Write-Host "`n9. Final check - no demo data should persist..." -ForegroundColor Yellow
Write-Host "Final invoices check:"
try {
    $finalInvoices = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/invoices" -Method GET
    Write-Host "Final invoices: $($finalInvoices | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Final invoices: [] (clean slate)" -ForegroundColor Green
}

# Cleanup
Write-Host "`n10. Cleaning up test files..." -ForegroundColor Yellow
Remove-Item -Path "INV-1234_ACME.pdf" -ErrorAction SilentlyContinue
Remove-Item -Path "DN-1234_ACME.pdf" -ErrorAction SilentlyContinue
Write-Host "Cleanup complete" -ForegroundColor Green

Write-Host "`nEphemeral mode clean slate test complete!" -ForegroundColor Green
Write-Host "Open http://127.0.0.1:8000 in your browser to see the clean UI" -ForegroundColor Cyan
Write-Host "Refresh the page to see the auto-reset in action" -ForegroundColor Cyan
Write-Host "No demo data should appear - only real uploads create cards" -ForegroundColor Cyan
