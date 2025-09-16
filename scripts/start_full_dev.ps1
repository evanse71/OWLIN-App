# OWLIN - Full Development Mode Launcher
# Usage:
#   .\scripts\start_full_dev.ps1
# Then open http://127.0.0.1:8001

param(
    [switch]$Force,
    [int]$MaxRetries = 30,
    [int]$RetryDelay = 2
)

# ------------------ bootstrap (do not remove) ------------------
# Force UTF-8 and robust Python IO
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Resolve repo root from script location and cd there (location-proof)
$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot  = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

# Always prefer .cmd shims for npm/npx to avoid npm.ps1 policy blocks
$npmCmds = @(
    (Join-Path $env:ProgramFiles           "nodejs\npm.cmd"),
    (Join-Path $env:LOCALAPPDATA           "Programs\nodejs\npm.cmd")
)
$npxCmds = @(
    (Join-Path $env:ProgramFiles           "nodejs\npx.cmd"),
    (Join-Path $env:LOCALAPPDATA           "Programs\nodejs\npx.cmd")
)
$npmShim = $npmCmds | Where-Object { Test-Path $_ } | Select-Object -First 1
$npxShim = $npxCmds | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($npmShim) { Set-Alias -Name npm -Value $npmShim -Scope Script -Force }
if ($npxShim) { Set-Alias -Name npx -Value $npxShim -Scope Script -Force }

# Verify npm works; show actionable help if not
try {
    $npmVersion = (& npm -v) 2>$null
} catch {
    $npmVersion = $null
}
if (-not $npmVersion) {
    Write-Host "ERROR: npm not found or blocked." -ForegroundColor Red
    Write-Host "Install Node.js from https://nodejs.org/ and restart PowerShell." -ForegroundColor Yellow
    Write-Host "If PowerShell still blocks npm.ps1, this script will route to npm.cmd automatically." -ForegroundColor Yellow
    exit 1
}
# ---------------- end bootstrap (do not remove) ----------------

$env:PYTHONPATH = (Get-Location).Path

Write-Host "OWLIN - Full Development Mode Launcher" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Function to check if a port is in use
function Test-Port {
    param([int]$Port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("127.0.0.1", $Port)
        $connection.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Function to kill processes on a port
function Stop-ProcessOnPort {
    param([int]$Port)
    try {
        $processes = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($processes) {
        $processes | ForEach-Object {
            $processId = $_.OwningProcess
            $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "Killing process $($process.ProcessName) (PID: $processId) on port $Port" -ForegroundColor Yellow
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            }
        }
        }
    }
    catch {
        # Ignore errors if no processes found
    }
}

# Function to wait for a service to be responsive
function Wait-ForService {
    param(
        [string]$Url,
        [int]$MaxRetries = 30,
        [int]$RetryDelay = 2
    )
    
    Write-Host "Waiting for service at $Url..." -ForegroundColor Yellow
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            Invoke-WebRequest -Uri $Url -TimeoutSec 5 -ErrorAction Stop | Out-Null
            Write-Host "Service is responsive after $i attempts" -ForegroundColor Green
            return $true
        }
        catch {
            Write-Host "Attempt $i/$MaxRetries failed: $($_.Exception.Message)" -ForegroundColor DarkYellow
            if ($i -lt $MaxRetries) {
                Start-Sleep -Seconds $RetryDelay
            }
        }
    }
    return $false
}

# Step 1: Verify repo root
Write-Host "Step 1: Verifying repository structure..." -ForegroundColor Blue

if (-not (Test-Path "package.json")) {
    Write-Host "ERROR: package.json not found. Are you in the repo root?" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "backend/final_single_port.py")) {
    Write-Host "ERROR: backend/final_single_port.py not found. Are you in the repo root?" -ForegroundColor Red
    exit 1
}

Write-Host "Repository structure verified" -ForegroundColor Green

# Step 2: Clean up any stale processes
Write-Host "Step 2: Cleaning up stale processes..." -ForegroundColor Blue

if ($Force -or (Test-Port 3000)) {
    Write-Host "Port 3000 is in use, cleaning up..." -ForegroundColor Yellow
    Stop-ProcessOnPort 3000
    Start-Sleep -Seconds 2
}

if ($Force -or (Test-Port 8001)) {
    Write-Host "Port 8001 is in use, cleaning up..." -ForegroundColor Yellow
    Stop-ProcessOnPort 8001
    Start-Sleep -Seconds 2
}

Write-Host "Cleanup completed" -ForegroundColor Green

# Step 3: Start Next.js dev server
Write-Host "Step 3: Starting Next.js dev server..." -ForegroundColor Blue

if (Test-Path "package.json") {
    Write-Host "Starting Next.js dev server..." -ForegroundColor Yellow
    # Use npm.cmd shim directly to bypass policy restrictions
    Start-Process -NoNewWindow -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $PSScriptRoot\.. 
    Start-Sleep -Seconds 5
} else {
    Write-Host "ERROR: package.json not found, cannot start Next.js" -ForegroundColor Red
    exit 1
}

# Step 4: Wait for Next.js to be responsive
Write-Host "Step 4: Waiting for Next.js to be ready..." -ForegroundColor Blue

if (-not (Wait-ForService -Url "http://127.0.0.1:3000" -MaxRetries $MaxRetries -RetryDelay $RetryDelay)) {
    Write-Host "ERROR: Next.js failed to start or become responsive" -ForegroundColor Red
    Write-Host "Please check if Next.js is running and accessible at http://127.0.0.1:3000" -ForegroundColor Yellow
    exit 1
}

Write-Host "Next.js is ready!" -ForegroundColor Green

# Step 5: Start FastAPI backend
Write-Host "Step 5: Starting FastAPI backend..." -ForegroundColor Blue

# Check if Python is available
try {
    $pythonVersion = python --version 2>$null
    if ($pythonVersion) {
        Write-Host "Using Python: $pythonVersion" -ForegroundColor Gray
    } else {
        throw "Python not found"
    }
}
catch {
    Write-Host "ERROR: Python not found. Please install Python." -ForegroundColor Red
    Write-Host ""
    Write-Host "To install Python:" -ForegroundColor Yellow
    Write-Host "1. Download from https://python.org/" -ForegroundColor Yellow
    Write-Host "2. Or use winget: winget install Python.Python.3" -ForegroundColor Yellow
    Write-Host "3. Or use chocolatey: choco install python" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installation, restart PowerShell and try again." -ForegroundColor Yellow
    Cleanup
    exit 1
}

# Set environment variables
$env:UI_MODE = "PROXY_NEXT"
$env:NEXT_BASE = "http://127.0.0.1:3000"
$env:LLM_BASE = "http://127.0.0.1:11434"
$env:OWLIN_PORT = "8001"
$env:PYTHONPATH = $PWD

Write-Host "Environment variables set:" -ForegroundColor Gray
Write-Host "  UI_MODE = $env:UI_MODE" -ForegroundColor Gray
Write-Host "  NEXT_BASE = $env:NEXT_BASE" -ForegroundColor Gray
Write-Host "  LLM_BASE = $env:LLM_BASE" -ForegroundColor Gray
Write-Host "  OWLIN_PORT = $env:OWLIN_PORT" -ForegroundColor Gray

# Step 6: Success message and start backend
Write-Host ""
Write-Host "SUCCESS: Owlin full app starting!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host "Owlin full app running at http://127.0.0.1:8001" -ForegroundColor White
Write-Host "Frontend proxied from Next.js dev server" -ForegroundColor White
Write-Host "Backend API served from /api/*" -ForegroundColor White
Write-Host "LLM proxy served from /llm/*" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop both services" -ForegroundColor Yellow
Write-Host ""

# Cleanup function
function Cleanup {
    Write-Host ""
    Write-Host "Shutting down services..." -ForegroundColor Yellow
    
    # Stop any remaining processes on our ports
    Stop-ProcessOnPort 3000
    Stop-ProcessOnPort 8001
    
    Write-Host "Cleanup completed" -ForegroundColor Green
    exit 0
}

# Set up cleanup on script termination
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

# Open browser
Write-Host "Opening browser to http://127.0.0.1:8001..." -ForegroundColor Blue
Start-Process "http://127.0.0.1:8001"

# Start the FastAPI backend (this will run in foreground)
try {
    Write-Host "Starting FastAPI backend..." -ForegroundColor Blue
    python -m backend.final_single_port
}
catch {
    Write-Host "ERROR: Failed to start FastAPI backend: $($_.Exception.Message)" -ForegroundColor Red
    Cleanup
}

# If we get here, the backend stopped
Cleanup
