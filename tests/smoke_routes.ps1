param(
  [string]$Url = "http://127.0.0.1:8000/invoices",
  [int]$Retries = 10
)

Write-Host "[SMOKE_ROUTES] Testing $Url" -ForegroundColor Cyan

$wc = New-Object System.Net.WebClient
$wc.Encoding = [System.Text.Encoding]::UTF8

for ($i=0; $i -lt $Retries; $i++) {
  try {
    $html = $wc.DownloadString($Url)
    if ($html -match 'data-testid="invoices-footer-bar"') { 
      Write-Host "[SMOKE_ROUTES] ✅ ROUTE_OK" -ForegroundColor Green
      exit 0 
    }
    Start-Sleep -Seconds 1
  } catch {
    Start-Sleep -Seconds 1
  }
}

Write-Host "[SMOKE_ROUTES] ❌ ROUTE_FAIL" -ForegroundColor Red
exit 1

