@echo off
echo ==========================================================
echo    OWLIN BACKUP - WORKING VERSION
echo ==========================================================

:: Create backup directory
set "BACKUP_DIR=%USERPROFILE%\Documents\Owlin Backups"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: Generate timestamp
for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'"`) do set "TS=%%T"

:: Build archive filename
set "ZIP_NAME=Owlin_Backup_%TS%.zip"
set "ZIP_PATH=%BACKUP_DIR%\%ZIP_NAME%"

echo Creating backup: %ZIP_PATH%
echo.

:: Use simple PowerShell compression
powershell -NoProfile -Command "Compress-Archive -Path 'C:\Users\tedev\Desktop\owlin_backup_2025-10-02_225554\*' -DestinationPath '%ZIP_PATH%' -Force"

if exist "%ZIP_PATH%" (
    echo ✅ Backup created successfully!
    echo    → %ZIP_PATH%
    
    :: Show file size
    for %%A in ("%ZIP_PATH%") do set "ZIP_SIZE=%%~zA"
    set /a "ZIP_SIZE_MB=!ZIP_SIZE!/1024/1024"
    echo    → Size: !ZIP_SIZE_MB! MB
    
    echo.
    echo 📂 Existing backups:
    dir "%BACKUP_DIR%\Owlin_Backup_*.zip" /O:-D 2>nul
    
) else (
    echo ❌ Backup failed!
    exit /b 1
)

echo.
echo 🎉 Backup completed successfully!
pause
