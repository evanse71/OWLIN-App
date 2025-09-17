from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from starlette.requests import Request
from pathlib import Path
import importlib, pkgutil, inspect
import sys
import os

# Import the new routers
try:
    from backend.routers import health as health_router
    from backend.routers import invoices as invoices_router
    from backend.routers import uploads as uploads_router
    from backend.routers import exports as exports_router
    from backend.routers import pairing as pairing_router
except ImportError:
    from routers import health as health_router
    from routers import invoices as invoices_router
    from routers import uploads as uploads_router
    from routers import exports as exports_router
    from routers import pairing as pairing_router

# Add the project root to Python path
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path: 
    sys.path.insert(0, ROOT)
print(f"[startup] PYTHONPATH -> {ROOT}")

# --- logging + exception handler (DEV ONLY) ---
import logging, traceback
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("owlin")

# ROOT already defined above

def _resolve_frontend_out() -> Path:
    for p in (Path(ROOT) / "frontend" / "out", Path(ROOT) / "out"):
        if (p / "index.html").exists():
            return p
    raise RuntimeError("Exported frontend missing (frontend/out or ./out)")
FRONTEND_OUT = _resolve_frontend_out()
print(f"[startup] FRONTEND_OUT -> {FRONTEND_OUT}")

def _include_all_api_routers(app: FastAPI):
    blacklist = {
        "backend.routes.upload_fixed",
        "backend.routes.upload_bulletproof",
        "backend.routes.upload_legacy",
    }
    for pkg_name in ("backend.api", "backend.routes"):
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception as e:
            print(f"[router-scan] skip {pkg_name}: {e}")
            continue
        for _, modname, _ in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
            if modname in blacklist:
                print(f"[router-scan] BLACKLISTED {modname}")
                continue
            try:
                mod = importlib.import_module(modname)
            except Exception as e:
                print(f"[router-scan] import fail {modname}: {e}")
                continue
            mounted = False
            for name, obj in vars(mod).items():
                if isinstance(obj, APIRouter):
                    app.include_router(obj, prefix="/api")
                    print(f"[router-scan] mounted {modname}.{name}")
                    mounted = True
            get_router = getattr(mod, "get_router", None)
            if callable(get_router):
                r = get_router()
                if isinstance(r, APIRouter):
                    app.include_router(r, prefix="/api")
                    print(f"[router-scan] mounted via get_router {modname}")
                    mounted = True
            if not mounted:
                pass

app = FastAPI(title="Owlin Unified Single Port")

# Include the new routers
app.include_router(health_router.router)
app.include_router(uploads_router.router)
app.include_router(uploads_router.legacy)  # legacy shim for /api/upload?kind=invoice
app.include_router(invoices_router.router)
app.include_router(exports_router.router)
app.include_router(pairing_router.router)

@app.exception_handler(Exception)
async def global_exc_handler(request, exc):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "trace": traceback.format_exc().splitlines()[-10:]  # last 10 lines
        }
    )

_include_all_api_routers(app)  # your scanner, keeps prefix="/api"

# ✅ MINIMAL SPA (never touches /api)
@app.middleware("http")
async def spa_fallback(request: Request, call_next):
    resp = await call_next(request)
    if resp.status_code == 404 and request.method == "GET" and not request.url.path.startswith("/api"):
        return HTMLResponse((FRONTEND_OUT/'index.html').read_text(encoding='utf-8'), status_code=200)
    return resp

# ✅ STATIC ON (after API routes)
app.mount("/", StaticFiles(directory=str(FRONTEND_OUT), html=True), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    return (FRONTEND_OUT / "index.html").read_text(encoding="utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8081)