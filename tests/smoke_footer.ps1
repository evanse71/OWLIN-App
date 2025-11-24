param([string]$Url="http://127.0.0.1:8000/invoices")

Write-Host "[SMOKE] Testing footer presence at: $Url" -ForegroundColor Cyan

try {
    Start-Sleep -Seconds 1
    
    $wc = New-Object System.Net.WebClient
    $wc.Encoding = [System.Text.Encoding]::UTF8
    $html = $wc.DownloadString($Url)
    
    if ($html -match 'data-testid="invoices-footer-bar"') {
        Write-Host "[SMOKE] ✅ FOOTER_PRESENT" -ForegroundColor Green
        Write-Host "       Found: data-testid=`"invoices-footer-bar`" in HTML" -ForegroundColor Gray
        exit 0
    } else {
        Write-Host "[SMOKE] ❌ FOOTER_MISSING" -ForegroundColor Red
        Write-Host "       data-testid=`"invoices-footer-bar`" not found in HTML response" -ForegroundColor Gray
        Write-Host "       HTML length: $($html.Length) bytes" -ForegroundColor Gray
        exit 1
    }
} catch {
    Write-Host "[SMOKE] ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

