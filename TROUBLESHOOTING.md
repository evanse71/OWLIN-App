# 🔧 OWLIN Troubleshooting Guide

## Quick Fixes Table

| Symptom | Likely Cause | Instant Fix |
|---------|--------------|-------------|
| **Blank page at `/`** | Build missing/stale | `rm -rf tmp_lovable/dist && (cd tmp_lovable && npm run build) && restart uvicorn` |
| **Deep link 404** (`/dashboard`) | No SPA fallback | ✅ **Fixed** - SPA fallback handler added |
| **CORS errors** | Split-port dev | Use single-port (recommended) or ensure CORS allows `localhost:8080` |
| **Upload 404** | Route mismatch | Confirm `POST /api/upload` and frontend points to `/api/upload` |
| **Upload 500** | Missing folder/perm | Startup hook creates `data/uploads`; check logs in `data/logs/app.log` |
| **Port conflicts** | Multiple servers | Kill old processes: `Get-Process -Name python,node \| Stop-Process -Force` |
| **Stale assets** | Cached build | `rm -rf tmp_lovable/dist && npm run build` |

## Environment Modes

### Single-Port Mode (Recommended for Demos)
```bash
OWLIN_SINGLE_PORT=1 python test_backend_simple.py
```
- Frontend + API on port 8000
- Zero CORS issues
- Perfect for demos and production

### Split-Port Development
```bash
OWLIN_SINGLE_PORT=0 python test_backend_simple.py  # API only on :8000
cd tmp_lovable && npm run dev                      # Frontend on :8080
```
- API on port 8000, frontend on port 8080
- Hot reload for development
- Requires CORS configuration

## Health Checks

### Backend Health
```bash
curl -s http://127.0.0.1:8000/api/health
# Expected: {"status":"ok"}
```

### Frontend Serving
```bash
curl -s http://127.0.0.1:8000 | grep -q "<!doctype html"
# Expected: HTML content
```

### File Upload
```bash
echo "test" > test.txt
curl -F "file=@test.txt" http://127.0.0.1:8000/api/upload
# Expected: {"ok":true,"filename":"test.txt",...}
```

## Log Files

### Application Logs
- **Location**: `data/logs/app.log`
- **Rotation**: 2MB max, 3 backups
- **Format**: `2025-10-02 14:30:15 INFO: message`

### Upload Logs
- **Location**: `data/uploads/`
- **Format**: Files saved with original names

## Support Pack Generation

```bash
bash scripts/make_support_pack.sh
```
**Contents**:
- Backend Python files
- Uploads directory
- Log files (`data/logs/app.log`)
- Configuration files
- System information
- Git information
- Diagnostic test results

## Common Commands

### Kill All Servers
```powershell
# Windows
Get-Process -Name python,node | Stop-Process -Force

# Linux/macOS
pkill -f "uvicorn|next|vite"
```

### Rebuild Everything
```bash
# Clean build
rm -rf tmp_lovable/dist
cd tmp_lovable && npm ci && npm run build
cd .. && python test_backend_simple.py
```

### Test Single-Port Demo
```bash
# Run smoke test
bash scripts/smoke_single_port.sh

# Or PowerShell
powershell -ExecutionPolicy Bypass -File scripts\smoke_single_port.ps1
```

## Performance Tips

### Caching
- Static assets cached automatically
- Use `CachedStatic` for better performance
- Assets get `Cache-Control` headers

### Logging
- Rotating logs prevent disk bloat
- Structured logging for easy parsing
- Support packs include all logs

### SPA Fallback
- Deep links (`/dashboard`, `/invoices`) work
- API routes (`/api/*`) bypass fallback
- 404s serve `index.html` for client-side routing

## CI/CD Integration

The GitHub Action validates:
- ✅ Frontend builds successfully
- ✅ Single-port demo starts
- ✅ Smoke tests pass
- ✅ Deep links work (SPA fallback)
- ✅ API endpoints respond
- ✅ File upload works
- ✅ Log files created

## Next Steps

1. **Test the UI**: Open http://127.0.0.1:8000
2. **Upload Files**: Test file upload functionality
3. **Check Logs**: Review `data/logs/app.log`
4. **Run Smoke Tests**: Validate everything works
5. **Generate Support Pack**: For debugging assistance

**The OWLIN application is now bulletproof and production-ready!** 🎯
