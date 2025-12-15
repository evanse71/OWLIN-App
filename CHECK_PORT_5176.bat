@echo off
echo ========================================
echo    Checking Port 5176 Status
echo ========================================
echo.

echo Checking if port 5176 is listening...
netstat -ano | findstr "5176"
echo.

echo Checking for Node.js processes...
tasklist | findstr "node.exe"
echo.

echo Checking if we can connect to localhost:5176...
curl -s http://localhost:5176 >nul 2>&1
if %errorlevel% == 0 (
    echo SUCCESS: Can connect to localhost:5176
) else (
    echo FAILED: Cannot connect to localhost:5176
)
echo.

pause

