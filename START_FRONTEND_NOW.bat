@echo off
echo ========================================
echo    Starting Frontend on Port 5176
echo ========================================
echo.

cd /d "%~dp0frontend_clean"

echo Current directory: %CD%
echo.

echo Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Node.js is not installed or not in PATH!
    echo.
    echo Please install Node.js from: https://nodejs.org/
    echo.
    pause
    exit /b 1
)

node --version
npm --version
echo.

echo Checking package.json...
if not exist "package.json" (
    echo ERROR: package.json not found!
    echo Current directory: %CD%
    pause
    exit /b 1
)
echo OK: package.json found
echo.

echo Checking node_modules...
if not exist "node_modules" (
    echo WARNING: node_modules not found
    echo Installing dependencies (this may take a minute)...
    echo.
    call npm install
    if errorlevel 1 (
        echo.
        echo ERROR: npm install failed!
        echo Please check the error messages above.
        pause
        exit /b 1
    )
    echo.
    echo Dependencies installed successfully!
) else (
    echo OK: node_modules exists
)
echo.

echo Checking if port 5176 is in use...
netstat -ano | findstr ":5176" | findstr "LISTENING" >nul
if %errorlevel% == 0 (
    echo WARNING: Port 5176 is already in use!
    echo Killing processes on port 5176...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5176" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
    echo Done.
) else (
    echo OK: Port 5176 is available
)
echo.

echo ========================================
echo    Starting Vite Dev Server
echo ========================================
echo.
echo The server will start in this window.
echo Wait for: "Local: http://localhost:5176/"
echo.
echo Then open your browser to:
echo   http://localhost:5176/invoices?dev=1
echo.
echo Press Ctrl+C to stop the server
echo.
echo ========================================
echo.

npm run dev

pause

