from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
import httpx
import os
from pathlib import Path

FRONTEND_DIR = Path("out")  # adjust if yours differs
LLM_BASE = os.environ.get("LLM_BASE", "http://127.0.0.1:11434")

# ✅ create/close HTTP client during lifespan (not at import-time)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.http = httpx.AsyncClient(follow_redirects=True, timeout=120)
    yield
    # Shutdown
    if hasattr(app.state, "http"):
        try:
            await app.state.http.aclose()
        except Exception:
            pass

app = FastAPI(title="Owlin Single-Port", lifespan=lifespan)

# --- include your real API routers here ---
from backend.routers import manual_entry
from backend.routers.health import router as health_router
app.include_router(manual_entry.router, prefix="/api")
app.include_router(health_router, prefix="/api")

# Serve static UI
if FRONTEND_DIR.exists():
    app.mount("/_static", StaticFiles(directory=str(FRONTEND_DIR), html=False), name="static")
INDEX_FILE = FRONTEND_DIR / "index.html"

async def _proxy(request: Request, upstream_base: str) -> Response:
    # build upstream URL
    upstream_url = upstream_base + request.url.path[len("/llm"):]  # strip '/llm'
    headers = dict(request.headers)
    headers.pop("host", None)
    body = await request.body()

    r = await app.state.http.request(
        request.method,
        upstream_url,
        headers=headers,
        content=body,
        params=request.query_params,
        stream=True,
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

# SPA fallback
@app.get("/{full_path:path}")
async def spa(full_path: str):
    # if we don't have an export yet, just show a basic page to avoid SystemExit killing the server
    if not INDEX_FILE.exists():
        return JSONResponse({"ok": True, "ui": "not-built-yet"}, status_code=200)
    if full_path.startswith("_static/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return FileResponse(str(INDEX_FILE), media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.single_port_app:app", host="127.0.0.1", port=8001, reload=False, factory=False)
