# Fix-And-Launch-Owlin.ps1 (v2.7 – no PID capture, separate logs)
[CmdletBinding()]
param([switch]$Fix,[int]$Port=8000)
Set-StrictMode -Version Latest; $ErrorActionPreference='Stop'

function Assert-NotSystem32{ $cwd=(Resolve-Path ".").Path; if($cwd -match '\\Windows\\System32($|\\)'){throw "You're in $cwd. cd to your Owlin repo root first."}}
function Find-RepoRoot([string]$StartDir){ $cur=(Resolve-Path $StartDir).Path; for($i=0;$i -lt 12;$i++){ $candidate=Join-Path $cur "backend\main.py"; if(Test-Path $candidate){return $cur}; $parent=Split-Path $cur -Parent; if(-not $parent -or $parent -eq $cur){break}; $cur=$parent}; return $null}

Assert-NotSystem32
$DefaultStart=(Resolve-Path ".").Path
$RepoRoot=Find-RepoRoot -StartDir $DefaultStart
if(-not $RepoRoot){ throw "Could not locate repo root from '$DefaultStart'. Please cd to the folder that contains 'backend\main.py'."}
$BackendDir=Join-Path $RepoRoot "backend"
$DataDir=Join-Path $RepoRoot "data"
$DbPath=Join-Path $DataDir "owlin.db"
$StdOutPath=Join-Path $BackendDir "backend_stdout.log"
$StdErrPath=Join-Path $BackendDir "backend_stderr.log"
Write-Host "RepoRoot: $RepoRoot" -ForegroundColor Cyan
Write-Host "Backend : $BackendDir" -ForegroundColor Cyan
if(!(Test-Path $BackendDir)){ throw "backend/ not found at $BackendDir. Run this from the project root."}

function Stop-Port([int]$P){
  Write-Host "Checking for processes on port $P..." -ForegroundColor Yellow
  $conns = netstat -ano | Select-String ":$P\s"
  if($conns){
    $procIds = $conns | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
    foreach($procId in $procIds){ try{ Write-Host "Killing PID $procId using port $P" -ForegroundColor Yellow; Stop-Process -Id ([int]$procId) -Force -ErrorAction Stop }catch{} }
  } else { Write-Host "No processes bound to port $P." -ForegroundColor Green }
}

function Clean-Caches{
  Write-Host "Cleaning __pycache__ and *.pyc..." -ForegroundColor Yellow
  Get-ChildItem -Path $RepoRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  Get-ChildItem -Path $RepoRoot -Recurse -Filter "*.pyc" -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
}

function Ensure-Data{
  if(!(Test-Path $DataDir)){ New-Item -ItemType Directory -Path $DataDir | Out-Null }
  Write-Host "Data dir present: $DataDir" -ForegroundColor Green
}

function Scan-Legacy-Imports{
  Write-Host "Scanning for legacy imports..." -ForegroundColor Yellow
  $patterns=@('from\s+backend\.','import\s+backend\.settings','import\s+backend\.config','from\s+backend\s+import')
  $files=Get-ChildItem -Path $BackendDir -Recurse -Filter "*.py" -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
  $hits=@()
  foreach($f in $files){
    try{
      $c=Get-Content $f -Raw -ErrorAction Stop
      foreach($p in $patterns){ if($c -match $p){ $hits += [pscustomobject]@{ File=$f; Pattern=$p } } }
    }catch{}
  }
  if($hits.Count){ Write-Host ("Found {0} legacy import occurrence{1}:" -f $hits.Count, $(if($hits.Count -eq 1){""}else{"s"})) -ForegroundColor Red
    ($hits | Sort-Object File,Pattern) | ForEach-Object { Write-Host (" - {0}" -f $_.File) -ForegroundColor DarkYellow }
  } else { Write-Host "No legacy imports found." -ForegroundColor Green }
  return @($hits)
}

function Auto-Fix-Legacy-Imports($hits){
  $hits = @($hits) | Where-Object { $_ -and $_.PSObject -and $_.PSObject.Properties['File'] }
  if(-not $hits.Count){ return }
  Write-Host "Auto-fixing common patterns..." -ForegroundColor Yellow
  $rules=@(
    @{Pattern='from\s+backend\.(\S+)\s+import\s+';Replacement='from $1 import '},
    @{Pattern='import\s+backend\.settings\b';Replacement='import settings'},
    @{Pattern='import\s+backend\.config\b';Replacement='import config'},
    @{Pattern='from\s+backend\s+import\s+settings';Replacement='import settings'},
    @{Pattern='from\s+backend\s+import\s+config';Replacement='import config'}
  )
  $touched=0
  $files = $hits | ForEach-Object { $_.File } | Where-Object { $_ } | Sort-Object -Unique
  foreach($file in $files){
    try{
      $t = Get-Content $file -Raw -ErrorAction Stop
      $o = $t
      foreach($r in $rules){ $t = [regex]::Replace($t,$r.Pattern,$r.Replacement) }
      if($t -ne $o){ Set-Content -Path $file -Value $t -Encoding UTF8; Write-Host "Rewrote: $file" -ForegroundColor Cyan; $touched++ }
    }catch{ Write-Warning "Could not modify $file : $($_.Exception.Message)" }
  }
  Write-Host "Auto-fix complete. Files touched: $touched" -ForegroundColor Green
}

function Activate-Venv{
  $venv=Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"
  if(Test-Path $venv){ Write-Host "Activating virtual environment..." -ForegroundColor Yellow; . $venv }
  else { Write-Host "No .venv found; using system Python." -ForegroundColor Yellow }
}

# Fire-and-forget start: DO NOT return or store the process object
function Start-Backend{
  param([int]$P)
  $env:PYTHONPATH=$BackendDir
  if(Test-Path $StdOutPath){ Remove-Item $StdOutPath -Force -ErrorAction SilentlyContinue }
  if(Test-Path $StdErrPath){ Remove-Item $StdErrPath -Force -ErrorAction SilentlyContinue }
  $python="python"; $args="-m uvicorn main:app --host 127.0.0.1 --port $P"
  Write-Host "Starting: $python $args" -ForegroundColor Yellow
  Start-Process -FilePath $python -ArgumentList $args `
    -WorkingDirectory $BackendDir -WindowStyle Hidden `
    -RedirectStandardOutput $StdOutPath -RedirectStandardError $StdErrPath | Out-Null
  Start-Sleep -Seconds 1 | Out-Null
}

function Wait-Health([int]$P,[int]$TimeoutSec=40){
  $deadline=(Get-Date).AddSeconds($TimeoutSec); $url="http://127.0.0.1:$P/api/health"
  Write-Host "Waiting for health at $url ..." -ForegroundColor Yellow
  do{
    try{
      $r=Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
      if($r.StatusCode -eq 200 -and $r.Content -match '"status"\s*:\s*"ok"'){
        Write-Host "Backend healthy: $($r.Content)" -ForegroundColor Green
        return $true
      }
    }catch{ Start-Sleep -Milliseconds 500 }
  } while((Get-Date) -lt $deadline)
  Write-Warning "Health check FAILED."
  return $false
}

Write-Host "`n== VALIDATE LOCATION ==" -ForegroundColor Magenta
Write-Host "Using RepoRoot: $RepoRoot" -ForegroundColor Cyan

Write-Host "`n== KILL & CLEAN ==" -ForegroundColor Magenta
Stop-Port -P $Port
Get-Process python,uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Clean-Caches
Ensure-Data

Write-Host "`n== SCAN IMPORTS ==" -ForegroundColor Magenta
$hits=@(Scan-Legacy-Imports)
if($Fix -and $hits -and $hits.Count){
  Write-Host "`n== AUTO-FIX IMPORTS ==" -ForegroundColor Magenta
  Auto-Fix-Legacy-Imports -hits $hits
  Write-Host "`n== RESCAN IMPORTS ==" -ForegroundColor Magenta
  $hits=@(Scan-Legacy-Imports)
  if($hits -and $hits.Count){ Write-Warning "Some legacy imports remain. Review above list manually." } else { Write-Host "All legacy imports resolved." -ForegroundColor Green }
}

Write-Host "`n== ENV & VENV ==" -ForegroundColor Magenta
Activate-Venv
$env:OWLIN_DB=$DbPath
Write-Host "OWLIN_DB -> $($env:OWLIN_DB)" -ForegroundColor Cyan

Write-Host "`n== START BACKEND ==" -ForegroundColor Magenta
Start-Backend -P $Port

if(-not (Wait-Health -P $Port -TimeoutSec 40)){
  Write-Warning "Backend failed health. Tail of logs (if present):"
  if(Test-Path $StdOutPath){ Write-Host "`n--- stdout tail ---" -ForegroundColor DarkCyan; Get-Content $StdOutPath -Tail 120 | Write-Host }
  if(Test-Path $StdErrPath){ Write-Host "`n--- stderr tail ---" -ForegroundColor DarkCyan; Get-Content $StdErrPath -Tail 120 | Write-Host }
  throw "Backend failed health check. See $StdOutPath / $StdErrPath for details."
}
Write-Host "`nAll good. FastAPI is up on http://127.0.0.1:$Port" -ForegroundColor Green
