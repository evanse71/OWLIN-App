@echo off
echo ========================================
echo    Starting Owlin Development Servers
echo ========================================
echo.

REM Start Backend in new window
echo Starting Backend on port 8000...
start "Owlin Backend" cmd /k "cd /d %~dp0 && .venv311\Scripts\activate.bat && set OWLIN_ENV=dev && set FEATURE_OCR_PIPELINE_V2=true && set PYTHONPATH=%~dp0 && set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

REM Start Frontend in new window
echo Starting Frontend on port 5176...
start "Owlin Frontend" cmd /k "cd /d %~dp0\frontend_clean && npm run dev"

echo.
echo ========================================
echo    Servers are starting in new windows
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5176
echo.
echo Waiting 15 seconds for servers to start...
timeout /t 15 /nobreak >nul

echo.
echo Testing connections...
echo.

curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Backend is running on http://localhost:8000
) else (
    echo [WAIT] Backend still starting... check the backend window
)

curl -s http://localhost:5176 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Frontend is running on http://localhost:5176
) else (
    echo [WAIT] Frontend still starting... check the frontend window
)

echo.
echo ========================================
echo    Open http://localhost:5176 in your browser
echo ========================================
echo.
pause
