# Test Backend 409 Duplicate Handling
Write-Host "🧪 Testing Backend 409 Duplicate Handling" -ForegroundColor Green

$baseUrl = "http://127.0.0.1:8001"

# Test 1: Create first invoice
Write-Host "`n1. Creating first invoice..." -ForegroundColor Yellow
$invoiceData = @{
    supplier_id = "sup1"
    supplier_name = "Acme"
    invoice_date = "2025-09-13"
    invoice_ref = "INV-TEST-001"
    currency = "GBP"
    lines = @(
        @{
            description = "Beer"
            outer_qty = 2
            items_per_outer = 24
            unit_price = 1.05
            vat_rate_percent = 20
        }
    )
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/manual/invoices" -Method POST -Body $invoiceData -ContentType "application/json"
    Write-Host "✅ First invoice created: $($response.id)" -ForegroundColor Green
} catch {
    Write-Host "❌ First invoice creation failed: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Try duplicate (should return 409)
Write-Host "`n2. Testing duplicate invoice (should return 409)..." -ForegroundColor Yellow
$duplicateData = @{
    supplier_id = "sup1"
    supplier_name = "Acme"
    invoice_date = "2025-09-13"
    invoice_ref = "INV-TEST-001"  # Same ref
    currency = "GBP"
    lines = @(
        @{
            description = "Beer"
            outer_qty = 1
            items_per_outer = 24
            unit_price = 1.05
            vat_rate_percent = 20
        }
    )
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/manual/invoices" -Method POST -Body $duplicateData -ContentType "application/json"
    Write-Host "❌ Duplicate should have failed but didn't!" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Write-Host "✅ Duplicate correctly rejected with 409" -ForegroundColor Green
    } else {
        Write-Host "❌ Expected 409 but got: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}

# Test 3: Test delivery note duplicate
Write-Host "`n3. Testing delivery note duplicate..." -ForegroundColor Yellow
$dnData = @{
    supplier_id = "sup1"
    supplier_name = "Acme"
    delivery_date = "2025-09-13"
    delivery_ref = "DN-TEST-001"
    currency = "GBP"
    lines = @(
        @{
            description = "Beer"
            outer_qty = 2
            items_per_outer = 24
            unit_price = 1.05
            vat_rate_percent = 20
        }
    )
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/manual/delivery-notes" -Method POST -Body $dnData -ContentType "application/json"
    Write-Host "✅ First delivery note created: $($response.id)" -ForegroundColor Green
} catch {
    Write-Host "❌ First delivery note creation failed: $_" -ForegroundColor Red
}

# Try duplicate DN
$duplicateDnData = $dnData | ConvertFrom-Json | ConvertTo-Json -Depth 3
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/manual/delivery-notes" -Method POST -Body $duplicateDnData -ContentType "application/json"
    Write-Host "❌ Duplicate DN should have failed but didn't!" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Write-Host "✅ Duplicate DN correctly rejected with 409" -ForegroundColor Green
    } else {
        Write-Host "❌ Expected 409 but got: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}

Write-Host "`n🎉 Backend 409 tests complete!" -ForegroundColor Green
Write-Host "The overlay should now handle duplicates gracefully with inline errors." -ForegroundColor Cyan
