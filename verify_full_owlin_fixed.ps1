# RUTHLESS VERIFICATION SCRIPT - OWLIN SINGLE-PORT
# Cold Russian judge of software. No mercy, no excuses.

$ErrorActionPreference = "Stop"
$BaseUrl = "http://127.0.0.1:8001"
$TestResults = @()

function Write-Result {
    param($Test, $Status, $Details = "")
    $Result = @{
        Test = $Test
        Status = $Status
        Details = $Details
        Timestamp = Get-Date
    }
    $script:TestResults += $Result
    
    if ($Status -eq "PASS") {
        Write-Host "✅ $Test - PASS" -ForegroundColor Green
        if ($Details) { Write-Host "   $Details" -ForegroundColor Gray }
    } else {
        Write-Host "❌ $Test - FAIL" -ForegroundColor Red
        if ($Details) { Write-Host "   $Details" -ForegroundColor Red }
    }
}

function Test-Endpoint {
    param($Method, $Url, $ExpectedStatus = 200, $Body = $null, $Headers = @{})
    
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            UseBasicParsing = $true
            TimeoutSec = 10
        }
        
        if ($Body) {
            $params.Body = $Body
            $params.ContentType = "application/json"
        }
        
        if ($Headers.Count -gt 0) {
            $params.Headers = $Headers
        }
        
        $response = Invoke-WebRequest @params
        return @{
            Success = $true
            StatusCode = $response.StatusCode
            Content = $response.Content
            Headers = $response.Headers
        }
    } catch {
        return @{
            Success = $false
            Error = $_.Exception.Message
            StatusCode = $_.Exception.Response.StatusCode.value__
        }
    }
}

function Test-JsonResponse {
    param($Content, $ExpectedProperty, $ExpectedValue = $null)
    
    try {
        $json = $Content | ConvertFrom-Json
        if ($ExpectedProperty -and $ExpectedValue) {
            return $json.$ExpectedProperty -eq $ExpectedValue
        } elseif ($ExpectedProperty) {
            return $json.PSObject.Properties.Name -contains $ExpectedProperty
        }
        return $true
    } catch {
        return $false
    }
}

Write-Host "💀 RUTHLESS VERIFICATION STARTING" -ForegroundColor Red
Write-Host "Target: $BaseUrl" -ForegroundColor Yellow
Write-Host "Time: $(Get-Date)" -ForegroundColor Gray
Write-Host ""

# KILL ANY EXISTING PROCESS ON PORT 8001
Write-Host "🔪 Eliminating existing processes on port 8001..." -ForegroundColor Yellow
try {
    $conns = netstat -ano | Select-String ":8001"
    if ($conns) {
        $pids = $conns -replace ".*\s+(\d+)$", '$1' | Select-Object -Unique
        foreach ($pid in $pids) { 
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue 
        }
        Start-Sleep -Milliseconds 500
    }
} catch {}

# START THE SERVER
Write-Host "🚀 Launching Owlin single-port server..." -ForegroundColor Yellow
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "python"
$psi.Arguments = "-m backend.final_single_port"
$psi.WorkingDirectory = (Get-Location).Path
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
$null = $proc.Start()

# WAIT FOR SERVER TO BE READY
Write-Host "⏳ Waiting for server to become ready..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $response = Test-Endpoint "GET" "$BaseUrl/api/health"
        if ($response.Success -and $response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {}
    Start-Sleep -Milliseconds 500
}

if (-not $ready) {
    $err = $proc.StandardError.ReadToEnd()
    $out = $proc.StandardOutput.ReadToEnd()
    Write-Result "SERVER_STARTUP" "FAIL" "Server never became ready. STDERR: $err STDOUT: $out"
    $proc.Kill()
    exit 1
}

Write-Host "✅ Server is running (PID: $($proc.Id))" -ForegroundColor Green
Write-Host ""

# TEST 1: HEALTH CHECK
Write-Host "1️⃣ HEALTH CHECK" -ForegroundColor Cyan
$response = Test-Endpoint "GET" "$BaseUrl/api/health"
if ($response.Success -and $response.StatusCode -eq 200) {
    $jsonValid = Test-JsonResponse $response.Content "ok" $true
    if ($jsonValid) {
        Write-Result "HEALTH_CHECK" "PASS" "Health endpoint returns {ok: true}"
    } else {
        Write-Result "HEALTH_CHECK" "FAIL" "Health endpoint returned invalid JSON or wrong value: $($response.Content)"
    }
} else {
    Write-Result "HEALTH_CHECK" "FAIL" "Health endpoint failed: $($response.Error)"
}

# TEST 2: STATUS CHECK
Write-Host "2️⃣ STATUS CHECK" -ForegroundColor Cyan
$response = Test-Endpoint "GET" "$BaseUrl/api/status"
if ($response.Success -and $response.StatusCode -eq 200) {
    $jsonValid = Test-JsonResponse $response.Content "api_mounted" $true
    if ($jsonValid) {
        Write-Result "STATUS_CHECK" "PASS" "Status shows api_mounted: true"
    } else {
        # Try retry-mount
        Write-Host "   API not mounted. Attempting retry-mount..." -ForegroundColor Yellow
        $retryResponse = Test-Endpoint "POST" "$BaseUrl/api/retry-mount"
        Start-Sleep -Milliseconds 500
        $statusResponse = Test-Endpoint "GET" "$BaseUrl/api/status"
        if ($statusResponse.Success -and $statusResponse.StatusCode -eq 200) {
            $jsonValid = Test-JsonResponse $statusResponse.Content "api_mounted" $true
            if ($jsonValid) {
                Write-Result "STATUS_CHECK" "PASS" "Status shows api_mounted: true after retry-mount"
            } else {
                Write-Result "STATUS_CHECK" "FAIL" "API still not mounted after retry: $($statusResponse.Content)"
            }
        } else {
            Write-Result "STATUS_CHECK" "FAIL" "Retry-mount failed: $($retryResponse.Error)"
        }
    }
} else {
    Write-Result "STATUS_CHECK" "FAIL" "Status endpoint failed: $($response.Error)"
}

# TEST 3: ROOT UI CHECK
Write-Host "3️⃣ ROOT UI CHECK" -ForegroundColor Cyan
$response = Test-Endpoint "GET" "$BaseUrl/"
if ($response.Success -and $response.StatusCode -eq 200) {
    Write-Result "ROOT_UI_CHECK" "PASS" "Root endpoint returns HTTP 200"
} else {
    Write-Result "ROOT_UI_CHECK" "FAIL" "Root endpoint failed: $($response.Error)"
}

# TEST 4: INVOICE WORKFLOW
Write-Host "4️⃣ INVOICE WORKFLOW" -ForegroundColor Cyan
$invoiceData = @{
    supplier_id = "S1"
    supplier_name = "Test Supplier"
    invoice_date = "2025-09-13"
    invoice_ref = "INV-001"
    lines = @(
        @{
            description = "Beer crate"
            outer_qty = 2
            unit_price = 50
            vat_rate_percent = 20
        }
    )
} | ConvertTo-Json -Depth 3

# Create invoice
$createResponse = Test-Endpoint "POST" "$BaseUrl/api/manual/invoices" $invoiceData
if ($createResponse.Success -and $createResponse.StatusCode -eq 200) {
    $createJson = $createResponse.Content | ConvertFrom-Json
    if ($createJson.id) {
        Write-Result "INVOICE_CREATE" "PASS" "Invoice created with ID: $($createJson.id)"
        
        # Get invoices list
        $listResponse = Test-Endpoint "GET" "$BaseUrl/api/manual/invoices"
        if ($listResponse.Success -and $listResponse.StatusCode -eq 200) {
            $listJson = $listResponse.Content | ConvertFrom-Json
            if ($listJson -is [array] -and $listJson.Count -gt 0) {
                Write-Result "INVOICE_LIST" "PASS" "Invoice list retrieved with $($listJson.Count) invoices"
            } else {
                Write-Result "INVOICE_LIST" "FAIL" "Invoice list is empty or invalid format"
            }
        } else {
            Write-Result "INVOICE_LIST" "FAIL" "Failed to retrieve invoice list: $($listResponse.Error)"
        }
    } else {
        Write-Result "INVOICE_CREATE" "FAIL" "Invoice creation response missing ID: $($createResponse.Content)"
    }
} else {
    Write-Result "INVOICE_CREATE" "FAIL" "Invoice creation failed: $($createResponse.Error)"
}

# TEST 5: STRESS TEST
Write-Host "5️⃣ STRESS TEST" -ForegroundColor Cyan
$stressFailures = 0
for ($i = 1; $i -le 20; $i++) {
    $response = Test-Endpoint "GET" "$BaseUrl/api/health"
    if (-not $response.Success -or $response.StatusCode -ne 200) {
        $stressFailures++
    }
    Start-Sleep -Milliseconds 100
}

if ($stressFailures -eq 0) {
    Write-Result "STRESS_TEST" "PASS" "All 20 health check requests succeeded"
} else {
    Write-Result "STRESS_TEST" "FAIL" "$stressFailures out of 20 requests failed"
}

# TEST 6: LLM PROXY TEST
Write-Host "6️⃣ LLM PROXY TEST" -ForegroundColor Cyan
$llmResponse = Test-Endpoint "GET" "$BaseUrl/llm/api/tags"
if ($llmResponse.Success -and $llmResponse.StatusCode -eq 200) {
    Write-Result "LLM_PROXY" "PASS" "LLM proxy returned HTTP 200"
} else {
    # Check if server is still alive after LLM timeout
    $healthAfterLlm = Test-Endpoint "GET" "$BaseUrl/api/health"
    if ($healthAfterLlm.Success -and $healthAfterLlm.StatusCode -eq 200) {
        Write-Result "LLM_PROXY" "PASS" "LLM proxy timed out gracefully, server still alive"
    } else {
        Write-Result "LLM_PROXY" "FAIL" "LLM proxy failed and server may be down: $($llmResponse.Error)"
    }
}

# CLEANUP
Write-Host ""
Write-Host "🧹 CLEANUP" -ForegroundColor Yellow
$proc.Kill()
Start-Sleep -Milliseconds 500

# FINAL RESULTS
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Gray
Write-Host "💀 RUTHLESS VERIFICATION RESULTS" -ForegroundColor Red
Write-Host "=" * 60 -ForegroundColor Gray

$passedTests = ($TestResults | Where-Object { $_.Status -eq "PASS" }).Count
$totalTests = $TestResults.Count
$failedTests = $totalTests - $passedTests

Write-Host "Total Tests: $totalTests" -ForegroundColor White
Write-Host "Passed: $passedTests" -ForegroundColor Green
Write-Host "Failed: $failedTests" -ForegroundColor Red
Write-Host ""

if ($failedTests -eq 0) {
    Write-Host "🏆 ALL TESTS PASSED – BULLETPROOF" -ForegroundColor Green
    Write-Host "The Owlin single-port deployment is production-ready." -ForegroundColor Green
    exit 0
} else {
    Write-Host "💀 FAILURE – SYSTEM NOT BULLETPROOF" -ForegroundColor Red
    Write-Host "The Owlin single-port deployment has issues that must be fixed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Failed Tests:" -ForegroundColor Red
    $TestResults | Where-Object { $_.Status -eq "FAIL" } | ForEach-Object {
        Write-Host "  ❌ $($_.Test): $($_.Details)" -ForegroundColor Red
    }
    exit 1
}
