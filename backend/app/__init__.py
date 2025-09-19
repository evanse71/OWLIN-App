from fastapi import APIRouter
from ..routes.invoices import router as invoices_router
from ..routes.invoices_manual import router as manual_entry_router
from ..routes.upload import router as upload_router
from ..routes.health import router as health_router

# Create the main API router
api_router = APIRouter()

# Include all the route modules
api_router.include_router(health_router)
api_router.include_router(invoices_router)
api_router.include_router(manual_entry_router)
api_router.include_router(upload_router)

