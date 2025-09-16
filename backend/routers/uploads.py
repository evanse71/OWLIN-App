from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from typing import List, Dict, Any, Optional
import os, uuid
import fitz
import numpy as np
import cv2
import json

try:
    from ..ocr.unified_ocr_engine import UnifiedOCREngine
    from ..extraction.parsers.invoice_parser import parse_invoice_from_ocr
    from ..db import execute, fetch_one, fetch_all, uuid_str
except ImportError:
    from backend.ocr.unified_ocr_engine import UnifiedOCREngine
    from backend.extraction.parsers.invoice_parser import parse_invoice_from_ocr
    from backend.db import execute, fetch_one, fetch_all, uuid_str

router = APIRouter(prefix="/api/uploads", tags=["uploads"])
legacy = APIRouter(prefix="/api/upload", tags=["uploads-legacy"])

UPLOAD_DIR = os.path.join("data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMG = {"image/png","image/jpeg","image/jpg"}
ALLOWED_PDF = {"application/pdf"}

def _save_to_disk(f: UploadFile) -> str:
    ext = os.path.splitext(f.filename or "")[1]
    doc_id = str(uuid.uuid4())
    fname = f"{doc_id}{ext}"
    out_path = os.path.join(UPLOAD_DIR, fname)
    with open(out_path, "wb") as w:
        w.write(f.file.read())
    return out_path

def _pdf_to_bgr_list(pdf_path: str) -> List[np.ndarray]:
    pages = []
    doc = fitz.open(pdf_path)
    for i in range(doc.page_count):
        page = doc.load_page(i)
        pix = page.get_pixmap(alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        pages.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    doc.close()
    return pages

def _decode_img(path: str) -> np.ndarray:
    with open(path, "rb") as r:
        arr = np.frombuffer(r.read(), dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Failed to decode image")
    return img

def _guess_kind(texts: List[str], fallback: Optional[str]) -> str:
    if fallback: return fallback
    j = " ".join(t.lower() for t in texts if t)
    if "delivery note" in j or "goods received" in j or "grn" in j:
        return "delivery_note"
    if "invoice" in j:
        return "invoice"
    return "unknown"

def _persist_doc(path: str) -> str:
    doc_id = uuid_str()
    execute("INSERT INTO documents (id, path) VALUES (?,?)", (doc_id, path))
    return doc_id

def _persist_invoice(parsed: Dict[str,Any], document_id: str, page_no: int) -> str:
    inv_id = uuid_str()
    execute(
        "INSERT INTO invoices (id, supplier, invoice_date, status, currency, document_id, page_no, total_value) VALUES (?,?,?,?,?,?,?,?)",
        (inv_id, parsed.get("supplier"), parsed.get("invoice_date"), "scanned", parsed.get("currency","GBP"), document_id, page_no, None)
    )
    for li in parsed.get("line_items", []):
        qty = float(li.get("quantity") or 0.0)
        up  = float(li.get("unit_price") or 0.0)
        tot = qty * up
        execute(
          "INSERT INTO invoice_line_items (invoice_id, description, quantity, unit_price, total, uom, vat_rate, source) VALUES (?,?,?,?,?,?,?,?)",
          (inv_id, li.get("description"), qty, up, tot, li.get("uom"), li.get("vat_rate") or 0, "ocr")
        )
    return inv_id

def _persist_dn(parsed: Dict[str,Any], document_id: str, page_no: int) -> str:
    dn_id = uuid_str()
    execute(
        "INSERT INTO delivery_notes (id, supplier, note_date, status, document_id, page_no, total_amount) VALUES (?,?,?,?,?,?,?)",
        (dn_id, parsed.get("supplier"), parsed.get("invoice_date"), "scanned", document_id, page_no, None)
    )
    return dn_id

def _create_job(total_pages: int, document_id: str, kind: Optional[str]) -> str:
    job_id = uuid_str()
    execute(
        "INSERT INTO processing_jobs (id, kind, status, current_page, total_pages, message, created_ids, document_id) VALUES (?,?,?,?,?,?,?,?)",
        (job_id, kind or "unknown", "queued", 0, total_pages, "Queued", json.dumps([]), document_id)
    )
    return job_id

def _update_job(job_id: str, **fields):
    cols = ", ".join([f"{k}=?" for k in fields.keys()])
    vals = list(fields.values())
    vals.append(job_id)
    execute(f"UPDATE processing_jobs SET {cols} WHERE id=?", tuple(vals))

@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    row = fetch_one("SELECT * FROM processing_jobs WHERE id=?", (job_id,))
    if not row: raise HTTPException(404, "job not found")
    return dict(row)

def _process_pages(job_id: str, pages: List[np.ndarray], doc_type: Optional[str], document_id: str) -> List[Dict[str,Any]]:
    engine = UnifiedOCREngine.instance()
    created = []
    _update_job(job_id, status="processing", message="OCR running", current_page=0)
    for idx, bgr in enumerate(pages):
        _update_job(job_id, current_page=idx, message=f"OCR page {idx+1}")
        ocr = engine.run_ocr(bgr)
        texts = [l.get("text","") for l in ocr.get("lines",[])]
        inferred = _guess_kind(texts, doc_type)
        parsed = parse_invoice_from_ocr(ocr)
        if inferred == "invoice":
            eid = _persist_invoice(parsed, document_id, idx)
            created.append({"type":"invoice","id":eid,"page":idx})
        elif inferred == "delivery_note":
            eid = _persist_dn(parsed, document_id, idx)
            created.append({"type":"delivery_note","id":eid,"page":idx})
        else:
            created.append({"type":"unknown","id":None,"page":idx})
    _update_job(job_id, status="persisted", message="Entities saved", created_ids=json.dumps(created))
    _update_job(job_id, status="done", message="Complete")
    return created

@router.post("")
async def upload(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form(None),
    kind: Optional[str] = Query(None)
):
    path = _save_to_disk(file)
    doc_id = _persist_doc(path)
    ctype = (file.content_type or "").lower()

    # pages
    if ctype in ALLOWED_PDF or path.lower().endswith(".pdf"):
        pages = _pdf_to_bgr_list(path)
    elif ctype in ALLOWED_IMG or any(path.lower().endswith(ext) for ext in [".png",".jpg",".jpeg"]):
        pages = [_decode_img(path)]
    else:
        raise HTTPException(415, f"Unsupported file type: {ctype or os.path.splitext(path)[1]}")

    job_id = _create_job(len(pages), doc_id, doc_type or kind)
    # process inline (simple) so we don't introduce a new worker system
    created = _process_pages(job_id, pages, doc_type or kind, doc_id)
    return {"job_id": job_id, "document_id": doc_id, "items": created, "stored_path": path}

# legacy shim: POST /api/upload?kind=invoice
@legacy.post("")
async def upload_legacy(file: UploadFile = File(...), kind: Optional[str] = Query(None)):
    return await upload(file=file, doc_type=None, kind=kind)