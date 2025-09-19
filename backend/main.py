# backend/main.py
from __future__ import annotations
import os
import sys
from pathlib import Path

# --- Make backend importable whether run from repo root OR /backend ---
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Robust router imports (work both ways)
try:
    from backend.routers.health import router as health_router
    from backend.routers.invoices import router as invoices_router
    from backend.routers.uploads import (
        router as uploads_router,
        legacy_router as uploads_legacy_router,
    )
    from backend.routers.pairing import (
        router as pairing_router,
        dn_router as pairing_dn_router,
    )
    from backend.routers.annotations import router as annotations_router
    from backend.routers.pairings import router as pairings_router
except ImportError:
    from routers.health import router as health_router
    from routers.invoices import router as invoices_router
    from routers.uploads import (
        router as uploads_router,
        legacy_router as uploads_legacy_router,
    )
    from routers.pairing import router as pairing_router, dn_router as pairing_dn_router
    from routers.annotations import router as annotations_router
    from routers.pairings import router as pairings_router

app = FastAPI(title="Owlin Backend", version="0.1.0")

# CORS wide open for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers (order: health first)
app.include_router(health_router)
app.include_router(invoices_router)
app.include_router(uploads_router)
app.include_router(uploads_legacy_router)
app.include_router(pairing_router)
app.include_router(pairing_dn_router)
app.include_router(annotations_router)
app.include_router(pairings_router)


@app.get("/")
def root():
    return {"status": "ok", "service": "owlin-backend"}