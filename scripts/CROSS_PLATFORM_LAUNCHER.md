# OWLIN - Cross-Platform One-Click Launchers

ASCII-safe, UTF-8 compatible launchers for Windows, Linux, and macOS.

## 🪟 Windows

### Launch
```powershell
.\scripts\start_and_verify.ps1
```

### Features
- ✅ UTF-8 encoding forced for console and Python
- ✅ ASCII-only Python import test
- ✅ .env file loading
- ✅ UI build if missing (`npm run build`)
- ✅ Port clearing (netstat)
- ✅ Health check with retry
- ✅ API mount verification
- ✅ Browser opening (Start-Process)
- ✅ Live log tailing

## 🐧 Linux / 🍎 macOS

### Setup
```bash
chmod +x scripts/start_and_verify.sh
```

### Launch
```bash
./scripts/start_and_verify.sh
```

### Features
- ✅ UTF-8 encoding (`LC_ALL=C.UTF-8`)
- ✅ ASCII-only Python import test
- ✅ .env file loading
- ✅ UI build if missing (`npm ci && npm run build`)
- ✅ Port clearing (lsof/netstat)
- ✅ Health check with retry
- ✅ API mount verification
- ✅ Browser opening (xdg-open/open)
- ✅ Live log tailing

## 🔍 Quick Sanity Checks

### Windows (PowerShell)
```powershell
irm http://127.0.0.1:8001/api/health | % Content
irm http://127.0.0.1:8001/api/status | % Content
```

### Linux/macOS (Bash)
```bash
curl -fsS http://127.0.0.1:8001/api/health
curl -fsS http://127.0.0.1:8001/api/status
```

## 🛠️ Troubleshooting

### Common Issues
- **"Module not found"** → Ensure you're in repo root with `backend/__init__.py`
- **"Port busy"** → Launchers auto-clear ports, or change `OWLIN_PORT`
- **"UI not built"** → Launchers auto-build with `npm run build`
- **"API not mounted"** → Launchers auto-retry mount

### Environment Variables
```bash
OWLIN_PORT=8001                    # Port to run on
LLM_BASE=http://127.0.0.1:11434   # Ollama URL
OWLIN_DB_URL=sqlite:///./owlin.db # Database URL
```

## 🚀 Production Deployment

### Windows (NSSM Service)
```powershell
.\scripts\windows_service_setup.ps1
```

### Linux (systemd Service)
```bash
sudo ./scripts/linux_service_setup.sh
```

### Docker (Complete Stack)
```bash
docker-compose up -d
```

## 📋 CI/CD Integration

### GitHub Actions (Ubuntu)
```yaml
- name: Test Owlin
  run: |
    chmod +x scripts/start_and_verify.sh
    ./scripts/start_and_verify.sh &
    sleep 10
    curl -fsS http://127.0.0.1:8001/api/health
```

### GitHub Actions (Windows)
```yaml
- name: Test Owlin
  run: |
    .\scripts\start_and_verify.ps1
    Start-Sleep 10
    irm http://127.0.0.1:8001/api/health
```

## ✅ All Platforms Support

- **ASCII-only output** (no emoji encoding issues)
- **UTF-8 safe** (proper encoding handling)
- **Auto-environment setup** (PYTHONPATH, .env loading)
- **Auto-UI building** (npm run build if needed)
- **Auto-port clearing** (kills stale processes)
- **Auto-health verification** (waits for readiness)
- **Auto-API mounting** (retry if needed)
- **Auto-browser opening** (platform-specific)
- **Live log tailing** (Ctrl+C to stop)

**🎉 One command to rule them all!** 🚀
