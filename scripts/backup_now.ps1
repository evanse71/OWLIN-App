param(
  [string]$Mode = "FULL",              # FULL or SLIM
  [string]$DestRoot = "C:\Owlin (new contents)",
  [int]$Keep = 10                      # how many backups to retain
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

# Robust project root: parent of this script's directory
$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

# 0) Paths
$Now = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$DestRootQuoted = $DestRoot
Ensure-Dir -p $DestRootQuoted

$Tag = $(if ($Mode -ieq "SLIM") { "slim" } else { "full" })
$ZipName = "owlin_backup_${Tag}_$Now.zip"
$ZipPath = Join-Path $DestRootQuoted $ZipName
$LogPath = Join-Path $DestRootQuoted ("owlin_backup_"+$Tag+"_"+$Now+".log")

# Begin log
"=== OWLIN BACKUP START $(Get-Date -Format s) ===" | Tee-Object -FilePath $LogPath
"ProjectRoot: $ProjectRoot" | Tee-Object -FilePath $LogPath -Append
"DestRoot   : $DestRootQuoted" | Tee-Object -FilePath $LogPath -Append
"Mode       : $Mode" | Tee-Object -FilePath $LogPath -Append

# 1) Stop common dev servers (best-effort)
"[$(Get-Date)] Stopping dev processes..." | Tee-Object -FilePath $LogPath -Append
$procs = @("uvicorn","python","node","streamlit")
foreach ($p in $procs) {
  try { Get-Process $p -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue } catch {}
}

# 2) Build exclusion lists
$Excludes = @(
  "node_modules", ".next", "dist", "build", "out\.next", "out\_next",
  ".git", ".turbo", ".cache", ".pytest_cache", "__pycache__", ".mypy_cache",
  "data\uploads\temp", "backups", ".DS_Store", "Thumbs.db"
)

$Critical = @(
  "data", "data\uploads", "data\owlin.db", "data\audit.log",
  ".github", "backend", "frontend", "src", "scripts", "package.json", "requirements.txt"
)

# 3) Stage files via robocopy
$TempDir = Join-Path $env:TEMP ("owlin_stage_" + [guid]::NewGuid())
Ensure-Dir -p $TempDir
"[$(Get-Date)] Staging dir: $TempDir" | Tee-Object -FilePath $LogPath -Append

# Base robocopy args
$rcArgs = @("`"$ProjectRoot`"", "`"$TempDir`"", "/MIR", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/SL")

if ($Mode -ieq "SLIM") {
  foreach ($ex in $Excludes) { $rcArgs += @("/XD", "`"$ProjectRoot\$ex`"") }
}

"[$(Get-Date)] Robocopy args: $($rcArgs -join ' ')" | Tee-Object -FilePath $LogPath -Append
$rcOut = robocopy @rcArgs
$rcCode = $LASTEXITCODE
"[$(Get-Date)] Robocopy exit code: $rcCode" | Tee-Object -FilePath $LogPath -Append

# 3b) Force-include critical paths in SLIM
if ($Mode -ieq "SLIM") {
  foreach ($c in $Critical) {
    $src = Join-Path $ProjectRoot $c
    if (Test-Path -LiteralPath $src) {
      $dst = Join-Path $TempDir $c
      Ensure-Dir -p (Split-Path $dst -Parent)
      try {
        robocopy "`"$src`"" "`"$dst`"" /MIR /R:1 /W:1 /NFL /NDL /NJH /NJS /NP /SL | Out-Null
      } catch {}
    }
  }
}

# Validate staged content
$FileCount = (Get-ChildItem -LiteralPath $TempDir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
"[$(Get-Date)] Staged file count: $FileCount" | Tee-Object -FilePath $LogPath -Append
if ($FileCount -lt 5) {
  "[$(Get-Date)] ERROR: Staged too few files ($FileCount). Check ProjectRoot/exclusions." | Tee-Object -FilePath $LogPath -Append
  throw "Backup aborted: staged file count is too low."
}

# 4) Create ZIP
"[$(Get-Date)] Creating ZIP: $ZipPath" | Tee-Object -FilePath $LogPath -Append
Add-Type -AssemblyName 'System.IO.Compression.FileSystem'
[System.IO.Compression.ZipFile]::CreateFromDirectory($TempDir, $ZipPath)

# 5) Hash & retention
"[$(Get-Date)] Generating SHA256..." | Tee-Object -FilePath $LogPath -Append
$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $ZipPath
$hashFile = $ZipPath + ".sha256.txt"
"$($hash.Hash)  $(Split-Path $ZipPath -Leaf)" | Out-File -FilePath $hashFile -Encoding ASCII

"[$(Get-Date)] Applying retention (keep last $Keep)..." | Tee-Object -FilePath $LogPath -Append
$backups = Get-ChildItem -LiteralPath $DestRootQuoted -Filter "owlin_backup_*.zip" | Sort-Object LastWriteTime -Descending
if ($backups.Count -gt $Keep) {
  $old = $backups[$Keep..($backups.Count-1)]
  foreach ($f in $old) {
    Remove-Item -LiteralPath $f.FullName -Force -ErrorAction SilentlyContinue
    $sha = $f.FullName + ".sha256.txt"
    if (Test-Path -LiteralPath $sha) { Remove-Item -LiteralPath $sha -Force -ErrorAction SilentlyContinue }
  }
}

# 6) Cleanup & final log
Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction SilentlyContinue
"[$(Get-Date)] DONE. Backup created: $ZipPath" | Tee-Object -FilePath $LogPath -Append
"=== OWLIN BACKUP END $(Get-Date -Format s) ===" | Tee-Object -FilePath $LogPath -Append
Write-Host "OK: $ZipPath"
