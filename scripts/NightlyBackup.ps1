# Owlin Nightly Backup Script
# Creates timestamped backups with 30-day retention
# Run via Windows Task Scheduler or cron equivalent

param(
    [string]$DataPath = ".\source_extracted\data",
    [string]$BackupPath = ".\backups",
    [int]$RetentionDays = 30
)

# Ensure backup directory exists
if (!(Test-Path $BackupPath)) {
    New-Item -ItemType Directory -Path $BackupPath -Force
    Write-Host "Created backup directory: $BackupPath"
}

# Generate timestamp for backup
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupName = "owlin-backup-$timestamp"
$backupFile = "$BackupPath\$backupName.zip"

Write-Host "Starting Owlin backup at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

try {
    # Create backup archive
    $filesToBackup = @(
        "$DataPath\owlin.db",
        "$DataPath\logs\*",
        "$DataPath\uploads\*",
        "$DataPath\meta\*"
    )
    
    # Only include files that exist
    $existingFiles = $filesToBackup | Where-Object { Test-Path $_ }
    
    if ($existingFiles.Count -eq 0) {
        Write-Warning "No files found to backup in $DataPath"
        exit 1
    }
    
    Compress-Archive -Path $existingFiles -DestinationPath $backupFile -Force
    $backupSize = (Get-Item $backupFile).Length
    Write-Host "Backup created: $backupFile ($([math]::Round($backupSize/1MB, 2)) MB)"
    
    # Create backup manifest
    $manifest = @{
        timestamp = $timestamp
        backupFile = $backupFile
        size = $backupSize
        files = $existingFiles
        retentionDays = $RetentionDays
    }
    
    $manifestFile = "$BackupPath\$backupName-manifest.json"
    $manifest | ConvertTo-Json -Depth 3 | Out-File -FilePath $manifestFile -Encoding UTF8
    
    # Clean up old backups (retention policy)
    $cutoffDate = (Get-Date).AddDays(-$RetentionDays)
    $oldBackups = Get-ChildItem -Path $BackupPath -Filter "owlin-backup-*.zip" | 
                  Where-Object { $_.CreationTime -lt $cutoffDate }
    
    if ($oldBackups.Count -gt 0) {
        Write-Host "Cleaning up $($oldBackups.Count) old backup(s) (older than $RetentionDays days)"
        $oldBackups | Remove-Item -Force
        Write-Host "Removed old backups: $($oldBackups.Name -join ', ')"
    }
    
    # Generate backup report
    $reportFile = "$BackupPath\backup-report-$timestamp.txt"
    $report = @"
Owlin Backup Report - $timestamp
=====================================

Backup File: $backupFile
Size: $([math]::Round($backupSize/1MB, 2)) MB
Files Backed Up: $($existingFiles.Count)
Retention: $RetentionDays days

Files Included:
$($existingFiles -join "`n")

Old Backups Removed: $($oldBackups.Count)
$($oldBackups.Name -join "`n")

Backup completed successfully at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@
    
    $report | Out-File -FilePath $reportFile -Encoding UTF8
    Write-Host "Backup report saved: $reportFile"
    
    Write-Host "Backup completed successfully!"
    
} catch {
    Write-Error "Backup failed: $($_.Exception.Message)"
    exit 1
}

# Optional: Send notification (uncomment and configure as needed)
# $notification = "Owlin backup completed: $backupFile ($([math]::Round($backupSize/1MB, 2)) MB)"
# Write-Host $notification
# # Send-EmailNotification -Subject "Owlin Backup Complete" -Body $notification
