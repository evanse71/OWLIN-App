from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import invoices, flagged_issues, suppliers, analytics, ocr, products
from backend.routes import upload_fixed

app = FastAPI(title="Owlin API", version="1.0.0")

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route modules
app.include_router(upload_fixed.router, prefix="/api")
app.include_router(invoices.router, prefix="/api")
app.include_router(flagged_issues.router, prefix="/api")
app.include_router(suppliers.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(ocr.router, prefix="/api")
app.include_router(products.router, prefix="/api/products")

@app.get("/")
async def root():
    return {"message": "Owlin API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/health")
def api_health_check():
    return {"status": "ok"} 