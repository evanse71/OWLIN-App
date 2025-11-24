param([string]$Url = "http://127.0.0.1:8000/invoices")

Write-Host "[SMOKE_SPA] Testing SPA fallback at: $Url" -ForegroundColor Cyan

try {
    $inv = Invoke-WebRequest $Url -UseBasicParsing
    
    if ($inv.StatusCode -ne 200) {
        Write-Host "❌ SPA fallback failed: HTTP $($inv.StatusCode)" -ForegroundColor Red
        exit 1
    }
    
    if ($inv.Content -notmatch "<div") {
        Write-Host "❌ SPA fallback failed: Response is not HTML" -ForegroundColor Red
        Write-Host "   Content-Type: $($inv.Headers.'Content-Type')" -ForegroundColor Gray
        Write-Host "   Content length: $($inv.Content.Length) bytes" -ForegroundColor Gray
        exit 1
    }
    
    if ($inv.Content -match "owlin-desk-harmony") {
        Write-Host "✅ SPA route $Url returns HTML (index.html)" -ForegroundColor Green
        Write-Host "   Status: $($inv.StatusCode)" -ForegroundColor Gray
        Write-Host "   Content-Type: $($inv.Headers.'Content-Type')" -ForegroundColor Gray
        exit 0
    } else {
        Write-Host "⚠️  SPA route returns HTML but may not be index.html" -ForegroundColor Yellow
        exit 0  # Still pass, but warn
    }
} catch {
    Write-Host "❌ SPA fallback failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

