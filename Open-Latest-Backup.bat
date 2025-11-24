@echo off
setlocal
title OWLIN - Open Latest Backup

REM Set project root to this .bat's parent folder by default
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "BACKUP_DIR=%ROOT%\backups"

if not exist "%BACKUP_DIR%" (
  echo ? Backup directory not found: "%BACKUP_DIR%"
  pause & exit /b 1
)

echo ?? Opening latest backup...
for /f "dir /b /a-d /od" %%i in ('dir "%BACKUP_DIR%\owlin_save_*.zip" /b /a-d /od 2^>nul') do set "LATEST_ZIP=%%i"

if defined LATEST_ZIP (
  echo ? Found latest backup: "%BACKUP_DIR%\%LATEST_ZIP%"
  explorer.exe "/select,\"%BACKUP_DIR%\%LATEST_ZIP%\""
) else (
  echo ? No backup ZIP files found in "%BACKUP_DIR%".
)
pause
