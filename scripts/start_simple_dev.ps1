# OWLIN - Simple Development Mode Launcher
# This version works around TypeScript issues by using a minimal setup

Write-Host "OWLIN - Simple Development Mode Launcher" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Set UTF-8 safe console
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

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

Write-Host "Step 1: Verifying repository structure..." -ForegroundColor Blue
if (-not (Test-Path "package.json")) {
    Write-Host "ERROR: package.json not found" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "backend/final_single_port.py")) {
    Write-Host "ERROR: backend/final_single_port.py not found" -ForegroundColor Red
    exit 1
}
Write-Host "Repository structure verified" -ForegroundColor Green

Write-Host "Step 2: Cleaning up stale processes..." -ForegroundColor Blue
if (Test-Port 3000) {
    Write-Host "Port 3000 is in use, cleaning up..." -ForegroundColor Yellow
    Stop-ProcessOnPort 3000
    Start-Sleep -Seconds 2
}
if (Test-Port 8001) {
    Write-Host "Port 8001 is in use, cleaning up..." -ForegroundColor Yellow
    Stop-ProcessOnPort 8001
    Start-Sleep -Seconds 2
}
Write-Host "Cleanup completed" -ForegroundColor Green

Write-Host "Step 3: Starting FastAPI backend in PROXY_NEXT mode..." -ForegroundColor Blue

# Set environment variables
$env:UI_MODE = "PROXY_NEXT"
$env:NEXT_BASE = "http://127.0.0.1:3000"
$env:LLM_BASE = "http://127.0.0.1:11434"
$env:OWLIN_PORT = "8001"

Write-Host "Environment variables set:" -ForegroundColor Gray
Write-Host "  UI_MODE = $env:UI_MODE" -ForegroundColor Gray
Write-Host "  NEXT_BASE = $env:NEXT_BASE" -ForegroundColor Gray
Write-Host "  LLM_BASE = $env:LLM_BASE" -ForegroundColor Gray
Write-Host "  OWLIN_PORT = $env:OWLIN_PORT" -ForegroundColor Gray

Write-Host ""
Write-Host "SUCCESS: Owlin backend starting!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host "Backend running at http://127.0.0.1:8001" -ForegroundColor White
Write-Host "API served from /api/*" -ForegroundColor White
Write-Host "LLM proxy served from /llm/*" -ForegroundColor White
Write-Host ""
Write-Host "NOTE: Next.js frontend needs to be started separately:" -ForegroundColor Yellow
Write-Host "  Terminal 2: npm run dev" -ForegroundColor Yellow
Write-Host "  Then open http://127.0.0.1:8001" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop the backend" -ForegroundColor Yellow
Write-Host ""

# Start the FastAPI backend
try {
    python -m backend.final_single_port
}
catch {
    Write-Host "ERROR: Failed to start FastAPI backend: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
