@echo off
cd /d "%~dp0"
echo Starting Backend on Port 8000...
echo.

if exist ".venv311\Scripts\python.exe" (
    set PYTHON=.venv311\Scripts\python.exe
) else if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    echo ERROR: Python virtual environment not found!
    pause
    exit /b 1
)

set OWLIN_ENV=dev
set FEATURE_OCR_PIPELINE_V2=true
set PYTHONPATH=%~dp0
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

if not exist "data" mkdir "data"
if not exist "data\uploads" mkdir "data\uploads"
if not exist "data\logs" mkdir "data\logs"

echo Using Python: %PYTHON%
echo Starting uvicorn...
echo.

"%PYTHON%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

pause
