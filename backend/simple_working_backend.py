from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
import httpx
import os
from pathlib import Path

FRONTEND_DIR = Path("out")
LLM_BASE = os.environ.get("LLM_BASE", "http://127.0.0.1:11434")
NEXT_BASE = os.environ.get("NEXT_BASE", "http://127.0.0.1:3000")
UI_MODE = os.environ.get("UI_MODE", "PROXY_NEXT")
OWLIN_PORT = int(os.environ.get("OWLIN_PORT", "8001"))

app = FastAPI(title="OWLIN Simple Working Backend")

# Simple health endpoint
@app.get("/api/health")
def health():
    return {"ok": True}

# Status endpoint
@app.get("/api/status")
def status():
    return {
        "ok": True,
        "api_mounted": True,
        "ui_mode": UI_MODE,
        "port": OWLIN_PORT,
        "llm_base": LLM_BASE,
        "next_base": NEXT_BASE,
        "message": "Simple working backend running successfully"
    }

# Mock invoices endpoint
@app.get("/api/invoices")
def get_invoices():
    return {
        "items": [
            {
                "id": "sample-1",
                "supplier": "Sample Supplier",
                "invoice_no": "INV-001",
                "date": "2024-01-15",
                "total": 1500.00,
                "currency": "GBP",
                "status": "processed"
            }
        ]
    }

# Mock invoice detail endpoint
@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    return {
        "id": invoice_id,
        "supplier": "Sample Supplier",
        "invoice_no": "INV-001",
        "date": "2024-01-15",
        "total": 1500.00,
        "currency": "GBP",
        "status": "processed",
        "line_items": [
            {
                "id": 1,
                "description": "Sample Item 1",
                "quantity": 2,
                "unit_price": 500.00,
                "total": 1000.00
            },
            {
                "id": 2,
                "description": "Sample Item 2", 
                "quantity": 1,
                "unit_price": 500.00,
                "total": 500.00
            }
        ]
    }

# Mock upload endpoint
@app.post("/api/uploads")
async def upload_file(file: Request):
    return {
        "job_id": "sample-job-1",
        "document_id": "sample-doc-1",
        "items": [],
        "stored_path": "/uploads/sample.pdf"
    }

# Proxy to Next.js for UI
@app.get("/{path:path}")
async def proxy_to_nextjs(path: str, request: Request):
    if UI_MODE == "PROXY_NEXT":
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{NEXT_BASE}/{path}"
                if request.query_params:
                    url += "?" + str(request.query_params)
                
                print(f"Proxying request to: {url}")
                response = await client.get(url, follow_redirects=True)
                
                # Filter out problematic headers
                headers = {}
                for key, value in response.headers.items():
                    if key.lower() not in ['content-encoding', 'transfer-encoding', 'connection', 'content-length']:
                        headers[key] = value
                
                print(f"Proxy response: {response.status_code}")
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=headers
                )
        except Exception as e:
            print(f"Proxy error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Proxy error: {str(e)}"}
            )
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "UI mode not configured"}
        )

if __name__ == "__main__":
    import uvicorn
    print(f"Starting OWLIN Simple Backend on port {OWLIN_PORT}")
    print(f"UI Mode: {UI_MODE}")
    print(f"Next.js Base: {NEXT_BASE}")
    print(f"LLM Base: {LLM_BASE}")
    uvicorn.run(app, host="127.0.0.1", port=OWLIN_PORT)
