@echo off
echo ========================================
echo    Starting Frontend - Capturing Output
echo ========================================
echo.

cd /d "%~dp0frontend_clean"

echo Current directory: %CD%
echo.

echo Running: npm run dev -- --port 5176
echo.
echo This will show all output including any errors.
echo.
echo ========================================
echo.

npm run dev -- --port 5176 2>&1 | tee frontend_output.log

echo.
echo ========================================
echo Output saved to frontend_output.log
echo ========================================
pause

