import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes import invoices, flagged_issues, suppliers, analytics, ocr, products
from backend.routes import document_queue, upload_review, confirm_splits, upload_fixed
from backend.routes import dev, agent, test_ocr, upload_enhanced, matching, upload_validation
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Owlin API", version="1.0.0")

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

# Include all route modules
app.include_router(upload_fixed.router, prefix="/api")
app.include_router(upload_review.router, prefix="/api")
app.include_router(confirm_splits.router, prefix="/api")
app.include_router(invoices.router, prefix="/api")
app.include_router(flagged_issues.router, prefix="/api")
app.include_router(suppliers.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(ocr.router, prefix="/api")
app.include_router(products.router, prefix="/api/products")
app.include_router(document_queue.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(test_ocr.router)

# ✅ Include enhanced upload routes
app.include_router(upload_enhanced.router, prefix="/api", tags=["enhanced-upload"])

# ✅ Include matching routes
app.include_router(matching.router, prefix="/api", tags=["matching"])

# ✅ Include upload validation routes
app.include_router(upload_validation.router, prefix="/api", tags=["upload-validation"])

# ✅ Include dev routes for testing
app.include_router(dev.router, prefix="/api/dev", tags=["development"])

@app.get("/")
async def root():
    return {"message": "Owlin API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/health")
def api_health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Owlin Backend Server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("✅ Health check: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)