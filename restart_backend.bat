@echo off
echo.
echo ========================================
echo   Restarting Backend Server
echo ========================================
echo.

REM Kill any existing Python processes (optional - be careful!)
REM taskkill /F /IM python.exe /T 2>nul

echo Starting backend on port 8000...
echo.
python -m uvicorn backend.main:app --port 8000 --reload

pause

