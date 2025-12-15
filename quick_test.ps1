# Quick test - just run this after restarting backend manually
$filename = "2e1c65d2-ea57-4fc5-ab6c-5ed67d45dabc__26.08INV.jpeg"
$result = Invoke-RestMethod -Uri "http://127.0.0.1:5176/api/dev/ocr-test?filename=$filename" -Method GET -TimeoutSec 90
Write-Host "Status: $($result.status)"
Write-Host "Items: $($result.line_items.Count)"
Write-Host "Coverage: $($result.value_coverage)"
if ($result.error) { Write-Host "Error: $($result.error)" }
$result | ConvertTo-Json -Depth 10 | Out-File "phase6_test_result.json" -Encoding utf8
