from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes import invoices, flagged_issues, suppliers, analytics, ocr, products
from backend.routes import document_queue, upload_review, confirm_splits
from backend import upload_fixed
from backend.routes import dev
import os

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

# ✅ Include dev routes only in development
if os.getenv('NODE_ENV') == 'development' or os.getenv('ENVIRONMENT') == 'development':
    app.include_router(dev.router, prefix="/api/dev", tags=["development"])

@app.get("/")
async def root():
    return {"message": "Owlin API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/health")
def api_health_check():
    return {"status": "ok"} 