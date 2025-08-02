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
def startup_event():
    """Preload OCR models at FastAPI startup to prevent first-upload delays."""
    import threading
    
    def preload_models():
        try:
            import time
            logging.info("🔄 Preloading OCR models at startup...")
            start_time = time.time()
            
            # Import and preload PaddleOCR model
            from backend.upload_pipeline import get_paddle_ocr_model
            
            # Run model initialization
            get_paddle_ocr_model()
            
            elapsed_time = time.time() - start_time
            logging.info(f"✅ OCR models preloaded successfully in {elapsed_time:.2f} seconds")
            
            # Also initialize Tesseract availability check
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                logging.info("✅ Tesseract fallback available")
            except Exception as e:
                logging.warning(f"⚠️ Tesseract not available: {e}")
                
        except Exception as e:
            logging.error(f"❌ Failed to preload OCR models at startup: {e}")
            logging.error("⚠️ First upload may experience delays due to model loading")
    
    # Run in background thread to avoid blocking startup
    thread = threading.Thread(target=preload_models, daemon=True)
    thread.start()

@app.get("/")
async def root():
    return {"message": "Owlin API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/health")
def api_health_check():
    return {"status": "ok"} 