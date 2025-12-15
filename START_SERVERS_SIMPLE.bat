@echo off
echo ========================================
echo    Starting Owlin Servers
echo ========================================
echo.

cd /d %~dp0

echo [1/2] Starting Backend on port 8000...
start "Owlin Backend - Port 8000" cmd /k "cd /d %~dp0 && .venv311\Scripts\activate.bat && set OWLIN_ENV=dev && set FEATURE_OCR_PIPELINE_V2=true && set PYTHONPATH=%~dp0 && set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python && echo Starting backend... && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 5 /nobreak >nul

echo [2/2] Starting Frontend on port 5176...
cd frontend_clean
start "Owlin Frontend - Port 5176" cmd /k "cd /d %~dp0frontend_clean && echo Starting frontend... && npm run dev"

cd ..

echo.
echo ========================================
echo    Servers starting in separate windows
echo ========================================
echo.
echo Please check the two command windows that opened.
echo.
echo Backend should show:  "Uvicorn running on http://127.0.0.1:8000"
echo Frontend should show: "Local: http://localhost:5176/"
echo.
echo Once you see those messages, open:
echo   http://localhost:5176
echo.
echo Press any key to exit this window (servers will keep running)...
pause >nul
