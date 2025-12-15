# Test Port 5176 Connectivity
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Port 5176 Connectivity Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if port is listening
Write-Host "[1] Checking if port 5176 is listening..." -ForegroundColor Yellow
$listening = netstat -ano | Select-String "5176.*LISTENING"
if ($listening) {
    Write-Host "  SUCCESS: Port 5176 is LISTENING" -ForegroundColor Green
    $listening | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
} else {
    Write-Host "  FAILED: Port 5176 is NOT listening" -ForegroundColor Red
    Write-Host "  Make sure Vite is running!" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Test 2: TCP Connection Test
Write-Host "[2] Testing TCP connection to localhost:5176..." -ForegroundColor Yellow
try {
    $tcpTest = Test-NetConnection -ComputerName localhost -Port 5176 -WarningAction SilentlyContinue
    if ($tcpTest.TcpTestSucceeded) {
        Write-Host "  SUCCESS: TCP connection succeeded!" -ForegroundColor Green
        Write-Host "    RemoteAddress: $($tcpTest.RemoteAddress)" -ForegroundColor Gray
        Write-Host "    RemotePort: $($tcpTest.RemotePort)" -ForegroundColor Gray
        Write-Host "    InterfaceAlias: $($tcpTest.InterfaceAlias)" -ForegroundColor Gray
    } else {
        Write-Host "  FAILED: TCP connection test failed" -ForegroundColor Red
        Write-Host "    TcpTestSucceeded: $($tcpTest.TcpTestSucceeded)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 3: HTTP Request to localhost
Write-Host "[3] Testing HTTP request to http://localhost:5176/..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest "http://localhost:5176/" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  SUCCESS: HTTP request succeeded!" -ForegroundColor Green
    Write-Host "    Status Code: $($response.StatusCode)" -ForegroundColor Gray
    Write-Host "    Content Length: $($response.Content.Length) bytes" -ForegroundColor Gray
    Write-Host "    Content Type: $($response.Headers['Content-Type'])" -ForegroundColor Gray
    if ($response.Content -match "root|html|vite") {
        Write-Host "    Content appears to be HTML (contains HTML/Vite markers)" -ForegroundColor Green
    }
} catch {
    Write-Host "  FAILED: HTTP request failed" -ForegroundColor Red
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Yellow
    if ($_.Exception.Response) {
        Write-Host "    Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Yellow
    }
}
Write-Host ""

# Test 4: HTTP Request to 127.0.0.1
Write-Host "[4] Testing HTTP request to http://127.0.0.1:5176/..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest "http://127.0.0.1:5176/" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  SUCCESS: HTTP request succeeded!" -ForegroundColor Green
    Write-Host "    Status Code: $($response.StatusCode)" -ForegroundColor Gray
    Write-Host "    Content Length: $($response.Content.Length) bytes" -ForegroundColor Gray
} catch {
    Write-Host "  FAILED: HTTP request failed" -ForegroundColor Red
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Yellow
}
Write-Host ""

# Test 5: HTTP Request to network IP
Write-Host "[5] Testing HTTP request to http://192.168.0.101:5176/..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest "http://192.168.0.101:5176/" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  SUCCESS: HTTP request succeeded!" -ForegroundColor Green
    Write-Host "    Status Code: $($response.StatusCode)" -ForegroundColor Gray
    Write-Host "    Content Length: $($response.Content.Length) bytes" -ForegroundColor Gray
} catch {
    Write-Host "  FAILED: HTTP request failed" -ForegroundColor Red
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "    (This is OK if firewall blocks external access)" -ForegroundColor Gray
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Test Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "- If TCP test succeeded but HTTP failed: Check Vite configuration" -ForegroundColor White
Write-Host "- If both succeeded: Problem is likely browser-related (cache, extension, etc.)" -ForegroundColor White
Write-Host "- If TCP failed: Check firewall or port binding" -ForegroundColor White
Write-Host ""

