# NightlySnapshot.ps1
# Automated nightly backup for Owlin installation
# Schedule via Task Scheduler (daily at 02:00)
# WAL-safe: SQLite allows concurrent reads during backup

param(
    [string]$InstallPath = "C:\Owlin",
    [string]$SnapshotPath = "C:\Owlin_Snapshots",
    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Continue"
$ts = (Get-Date).ToString("yyyy-MM-dd_HH-mm-ss")
$dst = "$SnapshotPath\FixPack_$ts"
$logFile = "$SnapshotPath\snapshot.log"

# Log function
function Write-Log {
    param([string]$Message)
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "$timestamp - $Message" | Out-File -FilePath $logFile -Append -Encoding UTF8
    Write-Host $Message
}

Write-Log "========================================="
Write-Log "NIGHTLY SNAPSHOT STARTED"
Write-Log "========================================="
Write-Log "Source: $InstallPath"
Write-Log "Destination: $dst"

# Ensure snapshot directory exists
if (-not (Test-Path $SnapshotPath)) {
    New-Item -ItemType Directory -Path $SnapshotPath | Out-Null
    Write-Log "Created snapshot directory: $SnapshotPath"
}

# Create this snapshot directory
try {
    New-Item -ItemType Directory -Path $dst | Out-Null
    Write-Log "Created snapshot: $dst"
} catch {
    Write-Log "ERROR: Failed to create snapshot directory: $_"
    exit 1
}

# Copy code (exclude large deps)
Write-Log "Copying code..."
$codeResult = Robocopy "$InstallPath\backend" "$dst\backend" /E /XD __pycache__ .pytest_cache /NFL /NDL /NJH /NJS
Write-Log "Code copied (exit code: $LASTEXITCODE)"

# Copy static files
Write-Log "Copying static files..."
if (Test-Path "$InstallPath\backend\static") {
    $staticResult = Robocopy "$InstallPath\backend\static" "$dst\static" /E /NFL /NDL /NJH /NJS
    Write-Log "Static files copied (exit code: $LASTEXITCODE)"
}

# Copy database (WAL-safe: SQLite allows concurrent reads)
Write-Log "Copying database..."
if (Test-Path "$InstallPath\data") {
    $dataResult = Robocopy "$InstallPath\data" "$dst\data" /E /NFL /NDL /NJH /NJS
    Write-Log "Database copied (exit code: $LASTEXITCODE)"
    
    # Copy WAL files if present
    if (Test-Path "$InstallPath\data\owlin.db-wal") {
        Copy-Item "$InstallPath\data\owlin.db-wal" "$dst\data\" -ErrorAction SilentlyContinue
        Write-Log "WAL file copied"
    }
    if (Test-Path "$InstallPath\data\owlin.db-shm") {
        Copy-Item "$InstallPath\data\owlin.db-shm" "$dst\data\" -ErrorAction SilentlyContinue
        Write-Log "SHM file copied"
    }
}

# Copy logs
Write-Log "Copying logs..."
Copy-Item "$InstallPath\backend_stdout.log*" "$dst\" -ErrorAction SilentlyContinue
Copy-Item "$InstallPath\backend_stderr.log*" "$dst\" -ErrorAction SilentlyContinue
Write-Log "Logs copied"

# Copy docs and scripts
Write-Log "Copying documentation..."
if (Test-Path "$InstallPath\docs") {
    Robocopy "$InstallPath\docs" "$dst\docs" /E /NFL /NDL /NJH /NJS | Out-Null
}
Copy-Item "$InstallPath\*.ps1" "$dst\" -ErrorAction SilentlyContinue
Copy-Item "$InstallPath\*.md" "$dst\" -ErrorAction SilentlyContinue
Write-Log "Documentation copied"

# Create snapshot metadata
$metadata = @"
Owlin Snapshot Metadata
========================
Created: $ts
Source: $InstallPath
Host: $env:COMPUTERNAME
User: $env:USERNAME

Contents:
---------
/backend/       - Backend source code
/static/        - Frontend build
/data/          - SQLite database (with WAL/SHM if present)
*.log           - Application logs
/docs/          - Documentation
*.ps1           - Scripts

Restore:
--------
1. Stop service: nssm stop Owlin-Backend
2. Restore code: Robocopy "$dst\backend" "$InstallPath\backend" /MIR
3. Restore static: Robocopy "$dst\static" "$InstallPath\backend\static" /MIR
4. Restore data: Robocopy "$dst\data" "$InstallPath\data" /MIR
5. Start service: nssm start Owlin-Backend

Health Check:
-------------
Invoke-RestMethod http://127.0.0.1:8000/api/health/details
"@
$metadata | Out-File "$dst\SNAPSHOT_README.txt" -Encoding UTF8
Write-Log "Metadata created"

# Calculate snapshot size
$snapshotSize = (Get-ChildItem $dst -Recurse -File | Measure-Object -Property Length -Sum).Sum
$snapshotSizeMB = [math]::Round($snapshotSize / 1MB, 2)
Write-Log "Snapshot size: $snapshotSizeMB MB"

# Cleanup old snapshots (retention policy)
Write-Log "Applying retention policy ($RetentionDays days)..."
$cutoffDate = (Get-Date).AddDays(-$RetentionDays)
$oldSnapshots = Get-ChildItem $SnapshotPath -Directory | 
    Where-Object { $_.Name -like "FixPack_*" -and $_.LastWriteTime -lt $cutoffDate }

foreach ($old in $oldSnapshots) {
    Write-Log "Removing old snapshot: $($old.Name)"
    Remove-Item $old.FullName -Recurse -Force
}

Write-Log "Cleanup complete. Snapshots retained: $((Get-ChildItem $SnapshotPath -Directory | Where-Object { $_.Name -like "FixPack_*" }).Count)"

Write-Log "========================================="
Write-Log "NIGHTLY SNAPSHOT COMPLETED"
Write-Log "========================================="

# Exit with success (Robocopy exit codes 0-7 are success)
if ($LASTEXITCODE -le 7) { exit 0 } else { exit $LASTEXITCODE }

