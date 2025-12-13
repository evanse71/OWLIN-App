# OWLIN - Health Verifier
# Usage: .\scripts\verify_full_owlin.ps1 [-Force]

param(
    [switch]$Force
)

# Always run from repo root relative to this script
Set-StrictMode -Version Latest
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $here
Set-Location ..

Write-Host "OWLIN - Health Verifier"
Write-Host "======================"
Write-Host ""

# Function to kill processes on a port
function Stop-ProcessOnPort {
    param([int]$Port)
    try {
        $processes = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($processes) {
            $processes | ForEach-Object {
                $pid = $_.OwningProcess
                $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "Killing process $($process.ProcessName) (PID: $pid) on port $Port" -ForegroundColor Yellow
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }
    catch {
        # Ignore errors if no processes found
    }
}

# Function to test HTTP endpoint
function Test-HttpEndpoint {
    param(
        [string]$Url,
        [string]$ExpectedContent = $null
    )
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 10 -ErrorAction Stop
        if ($ExpectedContent) {
            return $response.Content -like "*$ExpectedContent*"
        }
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

# Step 1: Kill anything on port 8001 if Force is specified
if ($Force) {
    Write-Host "Step 1: Force killing processes on port 8001..." -ForegroundColor Yellow
    Stop-ProcessOnPort 8001
    Start-Sleep -Seconds 2
} else {
    Write-Host "Step 1: Checking port 8001..." -ForegroundColor Blue
}

# Step 2: Start backend if not running
Write-Host "Step 2: Starting backend..." -ForegroundColor Blue

# Check if backend is already running
$backendRunning = Test-HttpEndpoint -Url "http://127.0.0.1:8001/api/health"
if (-not $backendRunning) {
    Write-Host "Backend not running, starting..." -ForegroundColor Yellow
    
    # Set environment variables
    $env:UI_MODE = "PROXY_NEXT"
    $env:NEXT_BASE = "http://127.0.0.1:3000"
    $env:LLM_BASE = "http://127.0.0.1:11434"
    $env:OWLIN_PORT = "8001"
    $env:PYTHONPATH = $PWD
    
    # Start backend in background
    $backendJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        python -m backend.final_single_port
    }
    
    # Wait for backend to start
    Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
    $maxWait = 30
    $waited = 0
    do {
        Start-Sleep -Seconds 1
        $waited++
        $backendRunning = Test-HttpEndpoint -Url "http://127.0.0.1:8001/api/health"
    } while (-not $backendRunning -and $waited -lt $maxWait)
    
    if (-not $backendRunning) {
        Write-Host "FAIL: Backend failed to start within $maxWait seconds" -ForegroundColor Red
        if ($backendJob) {
            Stop-Job -Id $backendJob.Id -ErrorAction SilentlyContinue
            Remove-Job -Id $backendJob.Id -ErrorAction SilentlyContinue
        }
        exit 1
    }
    
    Write-Host "Backend started successfully" -ForegroundColor Green
} else {
    Write-Host "Backend already running" -ForegroundColor Green
}

# Step 3: Test /api/health endpoint
Write-Host "Step 3: Testing /api/health..." -ForegroundColor Blue
$healthOk = Test-HttpEndpoint -Url "http://127.0.0.1:8001/api/health" -ExpectedContent '"ok":true'
if ($healthOk) {
    Write-Host "PASS: /api/health returns {\"ok\":true}" -ForegroundColor Green
} else {
    Write-Host "FAIL: /api/health does not return {\"ok\":true}" -ForegroundColor Red
    exit 1
}

# Step 4: Test /api/status endpoint
Write-Host "Step 4: Testing /api/status..." -ForegroundColor Blue
$statusOk = Test-HttpEndpoint -Url "http://127.0.0.1:8001/api/status" -ExpectedContent '"api_mounted":true'
if ($statusOk) {
    Write-Host "PASS: /api/status contains \"api_mounted\":true" -ForegroundColor Green
} else {
    Write-Host "FAIL: /api/status does not contain \"api_mounted\":true" -ForegroundColor Red
    exit 1
}

# Step 5: Test root endpoint
Write-Host "Step 5: Testing root endpoint..." -ForegroundColor Blue
$rootOk = Test-HttpEndpoint -Url "http://127.0.0.1:8001/"
if ($rootOk) {
    Write-Host "PASS: Root endpoint returns 200" -ForegroundColor Green
} else {
    Write-Host "FAIL: Root endpoint does not return 200" -ForegroundColor Red
    exit 1
}

# All tests passed
Write-Host ""
Write-Host "SUCCESS: All health checks passed!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host "Backend is healthy and responsive" -ForegroundColor White
Write-Host "API endpoints are working correctly" -ForegroundColor White
Write-Host "Root endpoint is accessible" -ForegroundColor White
Write-Host ""
Write-Host "Owlin is ready at: http://127.0.0.1:8001" -ForegroundColor Cyan
Write-Host ""

exit 0
