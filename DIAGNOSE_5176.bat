@echo off
echo ========================================
echo    Port 5176 Connection Diagnostic
echo ========================================
echo.

echo [1] Checking if port 5176 is in use...
netstat -ano | findstr ":5176" | findstr "LISTENING"
if %errorlevel% == 0 (
    echo Port 5176 IS in use - this is GOOD if frontend is running
) else (
    echo Port 5176 is NOT in use - frontend is NOT running
)
echo.

echo [2] Checking for Node.js processes...
tasklist | findstr "node.exe"
if %errorlevel% == 0 (
    echo Node.js processes found
) else (
    echo No Node.js processes running
)
echo.

echo [3] Checking if Node.js is installed...
where node >nul 2>&1
if %errorlevel% == 0 (
    echo Node.js is installed
    node --version
) else (
    echo ERROR: Node.js is NOT installed or not in PATH
    echo Please install from: https://nodejs.org/
)
echo.

echo [4] Checking frontend directory...
cd /d "%~dp0frontend_clean"
if exist "package.json" (
    echo package.json found
) else (
    echo ERROR: package.json not found in frontend_clean
)
echo.

if exist "node_modules" (
    echo node_modules exists
) else (
    echo WARNING: node_modules not found - need to run npm install
)
echo.

echo [5] Testing if we can start the server...
echo.
echo ========================================
echo    Attempting to start frontend...
echo ========================================
echo.
echo If you see errors below, that's the problem!
echo.
echo Press Ctrl+C to stop after you see the result
echo.

npm run dev

pause

