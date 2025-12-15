@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: ============================================
:: Owlin - Simple Backup Script
:: ============================================

set "OWLIN_ROOT=%~dp0"
if "%OWLIN_ROOT:~-1%"=="\" set "OWLIN_ROOT=%OWLIN_ROOT:~0,-1%"

cd /d "%~dp0"

echo.
echo ==========================================================
echo    OWLIN BACKUP - SIMPLE VERSION
echo ==========================================================
echo  Root: "%OWLIN_ROOT%"
echo.

:: Create backup directory
set "BACKUP_DIR=%USERPROFILE%\Documents\Owlin Backups"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: Generate timestamp
for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'"`) do set "TS=%%T"

:: Build archive filename
set "ZIP_NAME=Owlin_Backup_%TS%.zip"
set "ZIP_PATH=%BACKUP_DIR%\%ZIP_NAME%"

echo 📦 Creating backup: "%ZIP_PATH%"
echo.

:: Use PowerShell to create the backup
powershell -NoProfile -Command ^
  "Get-ChildItem -Path '%OWLIN_ROOT%' -Recurse | Where-Object { $_.FullName -notmatch '__pycache__|node_modules|\.git|\.venv|\.log$|\.tmp$' } | Compress-Archive -DestinationPath '%ZIP_PATH%' -Force"

if exist "%ZIP_PATH%" (
    echo ✅ Backup created successfully!
    echo    → %ZIP_PATH%
    
    :: Show file size
    for %%A in ("%ZIP_PATH%") do set "ZIP_SIZE=%%~zA"
    set /a "ZIP_SIZE_MB=!ZIP_SIZE!/1024/1024"
    echo    → Size: !ZIP_SIZE_MB! MB
    
    :: Create SHA256 checksum
    set "SHA_PATH=%ZIP_PATH%.sha256.txt"
    powershell -NoProfile -Command ^
      "$h=Get-FileHash -Algorithm SHA256 -LiteralPath '%ZIP_PATH%'; ('{0} *{1}' -f $h.Hash, Split-Path -Leaf '%ZIP_PATH%') | Out-File -FilePath '%SHA_PATH%' -Encoding ascii"
    
    if exist "%SHA_PATH%" (
        echo    → SHA256: %SHA_PATH%
    )
    
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
exit /b 0
