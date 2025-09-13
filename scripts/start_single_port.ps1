# Requires: PowerShell 5+ | Windows
# If blocked, run once: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

$ErrorActionPreference = "Stop"

function Write-Info($m){ Write-Host "• $m" -ForegroundColor Gray }
function Write-Ok($m){ Write-Host "✅ $m" -ForegroundColor Green }
function Write-Fail($m){ Write-Host "❌ $m" -ForegroundColor Red }

# 1) Move to repo root (this script lives in /scripts)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot
Write-Info "Repo root: $(Get-Location)"

# 2) Ensure backend package marker exists
$backendInit = ".\backend\__init__.py"
if (-not (Test-Path $backendInit)) { New-Item -ItemType File -Path $backendInit -Force | Out-Null; Write-Info "Created backend\__init__.py" }

# 3) Load .env if present (simple parser: KEY=VALUE)
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
      # Remove surrounding quotes if any
      if ($v.StartsWith('"') -and $v.EndsWith('"')) { $v = $v.Substring(1, $v.Length-2) }
      if ($v.StartsWith("'") -and $v.EndsWith("'")) { $v = $v.Substring(1, $v.Length-2) }
      [System.Environment]::SetEnvironmentVariable($k, $v)
      Set-Item -Path "env:$k" -Value $v
    }
  }
}

# 4) Resolve env config with defaults
if (-not $env:OWLIN_PORT -and $env:PORT) { $env:OWLIN_PORT = $env:PORT }
if (-not $env:OWLIN_PORT) { $env:OWLIN_PORT = "8001" }
if (-not $env:LLM_BASE)   { $env:LLM_BASE = "http://127.0.0.1:11434" }
if (-not $env:OWLIN_DB_URL) { $env:OWLIN_DB_URL = "sqlite:///./owlin.db" }

Write-Info "PORT     = $($env:OWLIN_PORT)"
Write-Info "LLM_BASE = $($env:LLM_BASE)"
Write-Info "DB_URL   = $($env:OWLIN_DB_URL)"

# 5) Set PYTHONPATH to repo root to guarantee module imports
$env:PYTHONPATH = (Get-Location).Path

# 6) Build UI if missing and npm is available
$indexPath = ".\out\index.html"
if (-not (Test-Path $indexPath)) {
  if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Info "UI not built. Running: npm run build"
    npm run build
  } else {
    Write-Info "npm not found; proceeding with JSON fallback for UI."
  }
}

# 7) Optional: kill any process bound to the target port (Windows 10+)
try {
  $port = [int]$env:OWLIN_PORT
  $cons = netstat -ano | Select-String ":$port"
  if ($cons) {
    $pids = $cons -replace ".*\s+(\d+)$", '$1' | Select-Object -Unique
    foreach ($pid in $pids) {
      try { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } catch {}
    }
    Start-Sleep -Milliseconds 300
    Write-Info "Cleared processes on port $port"
  }
} catch { Write-Info "Port pre-clear skipped." }

# 8) Launch the server (try module run, then fallback to direct file)
$py = "python"
$launchCmds = @(
  @{ exe=$py; args="-m backend.final_single_port" },
  @{ exe=$py; args=".\backend\final_single_port.py" }
)

$proc = $null
foreach ($cmd in $launchCmds) {
  try {
    Write-Info "Launching: $($cmd.exe) $($cmd.args)"
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
      Start-Sleep -Milliseconds 150
      if (!$proc.HasExited) { break }
    }
  } catch {}
}
if ($proc -eq $null -or $proc.HasExited) {
  Write-Fail "Failed to launch Owlin server."
  exit 1
}

# 9) Readiness wait (health → ok:true)
$base = "http://127.0.0.1:$($env:OWLIN_PORT)"
$healthUrl = "$base/api/health"
$statusUrl = "$base/api/status"
$retryMountUrl = "$base/api/retry-mount"

$ready = $false
for ($i=0; $i -lt 60; $i++) {
  try {
    $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200 -and $r.Content -match '"ok"\s*:\s*true') { $ready = $true; break }
  } catch {}
  Start-Sleep -Milliseconds 250
}
if (-not $ready) {
  Write-Fail "Server did not become healthy at $healthUrl"
  try { Write-Host ($proc.StandardError.ReadToEnd()) } catch {}
  try { Write-Host ($proc.StandardOutput.ReadToEnd()) } catch {}
  try { $proc.Kill() } catch {}
  exit 1
}
Write-Ok "Health OK"

# 10) Ensure real API is mounted
try {
  $s = Invoke-WebRequest -Uri $statusUrl -UseBasicParsing -TimeoutSec 3
  if ($s.Content -notmatch '"api_mounted"\s*:\s*true') {
    Write-Info "API not mounted. Attempting retry-mount..."
    Invoke-WebRequest -Method POST -Uri $retryMountUrl -UseBasicParsing -TimeoutSec 5 | Out-Null
    Start-Sleep -Milliseconds 300
    $s2 = Invoke-WebRequest -Uri $statusUrl -UseBasicParsing -TimeoutSec 3
    if ($s2.Content -notmatch '"api_mounted"\s*:\s*true') {
      Write-Fail "API failed to mount. /api/status: $($s2.Content)"
      try { $proc.Kill() } catch {}
      exit 1
    }
  }
  Write-Ok "API mounted"
} catch {
  Write-Fail "Status check failed: $($_.Exception.Message)"
  try { $proc.Kill() } catch {}
  exit 1
}

Write-Host ""
Write-Ok "Owlin is running on $base"
Write-Info "UI:       $base"
Write-Info "Health:   $healthUrl"
Write-Info "Status:   $statusUrl"
Write-Host ""
Write-Host "Press Ctrl+C to stop the server."

# 11) Keep this window attached to the server process output
#    (Optional live tail; comment out if you prefer a quiet window)
try {
  while (-not $proc.HasExited) {
    Start-Sleep -Milliseconds 500
    while (-not $proc.StandardOutput.EndOfStream) { Write-Host ($proc.StandardOutput.ReadLine()) }
    while (-not $proc.StandardError.EndOfStream)  { Write-Host ($proc.StandardError.ReadLine()) }
  }
} catch {}
if ($proc.ExitCode -ne 0) { Write-Fail "Server exited with code $($proc.ExitCode)"; exit $proc.ExitCode }