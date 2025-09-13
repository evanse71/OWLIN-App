# OWLIN - One-Click Start & Verify (Windows)
# Launches server, waits for readiness, auto-remounts API if needed, and prints PASS/FAIL

# Force UTF-8 encoding for all console output and Python child processes
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$ErrorActionPreference = "Stop"

function Write-Info($m){ Write-Host "• $m" -ForegroundColor Gray }
function Write-Ok($m){ Write-Host "✅ $m" -ForegroundColor Green }
function Write-Fail($m){ Write-Host "❌ $m" -ForegroundColor Red }
function Write-Warn($m){ Write-Host "⚠️  $m" -ForegroundColor Yellow }

Write-Host "🚀 OWLIN - One-Click Start & Verify" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# 1) Ensure we're in repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot
Write-Info "Repo root: $(Get-Location)"

# 2) Verify critical files exist
if (!(Test-Path ".\backend\final_single_port.py")) { 
    Write-Fail "Not in repo root. Missing backend/final_single_port.py"
    Write-Info "Expected location: $repoRoot"
    exit 1 
}
if (!(Test-Path ".\backend\__init__.py")) { 
    New-Item ".\backend\__init__.py" -ItemType File -Force | Out-Null
    Write-Info "Created backend/__init__.py"
}

# 3) Set PYTHONPATH to ensure module imports work
$env:PYTHONPATH = (Get-Location).Path
Write-Info "PYTHONPATH set to: $env:PYTHONPATH"

# 4) Load .env if present
$envFile = ".\.env"
if (Test-Path $envFile) {
    Write-Info "Loading .env"
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*#") { return }
        if ($_ -match "^\s*$") { return }
        $kv = $_ -split "=",2
        if ($kv.Length -eq 2) {
            $k = $kv[0].Trim()
            $v = $kv[1].Trim()
            if ($v.StartsWith('"') -and $v.EndsWith('"')) { $v = $v.Substring(1, $v.Length-2) }
            if ($v.StartsWith("'") -and $v.EndsWith("'")) { $v = $v.Substring(1, $v.Length-2) }
            [System.Environment]::SetEnvironmentVariable($k, $v)
            Set-Item -Path "env:$k" -Value $v
        }
    }
}

# 5) Set defaults
if (-not $env:OWLIN_PORT) { $env:OWLIN_PORT = "8001" }
if (-not $env:LLM_BASE) { $env:LLM_BASE = "http://127.0.0.1:11434" }
if (-not $env:OWLIN_DB_URL) { $env:OWLIN_DB_URL = "sqlite:///./owlin.db" }

Write-Info "PORT: $($env:OWLIN_PORT)"
Write-Info "LLM_BASE: $($env:LLM_BASE)"

# 6) Build UI if missing
$indexPath = ".\out\index.html"
if (-not (Test-Path $indexPath)) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Info "UI not built. Running: npm run build"
        npm run build
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "npm run build failed, proceeding with JSON fallback"
        }
    } else {
        Write-Info "npm not found; proceeding with JSON fallback for UI"
    }
}

# 7) Kill any existing processes on the target port
$port = [int]$env:OWLIN_PORT
try {
    $cons = netstat -ano | Select-String ":$port"
    if ($cons) {
        $pids = $cons -replace ".*\s+(\d+)$", '$1' | Select-Object -Unique
        foreach ($pid in $pids) {
            try { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } catch {}
        }
        Start-Sleep -Milliseconds 300
        Write-Info "Cleared processes on port $port"
    }
} catch { Write-Info "Port pre-clear skipped" }

# 8) Test Python import before launching
Write-Host "• Testing Python module import..."
try {
    $code = @'
import importlib, sys, os
print("Python OK:", sys.version)
print("CWD:", os.getcwd())
importlib.import_module("backend")
print("backend import OK")
'@
    python - <<$code
$code
    $importOk = $LASTEXITCODE -eq 0
} catch {
    $importOk = $false
}

if (-not $importOk) {
    Write-Host "Python cannot import backend module"
    Write-Host "• Make sure you're in the repo root and Python is installed"
    exit 1
}

# 9) Launch the server
Write-Info "Launching Owlin server..."
$launchCmds = @(
    @{ exe="python"; args="-m backend.final_single_port" },
    @{ exe="python"; args=".\backend\final_single_port.py" }
)

$proc = $null
foreach ($cmd in $launchCmds) {
    try {
        Write-Info "Trying: $($cmd.exe) $($cmd.args)"
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $cmd.exe
        $psi.Arguments = $cmd.args
        $psi.WorkingDirectory = (Get-Location).Path
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true

        $proc = New-Object System.Diagnostics.Process
        $proc.StartInfo = $psi
        if ($proc.Start()) {
            Start-Sleep -Milliseconds 500
            if (!$proc.HasExited) { 
                Write-Ok "Server launched successfully"
                break 
            }
        }
    } catch {
        Write-Warn "Launch attempt failed: $($_.Exception.Message)"
    }
}

if ($proc -eq $null -or $proc.HasExited) {
    Write-Fail "Failed to launch Owlin server"
    Write-Info "Try running manually: python -m backend.final_single_port"
    exit 1
}

# 10) Wait for health check
$base = "http://127.0.0.1:$($env:OWLIN_PORT)"
$healthUrl = "$base/api/health"
$statusUrl = "$base/api/status"
$retryMountUrl = "$base/api/retry-mount"

Write-Info "Waiting for server to become healthy..."
$ready = $false
for ($i=0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200 -and $r.Content -match '"ok"\s*:\s*true') { 
            $ready = $true
            break 
        }
    } catch {}
    Start-Sleep -Milliseconds 250
}

if (-not $ready) {
    Write-Fail "Server did not become healthy at $healthUrl"
    try { Write-Host "Server output: $($proc.StandardOutput.ReadToEnd())" } catch {}
    try { Write-Host "Server errors: $($proc.StandardError.ReadToEnd())" } catch {}
    try { $proc.Kill() } catch {}
    exit 1
}
Write-Ok "Health check passed"

# 11) Ensure API is mounted
Write-Info "Checking API mount status..."
try {
    $s = Invoke-WebRequest -Uri $statusUrl -UseBasicParsing -TimeoutSec 3
    if ($s.Content -notmatch '"api_mounted"\s*:\s*true') {
        Write-Warn "API not mounted. Attempting retry-mount..."
        Invoke-WebRequest -Method POST -Uri $retryMountUrl -UseBasicParsing -TimeoutSec 5 | Out-Null
        Start-Sleep -Milliseconds 500
        $s2 = Invoke-WebRequest -Uri $statusUrl -UseBasicParsing -TimeoutSec 3
        if ($s2.Content -notmatch '"api_mounted"\s*:\s*true') {
            Write-Fail "API failed to mount after retry"
            Write-Info "Status response: $($s2.Content)"
            try { $proc.Kill() } catch {}
            exit 1
        }
    }
    Write-Ok "API mounted successfully"
} catch {
    Write-Fail "API status check failed: $($_.Exception.Message)"
    try { $proc.Kill() } catch {}
    exit 1
}

# 12) Final verification
Write-Host ""
Write-Host "🎉 OWLIN STARTUP COMPLETE" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green
Write-Host ""
Write-Ok "Server is running on $base"
Write-Info "UI:       $base"
Write-Info "Health:   $healthUrl"
Write-Info "Status:   $statusUrl"
Write-Host ""
Write-Host "🌐 Opening browser..." -ForegroundColor Cyan
Start-Process "http://127.0.0.1:$($env:OWLIN_PORT)"
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# 13) Keep window attached to server output
try {
    while (-not $proc.HasExited) {
        Start-Sleep -Milliseconds 500
        while (-not $proc.StandardOutput.EndOfStream) { 
            $line = $proc.StandardOutput.ReadLine()
            if ($line) { Write-Host $line -ForegroundColor Gray }
        }
        while (-not $proc.StandardError.EndOfStream) { 
            $line = $proc.StandardError.ReadLine()
            if ($line) { Write-Host $line -ForegroundColor Red }
        }
    }
} catch {}
if ($proc.ExitCode -ne 0) { 
    Write-Fail "Server exited with code $($proc.ExitCode)"
    exit $proc.ExitCode 
}
