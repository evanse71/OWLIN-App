@echo off
echo ========================================
echo    Frontend Startup Diagnostic
echo ========================================
echo.

echo [1] Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)
node --version
echo.

echo [2] Checking npm...
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm is not installed or not in PATH
    pause
    exit /b 1
)
npm --version
echo.

echo [3] Checking frontend directory...
cd /d "%~dp0frontend_clean"
if not exist "package.json" (
    echo ERROR: package.json not found in frontend_clean directory
    pause
    exit /b 1
)
echo OK: package.json found
echo.

echo [4] Checking node_modules...
if not exist "node_modules" (
    echo WARNING: node_modules not found
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo ERROR: npm install failed
        pause
        exit /b 1
    )
) else (
    echo OK: node_modules exists
)
echo.

echo [5] Checking if port 5176 is available...
netstat -an | findstr ":5176" | findstr "LISTENING" >nul
if %errorlevel% == 0 (
    echo WARNING: Port 5176 is already in use
    echo Killing processes on port 5176...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5176" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
) else (
    echo OK: Port 5176 is available
)
echo.

echo [6] Starting Vite dev server on port 5176...
echo.
echo ========================================
echo    Frontend Starting...
echo ========================================
echo.
echo Once you see "Local: http://localhost:5176/", 
echo open: http://localhost:5176/invoices?dev=1
echo.
echo Press Ctrl+C to stop the server
echo.

npm run dev

pause

