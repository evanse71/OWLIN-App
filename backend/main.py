from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes import invoices, flagged_issues, suppliers, analytics, ocr, products
from backend.routes import document_queue, upload_review, confirm_splits, upload_fixed
from backend.routes import dev, agent, test_ocr, upload_enhanced, matching, upload_validation
import os
import logging
from pathlib import Path

# Configure comprehensive logging
def setup_logging():
    """Setup comprehensive logging for debugging upload issues."""
    # Create logs directory
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'ocr_errors.log'),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    # Set specific loggers to DEBUG level
    logging.getLogger('backend.routes.upload_fixed').setLevel(logging.DEBUG)
    logging.getLogger('backend.ocr').setLevel(logging.DEBUG)
    logging.getLogger('backend.routes.agent').setLevel(logging.DEBUG)
    
    logging.info("Logging configured successfully")

# Setup logging
setup_logging()

app = FastAPI(title="Owlin API", version="1.0.0")

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.on_event("startup")
async def startup_event():
    """Initialize PaddleOCR model at FastAPI startup."""
    try:
        from backend.ocr import ocr_engine
        # Check if ocr_model attribute exists, if not, initialize it
        if not hasattr(ocr_engine, 'ocr_model') or ocr_engine.ocr_model is None:
            try:
                from paddleocr import PaddleOCR
                ocr_engine.ocr_model = PaddleOCR(use_textline_orientation=True, lang='en')
                logging.info("✅ PaddleOCR model initialized at startup")
            except Exception as e:
                logging.error(f"❌ Failed to initialize PaddleOCR at startup: {e}")
                ocr_engine.ocr_model = None
    except Exception as e:
        logging.error(f"❌ Failed to import ocr_engine at startup: {e}")

@app.get("/")
async def root():
    return {"message": "Owlin API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/health")
def api_health_check():
    return {"status": "ok"} 