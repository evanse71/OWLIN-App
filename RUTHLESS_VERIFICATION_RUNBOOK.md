# 💀 RUTHLESS VERIFICATION RUNBOOK - OWLIN SINGLE-PORT

**Cold Russian judge of software. No mercy, no excuses. If it breaks, it fails.**

## 🚀 One-Liner Runbook

### Windows (PowerShell)
```powershell
# from repo root
.\scripts\start_single_port.ps1         # launch app on :8001
.\verify_full_owlin.ps1                 # brutal end-to-end verification
```

### macOS/Linux (Bash)
```bash
# from repo root
./scripts/start_single_port.sh          # launch app on :8001
./verify_full_owlin.sh                  # brutal end-to-end verification
```

## 🔍 Quick Sanity Checks

### Check Server Status
```powershell
# Windows PowerShell
irm http://127.0.0.1:8001/api/health | % Content
irm http://127.0.0.1:8001/api/status | % Content
```

```bash
# macOS/Linux
curl -s http://127.0.0.1:8001/api/health | jq .
curl -s http://127.0.0.1:8001/api/status | jq .
```

### Force Real API to (Re)Mount
```powershell
# Windows PowerShell
irm -Method POST http://127.0.0.1:8001/api/retry-mount | % Content
```

```bash
# macOS/Linux
curl -X POST http://127.0.0.1:8001/api/retry-mount | jq .
```

### Start LLM (Optional)
```bash
# If you want LLM proxy tests to pass
ollama serve
```

## 🧪 Verification Scripts

### PowerShell Version (`verify_full_owlin.ps1`)
- **Platform**: Windows
- **Features**: Full process management, JSON validation, stress testing
- **Output**: ✅/❌ with detailed error reporting
- **Cleanup**: Automatic process termination

### Bash Version (`verify_full_owlin.sh`)
- **Platform**: macOS/Linux
- **Features**: Lightweight, fast execution, trap-based cleanup
- **Output**: ✅/❌ with concise reporting
- **Dependencies**: `curl`, `lsof` (optional)

## 🔧 CI/CD Integration

### GitHub Actions (`.github/workflows/owlin-single-port.yml`)
- **Triggers**: Push, Pull Request
- **Platform**: Ubuntu Latest
- **Python**: 3.11
- **Tests**: Health, Status, API Mount, Root UI
- **Timeout**: 40 seconds for server startup

### Local CI Testing
```bash
# Test the CI workflow locally
act -j verify
```

## 📋 Test Coverage

### Core Tests
1. **Health Check** - `GET /api/health` → `{"ok": true}`
2. **Status Check** - `GET /api/status` → `api_mounted: true`
3. **Root UI Check** - `GET /` → HTTP 200
4. **Invoice Workflow** - POST invoice, GET list
5. **Stress Test** - 20 rapid health checks
6. **LLM Proxy Test** - `GET /llm/api/tags` (graceful timeout)

### Expected Results
```
💀 RUTHLESS VERIFICATION STARTING
Target: http://127.0.0.1:8001
Time: [timestamp]

🔪 Eliminating existing processes on port 8001...
🚀 Launching Owlin single-port server...
⏳ Waiting for server to become ready...
✅ Server is running (PID: [number])

1️⃣ HEALTH CHECK
✅ HEALTH CHECK - PASS
   Health endpoint returns {ok: true}

2️⃣ STATUS CHECK
✅ STATUS CHECK - PASS
   Status shows api_mounted: true

3️⃣ ROOT UI CHECK
✅ ROOT UI CHECK - PASS
   Root endpoint returns HTTP 200

4️⃣ INVOICE WORKFLOW
✅ INVOICE_CREATE - PASS
   Invoice endpoint accessible

5️⃣ STRESS TEST
✅ STRESS_TEST - PASS
   All 20 health check requests succeeded

6️⃣ LLM PROXY TEST
✅ LLM_PROXY - PASS
   LLM proxy timed out gracefully, server still alive

🧹 CLEANUP

============================================================
💀 RUTHLESS VERIFICATION RESULTS
============================================================
Total Tests: 6
Passed: 6
Failed: 0

🏆 ALL TESTS PASSED – BULLETPROOF
The Owlin single-port deployment is production-ready.
```

## 🚨 Troubleshooting

### Server Won't Start
```powershell
# Check for port conflicts
netstat -ano | findstr :8001

# Kill existing processes
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Stop-Process -Force
```

### API Not Mounting
```powershell
# Check status
irm http://127.0.0.1:8001/api/status | % Content

# Force retry mount
irm -Method POST http://127.0.0.1:8001/api/retry-mount | % Content
```

### Health Check Failing
```powershell
# Check server logs
python -m backend.final_single_port

# Check if frontend is built
Test-Path "out/index.html"
```

## 🎯 Success Criteria

**BULLETPROOF** = All 6 tests pass:
- ✅ Health endpoint responds correctly
- ✅ API is mounted and accessible
- ✅ Root UI serves successfully
- ✅ Invoice workflow functions
- ✅ Server handles stress (20 requests)
- ✅ LLM proxy works or times out gracefully

**FAILURE** = Any test fails:
- ❌ Server startup issues
- ❌ API mounting problems
- ❌ Endpoint errors
- ❌ Stress test failures
- ❌ Server crashes

## 🔥 Pro Tips

1. **Always run from repo root** - Scripts expect `backend/final_single_port.py`
2. **Kill existing processes** - Scripts handle this automatically
3. **Check logs** - Server output goes to stdout/stderr
4. **Use retry-mount** - Fix API issues without restarting
5. **Test both platforms** - PowerShell + Bash versions available

---

**No mercy. No excuses. If it breaks, it fails. 💀**
