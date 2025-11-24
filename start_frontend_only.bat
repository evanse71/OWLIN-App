@echo off
setlocal
set "ROOT=%~dp0"

echo ========================================
echo    🦉 O W L I N — Frontend Only
echo ========================================

echo [1/2] Killing stale processes...
taskkill /IM node.exe /F >nul 2>&1

echo [2/2] Starting frontend...
cd /d "%ROOT%frontend_clean"

echo Starting original Owlin Frontend on port 5176...
echo.
echo Frontend will be available at:
echo - http://localhost:5176/invoices?dev=1
echo - http://127.0.0.1:5176/invoices?dev=1
echo.
echo Note: Frontend uses proxy to backend on port 8000
echo       Make sure the backend is running on port 8000!
echo.
npm run dev
