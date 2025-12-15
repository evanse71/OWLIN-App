@echo off
echo ========================================
echo    Verifying Owlin Setup
echo ========================================
echo.

echo [1] Checking Frontend (Port 5176)...
netstat -ano | findstr "5176.*LISTENING" >nul
if %errorlevel% == 0 (
    echo   SUCCESS: Frontend is running on port 5176
) else (
    echo   FAILED: Frontend is NOT running on port 5176
    echo   Start it with: cd frontend_clean ^&^& npm run dev -- --port 5176
)
echo.

echo [2] Checking Backend (Port 8000)...
netstat -ano | findstr "8000.*LISTENING" >nul
if %errorlevel% == 0 (
    echo   SUCCESS: Backend is running on port 8000
) else (
    echo   FAILED: Backend is NOT running on port 8000
    echo   Start it with: start_backend_8000.bat
)
echo.

echo [3] Testing Backend Health Endpoint...
curl -s http://localhost:8000/api/health >nul 2>&1
if %errorlevel% == 0 (
    echo   SUCCESS: Backend health check passed
    curl -s http://localhost:8000/api/health
    echo.
) else (
    echo   FAILED: Cannot reach backend health endpoint
    echo   Make sure backend is running and accessible
)
echo.

echo ========================================
echo    URLs to Access
echo ========================================
echo.
echo Frontend: http://localhost:5176/
echo Frontend (Invoices): http://localhost:5176/invoices?dev=1
echo Backend Health: http://localhost:8000/api/health
echo.
echo ========================================
pause

