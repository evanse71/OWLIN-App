# backend/api/ocr_router.py
from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import uuid
import logging
import os
from typing import Any, Dict
from backend.config import env_bool, OCR_ARTIFACT_ROOT

logger = logging.getLogger("owlin.api.ocr")
router = APIRouter(prefix="/api/ocr", tags=["ocr"])

def _safe_save_upload(tmp_dir: Path, up: UploadFile) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    # keep original extension to benefit PyMuPDF/pdf identity
    suffix = Path(up.filename or "upload.pdf").suffix or ".pdf"
    dest = tmp_dir / f"upload_{uuid.uuid4().hex}{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(up.file, f)
    return dest

@router.post("/run")
async def ocr_run(file: UploadFile = File(...)) -> JSONResponse:
    """
    Run OCR on the uploaded PDF/image.

    If FEATURE_OCR_PIPELINE_V2=false (default), return a placeholder response
    confirming the feature is disabled, so existing behavior remains unchanged.
    """
    if not env_bool("FEATURE_OCR_PIPELINE_V2", False):
        return JSONResponse(
            {
                "status": "disabled",
                "message": "New OCR pipeline (v2) is disabled by feature flag.",
                "flag": "FEATURE_OCR_PIPELINE_V2",
            },
            status_code=200,
        )

    # Save upload to a temp workspace under OCR_ARTIFACT_ROOT/tmp
    try:
        tmp_dir = Path(OCR_ARTIFACT_ROOT) / "tmp"
        saved = _safe_save_upload(tmp_dir, file)
    except Exception as e:
        logger.exception("Failed to save upload")
        raise HTTPException(status_code=500, detail=f"Upload save failed: {e}")

    # Import lazily to keep cold-start cheap
    try:
        from backend.ocr.owlin_scan_pipeline import process_document
    except Exception as e:
        logger.exception("OCR pipeline import failed")
        raise HTTPException(status_code=500, detail=f"OCR pipeline unavailable: {e}")

    try:
        result: Dict[str, Any] = process_document(saved)
        # Attach a trace id for logs
        result.setdefault("trace_id", uuid.uuid4().hex)
        result.setdefault("feature", "v2")
        return JSONResponse(result, status_code=200)
    except Exception as e:
        logger.exception("OCR processing failed")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {e}")


