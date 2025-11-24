@echo off
setlocal
set "ROOT=%~dp0"

echo ========================================
echo    🦉 OWLIN Backend - Port 5177
echo ========================================

echo [1/4] Activating virtual environment...
call "%ROOT%.venv\Scripts\activate.bat"

echo [2/4] Setting environment variables...
set "OWLIN_ENV=dev"
set "FEATURE_OCR_PIPELINE_V2=true"
set "PYTHONPATH=%ROOT%"

echo [3/4] Ensuring directories exist...
if not exist "%ROOT%data" mkdir "%ROOT%data"
if not exist "%ROOT%data\uploads" mkdir "%ROOT%data\uploads"
if not exist "%ROOT%data\logs" mkdir "%ROOT%data\logs"

echo [4/4] Starting backend on port 5177...
cd /d "%ROOT%"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 5177 --reload

pause

