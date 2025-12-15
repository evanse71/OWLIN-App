# PowerShell script to test auto-backup functionality
# Usage: .\test_auto_backup.ps1

Write-Host "=== Testing Auto-Backup Functionality ===" -ForegroundColor Cyan
Write-Host ""

# Check if database exists
$dbPath = "data\owlin.db"
if (-not (Test-Path $dbPath)) {
    Write-Host "ERROR: Database not found at $dbPath" -ForegroundColor Red
    exit 1
}

# Use Python to query SQLite (since sqlite3 CLI may not be available)
$pythonCmd = "python"

Write-Host "1. Checking backup_sessions table..." -ForegroundColor Yellow
python -c @"
import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('data/owlin.db')
cur = conn.cursor()

# Check if backup_sessions table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backup_sessions'")
if cur.fetchone():
    cur.execute("SELECT * FROM backup_sessions ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        print(f"Last backup at: {row[1]}")
        print(f"Document count since backup: {row[2]}")
        print(f"Last backup ID: {row[3]}")
    else:
        print("No session data found")
else:
    print("backup_sessions table does not exist yet")
conn.close()
"@

Write-Host ""
Write-Host "2. Checking recent backup audit log entries..." -ForegroundColor Yellow
python -c @"
import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('data/owlin.db')
cur = conn.cursor()

# Try different possible column names for timestamp
timestamp_cols = ['created_at', 'timestamp', 'ts', 'at']
timestamp_col = None

cur.execute('PRAGMA table_info(audit_log)')
columns = [row[1] for row in cur.fetchall()]

for col in timestamp_cols:
    if col in columns:
        timestamp_col = col
        break

if timestamp_col:
    cur.execute(f\"SELECT action, entity_type, entity_id, {timestamp_col}, metadata_json FROM audit_log WHERE action LIKE '%backup%' ORDER BY {timestamp_col} DESC LIMIT 5\")
else:
    cur.execute(\"SELECT action, entity_type, entity_id, metadata_json FROM audit_log WHERE action LIKE '%backup%' ORDER BY id DESC LIMIT 5\")

rows = cur.fetchall()
if rows:
    for row in rows:
        print(f\"Action: {row[0]}, Entity: {row[1]}, ID: {row[2]}\")
        if len(row) > 3:
            print(f\"  Timestamp: {row[3]}\")
        if len(row) > 4 and row[4]:
            try:
                meta = json.loads(row[4])
                print(f\"  Metadata: {json.dumps(meta, indent=2)}\")
            except:
                print(f\"  Metadata: {row[4]}\")
        print(\"\")
else:
    print(\"No backup audit log entries found\")

conn.close()
"@

Write-Host ""
Write-Host "3. Checking backup files..." -ForegroundColor Yellow
$backups = Get-ChildItem backups\*.zip | Sort-Object LastWriteTime -Descending
if ($backups) {
    Write-Host "Recent backups:" -ForegroundColor Green
    $backups | Select-Object -First 5 | ForEach-Object {
        $sizeKB = [math]::Round($_.Length / 1KB, 2)
        Write-Host "  $($_.Name) - $sizeKB KB - $($_.LastWriteTime)" -ForegroundColor Green
    }
} else {
    Write-Host "No backup files found" -ForegroundColor Red
}

Write-Host ""
Write-Host "4. Checking backup_index table..." -ForegroundColor Yellow
python -c @"
import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/owlin.db')
cur = conn.cursor()

cur.execute('SELECT id, created_at, path, size_bytes, mode FROM backup_index ORDER BY created_at DESC LIMIT 5')
rows = cur.fetchall()

if rows:
    for row in rows:
        size_mb = row[3] / (1024 * 1024)
        print(f\"Backup ID: {row[0]}\")
        print(f\"  Created: {row[1]}\")
        print(f\"  Path: {row[2]}\")
        print(f\"  Size: {size_mb:.2f} MB\")
        print(f\"  Mode: {row[4]}\")
        print(\"\")
else:
    print(\"No backups in backup_index table\")

conn.close()
"@

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan

