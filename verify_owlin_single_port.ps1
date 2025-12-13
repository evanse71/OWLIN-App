# ruthless verification for Windows PowerShell
$ErrorActionPreference = "Stop"

function Fail($msg) { Write-Host "❌ $msg" -ForegroundColor Red; exit 1 }
function Info($msg) { Write-Host "• $msg" -ForegroundColor Gray }
function Ok($msg)   { Write-Host "✅ $msg" -ForegroundColor Green }

# 0) Repo sanity
if (!(Test-Path ".\backend\final_single_port.py")) { Fail "Where is backend\final_single_port.py? Stand in repo root, not some random dungeon." }

# 1) Kill anything on 8001 (optional)
try {
  $conns = netstat -ano | Select-String ":8001"
  if ($conns) {
    $pids = $conns -replace ".*\s+(\d+)$", '$1' | Select-Object -Unique
    foreach ($pid in $pids) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Milliseconds 300
  }
} catch {}

# 2) Start server
Info "Launching server like a proper worker: python -m backend.final_single_port"
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

# 3) Wait for readiness
$ready = $false
for ($i=0; $i -lt 40; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/health" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200 -and $r.Content -match '"ok"\s*:\s*true') { $ready = $true; break }
  } catch {}
  Start-Sleep -Milliseconds 250
}
if (-not $ready) {
  $err = $proc.StandardError.ReadToEnd()
  $out = $proc.StandardOutput.ReadToEnd()
  Fail "Server not healthy. STDERR: `n$err`nSTDOUT:`n$out"
}
Ok "Health endpoint breathes."

# 4) Status check
$r = Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/status" -UseBasicParsing -TimeoutSec 3
if ($r.StatusCode -ne 200) { Fail "/api/status returned $($r.StatusCode). Pathetic." }
$mounted = ($r.Content -match '"api_mounted"\s*:\s*true')
if (-not $mounted) {
  Info "API not mounted. We do not beg. We command. Retrying mount."
  $rm = Invoke-WebRequest -Method POST -Uri "http://127.0.0.1:8001/api/retry-mount" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 300
  $rs = Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/status" -UseBasicParsing -TimeoutSec 3
  if ($rs.Content -notmatch '"api_mounted"\s*:\s*true') {
    Fail "Real API refuses to stand at attention. /api/status: `n$($rs.Content)"
  }
}
Ok "Real API mounted. No crying."

# 5) Root page
$root = Invoke-WebRequest -Uri "http://127.0.0.1:8001" -UseBasicParsing -TimeoutSec 3
if ($root.StatusCode -ne 200) { Fail "Root / not 200. You call this a UI?" }
Ok "Root responds like a decent citizen."

# 6) LLM probe (non-fatal if Ollama off)
try {
  $llm = Invoke-WebRequest -Uri "http://127.0.0.1:8001/llm/api/tags" -UseBasicParsing -TimeoutSec 2
  if ($llm.StatusCode -eq 200) { Ok "LLM proxy alive. Acceptable." }
} catch {
  Info "LLM proxy not reachable. If Ollama isn't running, this is fine. If it should be—start it."
}

# 7) Real endpoint smoke (adjust path if needed)
try {
  $inv = Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/manual/invoices" -UseBasicParsing -TimeoutSec 3
  if ($inv.StatusCode -eq 200) { Ok "Manual invoices endpoint answers. Good." }
} catch { Info "Manual invoices endpoint absent or protected. Ensure routers are wired. Not fatal here." }

Ok "Verdict: PASS. The machine stands. Dismissed."
exit 0
