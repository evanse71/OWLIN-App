@echo off
setlocal enabledelayedexpansion
set "ROOT=%~dp0"

echo ========================================
echo    🦉 OWLIN - Complete Startup
echo ========================================
echo.
echo Starting Backend (port 8000) and Frontend (port 5176)
echo.

:: Check if ports are in use
echo [CHECK] Checking if ports are available...
netstat -an | findstr ":8000" >nul
if %errorlevel% == 0 (
    echo [WARN] Port 8000 is already in use!
    echo        Killing processes on port 8000...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)

netstat -an | findstr ":5176" >nul
if %errorlevel% == 0 (
    echo [WARN] Port 5176 is already in use!
    echo        Killing processes on port 5176...
    taskkill /IM node.exe /F >nul 2>&1
    timeout /t 2 /nobreak >nul
)

:: Kill any existing node/python processes
echo [CLEANUP] Killing stale processes...
taskkill /IM node.exe /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1
timeout /t 1 /nobreak >nul

:: Start Backend
echo.
echo [1/4] Starting Backend on port 8000...
if not exist "%ROOT%.venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at .venv\Scripts\activate.bat
    echo        Please create a virtual environment first!
    pause
    exit /b 1
)

start "Owlin Backend" cmd /k "cd /d %ROOT% && .venv\Scripts\activate.bat && set PYTHONPATH=%ROOT% && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for backend to start
echo [2/4] Waiting for backend to start...
set "BACKEND_READY=0"
for /l %%i in (1,1,30) do (
    timeout /t 1 /nobreak >nul
    curl -s http://localhost:8000/api/health >nul 2>&1
    if !errorlevel! == 0 (
        set "BACKEND_READY=1"
        echo [OK] Backend is ready!
        goto :backend_ready
    )
    echo        Waiting... (!time! seconds)
)
:backend_ready
if !BACKEND_READY! == 0 (
    echo [ERROR] Backend failed to start after 30 seconds
    echo        Please check the backend window for errors
    pause
    exit /b 1
)

:: Start Frontend
echo.
echo [3/4] Starting Frontend on port 5176...
cd /d "%ROOT%frontend_clean"

if not exist "package.json" (
    echo [ERROR] Frontend directory not found!
    echo        Expected: %ROOT%frontend_clean
    pause
    exit /b 1
)

:: Check if node_modules exists
if not exist "node_modules" (
    echo [WARN] node_modules not found. Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed!
        pause
        exit /b 1
    )
)

start "Owlin Frontend" cmd /k "cd /d %ROOT%frontend_clean && npm run dev"

:: Wait for frontend to start
echo [4/4] Waiting for frontend to start...
set "FRONTEND_READY=0"
for /l %%i in (1,1,30) do (
    timeout /t 1 /nobreak >nul
    curl -s http://localhost:5176 >nul 2>&1
    if !errorlevel! == 0 (
        set "FRONTEND_READY=1"
        echo [OK] Frontend is ready!
        goto :frontend_ready
    )
    echo        Waiting... (!time! seconds)
)
:frontend_ready

:: Final status
echo.
echo ========================================
echo    🎉 OWLIN IS READY!
echo ========================================
echo.
echo ✅ Backend:  http://localhost:8000
echo ✅ Frontend: http://localhost:5176/invoices?dev=1
echo.
echo Opening browser...
timeout /t 2 /nobreak >nul
start "" "http://localhost:5176/invoices?dev=1"

echo.
echo Two windows are open:
echo 1. Backend (port 8000) - Keep this running
echo 2. Frontend (port 5176) - Keep this running
echo.
echo If you see "Backend is offline" in the browser:
echo - Wait a few more seconds for backend to fully start
echo - Check the backend window for any errors
echo - Try refreshing the page
echo.
pause
