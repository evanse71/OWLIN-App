@echo off
setlocal
set "ROOT=%~dp0"

echo ========================================
echo    🦉 O W L I N — Frontend on Port 5176
echo ========================================

echo [1/2] Killing stale processes...
taskkill /IM node.exe /F >nul 2>&1

echo [2/2] Starting frontend on port 5176...
cd /d "%ROOT%frontend_clean"

if not exist "node_modules" (
    echo [WARN] node_modules not found. Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed!
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo    Frontend Configuration
echo ========================================
echo Frontend Port: 5176
echo API Base URL: %VITE_API_BASE_URL%
echo.
echo Frontend will be available at:
echo - http://localhost:5176/invoices?dev=1
echo - http://127.0.0.1:5176/invoices?dev=1
echo.
echo Make sure the backend is running on port 8000!
echo.
echo ========================================
echo.

echo Starting original Owlin frontend on port 5176...
npm run dev

