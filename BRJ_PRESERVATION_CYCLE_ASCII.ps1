# ============================================================================
# BRUTAL RUSSIAN JUDGE - END-OF-DAY PRESERVATION CYCLE
# ============================================================================
# Objective: Archive, verify, and report — NO project file edits.
# ============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ----------------------------------------------------------------------------
# 1️⃣ DETECT PROJECT ROOT
# ----------------------------------------------------------------------------
Write-Host "`n[BRJ] ═════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "[BRJ] BRUTAL RUSSIAN JUDGE - PRESERVATION CYCLE" -ForegroundColor Cyan
Write-Host "[BRJ] ═════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Get-Location
}

$ProjectRoot = $ScriptDir
$ParentDir = Split-Path -Parent $ProjectRoot

Write-Host "[1️⃣] Project Root: $ProjectRoot" -ForegroundColor Green
Write-Host "[1️⃣] Parent Directory: $ParentDir" -ForegroundColor Green

# Verify critical directories exist
$RequiredDirs = @("backend", "data")
$MissingDirs = @()
foreach ($dir in $RequiredDirs) {
    if (-not (Test-Path (Join-Path $ProjectRoot $dir))) {
        $MissingDirs += $dir
    }
}

if ($MissingDirs.Count -gt 0) {
    Write-Host "[[FAIL]] MISSING CRITICAL DIRECTORIES: $($MissingDirs -join ', ')" -ForegroundColor Red
    exit 1
}

# ----------------------------------------------------------------------------
# 2️⃣ CREATE TIMESTAMPED ARCHIVE FOLDER
# ----------------------------------------------------------------------------
$Timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$ArchiveFolderName = "FixPack_$Timestamp"
$ArchivePath = Join-Path $ParentDir $ArchiveFolderName
$ArchiveZipName = "$ArchiveFolderName.zip"
$ArchiveZipPath = Join-Path $ParentDir $ArchiveZipName

Write-Host "`n[2️⃣] Creating archive folder: $ArchivePath" -ForegroundColor Yellow

if (Test-Path $ArchivePath) {
    Write-Host "[[WARN]]  Archive folder already exists, removing..." -ForegroundColor Yellow
    Remove-Item -Path $ArchivePath -Recurse -Force
}

New-Item -ItemType Directory -Path $ArchivePath -Force | Out-Null
Write-Host "[[OK]] Archive folder created" -ForegroundColor Green

# ----------------------------------------------------------------------------
# 3️⃣ COPY CRITICAL ASSETS
# ----------------------------------------------------------------------------
Write-Host "`n[3️⃣] Copying critical assets..." -ForegroundColor Yellow

$CriticalAssets = @(
    "backend",
    "frontend",
    "app",
    "data",
    "license",
    "backups",
    "logs",
    "migrations",
    "scripts",
    "tests",
    "public",
    "pages",
    "styles",
    "lib",
    "sdk",
    "docs",
    "deploy",
    "uploads",
    "validation_output",
    "source_extracted",
    "support_extracted"
)

$CopiedAssets = @()
$SkippedAssets = @()

foreach ($asset in $CriticalAssets) {
    $SourcePath = Join-Path $ProjectRoot $asset
    if (Test-Path $SourcePath) {
        $DestPath = Join-Path $ArchivePath $asset
        Write-Host "  [ARCHIVE] Copying $asset..." -ForegroundColor Gray
        try {
            Copy-Item -Path $SourcePath -Destination $DestPath -Recurse -Force -ErrorAction Stop
            $CopiedAssets += $asset
            Write-Host "  [OK] $asset copied" -ForegroundColor Green
        } catch {
            Write-Host "  [FAIL] Failed to copy $asset : $_" -ForegroundColor Red
            $SkippedAssets += "$asset (error: $_)"
        }
    } else {
        $SkippedAssets += "$asset (not found)"
    }
}

# Copy critical files
$CriticalFiles = @(
    "*.bat",
    "*.ps1",
    "*.md",
    "*.json",
    "*.ts",
    "*.config.*",
    "env.local",
    "health.json",
    "*.code-workspace"
)

Write-Host "`n  [FILE] Copying critical files..." -ForegroundColor Gray
foreach ($pattern in $CriticalFiles) {
    $Files = Get-ChildItem -Path $ProjectRoot -Filter $pattern -File -ErrorAction SilentlyContinue
    foreach ($file in $Files) {
        try {
            Copy-Item -Path $file.FullName -Destination $ArchivePath -Force -ErrorAction Stop
            Write-Host "  [OK] $($file.Name)" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN]  Failed: $($file.Name)" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n[[OK]] Assets copied: $($CopiedAssets.Count) directories" -ForegroundColor Green
if ($SkippedAssets.Count -gt 0) {
    Write-Host "[[WARN]]  Skipped: $($SkippedAssets.Count) items" -ForegroundColor Yellow
}

# ----------------------------------------------------------------------------
# 4️⃣ ZIP THE ARCHIVE
# ----------------------------------------------------------------------------
Write-Host "`n[4️⃣] Creating ZIP archive: $ArchiveZipPath" -ForegroundColor Yellow

if (Test-Path $ArchiveZipPath) {
    Remove-Item -Path $ArchiveZipPath -Force
}

try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($ArchivePath, $ArchiveZipPath)
    $ZipSize = (Get-Item $ArchiveZipPath).Length / 1MB
    Write-Host "[[OK]] ZIP created: $([math]::Round($ZipSize, 2)) MB" -ForegroundColor Green
} catch {
    Write-Host "[[FAIL]] ZIP creation failed: $_" -ForegroundColor Red
    $ArchiveZipPath = $null
}

# ----------------------------------------------------------------------------
# 5️⃣ BACKEND HEALTH CHECK
# ----------------------------------------------------------------------------
Write-Host "`n[5️⃣] Running backend health check..." -ForegroundColor Yellow

$HealthCheckPassed = $false
$HealthCheckError = $null
$ServerProcess = $null

try {
    # Start server in background
    Write-Host "  [START] Starting backend server..." -ForegroundColor Gray
    $ServerProcess = Start-Process -FilePath "python" -ArgumentList @(
        "-m", "uvicorn", "backend.main:app",
        "--port", "8000",
        "--host", "127.0.0.1"
    ) -PassThru -WindowStyle Hidden -RedirectStandardOutput "$ProjectRoot\health_check_stdout.log" -RedirectStandardError "$ProjectRoot\health_check_stderr.log"
    
    # Wait for server to start (max 10 seconds)
    $MaxWait = 10
    $WaitInterval = 0.5
    $Elapsed = 0
    $ServerReady = $false
    
    while ($Elapsed -lt $MaxWait -and -not $ServerReady) {
        Start-Sleep -Seconds $WaitInterval
        $Elapsed += $WaitInterval
        try {
            $Response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
            if ($Response.StatusCode -eq 200) {
                $HealthData = $Response.Content | ConvertFrom-Json
                if ($HealthData.status -eq "ok") {
                    $ServerReady = $true
                    $HealthCheckPassed = $true
                    Write-Host "  [OK] Health check passed: $($Response.Content)" -ForegroundColor Green
                }
            }
        } catch {
            # Server not ready yet, continue waiting
        }
    }
    
    if (-not $ServerReady) {
        $HealthCheckError = "Server did not respond within $MaxWait seconds or returned invalid response"
        Write-Host "  [WARN]  $HealthCheckError" -ForegroundColor Yellow
    }
    
} catch {
    $HealthCheckError = "Failed to start server or execute health check: $_"
    Write-Host "  [FAIL] $HealthCheckError" -ForegroundColor Red
} finally {
    # Stop server
    if ($ServerProcess -and -not $ServerProcess.HasExited) {
        Write-Host "  [STOP] Stopping server..." -ForegroundColor Gray
        try {
            Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        } catch {
            Write-Host "  [WARN]  Could not cleanly stop server process" -ForegroundColor Yellow
        }
    }
    # Cleanup health check logs
    if (Test-Path "$ProjectRoot\health_check_stdout.log") {
        Remove-Item "$ProjectRoot\health_check_stdout.log" -ErrorAction SilentlyContinue
    }
    if (Test-Path "$ProjectRoot\health_check_stderr.log") {
        Remove-Item "$ProjectRoot\health_check_stderr.log" -ErrorAction SilentlyContinue
    }
}

# ----------------------------------------------------------------------------
# 6️⃣ VERIFY DATABASE INTEGRITY
# ----------------------------------------------------------------------------
Write-Host "`n[6️⃣] Verifying database integrity..." -ForegroundColor Yellow

$DbPath = Join-Path $ProjectRoot "data\owlin.db"
$DbIntegrityCheck = $null
$InvoiceCount = $null
$DbError = $null

if (Test-Path $DbPath) {
    try {
        # Check integrity using Python
        Write-Host "  [CHECK] Running integrity check..." -ForegroundColor Gray
        $IntegrityScript = @"
import sqlite3
import sys
db_path = r'$DbPath'
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('PRAGMA integrity_check;')
    result = cursor.fetchone()[0]
    conn.close()
    print(result)
    sys.exit(0 if result == 'ok' else 1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"@
        $IntegrityScript | Out-File -FilePath "$env:TEMP\check_db_integrity.py" -Encoding UTF8 -Force
        $IntegrityResult = python "$env:TEMP\check_db_integrity.py" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $DbIntegrityCheck = $IntegrityResult.Trim()
            if ($DbIntegrityCheck -eq "ok") {
                Write-Host "  [OK] Database integrity: OK" -ForegroundColor Green
            } else {
                Write-Host "  [WARN]  Database integrity: $DbIntegrityCheck" -ForegroundColor Yellow
            }
        } else {
            $DbError = "Database integrity check failed"
            Write-Host "  [FAIL] $DbError" -ForegroundColor Red
        }
        Remove-Item "$env:TEMP\check_db_integrity.py" -ErrorAction SilentlyContinue
        
        # Count invoices using Python
        Write-Host "  [STATS] Counting invoices..." -ForegroundColor Gray
        $CountScript = @"
import sqlite3
import sys
db_path = r'$DbPath'
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM invoices;')
    count = cursor.fetchone()[0]
    conn.close()
    print(count)
    sys.exit(0)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"@
        $CountScript | Out-File -FilePath "$env:TEMP\count_invoices.py" -Encoding UTF8 -Force
        $InvoiceResult = python "$env:TEMP\count_invoices.py" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $InvoiceCount = [int]$InvoiceResult.Trim()
            Write-Host "  [OK] Invoice count: $InvoiceCount" -ForegroundColor Green
        } else {
            Write-Host "  [WARN]  Could not count invoices" -ForegroundColor Yellow
        }
        Remove-Item "$env:TEMP\count_invoices.py" -ErrorAction SilentlyContinue
        
    } catch {
        $DbError = "Database check failed: $_"
        Write-Host "  [FAIL] $DbError" -ForegroundColor Red
    }
} else {
    $DbError = "Database file not found: $DbPath"
    Write-Host "  [FAIL] $DbError" -ForegroundColor Red
}

# ----------------------------------------------------------------------------
# 7️⃣ COPY LOG FILES
# ----------------------------------------------------------------------------
Write-Host "`n[7️⃣] Copying log files..." -ForegroundColor Yellow

$LogFiles = @(
    "backend_stdout.log",
    "backend_stderr.log"
)

$CopiedLogs = @()
foreach ($logFile in $LogFiles) {
    $LogPath = Join-Path $ProjectRoot $logFile
    if (Test-Path $LogPath) {
        try {
            $DestLogPath = Join-Path $ArchivePath $logFile
            Copy-Item -Path $LogPath -Destination $DestLogPath -Force
            $CopiedLogs += $logFile
            $LogSize = (Get-Item $LogPath).Length / 1KB
            Write-Host "  [OK] $logFile ($([math]::Round($LogSize, 2)) KB)" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN]  Failed to copy $logFile" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [WARN]  $logFile not found" -ForegroundColor Yellow
    }
}

# ----------------------------------------------------------------------------
# 8️⃣ GENERATE SUMMARY REPORT
# ----------------------------------------------------------------------------
Write-Host "`n[8️⃣] Generating summary report..." -ForegroundColor Yellow

$SummaryPath = Join-Path $ArchivePath "BRJ_PRESERVATION_SUMMARY.md"

$Summary = @"
# BRUTAL RUSSIAN JUDGE - PRESERVATION CYCLE SUMMARY
## Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

---

## [ARCHIVE] ARCHIVE INFORMATION

- **Archive Folder**: `$ArchiveFolderName`
- **Archive Path**: `$ArchivePath`
- **ZIP Archive**: `$ArchiveZipName`
- **ZIP Size**: $(
    if ($ArchiveZipPath -and (Test-Path $ArchiveZipPath)) {
        $ZipSize = (Get-Item $ArchiveZipPath).Length / 1MB
        "$([math]::Round($ZipSize, 2)) MB"
    } else {
        "NOT CREATED"
    }
)

---

## [OK] ASSETS COPIED

**Directories Copied**: $($CopiedAssets.Count)
- $($CopiedAssets -join "`n- ")

**Skipped/Missing**: $($SkippedAssets.Count)
$(
    if ($SkippedAssets.Count -gt 0) {
        "- " + ($SkippedAssets -join "`n- ")
    } else {
        "None"
    }
)

---

## [HEALTH] HEALTH CHECK RESULTS

**Status**: $(if ($HealthCheckPassed) { "[OK] PASSED" } else { "[FAIL] FAILED" })

$(if ($HealthCheckError) {
    "**Error**: $HealthCheckError"
} else {
    "Backend health endpoint responded with status OK within timeout period."
})

---

## [DB] DATABASE VERIFICATION

**Database Path**: `$DbPath`
**Database Exists**: $(if (Test-Path $DbPath) { "[OK] YES" } else { "[FAIL] NO" })

$(if ($DbError) {
    "**Error**: $DbError`n"
})

$(if ($DbIntegrityCheck) {
    "**Integrity Check**: $DbIntegrityCheck`n"
} else {
    "**Integrity Check**: NOT PERFORMED`n"
})

$(if ($InvoiceCount -ne $null) {
    "**Invoice Count**: $InvoiceCount`n"
} else {
    "**Invoice Count**: NOT AVAILABLE`n"
})

---

## [LOG] LOG FILES ARCHIVED

**Logs Copied**: $($CopiedLogs.Count)
$(
    if ($CopiedLogs.Count -gt 0) {
        "- " + ($CopiedLogs -join "`n- ")
    } else {
        "None found"
    }
)

---

## [STATS] PRESERVATION STATUS

| Component | Status |
|-----------|--------|
| Archive Folder | [OK] CREATED |
| ZIP Archive | $(if ($ArchiveZipPath -and (Test-Path $ArchiveZipPath)) { "[OK] CREATED" } else { "[FAIL] FAILED" }) |
| Assets Copied | $(if ($CopiedAssets.Count -gt 0) { "[OK] $($CopiedAssets.Count) directories" } else { "[FAIL] NONE" }) |
| Health Check | $(if ($HealthCheckPassed) { "[OK] PASSED" } else { "[FAIL] FAILED" }) |
| Database Integrity | $(if ($DbIntegrityCheck -eq "ok") { "[OK] OK" } elseif ($DbIntegrityCheck) { "[WARN]  ISSUES" } else { "[FAIL] NOT CHECKED" }) |
| Logs Archived | $(if ($CopiedLogs.Count -gt 0) { "[OK] $($CopiedLogs.Count) files" } else { "[WARN]  NONE" }) |

---

## [*] FINAL VERDICT

$(if ($HealthCheckPassed -and $DbIntegrityCheck -eq "ok" -and $ArchiveZipPath) {
    "**[OK] PRESERVATION CYCLE COMPLETE**`n`nAll critical assets archived, health checks passed, database verified."
} elseif ($ArchiveZipPath) {
    "**[WARN]  PRESERVATION CYCLE COMPLETE WITH WARNINGS**`n`nArchive created but some checks failed. Review details above."
} else {
    "**[FAIL] PRESERVATION CYCLE FAILED**`n`nCritical failures detected. Archive may be incomplete."
})

---

*End of preservation cycle report*
"@

$Summary | Out-File -FilePath $SummaryPath -Encoding UTF8
Write-Host "[[OK]] Summary report created: BRJ_PRESERVATION_SUMMARY.md" -ForegroundColor Green

# Display summary to console
Write-Host "`n" + ("="*70) -ForegroundColor Cyan
Write-Host "BRUTAL RUSSIAN JUDGE - PRESERVATION CYCLE COMPLETE" -ForegroundColor Cyan
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host ""
Write-Host "[ARCHIVE] Archive: $ArchiveFolderName" -ForegroundColor White
Write-Host "[ARCHIVE] ZIP: $ArchiveZipName" -ForegroundColor White
Write-Host ""
Write-Host "[OK] Assets: $($CopiedAssets.Count) directories copied" -ForegroundColor Green
if ($HealthCheckPassed) {
    $HealthStatus = "PASSED"
    $HealthColor = "Green"
} else {
    $HealthStatus = "FAILED"
    $HealthColor = "Red"
}
Write-Host "[HEALTH] Health: $HealthStatus" -ForegroundColor $HealthColor
if ($DbIntegrityCheck -eq "ok") {
    $DbStatus = "OK"
    $DbColor = "Green"
} elseif ($DbIntegrityCheck) {
    $DbStatus = "ISSUES DETECTED"
    $DbColor = "Yellow"
} else {
    $DbStatus = "NOT CHECKED"
    $DbColor = "Red"
}
Write-Host "[DB]  Database: $DbStatus" -ForegroundColor $DbColor
Write-Host "[LOG] Logs: $($CopiedLogs.Count) files archived" -ForegroundColor Green
Write-Host ""
Write-Host "[FILE] Full report: $SummaryPath" -ForegroundColor Cyan
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host ""


