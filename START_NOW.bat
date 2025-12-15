@echo off
title Owlin Server Launcher
color 0A
echo.
echo ========================================
echo    OWLIN SERVER LAUNCHER
echo ========================================
echo.

cd /d %~dp0

echo Checking setup...
if not exist ".venv311\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found!
    echo Expected: .venv311\Scripts\python.exe
    pause
    exit /b 1
)

if not exist "frontend_clean\package.json" (
    echo [ERROR] Frontend directory not found!
    pause
    exit /b 1
)

echo [OK] Setup looks good
echo.

echo Starting Backend on port 8000...
start "=== OWLIN BACKEND (Port 8000) ===" cmd /k "cd /d %~dp0 && .venv311\Scripts\activate.bat && set OWLIN_ENV=dev && set FEATURE_OCR_PIPELINE_V2=true && set PYTHONPATH=%~dp0 && set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python && echo. && echo ======================================== && echo   BACKEND SERVER - Port 8000 && echo ======================================== && echo. && echo Starting server... && echo. && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo Starting Frontend on port 5176...
start "=== OWLIN FRONTEND (Port 5176) ===" cmd /k "cd /d %~dp0frontend_clean && echo. && echo ======================================== && echo   FRONTEND SERVER - Port 5176 && echo ======================================== && echo. && echo Starting server... && echo. && npm run dev"

echo.
echo ========================================
echo    SERVERS ARE STARTING
echo ========================================
echo.
echo Two windows have opened:
echo   1. Backend window (port 8000)
echo   2. Frontend window (port 5176)
echo.
echo Please check those windows for:
echo.
echo BACKEND should show:
echo   "Uvicorn running on http://127.0.0.1:8000"
echo   "Application startup complete"
echo.
echo FRONTEND should show:
echo   "Local: http://localhost:5176/"
echo.
echo Once you see those messages, open your browser to:
echo   http://localhost:5176
echo.
echo ========================================
echo.
echo This window will close in 30 seconds...
echo (Servers will keep running in their own windows)
timeout /t 30 /nobreak >nul
