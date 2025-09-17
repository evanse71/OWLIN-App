from __future__ import annotations
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

try:
    from ..db import execute, fetch_one, uuid_str
except ImportError:
    try:
        from backend.db import execute, fetch_one, uuid_str
    except ImportError:
        from db import execute, fetch_one, uuid_str

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


class UploadResponse(BaseModel):
    document_id: str
    items: list  # minimal for UI progress; front-end re-fetches by id
    stored_path: str


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form(None),
) -> UploadResponse:
    """
    Accepts a PDF/IMG and creates a new 'invoices' row (or delivery note if wired).
    For now, we create a stub invoice with status='ocr' so UI can poll.
    """
    if file.content_type not in ("application/pdf", "image/png", "image/jpeg", "image/jpg"):
        raise HTTPException(status_code=415, detail="Unsupported file type")

    new_id = uuid_str()
    # Naive: store only metadata; your existing pipeline can overwrite later
    execute(
        """
        INSERT INTO invoices (id, supplier, invoice_date, status, currency, total_value, page_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (new_id, None, None, "ocr", "GBP", None, 1),
    )

    # Optionally: persist file to /data/uploads here (skipped for brevity)

    return UploadResponse(
        document_id=new_id,
        items=[{"id": new_id, "status": "ocr", "page_count": 1}],
        stored_path=f"/data/uploads/{new_id}",
    )


# Legacy compatibility endpoints (if your UI calls these older routes)
legacy_router = APIRouter(prefix="/api/upload", tags=["uploads-legacy"])


@legacy_router.post("")
async def upload_legacy(
    kind: str,
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    if kind not in ("invoice", "delivery_note"):
        raise HTTPException(status_code=400, detail="kind must be 'invoice' or 'delivery_note'")
    # Delegate to unified route
    resp = await upload_document(file=file, doc_type=kind)  # type: ignore
    return resp.dict()