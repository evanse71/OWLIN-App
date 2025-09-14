# OWLIN - Full App Development Mode

## Overview
Run Owlin in **full app mode** with Next.js frontend (sidebar, pages, uploads, live HMR) + FastAPI backend + LLM proxy, all unified on **http://127.0.0.1:8001**.

## Quick Start

### Terminal 1 — Next.js Dev Server
```bash
npm run dev
```
- Serves UI at `http://127.0.0.1:3000`
- Provides live HMR and development features

### Terminal 2 — FastAPI Single-Port with Proxy
```powershell
# Windows PowerShell
$env:UI_MODE="PROXY_NEXT"
$env:NEXT_BASE="http://127.0.0.1:3000"
$env:LLM_BASE="http://127.0.0.1:11434"
$env:OWLIN_PORT="8001"
python -m backend.final_single_port
```

```bash
# Linux/macOS
export UI_MODE="PROXY_NEXT"
export NEXT_BASE="http://127.0.0.1:3000"
export LLM_BASE="http://127.0.0.1:11434"
export OWLIN_PORT="8001"
python -m backend.final_single_port
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `UI_MODE` | `"STATIC"` | UI mode: `"PROXY_NEXT"` for dev proxy, `"STATIC"` for built frontend |
| `NEXT_BASE` | `"http://127.0.0.1:3000"` | Next.js dev server base URL |
| `LLM_BASE` | `"http://127.0.0.1:11434"` | Upstream LLM endpoint (Ollama) |
| `OWLIN_PORT` | `8001` | Port to bind the unified server |

## Verification

1. **Start both terminals** as shown above
2. **Open http://127.0.0.1:8001** in your browser
3. **Verify endpoints:**
   - `/api/health` → `{"ok": true}`
   - `/api/status` → Shows `"ui_mode": "PROXY_NEXT"` and `"api_mounted": true`
   - `/llm/*` → Proxies to LLM_BASE
   - All other routes → Proxies to Next.js dev server

## Features

### ✅ What Works
- **Unified Port**: Everything on `http://127.0.0.1:8001`
- **No CORS Issues**: Same-origin requests to API and LLM
- **Live HMR**: Next.js hot reload works through proxy
- **API Routes**: All `/api/*` routes handled by FastAPI
- **LLM Proxy**: All `/llm/*` routes proxied to Ollama
- **UI Proxy**: All other routes proxied to Next.js dev server

### 🔧 Route Order
1. `/api/*` → FastAPI backend (local)
2. `/llm/*` → LLM proxy (to LLM_BASE)
3. `/*` → Next.js proxy (to NEXT_BASE)

## Troubleshooting

### Next.js Not Starting
```bash
# Check if port 3000 is free
netstat -an | findstr :3000  # Windows
lsof -i :3000                # macOS/Linux

# Kill process if needed
taskkill /F /PID <PID>       # Windows
kill -9 <PID>                # macOS/Linux
```

### Backend Proxy Issues
```bash
# Check if Next.js is running
curl http://127.0.0.1:3000

# Check backend logs for proxy errors
# Look for "Next.js proxy error" in logs
```

### Port Conflicts
```bash
# Check if port 8001 is free
netstat -an | findstr :8001  # Windows
lsof -i :8001                # macOS/Linux

# Use different port
$env:OWLIN_PORT="8002"       # Windows
export OWLIN_PORT="8002"     # macOS/Linux
```

## Development Workflow

1. **Start Next.js**: `npm run dev` (Terminal 1)
2. **Start Backend**: Set env vars and run Python (Terminal 2)
3. **Develop**: Open `http://127.0.0.1:8001` and develop normally
4. **API Changes**: Backend auto-reloads on file changes
5. **UI Changes**: Next.js HMR works through proxy

## Production Mode

For production, use static mode:
```bash
# Build frontend
npm run build

# Run in static mode (default)
python -m backend.final_single_port
```

## Architecture

```
Browser → http://127.0.0.1:8001
    ├── /api/* → FastAPI Backend (local)
    ├── /llm/* → LLM Proxy → Ollama (127.0.0.1:11434)
    └── /* → Next.js Proxy → Next.js Dev (127.0.0.1:3000)
```

This setup provides a seamless development experience with all services unified on a single port while maintaining the benefits of Next.js HMR and FastAPI's development features.

## Dev (Next.js + Proxy)

### Quick Start Commands

**Terminal 1 - Next.js Frontend:**
```bash
npm run dev
```

**Terminal 2 - Backend with Proxy:**
```powershell
$env:UI_MODE="PROXY_NEXT"
$env:NEXT_BASE="http://127.0.0.1:3000"
$env:LLM_BASE="http://127.0.0.1:11434"
$env:OWLIN_PORT="8001"
python -m backend.final_single_port
```

**Open the full app:**
```
http://127.0.0.1:8001
```

### Health Checks
```powershell
# Test backend health
irm http://127.0.0.1:8001/api/health | % Content

# Test backend status  
irm http://127.0.0.1:8001/api/status | % Content

# Test Next.js directly (if needed)
curl http://127.0.0.1:3000
```

### Troubleshooting

**Next.js not starting:**
- Check for TypeScript errors: `npm run type-check`
- Ensure all dependencies installed: `npm ci`
- Check port 3000 is free: `netstat -ano | findstr :3000`

**Backend proxy issues:**
- Verify Next.js is running on port 3000
- Check backend logs for proxy errors
- Ensure environment variables are set correctly

**Full app not loading:**
- Verify both services are running
- Check browser console for errors
- Test API endpoints directly