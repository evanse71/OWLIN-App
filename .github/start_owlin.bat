@echo off
setlocal enabledelayedexpansion

:: ANSI color codes
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "RESET=[0m"

echo %CYAN%========================================%RESET%
echo %CYAN%    🦉 O W L I N — Smart Launcher%RESET%
echo %CYAN%========================================%RESET%
echo.

:: Detect current directory as Owlin root
set "OWLIN_ROOT=%~dp0"
cd /d "%OWLIN_ROOT%"

:: Check for existing processes
echo %BLUE%[CHECK]%RESET% Checking for running Owlin processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 "') do (
    set "BACKEND_PID=%%a"
    goto :backend_exists
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173 "') do (
    set "FRONTEND_PID=%%a"
    goto :frontend_exists
)
goto :no_processes

:backend_exists
echo %YELLOW%[WARN]%RESET% Backend already running on port 8000 (PID: !BACKEND_PID!)
set "BACKEND_RUNNING=1"
goto :check_frontend

:frontend_exists
echo %YELLOW%[WARN]%RESET% Frontend already running on port 5173 (PID: !FRONTEND_PID!)
set "FRONTEND_RUNNING=1"

:check_frontend
if defined FRONTEND_RUNNING goto :show_menu
goto :show_menu

:no_processes
echo %GREEN%[OK]%RESET% No Owlin processes detected

:show_menu
echo.
echo %CYAN%Choose launch mode:%RESET%
echo %GREEN%[1]%RESET% Single Port (Recommended) - Backend serves frontend on port 8000
echo %GREEN%[2]%RESET% Split Mode - Backend (8000) + Frontend (5173) on separate ports  
echo %GREEN%[3]%RESET% Backend Only - Just the API server
echo %GREEN%[4]%RESET% Frontend Only - Just the dev server (needs backend running)
echo %GREEN%[5]%RESET% Stop All - Kill all Owlin processes
echo %GREEN%[6]%RESET% Exit
echo.
set /p "choice=Enter your choice (1-6): "

if "%choice%"=="1" goto :single_port
if "%choice%"=="2" goto :split_mode
if "%choice%"=="3" goto :backend_only
if "%choice%"=="4" goto :frontend_only
if "%choice%"=="5" goto :stop_all
if "%choice%"=="6" goto :exit
echo %RED%[ERROR]%RESET% Invalid choice. Please enter 1-6.
goto :show_menu

:single_port
echo.
echo %BLUE%[MODE]%RESET% Starting Owlin in Single Port Mode...
echo %BLUE%[INFO]%RESET% Backend will serve both API and frontend on port 8000
echo.

:: Kill existing processes
echo %BLUE%[CLEANUP]%RESET% Stopping any existing processes...
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1

:: Set environment variables
echo %BLUE%[CONFIG]%RESET% Setting up environment...
set "OWLIN_ENV=dev"
set "OWLIN_DB_PATH=%OWLIN_ROOT%data\owlin.db"
set "OWLIN_UPLOADS_DIR=%OWLIN_ROOT%data\uploads"
set "OWLIN_DEMO=0"
set "OWLIN_DEFAULT_VENUE=Royal Oak Hotel"
set "OWLIN_SINGLE_PORT=1"

:: Ensure directories exist
if not exist "%OWLIN_ROOT%data" mkdir "%OWLIN_ROOT%data"
if not exist "%OWLIN_ROOT%data\uploads" mkdir "%OWLIN_ROOT%data\uploads"
if not exist "%OWLIN_ROOT%data\logs" mkdir "%OWLIN_ROOT%data\logs"
if not exist "%OWLIN_ROOT%data\meta" mkdir "%OWLIN_ROOT%data\meta"

:: Build frontend
echo %BLUE%[BUILD]%RESET% Building frontend with single-port configuration...
cd /d "%OWLIN_ROOT%..\source_extracted\tmp_lovable"
if not exist "package.json" (
    echo %RED%[ERROR]%RESET% Frontend directory not found!
    echo %RED%[ERROR]%RESET% Expected: %OWLIN_ROOT%..\source_extracted\tmp_lovable\package.json
    pause
    exit /b 1
)
set "VITE_API_BASE_URL=http://127.0.0.1:8000"
set "VITE_OWLIN_DEMO=0"
set "VITE_OWLIN_EPHEMERAL=0"
call npm run build >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Frontend build failed!
    echo %YELLOW%[INFO]%RESET% Make sure you have Node.js and npm installed.
    echo %YELLOW%[INFO]%RESET% Try running: npm install
    pause
    exit /b 1
)
cd /d "%OWLIN_ROOT%"

:: Start backend
echo %BLUE%[START]%RESET% Starting backend server...
cd /d "%OWLIN_ROOT%..\source_extracted"
start "Owlin Backend" cmd /k "echo Starting OWLIN Backend (Single Port Mode)... && set OWLIN_ENV=%OWLIN_ENV% && set OWLIN_DB_PATH=%OWLIN_DB_PATH% && set OWLIN_UPLOADS_DIR=%OWLIN_UPLOADS_DIR% && set OWLIN_DEMO=%OWLIN_DEMO% && set OWLIN_DEFAULT_VENUE=%OWLIN_DEFAULT_VENUE% && set OWLIN_SINGLE_PORT=%OWLIN_SINGLE_PORT% && python test_backend_simple.py"

:: Wait for backend to be healthy
echo %BLUE%[WAIT]%RESET% Waiting for backend to be healthy...
set "HEALTH_CHECK_COUNT=0"
:health_check_loop
set /a HEALTH_CHECK_COUNT+=1
if %HEALTH_CHECK_COUNT% gtr 15 (
    echo %RED%[ERROR]%RESET% Backend health check failed after 30 seconds
    echo %YELLOW%[INFO]%RESET% Check the backend window for errors
    pause
    exit /b 1
)

curl -s http://127.0.0.1:8000/api/health | findstr "\"status\":\"ok\"" >nul 2>&1
if errorlevel 0 (
    echo %GREEN%[OK]%RESET% Backend is healthy
    goto :open_browser
)

echo %YELLOW%[WAIT]%RESET% Backend not ready yet, retrying in 2 seconds... (%HEALTH_CHECK_COUNT%/15)
timeout /t 2 /nobreak >nul
goto :health_check_loop

:open_browser
echo %BLUE%[LAUNCH]%RESET% Opening browser to http://127.0.0.1:8000...
start "" "http://127.0.0.1:8000"

echo.
echo %GREEN%[SUCCESS]%RESET% Owlin launched successfully in single-port mode!
echo %GREEN%[INFO]%RESET% Backend + Frontend: http://127.0.0.1:8000
echo %GREEN%[INFO]%RESET% Health Check: http://127.0.0.1:8000/api/health
echo %GREEN%[INFO]%RESET% API Docs: http://127.0.0.1:8000/docs
echo.
echo %BLUE%[NOTE]%RESET% Press Ctrl+C in the backend window to stop the server
echo %BLUE%[NOTE]%RESET% Or run this script again and choose option 5 to stop all
goto :end

:split_mode
echo.
echo %BLUE%[MODE]%RESET% Starting Owlin in Split Mode...
echo %BLUE%[INFO]%RESET% Backend on port 8000, Frontend on port 5173
echo.

:: Kill existing processes
echo %BLUE%[CLEANUP]%RESET% Stopping any existing processes...
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1

:: Set environment variables
echo %BLUE%[CONFIG]%RESET% Setting up environment...
set "OWLIN_ENV=dev"
set "OWLIN_DB_PATH=%OWLIN_ROOT%data\owlin.db"
set "OWLIN_UPLOADS_DIR=%OWLIN_ROOT%data\uploads"
set "OWLIN_DEMO=0"
set "OWLIN_DEFAULT_VENUE=Royal Oak Hotel"
set "OWLIN_SINGLE_PORT=0"

:: Ensure directories exist
if not exist "%OWLIN_ROOT%data" mkdir "%OWLIN_ROOT%data"
if not exist "%OWLIN_ROOT%data\uploads" mkdir "%OWLIN_ROOT%data\uploads"
if not exist "%OWLIN_ROOT%data\logs" mkdir "%OWLIN_ROOT%data\logs"
if not exist "%OWLIN_ROOT%data\meta" mkdir "%OWLIN_ROOT%data\meta"

:: Start backend
echo %BLUE%[START]%RESET% Starting backend server (port 8000)...
cd /d "%OWLIN_ROOT%..\source_extracted"
start "Owlin Backend" cmd /k "echo Starting OWLIN Backend on port 8000... && set OWLIN_ENV=%OWLIN_ENV% && set OWLIN_DB_PATH=%OWLIN_DB_PATH% && set OWLIN_UPLOADS_DIR=%OWLIN_UPLOADS_DIR% && set OWLIN_DEMO=%OWLIN_DEMO% && set OWLIN_DEFAULT_VENUE=%OWLIN_DEFAULT_VENUE% && set OWLIN_SINGLE_PORT=%OWLIN_SINGLE_PORT% && python test_backend_simple.py"

:: Start frontend
echo %BLUE%[START]%RESET% Starting frontend server (port 5173)...
cd /d "%OWLIN_ROOT%..\source_extracted\tmp_lovable"
set "VITE_API_BASE_URL=http://127.0.0.1:8000"
set "VITE_OWLIN_DEMO=0"
set "VITE_OWLIN_EPHEMERAL=0"
start "Owlin Frontend" cmd /k "echo Starting OWLIN Frontend on port 5173... && npm run dev"

:: Wait for services
echo %BLUE%[WAIT]%RESET% Waiting for services to start (20 seconds)...
timeout /t 20 /nobreak >nul

:: Test connections
echo %BLUE%[TEST]%RESET% Testing connections...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 5; if ($response.StatusCode -eq 200) { Write-Host 'SUCCESS: Backend is ready!' -ForegroundColor Green } else { Write-Host 'ERROR: Backend returned status' $response.StatusCode -ForegroundColor Red } } catch { Write-Host 'ERROR: Cannot connect to backend' -ForegroundColor Red }"

powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:5173' -TimeoutSec 5; if ($response.StatusCode -eq 200) { Write-Host 'SUCCESS: Frontend is ready!' -ForegroundColor Green } else { Write-Host 'ERROR: Frontend returned status' $response.StatusCode -ForegroundColor Red } } catch { Write-Host 'ERROR: Cannot connect to frontend' -ForegroundColor Red }"

echo %BLUE%[LAUNCH]%RESET% Opening browser to http://127.0.0.1:5173...
start "" "http://127.0.0.1:5173"

echo.
echo %GREEN%[SUCCESS]%RESET% Owlin launched successfully in split mode!
echo %GREEN%[INFO]%RESET% Backend: http://127.0.0.1:8000
echo %GREEN%[INFO]%RESET% Frontend: http://127.0.0.1:5173
echo %GREEN%[INFO]%RESET% Health Check: http://127.0.0.1:8000/api/health
echo.
echo %BLUE%[NOTE]%RESET% Two windows should be open: Backend and Frontend
echo %BLUE%[NOTE]%RESET% Use this script again and choose option 5 to stop all
goto :end

:backend_only
echo.
echo %BLUE%[MODE]%RESET% Starting Backend Only...
echo.

:: Kill existing processes
echo %BLUE%[CLEANUP]%RESET% Stopping any existing processes...
taskkill /IM python.exe /F >nul 2>&1

:: Set environment variables
echo %BLUE%[CONFIG]%RESET% Setting up environment...
set "OWLIN_ENV=dev"
set "OWLIN_DB_PATH=%OWLIN_ROOT%data\owlin.db"
set "OWLIN_UPLOADS_DIR=%OWLIN_ROOT%data\uploads"
set "OWLIN_DEMO=0"
set "OWLIN_DEFAULT_VENUE=Royal Oak Hotel"
set "OWLIN_SINGLE_PORT=0"

:: Ensure directories exist
if not exist "%OWLIN_ROOT%data" mkdir "%OWLIN_ROOT%data"
if not exist "%OWLIN_ROOT%data\uploads" mkdir "%OWLIN_ROOT%data\uploads"
if not exist "%OWLIN_ROOT%data\logs" mkdir "%OWLIN_ROOT%data\logs"
if not exist "%OWLIN_ROOT%data\meta" mkdir "%OWLIN_ROOT%data\meta"

:: Start backend
echo %BLUE%[START]%RESET% Starting backend server...
cd /d "%OWLIN_ROOT%..\source_extracted"
echo Starting OWLIN Backend on port 8000...
echo Environment: %OWLIN_ENV%
echo Database: %OWLIN_DB_PATH%
echo Uploads: %OWLIN_UPLOADS_DIR%
echo.
echo Backend will be available at:
echo - http://127.0.0.1:8000
echo - http://127.0.0.1:8000/api/health
echo - http://127.0.0.1:8000/api/upload
echo.
python test_backend_simple.py
goto :end

:frontend_only
echo.
echo %BLUE%[MODE]%RESET% Starting Frontend Only...
echo %YELLOW%[WARN]%RESET% Make sure the backend is running on port 8000!
echo.

:: Kill existing frontend processes
echo %BLUE%[CLEANUP]%RESET% Stopping any existing frontend processes...
taskkill /IM node.exe /F >nul 2>&1

:: Start frontend
echo %BLUE%[START]%RESET% Starting frontend server...
cd /d "%OWLIN_ROOT%..\source_extracted\tmp_lovable"
set "VITE_API_BASE_URL=http://127.0.0.1:8000"
set "VITE_OWLIN_DEMO=0"
set "VITE_OWLIN_EPHEMERAL=0"

echo Starting OWLIN Frontend on port 5173...
echo API Base URL: %VITE_API_BASE_URL%
echo.
echo Frontend will be available at:
echo - http://127.0.0.1:5173
echo.
echo Make sure the backend is running on port 8000!
echo.
npm run dev
goto :end

:stop_all
echo.
echo %BLUE%[STOP]%RESET% Stopping all Owlin processes...
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1
echo %GREEN%[SUCCESS]%RESET% All Owlin processes stopped
goto :end

:exit
echo %BLUE%[EXIT]%RESET% Goodbye!
goto :end

:end
echo.
pause
exit /b 0