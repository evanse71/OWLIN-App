param(
  [string]$DestRoot = "C:\Owlin (new contents)"
)

$ErrorActionPreference = "Stop"

# Resolve project root as the parent of this script's directory
$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

# Prepare destination
New-Item -ItemType Directory -Force -Path $DestRoot | Out-Null
$stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$zip = Join-Path $DestRoot ("owlin_quick_backup_" + $stamp + ".zip")

Write-Host "ProjectRoot: $ProjectRoot"
Write-Host "Destination: $zip"

# Stop dev servers (best-effort)
$procs = @("uvicorn","python","node","streamlit")
foreach ($p in $procs) { Get-Process $p -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue }

# Create ZIP
Add-Type -AssemblyName 'System.IO.Compression.FileSystem'
[System.IO.Compression.ZipFile]::CreateFromDirectory($ProjectRoot, $zip)

# Hash
$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $zip
"$($hash.Hash)  $(Split-Path $zip -Leaf)" | Out-File -FilePath ($zip + ".sha256.txt") -Encoding ASCII

Write-Host "OK: $zip"
