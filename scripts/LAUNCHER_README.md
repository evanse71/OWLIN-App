# OWLIN - PowerShell Launchers

This directory contains PowerShell scripts to launch Owlin in different modes.

## Scripts

### `start_full_dev.ps1` - Full Development Mode
**One-click launcher for complete Owlin development environment.**

```powershell
.\scripts\start_full_dev.ps1
```

**What it does:**
1. Verifies repository structure (`package.json` and `backend/final_single_port.py`)
2. Cleans up any stale processes on ports 3000 and 8001
3. Starts Next.js dev server in background job
4. Waits for Next.js to be responsive (up to 30 retries)
5. Starts FastAPI backend with PROXY_NEXT mode
6. Keeps FastAPI logs in foreground
7. Provides cleanup on Ctrl+C

**Environment Variables Set:**
- `UI_MODE=PROXY_NEXT`
- `NEXT_BASE=http://127.0.0.1:3000`
- `LLM_BASE=http://127.0.0.1:11434`
- `OWLIN_PORT=8001`

**Result:** Everything unified on `http://127.0.0.1:8001`

### `start_and_verify.ps1` - Single-Port Mode
**Launcher for static frontend mode (production-like).**

```powershell
.\scripts\start_and_verify.ps1
```

**What it does:**
1. Tests Python module imports
2. Launches FastAPI backend in static mode
3. Verifies health endpoints
4. Opens browser automatically

### `test_launcher.ps1` - Test Mode
**Demonstrates launcher functionality without requiring Node.js.**

```powershell
.\scripts\test_launcher.ps1
```

## Prerequisites

### For Full Development Mode
- **Node.js 18+** with npm
- **Python 3.8+** with required packages
- **PowerShell 5.1+** or PowerShell Core

### Installation Commands
```powershell
# Install Node.js (choose one)
winget install OpenJS.NodeJS
# OR
choco install nodejs

# Install Python (choose one)  
winget install Python.Python.3
# OR
choco install python

# Install Python packages
pip install -r requirements.txt
```

## Usage Examples

### Quick Start (Full Dev)
```powershell
# Navigate to repo root
cd C:\path\to\OWLIN-App-main

# Start everything
.\scripts\start_full_dev.ps1

# Open browser to http://127.0.0.1:8001
```

### Force Restart
```powershell
# Kill any existing processes and restart
.\scripts\start_full_dev.ps1 -Force
```

### Custom Retry Settings
```powershell
# Wait longer for Next.js to start
.\scripts\start_full_dev.ps1 -MaxRetries 60 -RetryDelay 3
```

## Troubleshooting

### Port Already in Use
```powershell
# The script automatically cleans up ports, but you can force it:
.\scripts\start_full_dev.ps1 -Force

# Or manually kill processes:
netstat -ano | findstr :3000
netstat -ano | findstr :8001
taskkill /F /PID <PID>
```

### Next.js Not Starting
```powershell
# Check if Node.js is installed
node --version
npm --version

# Install dependencies
npm install

# Check for errors
npm run dev
```

### Python Backend Issues
```powershell
# Check Python installation
python --version

# Install requirements
pip install -r requirements.txt

# Test backend directly
python -m backend.final_single_port
```

### Script Execution Policy
```powershell
# If you get execution policy errors:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or run with bypass:
PowerShell -ExecutionPolicy Bypass -File .\scripts\start_full_dev.ps1
```

## Architecture

```
start_full_dev.ps1
├── Next.js Dev Server (Background Job)
│   └── Port 3000
├── FastAPI Backend (Foreground)
│   ├── /api/* → Local API
│   ├── /llm/* → LLM Proxy
│   └── /* → Next.js Proxy
└── Unified on Port 8001
```

## Features

- ✅ **Idempotent**: Can be run multiple times safely
- ✅ **Auto-cleanup**: Kills stale processes automatically
- ✅ **Error handling**: Clear error messages and solutions
- ✅ **Background jobs**: Next.js runs in background
- ✅ **Health checks**: Waits for services to be ready
- ✅ **Graceful shutdown**: Ctrl+C stops everything cleanly
- ✅ **UTF-8 safe**: Proper console encoding
- ✅ **Cross-platform**: Works on Windows PowerShell and PowerShell Core
