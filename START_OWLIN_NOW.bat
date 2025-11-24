@echo off
echo.
echo ========================================
echo    OWLIN SYSTEM - QUICK START
echo ========================================
echo.
echo Starting backend on port 8000...
echo Frontend will be at: http://localhost:5176/invoices?dev=1
echo.

cd source_extracted
start "Owlin Backend" cmd /k "cd .. && .venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo.
echo Waiting for backend to start (10 seconds)...
timeout /t 10 /nobreak

echo.
echo Testing backend health...
curl http://localhost:8000/api/health
echo.

echo.
echo ========================================
echo    OWLIN IS READY!
echo ========================================
echo.
echo Backend: http://localhost:8000
echo Health: http://localhost:8000/api/health
echo Upload: http://localhost:8000/api/upload
echo.
echo Frontend (Vite): http://localhost:5176/invoices?dev=1
echo.
echo Backend window is open and running.
echo.
echo TO TEST:
echo 1. Go to http://localhost:5176/invoices?dev=1
echo 2. You should see "Backend: Healthy" (green checkmark)
echo 3. Upload a PDF invoice or delivery note
echo 4. Watch for card to appear with extracted data
echo.
pause

