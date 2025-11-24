#!/usr/bin/env bash
set -euo pipefail

echo "🚀 OWLIN Single-Port Demo Mode"
echo "=============================="

# Configuration
BACKEND_PORT=8000
FRONTEND_BUILD_DIR="out"
STATIC_SERVE_PATH="/static"

echo "📦 Building frontend for production..."

# Build frontend
npm run build

echo "✅ Frontend build complete"

# Create static file serving script
cat > serve_demo.py << 'EOF'
#!/usr/bin/env python3
"""
Single-port demo mode: Serve frontend build via FastAPI
Zero CORS, cleaner demos, fewer environment variables
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s %(levelname)s: %(message)s"
)
logger = logging.getLogger("owlin.demo")

# Startup lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure uploads directory exists
    os.makedirs("data/uploads", exist_ok=True)
    logger.info("Created uploads directory: data/uploads")
    yield
    logger.info("Shutting down OWLIN demo server")

app = FastAPI(title="OWLIN Demo Server", version="1.0.0", lifespan=lifespan)

# CORS configuration (minimal for single-port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Single port, no CORS issues
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload endpoint for demo"""
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Read file content
        content = await file.read()
        
        # Save file
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info("upload saved: %s (%d bytes)", file_path, len(content))
        
        return {
            "ok": True, 
            "filename": file.filename, 
            "bytes": len(content),
            "saved_to": file_path
        }
        
    except Exception as e:
        logger.error("Upload failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files
app.mount("/static", StaticFiles(directory="out"), name="static")

# Serve frontend for all other routes
@app.get("/{path:path}")
async def serve_frontend(path: str):
    """Serve frontend for all routes"""
    # If it's an API route, let FastAPI handle it
    if path.startswith("api/"):
        return {"error": "API route not found"}
    
    # Serve index.html for all other routes (SPA)
    if os.path.exists("out/index.html"):
        return FileResponse("out/index.html")
    else:
        return {"error": "Frontend build not found. Run 'npm run build' first."}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting OWLIN Single-Port Demo Server...")
    print("📍 Frontend: http://localhost:8000")
    print("📍 API: http://localhost:8000/api/health")
    print("📍 Upload: http://localhost:8000/api/upload")
    print("📍 Zero CORS - cleaner demos!")
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

echo "📄 Created single-port demo server"

# Make demo server executable
chmod +x serve_demo.py

echo ""
echo "🎉 Single-port demo mode ready!"
echo ""
echo "To start the demo server:"
echo "  python serve_demo.py"
echo ""
echo "Then visit: http://localhost:8000"
echo "  - Frontend: http://localhost:8000"
echo "  - API: http://localhost:8000/api/health"
echo "  - Upload: http://localhost:8000/api/upload"
echo ""
echo "Benefits:"
echo "  ✅ Zero CORS issues"
echo "  ✅ Single port for demos"
echo "  ✅ Fewer environment variables"
echo "  ✅ Cleaner for presentations"
echo ""
echo "To stop: Ctrl+C"
