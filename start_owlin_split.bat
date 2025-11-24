@echo off
setlocal
set "ROOT=%~dp0"

echo ========================================
echo    🦉 O W L I N — Split Mode Launcher
echo    (Backend + Frontend on separate ports)
echo ========================================

echo [1/5] Killing stale processes...
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM node.exe /F   >nul 2>&1

echo [2/5] Setting environment variables...
set "OWLIN_ENV=dev"
set "OWLIN_DB_PATH=%ROOT%data\owlin.db"
set "OWLIN_UPLOADS_DIR=%ROOT%data\uploads"
set "OWLIN_DEMO=0"
set "OWLIN_DEFAULT_VENUE=Royal Oak Hotel"
set "OWLIN_SINGLE_PORT=0"

echo [3/5] Ensuring directories exist...
if not exist "%ROOT%data" mkdir "%ROOT%data"
if not exist "%ROOT%data\uploads" mkdir "%ROOT%data\uploads"
if not exist "%ROOT%data\logs" mkdir "%ROOT%data\logs"
if not exist "%ROOT%data\meta" mkdir "%ROOT%data\meta"

echo [4/5] Starting backend (port 8000)...
cd /d "%ROOT%source_extracted"
start "OWLIN Backend" cmd /k "echo Starting OWLIN Backend on port 8000... && set OWLIN_ENV=%OWLIN_ENV% && set OWLIN_DB_PATH=%OWLIN_DB_PATH% && set OWLIN_UPLOADS_DIR=%OWLIN_UPLOADS_DIR% && set OWLIN_DEMO=%OWLIN_DEMO% && set OWLIN_DEFAULT_VENUE=%OWLIN_DEFAULT_VENUE% && set OWLIN_SINGLE_PORT=%OWLIN_SINGLE_PORT% && python test_backend_simple.py"

echo [5/5] Starting frontend (port 5173)...
cd /d "%ROOT%source_extracted\tmp_lovable"
set "VITE_API_BASE_URL=http://127.0.0.1:8000"
set "VITE_OWLIN_DEMO=0"
set "VITE_OWLIN_EPHEMERAL=0"
start "OWLIN Frontend" cmd /k "echo Starting OWLIN Frontend on port 5173... && npm run dev"

echo.
echo Waiting for services to start (20 seconds)...
timeout /t 20

echo.
echo Testing connections...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 5; if ($response.StatusCode -eq 200) { Write-Host 'SUCCESS: Backend is ready!' -ForegroundColor Green } else { Write-Host 'ERROR: Backend returned status' $response.StatusCode -ForegroundColor Red } } catch { Write-Host 'ERROR: Cannot connect to backend' -ForegroundColor Red }"

powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:5173' -TimeoutSec 5; if ($response.StatusCode -eq 200) { Write-Host 'SUCCESS: Frontend is ready!' -ForegroundColor Green } else { Write-Host 'ERROR: Frontend returned status' $response.StatusCode -ForegroundColor Red } } catch { Write-Host 'ERROR: Cannot connect to frontend' -ForegroundColor Red }"

echo.
echo Opening browser...
start "" "http://127.0.0.1:5173"

echo.
echo ========================================
echo    🟢 Owlin Split Mode Running
echo    Backend:  http://127.0.0.1:8000
echo    Frontend: http://127.0.0.1:5173
echo    Health:   http://127.0.0.1:8000/api/health
echo ========================================
echo.
echo Two windows should be open:
echo - Backend window (FastAPI on port 8000)
echo - Frontend window (Vite dev server on port 5173)
echo.
echo Browser should open to the frontend.
echo.
echo To test file uploads:
echo 1. Use the frontend at http://127.0.0.1:5173
echo 2. Upload a PDF invoice or delivery note
echo 3. Check the backend window for OCR processing logs
echo.
pause
