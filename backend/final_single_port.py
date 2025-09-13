from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
import os
from pathlib import Path

# Load environment variables early
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Structured logging
import logging
import sys
import json
import time
import uuid
from datetime import datetime

# Configure structured JSON logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'route'):
            log_entry['route'] = record.route
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'latency_ms'):
            log_entry['latency_ms'] = record.latency_ms
        if hasattr(record, 'user_agent'):
            log_entry['user_agent'] = record.user_agent
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
            
        return json.dumps(log_entry)

# Setup logger
logger = logging.getLogger("owlin")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# Console handler with JSON formatting
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(JSONFormatter())
logger.addHandler(console_handler)

# File handler for production
if os.getenv("LOG_FILE"):
    file_handler = logging.FileHandler(os.getenv("LOG_FILE"))
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

FRONTEND_DIR = Path("out")
LLM_BASE = os.getenv("LLM_BASE", "http://127.0.0.1:11434")
PORT = int(os.getenv("OWLIN_PORT", os.getenv("PORT", "8001")))
DB_URL = os.getenv("OWLIN_DB_URL", "sqlite:///./owlin.db")

app = FastAPI(title="Owlin Single-Port")

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Extract client info
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Log request start
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "route": f"{request.method} {request.url.path}",
            "ip_address": client_ip,
            "user_agent": user_agent
        }
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate latency
    latency_ms = round((time.time() - start_time) * 1000, 2)
    
    # Log request completion
    logger.info(
        f"Request completed: {response.status_code}",
        extra={
            "request_id": request_id,
            "route": f"{request.method} {request.url.path}",
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "ip_address": client_ip,
            "user_agent": user_agent
        }
    )
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    
    return response

# Cache control middleware
class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        path = request.url.path
        if path.startswith("/_static/") or any(path.endswith(x) for x in (".js",".css",".png",".jpg",".svg",".ico",".woff2",".map")):
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            resp.headers["Cache-Control"] = "no-store"
        return resp

app.add_middleware(CacheControlMiddleware)

# Security headers middleware
@app.middleware("http")
async def security_headers(request, call_next):
    resp: Response = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Permissions-Policy", "geolocation=()")
    return resp

# Lazy-mount real API (won't crash server on import errors)
import traceback
from fastapi import HTTPException

def _mount_real_api():
    try:
        # Import the real API router with proper package structure
        from backend.app import api_router as real_api_router
        app.include_router(real_api_router, prefix="/api")
        app.state.api_mounted = True
        app.state.api_error = None
        return True, None
    except Exception:
        err = traceback.format_exc()
        app.state.api_mounted = False
        app.state.api_error = err
        return False, err

# call once at import
_mount_real_api()

# Basic health endpoint
@app.get("/api/health")
def health():
    return {"ok": True}

# Backup endpoint
@app.post("/api/backup")
def create_backup():
    import shutil
    import zipfile
    from datetime import datetime
    
    try:
        # Create backup directory
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"owlin_backup_{timestamp}.zip"
        
        # Create backup archive
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add database
            if Path("owlin.db").exists():
                zipf.write("owlin.db", "owlin.db")
            
            # Add config files
            if Path("config.env.example").exists():
                zipf.write("config.env.example", "config.env.example")
            
            # Add version info
            zipf.writestr("backup_info.txt", f"Backup created: {datetime.now().isoformat()}\nVersion: 1.0.0")
        
        logger.info(f"Backup created: {backup_file}")
        
        return {
            "ok": True,
            "backup_file": str(backup_file),
            "timestamp": timestamp,
            "message": "Backup created successfully"
        }
        
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500
        )

# Recovery endpoint
@app.post("/api/recovery")
async def restore_backup(file: bytes = None):
    import zipfile
    import shutil
    from datetime import datetime
    
    try:
        if not file:
            return JSONResponse(
                {"ok": False, "error": "No backup file provided"},
                status_code=400
            )
        
        # Create temporary backup file
        temp_backup = Path("temp_backup.zip")
        with open(temp_backup, "wb") as f:
            f.write(file)
        
        # Extract backup
        with zipfile.ZipFile(temp_backup, 'r') as zipf:
            zipf.extractall(".")
        
        # Clean up temp file
        temp_backup.unlink()
        
        logger.info("Backup restored successfully")
        
        return {
            "ok": True,
            "message": "Backup restored successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Recovery failed: {str(e)}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500
        )

# Deep health check for orchestrators
@app.get("/api/healthz")
def healthz(deep: bool = False):
    if not deep:
        return {"ok": True, "status": "lightweight"}
    
    # Deep health check - test DB and file system
    checks = {
        "ok": True,
        "status": "deep",
        "checks": {}
    }
    
    # Check database
    try:
        import sqlite3
        conn = sqlite3.connect(DB_URL.replace("sqlite:///", ""))
        conn.execute("SELECT 1")
        conn.close()
        checks["checks"]["database"] = "ok"
    except Exception as e:
        checks["checks"]["database"] = f"error: {str(e)}"
        checks["ok"] = False
    
    # Check frontend build
    if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
        checks["checks"]["frontend"] = "ok"
    else:
        checks["checks"]["frontend"] = "not_built"
    
    # Check LLM connectivity
    try:
        import httpx
        with httpx.Client(timeout=2) as client:
            response = client.get(f"{LLM_BASE}/api/tags")
            if response.status_code == 200:
                checks["checks"]["llm"] = "ok"
            else:
                checks["checks"]["llm"] = f"status_{response.status_code}"
    except Exception as e:
        checks["checks"]["llm"] = f"error: {str(e)}"
    
    return checks

# Status endpoint
from fastapi import APIRouter
status_router = APIRouter()

@status_router.get("/status")
def status():
    return {
        "ok": True,
        "api_mounted": getattr(app.state, "api_mounted", False),
        "api_error": getattr(app.state, "api_error", None),
        "message": "Single-port Owlin running successfully"
    }

app.include_router(status_router, prefix="/api")

# Retry-mount endpoint (no restarts needed)
retry_router = APIRouter()

@retry_router.post("/retry-mount")
def retry_mount():
    ok, err = _mount_real_api()
    if not ok:
        raise HTTPException(status_code=500, detail={"error": err})
    return {"ok": True, "message": "API mounted successfully"}

app.include_router(retry_router, prefix="/api")

# Static file mounting moved to after LLM proxy

# Global HTTP client
http_client = None

@app.on_event("startup")
async def startup():
    global http_client
    http_client = httpx.AsyncClient(
        follow_redirects=True, 
        timeout=httpx.Timeout(connect=5, read=120, write=30, pool=5)
    )

@app.on_event("shutdown")
async def shutdown():
    global http_client
    if http_client:
        await http_client.aclose()

async def _proxy(request: Request, upstream_base: str) -> Response:
    upstream_url = upstream_base + request.url.path[len("/llm"):]
    headers = dict(request.headers)
    headers.pop("host", None)
    body = await request.body()

    r = await http_client.request(
        request.method,
        upstream_url,
        headers=headers,
        content=body,
        params=request.query_params,
    )

    async def stream():
        async for chunk in r.aiter_bytes():
            yield chunk

    filtered = {k: v for k, v in r.headers.items()
                if k.lower() not in ("transfer-encoding", "connection", "keep-alive")}
    return StreamingResponse(stream(), status_code=r.status_code, headers=filtered,
                             background=BackgroundTask(r.aclose))

@app.api_route("/llm/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"])
async def llm_proxy(path: str, request: Request):
    return await _proxy(request, LLM_BASE)

# Serve static UI
if FRONTEND_DIR.exists():
    app.mount("/_static", StaticFiles(directory=str(FRONTEND_DIR), html=False), name="static")
INDEX_FILE = FRONTEND_DIR / "index.html"

# Catch-all for UI (must be LAST to not interfere with API routes)
@app.get("/{full_path:path}")
async def spa(full_path: str):
    # Don't intercept API or LLM routes
    if full_path.startswith("api/") or full_path.startswith("llm/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    
    if not INDEX_FILE.exists():
        return JSONResponse({
            "ok": True, 
            "ui": "not-built-yet",
            "message": "UI not built yet. Run 'npm run build' to build the frontend.",
            "endpoints": {
                "health": "/api/health",
                "status": "/api/status",
                "llm_proxy": "/llm/*"
            }
        }, status_code=200)
    if full_path.startswith("_static/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return FileResponse(str(INDEX_FILE), media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info")
