@echo off
setlocal
set "ROOT=%~dp0"

echo ========================================
echo    🦉 O W L I N — Backend Only
echo ========================================

echo [1/3] Killing stale processes...
taskkill /IM python.exe /F >nul 2>&1

echo [2/3] Setting environment variables...
set "OWLIN_ENV=dev"
set "OWLIN_DB_PATH=%ROOT%data\owlin.db"
set "OWLIN_UPLOADS_DIR=%ROOT%data\uploads"
set "OWLIN_DEMO=0"
set "OWLIN_DEFAULT_VENUE=Royal Oak Hotel"
set "OWLIN_SINGLE_PORT=0"

echo [3/3] Starting backend...
cd /d "%ROOT%source_extracted"
echo Starting OWLIN Backend on port 8000...
echo Environment: %OWLIN_ENV%
echo Database: %OWLIN_DB_PATH%
echo Uploads: %OWLIN_UPLOADS_DIR%
echo.
echo Backend will be available at:
echo - http://127.0.0.1:8000
echo - http://127.0.0.1:8000/api/health
echo - http://127.0.0.1:8000/api/upload
echo.
python test_backend_simple.py
