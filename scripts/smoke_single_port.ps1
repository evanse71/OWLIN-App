$ErrorActionPreference = "Stop"

Write-Host "🧪 OWLIN Single-Port Smoke Test" -ForegroundColor Green
Write-Host "===============================" -ForegroundColor Green

# 1) Root serves UI
Write-Host "1️⃣  Testing frontend serving..." -ForegroundColor Yellow
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000" -UseBasicParsing
if ($response.Content -match "<!doctype html") {
    Write-Host "   ✅ Frontend HTML served" -ForegroundColor Green
} else {
    Write-Host "   ❌ Frontend not serving HTML" -ForegroundColor Red
    exit 1
}

# 2) Health ok
Write-Host "2️⃣  Testing API health..." -ForegroundColor Yellow
$health = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing
if ($health.Content -match '"status":"ok"') {
    Write-Host "   ✅ API health check passed" -ForegroundColor Green
} else {
    Write-Host "   ❌ API health check failed" -ForegroundColor Red
    exit 1
}

# 3) Upload works
Write-Host "3️⃣  Testing file upload..." -ForegroundColor Yellow
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
    if ($uploadResponse.Content -match '"ok":') {
        Write-Host "   ✅ File upload working" -ForegroundColor Green
    } else {
        Write-Host "   ❌ File upload failed" -ForegroundColor Red
        exit 1
    }
} finally {
    Remove-Item $tempFile -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "🎉 Single-port smoke test PASSED!" -ForegroundColor Green
Write-Host "   Frontend: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "   API: http://127.0.0.1:8000/api/health" -ForegroundColor Cyan
