@echo off
cd /d "%~dp0"
echo ========================================
echo    Starting Backend (Fixed)
echo ========================================
echo.

REM Find Python
if exist ".venv311\Scripts\python.exe" (
    set PYTHON=.venv311\Scripts\python.exe
) else if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    echo ERROR: Python virtual environment not found!
    pause
    exit /b 1
)

REM Set environment
set OWLIN_ENV=dev
set FEATURE_OCR_PIPELINE_V2=true
set PYTHONPATH=%~dp0
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

REM Create directories
if not exist "data" mkdir "data"
if not exist "data\uploads" mkdir "data\uploads"
if not exist "data\logs" mkdir "data\logs"

echo Using: %PYTHON%
echo Starting backend on port 8000...
echo.
echo NOTE: If startup hangs, check the window for error messages
echo       or try: python test_backend_startup.py
echo.

REM Start without reload first to avoid reloader issues
"%PYTHON%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info

pause
