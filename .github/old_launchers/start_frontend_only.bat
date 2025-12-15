@echo off
setlocal
set "ROOT=%~dp0"

echo ========================================
echo    🦉 O W L I N — Frontend Only
echo ========================================

echo [1/2] Killing stale processes...
taskkill /IM node.exe /F >nul 2>&1

echo [2/2] Starting frontend...
cd /d "%ROOT%source_extracted\tmp_lovable"
set "VITE_API_BASE_URL=http://127.0.0.1:8000"
set "VITE_OWLIN_DEMO=0"
set "VITE_OWLIN_EPHEMERAL=0"

echo Starting OWLIN Frontend on port 5173...
echo API Base URL: %VITE_API_BASE_URL%
echo.
echo Frontend will be available at:
echo - http://127.0.0.1:5173
echo.
echo Make sure the backend is running on port 8000!
echo.
npm run dev
