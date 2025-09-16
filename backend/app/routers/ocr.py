from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any
import mimetypes
import os
from functools import lru_cache
from ..deps import get_settings
from ocr.unified_ocr_engine import UnifiedOCREngine

router = APIRouter(prefix="/ocr", tags=["ocr"])

@lru_cache
def get_engine():
    settings = get_settings()
    return UnifiedOCREngine(lang=settings.OCR_LANG)

@router.post("/parse")
async def parse_invoice(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        content = await file.read()
        mime = file.content_type or (mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream")
        # If PDF, engine will branch by mime; we pass bytes and let PIL open
        engine = get_engine()
        result = engine.extract(content, mime=mime)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OCR failed: {e}")
