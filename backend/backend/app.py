
from routes.invoices_api import router as invoices_router
app.include_router(invoices_router, prefix="/api")
