from __future__ import annotations
from typing import Dict, Any, Optional, List
import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

try:
    from ..db import execute, fetch_one, uuid_str
    from ..extraction.parsers import invoice_parser
    from ..services.enhanced_pairing import auto_pair_enhanced
    from ..services.document_classifier import classify_document_text, save_classification_result
except ImportError:
    try:
        from backend.db import execute, fetch_one, uuid_str
        from backend.extraction.parsers import invoice_parser
        from backend.services.enhanced_pairing import auto_pair_enhanced
        from backend.services.document_classifier import classify_document_text, save_classification_result
    except ImportError:
        from db import execute, fetch_one, uuid_str
        from extraction.parsers import invoice_parser
        from services.enhanced_pairing import auto_pair_enhanced
        from services.document_classifier import classify_document_text, save_classification_result

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


class UploadResponse(BaseModel):
    document_id: str
    items: list  # minimal for UI progress; front-end re-fetches by id
    stored_path: str


def process_upload(upload_id: int, file_path: str) -> None:
    """
    Process uploaded document with OCR, annotation detection, and pairing.
    
    Args:
        upload_id: ID of the uploaded file
        file_path: Path to the uploaded file
    """
    import sqlite3
    
    # Connect to database
    db = sqlite3.connect('data/owlin.db')
    cursor = db.cursor()
    
    try:
        # Update progress
        cursor.execute(
            "UPDATE uploaded_files SET status = 'processing' WHERE id = ?",
            (upload_id,)
        )
        db.commit()
        
        # Convert PDF to images (simplified - in production use proper PDF processing)
        images = []
        if file_path.lower().endswith('.pdf'):
            # For now, assume single page PDF converted to image
            # In production, this would use pypdfium2 or similar
            images = [file_path.replace('.pdf', '.png')]
        else:
            images = [file_path]
        
        # OCR and accumulate words and detect annotations across pages
        all_words: List[Dict[str, Any]] = []
        page_annotations: List[Dict[str, Any]] = []
        
        for img_path in images:
            # Simulate OCR processing
            ocr_result = {'words': []}  # In production, this would be real OCR
            all_words.extend(ocr_result['words'])
            
            # Detect annotations on this page
            anns = invoice_parser.detect_annotations(img_path)
            if anns:
                page_annotations.extend(anns)
        
        # Parse invoice from OCR words
        parsed = invoice_parser.parse_invoice_from_ocr({'lines': all_words})
        
        # Insert invoice record
        cursor.execute(
            """
            INSERT INTO invoices (
                supplier, invoice_date, invoice_number, status, 
                currency, total_value, page_count, source_file_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                parsed['supplier'],
                parsed['invoice_date'],
                parsed['reference'],
                'parsed',
                parsed['currency'],
                parsed['total_value'],
                len(images),
                upload_id
            )
        )
        
        invoice_id = cursor.lastrowid
        
        # If this document is a delivery note, also insert into delivery_notes
        if parsed.get('doc_type') == 'DELIVERY_NOTE':
            cursor.execute(
                """
                INSERT INTO delivery_notes (
                    source_file_id, supplier, dn_date, reference, status
                ) VALUES (?, ?, ?, ?, 'parsed')
                """,
                (
                    upload_id,
                    parsed['supplier'],
                    parsed['invoice_date'],
                    parsed['reference'],
                ),
            )
        
        # Insert line items
        for item in parsed.get('line_items', []):
            cursor.execute(
                """
                INSERT INTO line_items (
                    invoice_id, description, quantity, unit_price, uom, vat_rate
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    item.get('description'),
                    item.get('quantity'),
                    item.get('unit_price'),
                    item.get('uom'),
                    item.get('vat_rate', 0)
                )
            )
        
        # Insert annotations for this invoice
        if page_annotations:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
            for ann in page_annotations:
                cursor.execute(
                    """
                    INSERT INTO annotations (
                        invoice_id, line_item_id, kind, text, x, y, w, h, confidence, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        invoice_id,
                        ann.get('line_item_id'),
                        ann.get('kind'),
                        ann.get('text'),
                        ann.get('x'),
                        ann.get('y'),
                        ann.get('w'),
                        ann.get('h'),
                        ann.get('confidence'),
                        now,
                    ),
                )
        
        db.commit()
        
        # Perform enhanced pairing between invoices and delivery notes
        try:
            auto_pair_enhanced(db)
        except Exception:
            # Pairing should not block completion; continue silently on error
            pass
        
        # Update final status
        cursor.execute(
            "UPDATE uploaded_files SET status = 'complete' WHERE id = ?",
            (upload_id,)
        )
        db.commit()
        
    except Exception as e:
        # Handle errors
        cursor.execute(
            "UPDATE uploaded_files SET status = 'error' WHERE id = ?",
            (upload_id,)
        )
        db.commit()
        raise e
    finally:
        db.close()


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