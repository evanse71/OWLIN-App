# OWLIN - Quick Launch Reference

## 🚀 Two Terminal Launch

### Terminal 1 - Next.js (UI with HMR on :3000)
```bash
npm run dev
```

### Terminal 2 - FastAPI (single-port proxy on :8001)
```powershell
$env:UI_MODE="PROXY_NEXT"
$env:NEXT_BASE="http://127.0.0.1:3000"
$env:LLM_BASE="http://127.0.0.1:11434"
$env:OWLIN_PORT="8001"
python -m backend.final_single_port
```

### Or One-Click (Windows)
```powershell
.\scripts\start_full_dev.ps1
```

### Or Desktop Shortcuts (Double-Click)
- **Windows**: `scripts\launch_owlin_dev.bat` or `scripts\launch_owlin_dev.ps1`
- **macOS/Linux**: `scripts/launch_owlin_dev.sh`

## 🌐 Open the App
```
http://127.0.0.1:8001
```

## ✅ Sanity Checks
```powershell
# API Health
irm http://127.0.0.1:8001/api/health | % Content

# API Status  
irm http://127.0.0.1:8001/api/status | % Content

# UI Check
curl -I http://127.0.0.1:8001
```

**Expected:**
- `{"ok": true}` from health
- `"api_mounted": true, "ui_mode":"PROXY_NEXT"` from status
- Full Next.js UI with sidebar, pages, uploads, HMR

## 🔧 Quick Fixes

### Port Busy
```powershell
# Check ports
netstat -ano | findstr :3000
netstat -ano | findstr :8001

# Kill process
Stop-Process -Id <PID> -Force
```

### UI Blank/500
- Ensure `npm run dev` is running
- Check `http://127.0.0.1:3000` is reachable
- Verify Next.js started without errors

### LLM Not Up
- Start Ollama: `ollama serve`
- Or change `LLM_BASE` environment variable

## 🏗️ Architecture

```
Browser → http://127.0.0.1:8001
    ├── /api/* → FastAPI Backend (local)
    ├── /llm/* → LLM Proxy → Ollama (127.0.0.1:11434)
    └── /* → Next.js Proxy → Next.js Dev (127.0.0.1:3000)
```

## 📁 Key Files

- `scripts/start_full_dev.ps1` - One-click launcher
- `scripts/CARRY_CARD.md` - Complete documentation
- `backend/final_single_port.py` - Backend with PROXY_NEXT mode
- `lib/api.ts` - Frontend API client
- `.env.local` - Environment configuration

---

**Result:** Full Next.js UI (sidebar, pages, uploads, HMR) + FastAPI backend + LLM proxy, all unified on a single origin for realistic testing! 🎯
