@echo off
setlocal
title OWLIN - Setup Nightly Backup

REM Set project root to this .bat's parent folder by default
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

set "TASK_NAME=OWLIN Nightly Backup"
set "BACKUP_SCRIPT=%ROOT%\Backup-Now.bat"

echo ? Setting up nightly backup task...
echo    Task Name: "%TASK_NAME%"
echo    Script:    "%BACKUP_SCRIPT%"
echo    Time:      23:30 daily

if not exist "%BACKUP_SCRIPT%" (
  echo ? Backup script not found: "%BACKUP_SCRIPT%". Make sure Backup-Now.bat exists.
  pause & exit /b 1
)

REM Register the scheduled task using PowerShell
powershell -Command ^
  "$taskName = '%TASK_NAME%';" ^
  "$script   = '%BACKUP_SCRIPT%';" ^
  "$action   = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument \"/c `\"$script`\"\";" ^
  "$trigger  = New-ScheduledTaskTrigger -Daily -At '23:30';" ^
  "try {" ^
  "  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue;" ^
  "  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Description 'Nightly Owlin backup' -User \"$env:USERNAME\";" ^
  "  Write-Host '? Scheduled task created/updated successfully.';" ^
  "} catch {" ^
  "  Write-Host '? Failed to create scheduled task: ' $_.Exception.Message;" ^
  "}"
pause
