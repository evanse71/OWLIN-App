# OWLIN Single-Port Setup

## Quick Start

### Prerequisites
- Python 3.9+
- Optional: npm (for building UI)
- Optional: Ollama (for LLM functionality)

### One-Command Launch

From the repository root:

```bash
python -m backend.final_single_port
```

Or use the launcher script:

```powershell
.\scripts\start_single_port.ps1
```

Then open [http://127.0.0.1:8001](http://127.0.0.1:8001)

## Access Points

- **UI**: `http://127.0.0.1:8001`
- **API**: `http://127.0.0.1:8001/api/*`
- **LLM**: `http://127.0.0.1:8001/llm/*` (set `LLM_BASE` to override)
- **Health**: `http://127.0.0.1:8001/api/health`
- **Status**: `http://127.0.0.1:8001/api/status`

## Hot-Reload API

No restart needed for API changes:

```bash
curl -X POST http://127.0.0.1:8001/api/retry-mount
```

## Configuration

Create a `.env` file or set environment variables:

```bash
OWLIN_PORT=8001
LLM_BASE=http://127.0.0.1:11434
OWLIN_DB_URL=sqlite:///./owlin.db
```

Launch with custom config:

```powershell
$env:LLM_BASE="http://127.0.0.1:11434"; python -m backend.final_single_port
```

## Testing

Run the smoke tests:

```bash
pytest tests/test_single_port_smoke.py -v
```

## 30-Second Smoke Test

```powershell
# Health check
irm http://127.0.0.1:8001/api/health | % Content

# Status check
irm http://127.0.0.1:8001/api/status | % Content

# Hot-reload API
irm -Method POST http://127.0.0.1:8001/api/retry-mount | % Content

# Test real API
irm http://127.0.0.1:8001/api/manual/invoices | % Content
```

## Troubleshooting

### `ModuleNotFoundError` for `backend.*`
- **Solution**: You're not at repo root. Run: `python -m backend.final_single_port`

### `api_mounted: false`
- **Solution**: Read full traceback in `/api/status`, fix the line, then `POST /api/retry-mount`

### UI blank
- **Solution**: Build once: `npm run build` (serves `./out`). Fallback JSON appears if not built.

### LLM proxy 502
- **Solution**: Start Ollama: `ollama serve` or set `LLM_BASE`

## Key Benefits

✅ **One Command**: Start everything with one command  
✅ **One Port**: No CORS issues, everything on port 8001  
✅ **Never Crashes**: Stable, production-ready  
✅ **Hot Reload**: API changes without restart  
✅ **Real API**: Full invoice/delivery note functionality  
✅ **LLM Ready**: Proxies to Ollama when running  
✅ **Health Monitoring**: Built-in status endpoints  
✅ **Graceful Fallback**: Always responds, never dies  

## Architecture

The single-port setup consolidates:

- **UI**: Serves static files from `out/` directory
- **API**: FastAPI backend with real business logic
- **LLM Proxy**: Proxies requests to local Ollama/LM Studio
- **Health Monitoring**: Built-in status and health endpoints
- **Hot Reload**: Retry-mount API without restart

All running on a single port with no CORS issues.
