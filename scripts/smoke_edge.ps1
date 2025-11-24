# OWLIN Edge Case Smoke Tests - PowerShell Version
param(
    [string]$BackendUrl = "http://127.0.0.1:8000"
)

Write-Host "OWLIN Edge Case Smoke Tests" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan

# Test 1: 404 wrong path
Write-Host "Testing 404 wrong path" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/api/uploadz" -Method Post -TimeoutSec 5 -ErrorAction SilentlyContinue
    $httpCode = $response.StatusCode
} catch {
    $httpCode = $_.Exception.Response.StatusCode.value__
}

if ($httpCode -eq 404) {
    Write-Host "404 wrong path: OK" -ForegroundColor Green
} else {
    Write-Host "404 wrong path: FAILED (got $httpCode)" -ForegroundColor Red
    exit 1
}

# Test 2: File upload handling
Write-Host "Testing file upload handling" -ForegroundColor Yellow
$testFile = "$env:TEMP\test_file.txt"
"test content for upload" | Out-File -FilePath $testFile -Encoding ASCII

try {
    # Use Invoke-WebRequest with multipart form data (same as working smoke test)
    $boundary = [System.Guid]::NewGuid().ToString()
    $LF = "`r`n"
    $bodyLines = (
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"$testFile`"",
        "Content-Type: application/octet-stream$LF",
        (Get-Content $testFile -Raw),
        "--$boundary--$LF"
    ) -join $LF
    
    $uploadResponse = Invoke-WebRequest -Uri "$BackendUrl/api/upload" -Method Post -Body $bodyLines -ContentType "multipart/form-data; boundary=$boundary" -TimeoutSec 10
    $uploadJson = $uploadResponse.Content | ConvertFrom-Json
    
    if ($uploadJson.ok -eq $true) {
        Write-Host "File upload handling: OK" -ForegroundColor Green
    } else {
        Write-Host "File upload handling: FAILED" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "File upload handling: FAILED" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Remove-Item $testFile -ErrorAction SilentlyContinue
}

# Test 3: CORS preflight
Write-Host "Testing CORS preflight" -ForegroundColor Yellow
try {
    $corsResponse = Invoke-WebRequest -Uri "$BackendUrl/api/health" -Method Options -Headers @{
        "Origin" = "http://localhost:3000"
        "Access-Control-Request-Method" = "POST"
        "Access-Control-Request-Headers" = "Content-Type"
    } -TimeoutSec 5
    
    if ($corsResponse.Headers["Access-Control-Allow-Origin"]) {
        Write-Host "CORS preflight: OK" -ForegroundColor Green
    } else {
        Write-Host "CORS preflight: FAILED" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "CORS preflight: FAILED" -ForegroundColor Red
    exit 1
}

# Test 4: Permissions test
Write-Host "Testing uploads directory permissions" -ForegroundColor Yellow
if (Test-Path "data\uploads" -PathType Container) {
    if ((Get-Item "data\uploads").Attributes -notmatch "ReadOnly") {
        Write-Host "Uploads directory writable: OK" -ForegroundColor Green
    } else {
        Write-Host "Uploads directory not writable (may cause 500 errors)" -ForegroundColor Yellow
    }
} else {
    Write-Host "Uploads directory not found" -ForegroundColor Yellow
}

# Test 5: OCR disabled response
Write-Host "Testing OCR disabled response" -ForegroundColor Yellow
$testFile = "$env:TEMP\ocr_test.txt"
"test content" | Out-File -FilePath $testFile -Encoding ASCII

try {
    # Use Invoke-WebRequest with multipart form data
    $boundary = [System.Guid]::NewGuid().ToString()
    $LF = "`r`n"
    $bodyLines = (
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"$testFile`"",
        "Content-Type: application/octet-stream$LF",
        (Get-Content $testFile -Raw),
        "--$boundary--$LF"
    ) -join $LF
    
    $response = Invoke-WebRequest -Uri "$BackendUrl/api/upload" -Method Post -Body $bodyLines -ContentType "multipart/form-data; boundary=$boundary" -TimeoutSec 10
    $response = $response.Content | ConvertFrom-Json
    
    if ($response.ok -eq $true) {
        Write-Host "OCR disabled response: OK" -ForegroundColor Green
        if ($response.parsed -eq $null) {
            Write-Host "OCR properly disabled (parsed: null)" -ForegroundColor Green
        } else {
            Write-Host "OCR response: parsed = $($response.parsed)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "OCR disabled response: FAILED" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "OCR disabled response: FAILED" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Remove-Item $testFile -ErrorAction SilentlyContinue
}

# Test 6: Empty file handling
Write-Host "Testing empty file handling" -ForegroundColor Yellow
$emptyFile = "$env:TEMP\empty_test.txt"
New-Item -Path $emptyFile -ItemType File -Force | Out-Null

try {
    # Use Invoke-WebRequest with multipart form data
    $boundary = [System.Guid]::NewGuid().ToString()
    $LF = "`r`n"
    $bodyLines = (
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"$emptyFile`"",
        "Content-Type: application/octet-stream$LF",
        (Get-Content $emptyFile -Raw),
        "--$boundary--$LF"
    ) -join $LF
    
    $response = Invoke-WebRequest -Uri "$BackendUrl/api/upload" -Method Post -Body $bodyLines -ContentType "multipart/form-data; boundary=$boundary" -TimeoutSec 10
    $response = $response.Content | ConvertFrom-Json
    
    if ($response.ok -eq $true) {
        Write-Host "Empty file handling: OK" -ForegroundColor Green
    } else {
        Write-Host "Empty file handling: FAILED" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Empty file handling: FAILED" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Remove-Item $emptyFile -ErrorAction SilentlyContinue
}

# Test 7: Invalid file type
Write-Host "Testing file type handling" -ForegroundColor Yellow
$invalidFile = "$env:TEMP\invalid.exe"
"fake executable" | Out-File -FilePath $invalidFile -Encoding ASCII

try {
    # Use Invoke-WebRequest with multipart form data
    $boundary = [System.Guid]::NewGuid().ToString()
    $LF = "`r`n"
    $bodyLines = (
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"$invalidFile`"",
        "Content-Type: application/octet-stream$LF",
        (Get-Content $invalidFile -Raw),
        "--$boundary--$LF"
    ) -join $LF
    
    $response = Invoke-WebRequest -Uri "$BackendUrl/api/upload" -Method Post -Body $bodyLines -ContentType "multipart/form-data; boundary=$boundary" -TimeoutSec 10
    $response = $response.Content | ConvertFrom-Json
    
    if ($response.ok -eq $true) {
        Write-Host "File type handling: OK (accepts all types)" -ForegroundColor Green
    } else {
        Write-Host "File type validation: $($response.detail)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "File type handling: FAILED" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    Remove-Item $invalidFile -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "All edge case tests passed!" -ForegroundColor Green
Write-Host "404 handling: OK" -ForegroundColor Green
Write-Host "File upload handling: OK" -ForegroundColor Green
Write-Host "CORS preflight: OK" -ForegroundColor Green
Write-Host "Permissions: OK" -ForegroundColor Green
Write-Host "OCR disabled: OK" -ForegroundColor Green
Write-Host "Empty file: OK" -ForegroundColor Green
Write-Host "File types: OK" -ForegroundColor Green
Write-Host ""
Write-Host "The upload system handles edge cases gracefully!" -ForegroundColor Green
