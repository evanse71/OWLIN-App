# Backend Status and Startup Instructions

## Current Status

The backend server needs to be running on **port 8000** for the frontend to work properly.

## Quick Start

### Option 1: Use the Batch File (Easiest)
1. Double-click `START_BACKEND.bat` in the project root
2. A command window will open showing the backend starting
3. Wait for "Application startup complete" message
4. The backend will be available at http://localhost:8000

### Option 2: Manual Start
Open a command prompt in the project directory and run:

```batch
.venv311\Scripts\activate
set OWLIN_ENV=dev
set FEATURE_OCR_PIPELINE_V2=true
set PYTHONPATH=%CD%
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Option 3: PowerShell Script
Run:
```powershell
.\start_backend_now.ps1
```

## Verify Backend is Running

Run this command to check:
```bash
python check_backend.py
```

Or test manually:
```bash
curl http://127.0.0.1:8000/api/routes/status
```

## Expected Endpoints

Once running, these endpoints should be accessible:
- `http://localhost:8000/api/routes/status` - Route status
- `http://localhost:8000/api/chat/status` - Chat service status
- `http://localhost:8000/api/invoices?dev=1` - List invoices
- `http://localhost:8000/api/upload` - Upload documents
- `http://localhost:8000/docs` - API documentation

## Troubleshooting

### Port 8000 Already in Use
If you get an error that port 8000 is in use:
1. Find the process: `netstat -ano | findstr :8000`
2. Kill it: `taskkill /PID <process_id> /F`
3. Start the backend again

### Backend Won't Start
1. Check that the virtual environment exists: `.venv311\Scripts\python.exe`
2. Verify Python dependencies are installed
3. Check the error messages in the command window
4. Look for import errors or missing modules

### Frontend Still Can't Connect
1. Verify backend is running: `python check_backend.py`
2. Check that frontend proxy is configured correctly in `vite.config.ts`
3. Make sure frontend is running on port 5176
4. Check browser console for specific error messages

## Next Steps

Once the backend is running:
1. ✅ Backend should be accessible at http://localhost:8000
2. ✅ Frontend should connect automatically via proxy
3. ✅ You can upload documents via the web interface
4. ✅ Chat assistant should work (if Ollama is running)
