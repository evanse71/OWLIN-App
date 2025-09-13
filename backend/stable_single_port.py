from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
import httpx
import os
from pathlib import Path

FRONTEND_DIR = Path("out")
LLM_BASE = os.environ.get("LLM_BASE", "http://127.0.0.1:11434")

app = FastAPI(title="Owlin Single-Port")

# Basic health endpoint
@app.get("/api/health")
def health():
    return {"ok": True}

# Status endpoint
@app.get("/api/status")
def status():
    return {
        "ok": True,
        "api_mounted": True,
        "api_error": None,
        "message": "Basic API running - full backend can be mounted later"
    }

# Serve static UI
if FRONTEND_DIR.exists():
    app.mount("/_static", StaticFiles(directory=str(FRONTEND_DIR), html=False), name="static")
INDEX_FILE = FRONTEND_DIR / "index.html"

# Global HTTP client
http_client = None

@app.on_event("startup")
async def startup():
    global http_client
    http_client = httpx.AsyncClient(follow_redirects=True, timeout=120)

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

@app.get("/{full_path:path}")
async def spa(full_path: str):
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
    uvicorn.run(app, host="127.0.0.1", port=8001)
