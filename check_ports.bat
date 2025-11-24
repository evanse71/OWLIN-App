@echo off
echo ========================================
echo    Port Status Check
echo ========================================
echo.

echo Checking port 8000 (Backend)...
netstat -an | findstr ":8000" >nul
if %errorlevel% == 0 (
    echo [IN USE] Port 8000 is occupied
    netstat -ano | findstr ":8000" | findstr "LISTENING"
) else (
    echo [FREE] Port 8000 is available
)

echo.
echo Checking port 5176 (Frontend)...
netstat -an | findstr ":5176" >nul
if %errorlevel% == 0 (
    echo [IN USE] Port 5176 is occupied
    netstat -ano | findstr ":5176" | findstr "LISTENING"
) else (
    echo [FREE] Port 5176 is available
)

echo.
echo Testing backend connection...
curl -s http://localhost:8000/api/health >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Backend is responding on port 8000
    curl -s http://localhost:8000/api/health
    echo.
) else (
    echo [ERROR] Backend is not responding on port 8000
)

echo.
echo Testing frontend connection...
curl -s http://localhost:5176 >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Frontend is responding on port 5176
) else (
    echo [ERROR] Frontend is not responding on port 5176
)

echo.
pause

