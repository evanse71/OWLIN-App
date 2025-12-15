@echo off
echo ========================================
echo    Quick Fix for Port 5176
echo ========================================
echo.

echo Step 1: Killing any existing processes...
taskkill /IM node.exe /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul
echo Done.
echo.

echo Step 2: Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js found
node --version
echo.

echo Step 3: Checking frontend directory...
if not exist "frontend_clean\package.json" (
    echo [ERROR] frontend_clean\package.json not found!
    pause
    exit /b 1
)
echo [OK] Frontend directory found
echo.

echo Step 4: Checking/Installing dependencies...
cd frontend_clean
if not exist "node_modules" (
    echo [WARN] node_modules not found. Installing...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed!
        cd ..
        pause
        exit /b 1
    )
) else (
    echo [OK] node_modules exists
)
cd ..
echo.

echo Step 5: Starting frontend on port 5176...
echo.
echo ========================================
echo    Frontend Starting...
echo ========================================
echo.
echo IMPORTANT: A new window will open with the frontend server.
echo Wait until you see: "Local: http://localhost:5176/"
echo Then open: http://localhost:5176/invoices?dev=1
echo.
echo If you see errors in the new window, please share them.
echo.
timeout /t 3 /nobreak >nul

cd frontend_clean
start "Owlin Frontend - Port 5176" cmd /k "npm run dev"
cd ..

echo.
echo Frontend window should be opening now...
echo Check the new window for any errors.
echo.
pause

