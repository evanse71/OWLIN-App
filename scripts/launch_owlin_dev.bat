@echo off
REM OWLIN - Desktop Launcher for Windows
REM Double-click this file to start the full Owlin development environment

echo.
echo ========================================
echo   OWLIN - Full Development Launcher
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "package.json" (
    echo ERROR: package.json not found!
    echo Please run this from the Owlin project root directory.
    pause
    exit /b 1
)

if not exist "backend\final_single_port.py" (
    echo ERROR: backend\final_single_port.py not found!
    echo Please run this from the Owlin project root directory.
    pause
    exit /b 1
)

echo Starting Owlin development environment...
echo.

REM Start Next.js in a new window
echo [1/2] Starting Next.js frontend...
start "Owlin Frontend" cmd /k "npm run dev"

REM Wait a moment for Next.js to start
timeout /t 5 /nobreak >nul

REM Start FastAPI backend in a new window
echo [2/2] Starting FastAPI backend with proxy...
start "Owlin Backend" cmd /k "set UI_MODE=PROXY_NEXT && set NEXT_BASE=http://127.0.0.1:3000 && set LLM_BASE=http://127.0.0.1:11434 && set OWLIN_PORT=8001 && python -m backend.final_single_port"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   SUCCESS! Owlin is starting up...
echo ========================================
echo.
echo Frontend: http://127.0.0.1:3000
echo Backend:  http://127.0.0.1:8001
echo.
echo Opening the app in your browser...
echo.

REM Open the app in the default browser
start http://127.0.0.1:8001

echo.
echo Both services are starting in separate windows.
echo Close those windows to stop the services.
echo.
echo Press any key to close this launcher...
pause >nul
