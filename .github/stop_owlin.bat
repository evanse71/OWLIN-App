@echo off
setlocal

echo ========================================
echo    🦉 O W L I N — Stop All Services
echo ========================================

echo Stopping all OWLIN processes...

echo [1/2] Stopping Python processes (Backend)...
taskkill /IM python.exe /F >nul 2>&1
if errorlevel 1 (
    echo No Python processes found.
) else (
    echo Python processes stopped.
)

echo [2/2] Stopping Node processes (Frontend)...
taskkill /IM node.exe /F >nul 2>&1
if errorlevel 1 (
    echo No Node processes found.
) else (
    echo Node processes stopped.
)

echo.
echo ========================================
echo    ✅ All OWLIN services stopped
echo ========================================
echo.
echo All backend and frontend processes have been terminated.
echo You can now safely restart the services.
echo.
pause
