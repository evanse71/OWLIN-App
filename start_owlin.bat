@echo off
setlocal
set "ROOT=%~dp0"

echo ========================================
echo    🦉 O W L I N — Local Environment Launcher
echo ========================================

echo [1/6] Killing stale processes...
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM node.exe /F   >nul 2>&1

echo [2/6] Setting environment variables...
set "OWLIN_ENV=dev"
set "OWLIN_DB_PATH=%ROOT%data\owlin.db"
set "OWLIN_UPLOADS_DIR=%ROOT%data\uploads"
set "OWLIN_DEMO=0"
set "OWLIN_DEFAULT_VENUE=Royal Oak Hotel"
set "OWLIN_SINGLE_PORT=1"

echo [3/6] Ensuring directories exist...
if not exist "%ROOT%data" mkdir "%ROOT%data"
if not exist "%ROOT%data\uploads" mkdir "%ROOT%data\uploads"
if not exist "%ROOT%data\logs" mkdir "%ROOT%data\logs"
if not exist "%ROOT%data\meta" mkdir "%ROOT%data\meta"

echo [4/6] Building frontend...
pushd "%ROOT%source_extracted\tmp_lovable"
set "VITE_API_BASE_URL=http://127.0.0.1:8000"
set "VITE_OWLIN_DEMO=0"
set "VITE_OWLIN_EPHEMERAL=0"
call npm run build
if errorlevel 1 (
    echo ERROR: Frontend build failed!
    echo Make sure you have Node.js and npm installed.
    pause
    exit /b 1
)
popd

echo [5/6] Starting backend...
cd /d "%ROOT%source_extracted"
start "OWLIN Backend" cmd /k "echo Starting OWLIN Backend... && set OWLIN_ENV=%OWLIN_ENV% && set OWLIN_DB_PATH=%OWLIN_DB_PATH% && set OWLIN_UPLOADS_DIR=%OWLIN_UPLOADS_DIR% && set OWLIN_DEMO=%OWLIN_DEMO% && set OWLIN_DEFAULT_VENUE=%OWLIN_DEFAULT_VENUE% && set OWLIN_SINGLE_PORT=%OWLIN_SINGLE_PORT% && python test_backend_simple.py"

echo [6/6] Waiting for backend to start (15 seconds)...
timeout /t 15

echo.
echo Testing connection...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 5; if ($response.StatusCode -eq 200) { Write-Host 'SUCCESS: Backend is ready!' -ForegroundColor Green } else { Write-Host 'ERROR: Backend returned status' $response.StatusCode -ForegroundColor Red } } catch { Write-Host 'ERROR: Cannot connect to backend' -ForegroundColor Red; Write-Host 'Make sure the backend window is open and running' -ForegroundColor Yellow }"

echo.
echo Opening browser...
start "" "http://127.0.0.1:8000"

echo.
echo ========================================
echo    🟢 Owlin Local Environment Running
echo    Backend: http://127.0.0.1:8000
echo    Health:  http://127.0.0.1:8000/api/health
echo    Upload:  http://127.0.0.1:8000/api/upload
echo ========================================
echo.
echo Backend window should be open.
echo Browser should open to the main page.
echo.
echo To test file uploads:
echo 1. Go to the Invoices page
echo 2. Upload a PDF invoice or delivery note
echo 3. Check the backend window for OCR processing logs
echo.
pause
