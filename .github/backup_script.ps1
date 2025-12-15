# Step 1/10: Define paths & timestamp
$ROOT = "$env:USERPROFILE\Desktop\owlin_backup_2025-10-02_225554\source_extracted"
$BACKUPS = Join-Path $ROOT "backups"
$STAMP = (Get-Date).ToString("yyyy-MM-dd_HH-mm-ss")
$OUTZIP = Join-Path $BACKUPS "OWLIN_Save_$STAMP.zip"
$REPORT = Join-Path $BACKUPS "OWLIN_Save_$STAMP_report.txt"
$SQLDUMP = Join-Path $BACKUPS "owlin_$STAMP.sql"
$SHA256 = Join-Path $BACKUPS "OWLIN_Save_$STAMP.sha256.txt"

# Create backups folder if missing
if (!(Test-Path $BACKUPS)) {
    New-Item -ItemType Directory -Path $BACKUPS -Force | Out-Null
}

Write-Host "Step 1/10: Paths defined and backups folder created"
Write-Host "ROOT: $ROOT"
Write-Host "BACKUPS: $BACKUPS"
Write-Host "STAMP: $STAMP"
Write-Host "OUTZIP: $OUTZIP"
Write-Host "REPORT: $REPORT"
Write-Host "SQLDUMP: $SQLDUMP"
Write-Host "SHA256: $SHA256"

# Step 2/10: Stop any running processes
Write-Host "Step 2/10: Stopping running processes..."
try {
    taskkill /IM python.exe /F 2>$null
    Write-Host "Stopped python.exe processes"
} catch {
    Write-Host "No python.exe processes found"
}

try {
    taskkill /IM node.exe /F 2>$null
    Write-Host "Stopped node.exe processes"
} catch {
    Write-Host "No node.exe processes found"
}

# Step 3/10: Quick environment capture
Write-Host "Step 3/10: Capturing environment..."
$reportContent = @"
OWLIN Nightly Save-All Report
============================
Timestamp: $(Get-Date)
ROOT Path: $ROOT
DB Path: $ROOT\data\owlin.db
Uploads Dir: $ROOT\data\uploads
"@

# Check for OWLIN environment variables
$owlinVars = Get-ChildItem Env: | Where-Object { $_.Name -like "OWLIN_*" }
if ($owlinVars) {
    $reportContent += "`nOWLIN Environment Variables:`n"
    foreach ($var in $owlinVars) {
        $reportContent += "  $($var.Name) = $($var.Value)`n"
    }
} else {
    $reportContent += "`nNo OWLIN environment variables found`n"
}

# Check if backend is running
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/docs" -TimeoutSec 5 -UseBasicParsing
    $reportContent += "`nBackend Status: Running (HTTP 200)`n"
} catch {
    $reportContent += "`nBackend Status: Not running or not accessible`n"
}

$reportContent | Out-File -FilePath $REPORT -Encoding UTF8
Write-Host "Environment captured to report"

# Step 4/10: Verify DB presence and basic schema
Write-Host "Step 4/10: Verifying database..."
$dbPath = "$ROOT\data\owlin.db"
if (Test-Path $dbPath) {
    $reportContent += "`nDatabase Status: Found at $dbPath`n"
    
    # Use Python to check database schema
    $pythonScript = @"
import sqlite3
import sys

try:
    conn = sqlite3.connect(r'$dbPath')
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    table_names = [table[0] for table in tables]
    
    print(f"Tables found: {', '.join(table_names)}")
    
    # Count invoices if table exists
    if 'invoices' in table_names:
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        print(f"Invoice count: {invoice_count}")
    else:
        print("Invoice count: 0 (table not found)")
    
    # Count delivery_notes if table exists
    if 'delivery_notes' in table_names:
        cursor.execute("SELECT COUNT(*) FROM delivery_notes")
        delivery_count = cursor.fetchone()[0]
        print(f"Delivery notes count: {delivery_count}")
    else:
        print("Delivery notes count: 0 (table not found)")
    
    conn.close()
    print("Database verification completed successfully")
    
except Exception as e:
    print(f"Database verification failed: {e}")
    sys.exit(1)
"@
    
    $pythonScript | Out-File -FilePath "temp_db_check.py" -Encoding UTF8
    $dbOutput = python temp_db_check.py 2>&1
    Remove-Item "temp_db_check.py" -Force
    
    $reportContent += "`nDatabase Verification:`n$dbOutput`n"
    Write-Host "Database verification completed"
} else {
    $reportContent += "`nDatabase Status: NOT FOUND at $dbPath`n"
    Write-Host "WARNING: Database file not found!"
}

# Step 5/10: Produce SQL dump
Write-Host "Step 5/10: Creating SQL dump..."
if (Test-Path $dbPath) {
    $dumpScript = @"
import sqlite3
import sys

try:
    conn = sqlite3.connect(r'$dbPath')
    with open(r'$SQLDUMP', 'w', encoding='utf-8') as f:
        for line in conn.iterdump():
            f.write(line + '\n')
    conn.close()
    print("SQL dump completed successfully")
except Exception as e:
    print(f"SQL dump failed: {e}")
    sys.exit(1)
"@
    
    $dumpScript | Out-File -FilePath "temp_dump.py" -Encoding UTF8
    $dumpOutput = python temp_dump.py 2>&1
    Remove-Item "temp_dump.py" -Force
    
    if (Test-Path $SQLDUMP) {
        $dumpSize = (Get-Item $SQLDUMP).Length
        $reportContent += "`nSQL Dump: OK - Size: $dumpSize bytes`n"
        Write-Host "SQL dump created successfully"
    } else {
        $reportContent += "`nSQL Dump: FAILED - $dumpOutput`n"
        Write-Host "WARNING: SQL dump failed!"
    }
} else {
    $reportContent += "`nSQL Dump: SKIPPED - Database not found`n"
}

# Step 6/10: Create ZIP backup
Write-Host "Step 6/10: Creating ZIP backup..."
$filesToInclude = @(
    "data\owlin.db",
    "data\uploads\*",
    "logs\*",
    "tmp_lovable\*",
    "test_backend_simple.py",
    "Start-Owlin-From-Backup.bat",
    "Stop-Owlin.bat",
    "Quick-Start-Guide.txt"
)

$tempDir = Join-Path $env:TEMP "owlin_backup_$STAMP"
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

$fileCount = 0
foreach ($pattern in $filesToInclude) {
    $fullPattern = Join-Path $ROOT $pattern
    if (Test-Path $fullPattern) {
        if ((Get-Item $fullPattern) -is [System.IO.DirectoryInfo]) {
            # It's a directory
            $files = Get-ChildItem -Path $fullPattern -Recurse -File
            foreach ($file in $files) {
                $relativePath = $file.FullName.Substring($ROOT.Length + 1)
                $destPath = Join-Path $tempDir $relativePath
                $destDir = Split-Path $destPath -Parent
                if (!(Test-Path $destDir)) {
                    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
                }
                Copy-Item $file.FullName $destPath -Force
                $fileCount++
            }
        } else {
            # It's a file
            $relativePath = $pattern
            $destPath = Join-Path $tempDir $relativePath
            $destDir = Split-Path $destPath -Parent
            if (!(Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            Copy-Item $fullPattern $destPath -Force
            $fileCount++
        }
    }
}

# Also include any .py files in root
$pyFiles = Get-ChildItem -Path $ROOT -Filter "*.py" -File
foreach ($file in $pyFiles) {
    $destPath = Join-Path $tempDir $file.Name
    Copy-Item $file.FullName $destPath -Force
    $fileCount++
}

# Create the ZIP
Compress-Archive -Path "$tempDir\*" -DestinationPath $OUTZIP -Force
Remove-Item $tempDir -Recurse -Force

if (Test-Path $OUTZIP) {
    $zipSize = (Get-Item $OUTZIP).Length
    $reportContent += "`nZIP Backup: OK - Files: $fileCount, Size: $zipSize bytes`n"
    Write-Host "ZIP backup created with $fileCount files"
} else {
    $reportContent += "`nZIP Backup: FAILED`n"
    Write-Host "ERROR: ZIP backup failed!"
}

# Step 7/10: Write integrity checks
Write-Host "Step 7/10: Computing integrity checks..."
if (Test-Path $OUTZIP) {
    $hash = Get-FileHash -Path $OUTZIP -Algorithm SHA256
    $hash.Hash | Out-File -FilePath $SHA256 -Encoding UTF8
    $reportContent += "`nSHA256: $($hash.Hash)`n"
    Write-Host "SHA256 computed and saved"
} else {
    $reportContent += "`nSHA256: FAILED - ZIP not found`n"
}

# Step 8/10: Create friendly summary
Write-Host "Step 8/10: Creating summary..."
$summary = @"

=== BACKUP SUMMARY ===
Timestamp: $(Get-Date)
ZIP File: $OUTZIP
SQL Dump: $SQLDUMP
SHA256 File: $SHA256
Files Backed Up: $fileCount
ZIP Size: $zipSize bytes

=== RESTORATION INSTRUCTIONS ===
1. Extract the ZIP file to a new directory
2. Run Start-Owlin-From-Backup.bat to launch the application
3. The database will be restored from the SQL dump if needed

=== END OF REPORT ===
"@

$reportContent += $summary
$reportContent | Out-File -FilePath $REPORT -Encoding UTF8

# Step 9/10: Open File Explorer
Write-Host "Step 9/10: Opening File Explorer..."
Start-Process "explorer.exe" -ArgumentList "/select,`"$OUTZIP`""

# Step 10/10: Final message
Write-Host "Step 10/10: Backup complete!"
Write-Host "✅ Nightly Save-All complete"
Write-Host "ZIP: $OUTZIP"
Write-Host "Report: $REPORT"
Write-Host "Note: Use the Start-Owlin-From-Backup.bat in this backup to relaunch."

# Display last 20 lines of report
Write-Host "`n=== LAST 20 LINES OF REPORT ==="
Get-Content $REPORT | Select-Object -Last 20
