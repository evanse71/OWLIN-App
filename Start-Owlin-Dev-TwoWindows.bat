@echo off
setlocal ENABLEDELAYEDEXPANSION
set "ROOT=%USERPROFILE%\Desktop\owlin_backup_2025-10-02_225554"
title OWLIN (Backup Dev - Two Windows)

if not exist "%ROOT%" (
  echo ? Backup folder not found. Edit ROOT in this file.
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

REM Backend window
start "OWLIN Backend" cmd /k "cd /d %ROOT% && set OWLIN_ENV=%OWLIN_ENV%&& set OWLIN_DB_PATH=%OWLIN_DB_PATH%&& set OWLIN_UPLOADS_DIR=%OWLIN_UPLOADS_DIR%&& set OWLIN_DEMO=%OWLIN_DEMO%&& set OWLIN_DEFAULT_VENUE=%OWLIN_DEFAULT_VENUE%&& set OWLIN_LICENSE_PATH=%OWLIN_LICENSE_PATH%&& python test_backend_simple.py"

REM UI dev window (Vite). Ensure API base points to backend on 8000
start "OWLIN UI (Vite)" cmd /k "cd /d %ROOT%\tmp_lovable && set VITE_API_BASE_URL=http://127.0.0.1:8000 && npm run dev"

timeout /t 3 >nul
start "" "http://localhost:5173/invoices"
echo ? Backend + Vite dev started.
pause
