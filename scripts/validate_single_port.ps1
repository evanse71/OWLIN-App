$ErrorActionPreference = "Stop"

Write-Host "🚀 OWLIN 60-Second Validation" -ForegroundColor Green
Write-Host "==============================" -ForegroundColor Green

# 1) Boot single-port demo
Write-Host "1️⃣  Starting single-port demo..." -ForegroundColor Yellow
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
$env:OWLIN_SINGLE_PORT = "1"

# Start the demo in background
Start-Process -FilePath "powershell" -ArgumentList "-ExecutionPolicy Bypass -File scripts\run_single_port.ps1" -WindowStyle Hidden
$DEMO_PID = $LASTEXITCODE

# Wait for startup
Write-Host "   Waiting for startup..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# 2) Prove UI + API + Upload
Write-Host "2️⃣  Running smoke tests..." -ForegroundColor Yellow
powershell -ExecutionPolicy Bypass -File scripts\smoke_single_port.ps1

# 3) Deep-link sanity (served by SPA fallback)
Write-Host "3️⃣  Testing deep links..." -ForegroundColor Yellow
try {
    $dashboardResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8000/dashboard" -UseBasicParsing
    $invoicesResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8000/invoices" -UseBasicParsing
    
    if ($dashboardResponse.StatusCode -eq 200 -and $invoicesResponse.StatusCode -eq 200) {
        Write-Host "   ✅ Deep links working (SPA fallback)" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Deep links failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "   ❌ Deep links failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 4) Test API endpoints
Write-Host "4️⃣  Testing API endpoints..." -ForegroundColor Yellow
$healthResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing
if ($healthResponse.Content -match '"status":"ok"') {
    Write-Host "   ✅ API health check passed" -ForegroundColor Green
} else {
    Write-Host "   ❌ API health check failed" -ForegroundColor Red
    exit 1
}

# 5) Test file upload with OCR
Write-Host "5️⃣  Testing file upload with OCR..." -ForegroundColor Yellow
$tempFile = [System.IO.Path]::GetTempFileName() + ".pdf"
$pdfContent = @'
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Count 0 >>
endobj
trailer << /Root 1 0 R >>
%%EOF
'@
[System.IO.File]::WriteAllText($tempFile, $pdfContent)

try {
    $boundary = [System.Guid]::NewGuid().ToString()
    $LF = "`r`n"
    $bodyLines = (
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"test.pdf`"",
        "Content-Type: application/pdf",
        "",
        [System.IO.File]::ReadAllText($tempFile),
        "--$boundary--",
        ""
    ) -join $LF
    
    $uploadResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/upload" -Method POST -Body $bodyLines -ContentType "multipart/form-data; boundary=$boundary" -UseBasicParsing
    
    if ($uploadResponse.Content -match '"ok":true') {
        Write-Host "   ✅ File upload working" -ForegroundColor Green
        if ($uploadResponse.Content -match '"ocr"') {
            Write-Host "   ✅ OCR data included in response" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  OCR data not found (expected for mock)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ❌ File upload failed" -ForegroundColor Red
        exit 1
    }
} finally {
    Remove-Item $tempFile -ErrorAction SilentlyContinue
}

# 6) Check log files
Write-Host "6️⃣  Checking log files..." -ForegroundColor Yellow
if (Test-Path "data/logs/app.log") {
    Write-Host "   ✅ Log files created" -ForegroundColor Green
    Write-Host "   📝 Recent logs:" -ForegroundColor Gray
    Get-Content "data/logs/app.log" -Tail 3 | ForEach-Object { Write-Host "     $_" -ForegroundColor Gray }
} else {
    Write-Host "   ⚠️  Log files not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 60-second validation COMPLETE!" -ForegroundColor Green
Write-Host "   Frontend: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "   API: http://127.0.0.1:8000/api/health" -ForegroundColor Cyan
Write-Host "   Logs: data/logs/app.log" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 To stop the demo: Check running processes" -ForegroundColor Gray
