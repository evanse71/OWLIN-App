@echo off
echo Quick save - preserving all current work...

REM Create timestamp
set timestamp=%date:~-4,4%-%date:~-10,2%-%date:~-7,2%_%time:~0,2%-%time:~3,2%-%time:~6,2%
set timestamp=%timestamp: =0%

REM Create backup directory
mkdir "backups\quick_save_%timestamp%" 2>nul

echo Backing up to: backups\quick_save_%timestamp%

REM Copy all important directories
echo Copying directories...
robocopy "source_extracted" "backups\quick_save_%timestamp%\source_extracted" /E /NFL /NDL /NJH /NJS /NC /NS /NP
robocopy "backend" "backups\quick_save_%timestamp%\backend" /E /NFL /NDL /NJH /NJS /NC /NS /NP
robocopy "frontend" "backups\quick_save_%timestamp%\frontend" /E /NFL /NDL /NJH /NJS /NC /NS /NP
robocopy "data" "backups\quick_save_%timestamp%\data" /E /NFL /NDL /NJH /NJS /NC /NS /NP
robocopy "uploads" "backups\quick_save_%timestamp%\uploads" /E /NFL /NDL /NJH /NJS /NC /NS /NP
robocopy "logs" "backups\quick_save_%timestamp%\logs" /E /NFL /NDL /NJH /NJS /NC /NS /NP

REM Copy important files
echo Copying important files...
copy "*.env*" "backups\quick_save_%timestamp%\" >nul 2>&1
copy "*.md" "backups\quick_save_%timestamp%\" >nul 2>&1
copy "*.bat" "backups\quick_save_%timestamp%\" >nul 2>&1
copy "*.ps1" "backups\quick_save_%timestamp%\" >nul 2>&1
copy "*.py" "backups\quick_save_%timestamp%\" >nul 2>&1
copy "*.json" "backups\quick_save_%timestamp%\" >nul 2>&1
copy "*.txt" "backups\quick_save_%timestamp%\" >nul 2>&1

echo.
echo ========================================
echo QUICK SAVE COMPLETED!
echo ========================================
echo Backup location: backups\quick_save_%timestamp%
echo.
echo All your work is now safely backed up.
echo You can safely close everything.
echo.
pause
