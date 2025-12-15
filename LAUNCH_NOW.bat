@echo off
echo ========================================
echo    Starting OWLIN Servers
echo ========================================
echo.

cd /d "%~dp0"

REM Find Python virtual environment
if exist ".venv311\Scripts\python.exe" (
    set PYTHON=.venv311\Scripts\python.exe
    echo [OK] Found Python: .venv311
) else if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    echo [OK] Found Python: .venv
) else (
    echo [ERROR] Python virtual environment not found!
    echo Checked: .venv311\Scripts\python.exe
    echo Checked: .venv\Scripts\python.exe
    pause
    exit /b 1
)

REM Check Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found in PATH!
    pause
    exit /b 1
)
echo [OK] Found Node.js

REM Set environment variables
set OWLIN_ENV=dev
set FEATURE_OCR_PIPELINE_V2=true
set PYTHONPATH=%~dp0
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

REM Create directories
if not exist "data" mkdir "data"
if not exist "data\uploads" mkdir "data\uploads"
if not exist "data\logs" mkdir "data\logs"

echo.
echo Starting Backend on port 8000...
start "OWLIN Backend" cmd /k "cd /d %~dp0 && set OWLIN_ENV=dev && set FEATURE_OCR_PIPELINE_V2=true && set PYTHONPATH=%~dp0 && set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python && %PYTHON% -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo Starting Frontend on port 5176...
cd frontend_clean
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed!
        pause
        exit /b 1
    )
)
start "OWLIN Frontend" cmd /k "cd /d %~dp0frontend_clean && npm run dev"

cd ..

echo.
echo ========================================
echo    Servers are starting...
echo ========================================
echo.
echo Backend window: OWLIN Backend
echo Frontend window: OWLIN Frontend
echo.
echo Waiting 20 seconds for servers to start...
timeout /t 20 /nobreak

echo.
echo Testing connections...
echo.

curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [WARN] Backend not responding yet - check the Backend window
) else (
    echo [OK] Backend is running on http://localhost:8000
)

curl -s http://localhost:5176 >nul 2>&1
if errorlevel 1 (
    echo [WARN] Frontend not responding yet - check the Frontend window
) else (
    echo [OK] Frontend is running on http://localhost:5176
    start http://localhost:5176
)

echo.
echo ========================================
echo    Open your browser to:
echo    http://localhost:5176
echo ========================================
echo.
pause
