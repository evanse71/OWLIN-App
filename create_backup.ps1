$timestamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$backupDir = Join-Path $env:USERPROFILE "Desktop\owlin_backup_$timestamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Write-Host "Backup directory created: $backupDir"
Write-Host $backupDir
