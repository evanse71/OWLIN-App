from fastapi import APIRouter

try:
    from ..ocr.unified_ocr_engine import UnifiedOCREngine
except ImportError:
    try:
        from backend.ocr.unified_ocr_engine import UnifiedOCREngine
    except ImportError:
        from ocr.unified_ocr_engine import UnifiedOCREngine

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("/")
def health():
    return {"status": "healthy"}

@router.get("/ocr")
def ocr_health():
    return UnifiedOCREngine.instance().health()