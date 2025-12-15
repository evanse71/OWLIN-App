@echo off
setlocal enabledelayedexpansion

:: ANSI color codes
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

echo %BLUE%=== OWLIN LAUNCHER (SINGLE-PORT MODE) ===%RESET%
echo.

:: Detect current directory as Owlin root
set "OWLIN_ROOT=%~dp0"
cd /d "%OWLIN_ROOT%"
echo %GREEN%[INFO]%RESET% Owlin root: %OWLIN_ROOT%

:: Check if backend already running on port 8000
echo %BLUE%[CHECK]%RESET% Checking if backend is already running on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 "') do (
    set "BACKEND_PID=%%a"
    goto :backend_running
)

:: Ensure frontend is built with correct API configuration
echo %BLUE%[BUILD]%RESET% Ensuring frontend is built with correct API configuration...
cd /d "%OWLIN_ROOT%source_extracted\tmp_lovable"
set VITE_API_BASE_URL=http://127.0.0.1:8000
call npm run build >nul 2>&1
cd /d "%OWLIN_ROOT%"

:: Backend not running, start it
echo %YELLOW%[START]%RESET% Starting Owlin backend in single-port mode...
cd /d "%OWLIN_ROOT%source_extracted"
start "Owlin Backend" cmd /k "set OWLIN_SINGLE_PORT=1 && python -m uvicorn test_backend_simple:app --host 127.0.0.1 --port 8000 --reload"
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

:: Use curl to check health endpoint
curl -s http://127.0.0.1:8000/api/health | findstr "\"status\":\"ok\"" >nul 2>&1
if errorlevel 0 (
    echo %GREEN%[OK]%RESET% Backend is healthy
    goto :wait_for_frontend
)

echo %YELLOW%[WAIT]%RESET% Backend not ready yet, retrying in 2 seconds... (%HEALTH_CHECK_COUNT%/10)
timeout /t 2 /nobreak >nul
goto :health_check_loop

:backend_running
echo %GREEN%[OK]%RESET% Backend already running on port 8000 (PID: !BACKEND_PID!)

:wait_for_frontend
:: Wait for frontend to be served by backend
echo %BLUE%[WAIT]%RESET% Waiting for frontend to be ready...
set "FRONTEND_CHECK_COUNT=0"
:frontend_check_loop
set /a FRONTEND_CHECK_COUNT+=1
if %FRONTEND_CHECK_COUNT% gtr 10 (
    echo %YELLOW%[WARN]%RESET% Frontend may not be ready yet, but opening browser anyway...
    goto :open_browser
)

:: Check if frontend is responding
curl -s http://127.0.0.1:8000/ | findstr "<html" >nul 2>&1
if errorlevel 0 (
    echo %GREEN%[OK]%RESET% Frontend is ready
    goto :open_browser
)

echo %YELLOW%[WAIT]%RESET% Frontend not ready yet, retrying in 2 seconds... (%FRONTEND_CHECK_COUNT%/10)
timeout /t 2 /nobreak >nul
goto :frontend_check_loop

:open_browser
:: Open browser
echo %BLUE%[LAUNCH]%RESET% Opening browser to http://127.0.0.1:8000...
start "" "http://127.0.0.1:8000"
if errorlevel 1 (
    echo %YELLOW%[WARN]%RESET% Failed to open browser automatically
    echo %YELLOW%[INFO]%RESET% Please manually open: http://127.0.0.1:8000
)

echo.
echo %GREEN%[SUCCESS]%RESET% Owlin launched successfully in single-port mode!
echo %GREEN%[INFO]%RESET% Backend + Frontend: http://127.0.0.1:8000
echo %GREEN%[INFO]%RESET% Health Check: http://127.0.0.1:8000/api/health
echo %GREEN%[INFO]%RESET% API Docs: http://127.0.0.1:8000/docs
echo.
echo %BLUE%[NOTE]%RESET% Press Ctrl+C in the backend window to stop the server
echo %BLUE%[NOTE]%RESET% Or run 'stop_owlin.bat' to stop all servers
echo.

exit /b 0