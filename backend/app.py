# backend/app.py
from fastapi import APIRouter
# Import routers via absolute paths; they must not open DB/files at import time
from backend.routers.manual_entry import router as manual_entry_router

api_router = APIRouter()
api_router.include_router(manual_entry_router, prefix="/manual", tags=["manual"])

# Add more routers as needed
# api_router.include_router(invoices_router, prefix="/invoices", tags=["invoices"])
# api_router.include_router(suppliers_router, prefix="/suppliers", tags=["suppliers"])