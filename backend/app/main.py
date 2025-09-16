from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .deps import get_settings, cors_origins

from .routers import health
try:
    from .routers import ocr
    _HAS_OCR = True
except Exception:
    _HAS_OCR = False

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Owlin Backend")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(settings),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    if _HAS_OCR:
        app.include_router(ocr.router)

    return app

app = create_app()
