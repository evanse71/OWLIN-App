@echo off
setlocal enabledelayedexpansion

:: ANSI color codes
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

echo %BLUE%=== OWLIN LAUNCHER ===%RESET%
echo.

:: Detect current directory as Owlin root
set "OWLIN_ROOT=%~dp0"
cd /d "%OWLIN_ROOT%"
echo %GREEN%[INFO]%RESET% Owlin root: %OWLIN_ROOT%

:: Set environment variables
echo %BLUE%[SETUP]%RESET% Setting environment variables...
set "OWLIN_ENV=dev"
set "OWLIN_DB_PATH=%OWLIN_ROOT%data\owlin.db"
set "OWLIN_UPLOADS_DIR=%OWLIN_ROOT%data\uploads"
set "OWLIN_DEMO=0"
set "OWLIN_DEFAULT_VENUE=Royal Oak Hotel"
set "OWLIN_SINGLE_PORT=1"

:: Ensure directories exist
echo %BLUE%[SETUP]%RESET% Ensuring directories exist...
if not exist "%OWLIN_ROOT%data" mkdir "%OWLIN_ROOT%data"
if not exist "%OWLIN_ROOT%data\uploads" mkdir "%OWLIN_ROOT%data\uploads"
if not exist "%OWLIN_ROOT%data\logs" mkdir "%OWLIN_ROOT%data\logs"
if not exist "%OWLIN_ROOT%data\meta" mkdir "%OWLIN_ROOT%data\meta"

:: Check if backend already running on port 8000
echo %BLUE%[CHECK]%RESET% Checking if backend is already running on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 "') do (
    set "BACKEND_PID=%%a"
    goto :backend_running
)

:: Backend not running, start it
echo %YELLOW%[START]%RESET% Starting Owlin backend...
cd /d "%OWLIN_ROOT%source_extracted"
start "Owlin Backend" cmd /k "set OWLIN_ENV=%OWLIN_ENV% && set OWLIN_DB_PATH=%OWLIN_DB_PATH% && set OWLIN_UPLOADS_DIR=%OWLIN_UPLOADS_DIR% && set OWLIN_DEMO=%OWLIN_DEMO% && set OWLIN_DEFAULT_VENUE=%OWLIN_DEFAULT_VENUE% && set OWLIN_SINGLE_PORT=%OWLIN_SINGLE_PORT% && python test_backend_simple.py"
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Failed to start backend server
    exit /b 1
)
cd /d "%OWLIN_ROOT%"

:: Wait for backend to be healthy (up to 20 seconds)
echo %BLUE%[WAIT]%RESET% Waiting for backend to be healthy...
set "HEALTH_CHECK_COUNT=0"
:health_check_loop
set /a HEALTH_CHECK_COUNT+=1
if %HEALTH_CHECK_COUNT% gtr 10 (
    echo %RED%[ERROR]%RESET% Backend health check failed after 20 seconds
    exit /b 1
)

:: Use PowerShell to check health endpoint
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2; if ($response.Content -match '\"status\":\s*\"ok\"') { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if errorlevel 0 (
    echo %GREEN%[OK]%RESET% Backend is healthy
    goto :start_frontend
)

echo %YELLOW%[WAIT]%RESET% Backend not ready yet, retrying in 2 seconds... (%HEALTH_CHECK_COUNT%/10)
timeout /t 2 /nobreak >nul
goto :health_check_loop

:backend_running
echo %GREEN%[OK]%RESET% Backend already running on port 8000 (PID: !BACKEND_PID!)

:start_frontend
:: Check if built frontend exists (single-port mode)
if exist "source_extracted\tmp_lovable\dist\index.html" (
    echo %GREEN%[DETECT]%RESET% Built frontend found - single-port mode
    set "FRONTEND_URL=http://127.0.0.1:8000"
    set "FRONTEND_TYPE=Single-Port (Built)"
) else if exist "source_extracted\tmp_lovable\package.json" (
    echo %YELLOW%[DETECT]%RESET% React source found but not built - building frontend...
    cd source_extracted\tmp_lovable
    call npm run build
    if errorlevel 1 (
        echo %RED%[ERROR]%RESET% Failed to build frontend
        cd /d "%OWLIN_ROOT%"
        exit /b 1
    )
    cd /d "%OWLIN_ROOT%"
    set "FRONTEND_URL=http://127.0.0.1:8000"
    set "FRONTEND_TYPE=Single-Port (Built)"
) else (
    echo %RED%[ERROR]%RESET% No frontend found in source_extracted/tmp_lovable/
    echo %YELLOW%[INFO]%RESET% Expected: source_extracted/tmp_lovable/package.json
    exit /b 1
)

:: Wait a moment for frontend to start
echo %BLUE%[WAIT]%RESET% Waiting for frontend to start...
timeout /t 3 /nobreak >nul

:: Open browser
echo %BLUE%[LAUNCH]%RESET% Opening browser to %FRONTEND_URL%...
start "" "%FRONTEND_URL%"
if errorlevel 1 (
    echo %YELLOW%[WARN]%RESET% Failed to open browser automatically
    echo %YELLOW%[INFO]%RESET% Please manually open: %FRONTEND_URL%
)

echo.
echo %GREEN%[SUCCESS]%RESET% Owlin launched successfully!
echo %GREEN%[INFO]%RESET% Backend: http://127.0.0.1:8000
echo %GREEN%[INFO]%RESET% Frontend (%FRONTEND_TYPE%): %FRONTEND_URL%
echo %GREEN%[INFO]%RESET% Health Check: http://127.0.0.1:8000/api/health
echo.
echo %BLUE%[NOTE]%RESET% Press Ctrl+C in the backend window to stop the server
echo %BLUE%[NOTE]%RESET% Or run 'stop_owlin.bat' to stop all servers
echo.

exit /b 0
