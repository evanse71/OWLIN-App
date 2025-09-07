import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Owlin API Minimal", version="1.0.0")

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create data directories
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
previews_dir = data_dir / "previews"
previews_dir.mkdir(exist_ok=True)

# Mount static files for preview images
app.mount("/previews", StaticFiles(directory="data/previews"), name="previews")

@app.get("/")
async def root():
    return {"message": "Owlin API Minimal is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/health")
def api_health_check():
    return {"status": "ok"}

@app.post("/api/upload/test")
async def test_upload():
    """Test upload endpoint that returns a simple response"""
    return {
        "success": True,
        "message": "Test upload endpoint working",
        "document_id": "test-123",
        "processing_results": {
            "document_type": "invoice",
            "supplier": "Test Supplier",
            "invoice_number": "TEST-001",
            "overall_confidence": 0.8,
            "line_items_count": 1,
            "processing_time": 1.0,
            "pages_processed": 1,
            "pages_failed": 0
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Owlin Minimal Backend Server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("✅ Health check: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000) 