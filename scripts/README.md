# OWLIN Scripts Directory

Cross-platform launchers, deployment tools, and utilities for the Owlin application.

## 🚀 Quick Start

### Windows
```powershell
.\scripts\start_and_verify.ps1
```

### Linux/macOS
```bash
chmod +x scripts/start_and_verify.sh
./scripts/start_and_verify.sh
```

## 📁 Script Files

### Core Launchers
- **`start_and_verify.ps1`** - Windows one-click launcher (UTF-8 safe, ASCII-only)
- **`start_and_verify.sh`** - Linux/macOS one-click launcher (UTF-8 safe, ASCII-only)
- **`start_single_port.ps1`** - Original Windows launcher (legacy)

### Deployment Scripts
- **`windows_service_setup.ps1`** - Install Owlin as Windows service (NSSM)
- **`linux_service_setup.sh`** - Install Owlin as systemd service (Linux)
- **`create_desktop_shortcuts.ps1`** - Create desktop shortcuts for easy access

### Documentation
- **`CARRY_CARD.md`** - Quick reference for all platforms
- **`CROSS_PLATFORM_LAUNCHER.md`** - Detailed cross-platform guide
- **`README.md`** - This file

## 🛠️ Features

### All Launchers Support:
- ✅ **UTF-8 safe encoding** (no console errors)
- ✅ **ASCII-only output** (no emoji encoding issues)
- ✅ **Auto-environment setup** (PYTHONPATH, .env loading)
- ✅ **Auto-UI building** (npm run build if needed)
- ✅ **Auto-port clearing** (kills stale processes)
- ✅ **Auto-health verification** (waits for readiness)
- ✅ **Auto-API mounting** (retry if needed)
- ✅ **Auto-browser opening** (platform-specific)
- ✅ **Live log tailing** (Ctrl+C to stop)

## 🔧 Environment Variables

```bash
OWLIN_PORT=8001                    # Port to run on
LLM_BASE=http://127.0.0.1:11434   # Ollama URL
OWLIN_DB_URL=sqlite:///./owlin.db # Database URL
```

## 🧪 CI/CD Integration

### GitHub Actions
See `.github/workflows/test-owlin.yml` for complete cross-platform testing.

### Quick CI Snippets
```yaml
# Windows
- name: Start Owlin (Windows)
  run: |
    powershell -ExecutionPolicy Bypass -File .\scripts\start_and_verify.ps1
    Start-Sleep -s 10
    irm http://127.0.0.1:8001/api/health | % Content

# Linux/macOS
- name: Start Owlin (Linux)
  run: |
    chmod +x scripts/start_and_verify.sh
    ./scripts/start_and_verify.sh &
    curl -fsS http://127.0.0.1:8001/api/health
```

## 🚀 Production Deployment

### Windows Service
```powershell
.\scripts\windows_service_setup.ps1
```

### Linux Service
```bash
sudo ./scripts/linux_service_setup.sh
```

### Docker
```bash
docker-compose up -d
```

## 🧯 Troubleshooting

### Common Issues
- **"Module not found"** → Ensure you're in repo root with `backend/__init__.py`
- **"Port busy"** → Launchers auto-clear ports, or change `OWLIN_PORT`
- **"UI not built"** → Launchers auto-build with `npm run build`
- **"API not mounted"** → Launchers auto-retry mount

### Quick Fixes
```powershell
# Windows
irm -Method POST http://127.0.0.1:8001/api/retry-mount

# Linux/macOS
curl -fsS -X POST http://127.0.0.1:8001/api/retry-mount
```

## 📋 Guardrails

- **Route order:** `/api/*` → `/llm/*` → UI catch-all last
- **Frontend calls:** always `fetch('/api/...')` (leading slash)
- **PYTHONPATH:** points to repo root (launchers set this)
- **API mounting:** auto-retry if needed

## 🎯 Modes

### Static UI (Default)
```bash
npm run build  # creates out/index.html
python -m backend.final_single_port
```

### Full Next SSR (One Port)
```bash
# Terminal 1
npm run build && npm run start  # Next on :3000

# Terminal 2
UI_MODE=PROXY_NEXT NEXT_BASE=http://127.0.0.1:3000 python -m backend.final_single_port
```

## 🪪 Carry Card

See `CARRY_CARD.md` for the minimal reference you can keep handy.

---

**🎉 One command on any platform brings Owlin up, verifies health, mounts the real API, and opens the UI!** 🚀
