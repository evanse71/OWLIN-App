@echo off
setlocal ENABLEDELAYEDEXPANSION
title OWLIN (From Backup - Single Port)

set "ROOT=%USERPROFILE%\Desktop\owlin_backup_2025-10-02_225554"

echo ?? Using backup root: "%ROOT%"
if not exist "%ROOT%" (
  echo ? Backup folder not found. Edit the ROOT path in this .bat file.
  pause & exit /b 1
)

taskkill /IM python.exe /F >nul 2>&1
taskkill /IM node.exe /F   >nul 2>&1

set "OWLIN_ENV=dev"
set "OWLIN_DB_PATH=%ROOT%\data\owlin.db"
set "OWLIN_UPLOADS_DIR=%ROOT%\data\uploads"
set "OWLIN_DEMO=0"
set "OWLIN_DEFAULT_VENUE=Royal Oak Hotel"
if exist "%ROOT%\license\owlin.lic" set "OWLIN_LICENSE_PATH=%ROOT%\license\owlin.lic"

echo.
echo ?? DB:      %OWLIN_DB_PATH%
echo ?? Uploads: %OWLIN_UPLOADS_DIR%
echo ?? Venue:   %OWLIN_DEFAULT_VENUE%
echo.

pushd "%ROOT%\tmp_lovable"
echo ???  Building UI bundle...
call npm run build
if errorlevel 1 (
  echo ? npm build failed. Make sure Node/NPM are installed.
  popd & pause & exit /b 1
)
popd

pushd "%ROOT%"
echo ?? Starting backend (http://127.0.0.1:8000) ...
start "OWLIN Backend" cmd /k "set OWLIN_ENV=%OWLIN_ENV%&& set OWLIN_DB_PATH=%OWLIN_DB_PATH%&& set OWLIN_UPLOADS_DIR=%OWLIN_UPLOADS_DIR%&& set OWLIN_DEMO=%OWLIN_DEMO%&& set OWLIN_DEFAULT_VENUE=%OWLIN_DEFAULT_VENUE%&& set OWLIN_LICENSE_PATH=%OWLIN_LICENSE_PATH%&& python test_backend_simple.py"
popd

timeout /t 3 >nul
start "" "http://127.0.0.1:8000/invoices"
echo ? Launched. If the page looks stale, hard refresh (Ctrl+Shift+R).
pause
