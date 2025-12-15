# Manual Start Instructions

If the automated scripts aren't working, follow these steps manually:

## Step 1: Start Backend (Terminal 1)

Open a **Command Prompt** or **PowerShell** window and run:

```batch
cd c:\Users\tedev\FixPack_2025-11-02_133105
.venv311\Scripts\activate.bat
set OWLIN_ENV=dev
set FEATURE_OCR_PIPELINE_V2=true
set PYTHONPATH=%CD%
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**Wait for this message:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

**Keep this window open!**

## Step 2: Start Frontend (Terminal 2)

Open a **NEW Command Prompt** or **PowerShell** window and run:

```batch
cd c:\Users\tedev\FixPack_2025-11-02_133105\frontend_clean
npm run dev
```

**Wait for this message:**
```
  VITE v7.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5176/
```

**Keep this window open!**

## Step 3: Open Browser

Once both servers are running, open your browser to:
**http://localhost:5176**

## Troubleshooting

### Backend won't start?

1. Check if Python is available:
   ```batch
   .venv311\Scripts\python.exe --version
   ```

2. Check if uvicorn is installed:
   ```batch
   .venv311\Scripts\pip.exe list | findstr uvicorn
   ```

3. Look for error messages in the backend window

### Frontend won't start?

1. Check if Node.js is installed:
   ```batch
   node --version
   ```

2. Install dependencies if needed:
   ```batch
   cd frontend_clean
   npm install
   ```

3. Look for error messages in the frontend window

### Port already in use?

Kill the process using the port:
```batch
REM Find the process
netstat -ano | findstr :8000
netstat -ano | findstr :5176

REM Kill it (replace <PID> with the number from above)
taskkill /PID <PID> /F
```

## Quick Test

Once both are running, test them:
- Backend: http://localhost:8000/health
- Frontend: http://localhost:5176

Both should respond without errors.
