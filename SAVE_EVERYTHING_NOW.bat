@echo off
echo Saving everything to ensure all work is preserved...

REM Get current timestamp
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%-%MM%-%DD%_%HH%-%Min%-%Sec%"

echo Creating backup with timestamp: %timestamp%

REM Create backup directory
mkdir "backups\save_%timestamp%" 2>nul

REM Copy all important files and directories
echo Copying source files...
xcopy /E /I /Y "source_extracted" "backups\save_%timestamp%\source_extracted"
xcopy /E /I /Y "backend" "backups\save_%timestamp%\backend"
xcopy /E /I /Y "frontend" "backups\save_%timestamp%\frontend"
xcopy /E /I /Y "data" "backups\save_%timestamp%\data"
xcopy /E /I /Y "uploads" "backups\save_%timestamp%\uploads"
xcopy /E /I /Y "logs" "backups\save_%timestamp%\logs"

REM Copy important configuration files
copy "*.env*" "backups\save_%timestamp%\" 2>nul
copy "*.md" "backups\save_%timestamp%\" 2>nul
copy "*.bat" "backups\save_%timestamp%\" 2>nul
copy "*.ps1" "backups\save_%timestamp%\" 2>nul
copy "*.sh" "backups\save_%timestamp%\" 2>nul
copy "*.py" "backups\save_%timestamp%\" 2>nul
copy "*.json" "backups\save_%timestamp%\" 2>nul
copy "*.txt" "backups\save_%timestamp%\" 2>nul

REM Create a summary file
echo Backup completed at %timestamp% > "backups\save_%timestamp%\BACKUP_SUMMARY.txt"
echo. >> "backups\save_%timestamp%\BACKUP_SUMMARY.txt"
echo Files backed up: >> "backups\save_%timestamp%\BACKUP_SUMMARY.txt"
dir /B "backups\save_%timestamp%" >> "backups\save_%timestamp%\BACKUP_SUMMARY.txt"

echo.
echo ========================================
echo BACKUP COMPLETED SUCCESSFULLY!
echo ========================================
echo Backup location: backups\save_%timestamp%
echo.
echo All your work has been saved and is safe to close.
echo.
pause
