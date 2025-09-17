from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from typing import List, Dict, Any, Optional
import os, uuid, json
import numpy as np, cv2, pypdfium2 as pdfium

from ..ocr.unified_ocr_engine import UnifiedOCREngine
from ..extraction.parsers.invoice_parser import parse_invoice_from_ocr
from ..extraction.grouping import group_pages
from ..utils.pdf_to_image import render_pdf_page_bgr
from ..db import db

router = APIRouter(prefix="/api/uploads", tags=["uploads"])
legacy = APIRouter(prefix="/api/upload", tags=["uploads-legacy"])

UPLOAD_DIR = os.path.join("data","uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_IMG = {"image/png","image/jpeg","image/jpg"}
ALLOWED_PDF = {"application/pdf"}

def _save(pathlike: UploadFile) -> str:
    ext = os.path.splitext(pathlike.filename or "")[1]
    fname = f"{uuid.uuid4()}{ext}"
    out = os.path.join(UPLOAD_DIR, fname)
    with open(out, "wb") as w: w.write(pathlike.file.read())
    return out

def _persist_document(path: str) -> str:
    doc_id = str(uuid.uuid4())
    db.execute("INSERT INTO documents (id, path) VALUES (?,?)", (doc_id, path))
    return doc_id

def _ocr_page(img_bgr) -> Dict[str, Any]:
    ocr = UnifiedOCREngine.instance().run_ocr(img_bgr)
    # stash raw lines for grouping
    ocr["raw_lines"] = ocr.get("lines", [])
    return ocr

def _pdf_pages(path: str) -> List[int]:
    pdf = pdfium.PdfDocument(path)
    n = len(pdf)
    pdf.close()
    return list(range(n))

def _parse_and_group(path: str, doc_type: Optional[str]) -> List[Dict[str,Any]]:
    # 1) OCR every page
    pages = _pdf_pages(path)
    parsed_pages: List[Dict[str,Any]] = []
    for i in pages:
        bgr = render_pdf_page_bgr(path, i)
        ocr = _ocr_page(bgr)
        parsed = parse_invoice_from_ocr(ocr)
        parsed["raw_lines"] = ocr.get("lines", [])
        parsed_pages.append({"page_index": i, "parse": parsed})
    # 2) Group pages into invoices
    groups = group_pages(parsed_pages)  # e.g., [[4,5,7],[6],...]
    out: List[Dict[str,Any]] = []
    doc_id = None
    return_groups = []
    return_groups = groups
    return return_groups

def _persist_invoice_group(path: str, document_id: str, pages: List[int], page_parses: List[Dict[str,Any]]) -> Dict[str,Any]:
    """Create one invoice from multiple pages; merge line items and fields."""
    inv_id = str(uuid.uuid4())
    # merge fields (prefer first non-empty)
    supplier = next((p.get("supplier") for p in page_parses if p.get("supplier")), None)
    inv_date = next((p.get("invoice_date") for p in page_parses if p.get("invoice_date")), None)
    reference = next((p.get("reference") for p in page_parses if p.get("reference")), None)
    currency = next((p.get("currency") for p in page_parses if p.get("currency")), "GBP")
    db.execute(
        "INSERT INTO invoices (id, supplier, invoice_date, status, currency, document_id, page_no, total_value) VALUES (?,?,?,?,?,?,?,?)",
        (inv_id, supplier, inv_date, "scanned", currency, document_id, pages[0], None)
    )
    # pages table
    for idx in pages:
        db.execute("INSERT INTO invoice_pages (id, invoice_id, page_no, ocr_json) VALUES (?,?,?,?)",
                   (str(uuid.uuid4()), inv_id, idx, None))
    # merge line items: concat all, compute totals server-side
    for p in page_parses:
        for li in p.get("line_items", []):
            q = float(li.get("quantity") or 0)
            up = float(li.get("unit_price") or 0)
            tot = q * up
            db.execute(
              "INSERT INTO invoice_line_items (id, invoice_id, description, quantity, unit_price, total, uom, vat_rate, source) VALUES (?,?,?,?,?,?,?,?,?)",
              (str(uuid.uuid4()), inv_id, li.get("description"), q, up, tot, li.get("uom"), float(li.get("vat_rate") or 0), li.get("source") or "ocr")
            )
    return {"type":"invoice","id":inv_id,"pages":pages,"page_count":len(pages)}

@router.post("")
async def upload(file: UploadFile = File(...), doc_type: Optional[str] = Form(None), kind: Optional[str] = Query(None)):
    # Save & content-type gate
    path = _save(file)
    ctype = (file.content_type or "").lower()
    if not (ctype in ALLOWED_PDF or path.lower().endswith(".pdf") or ctype in ALLOWED_IMG or any(path.lower().endswith(e) for e in [".png",".jpg",".jpeg"])):
        raise HTTPException(415, f"Unsupported file type: {ctype or os.path.splitext(path)[1]}")

    document_id = _persist_document(path)
    items: List[Dict[str,Any]] = []

    if ctype in ALLOWED_PDF or path.lower().endswith(".pdf"):
        # PDF → OCR each page → group → persist per-invoice
        # Collect parses per page
        pages = _pdf_pages(path)
        per_page_parses = []
        for i in pages:
            bgr = render_pdf_page_bgr(path, i)
            ocr = _ocr_page(bgr)
            parsed = parse_invoice_from_ocr(ocr)
            parsed["raw_lines"] = ocr.get("lines", [])
            per_page_parses.append({"page_index": i, "parse": parsed})

        # Group into invoices
        groups = group_pages(per_page_parses)

        # Persist per-group (invoice)
        for grp in groups:
            grp_parses = [pp["parse"] for pp in per_page_parses if pp["page_index"] in grp]
            item = _persist_invoice_group(path, document_id, grp, grp_parses)
            items.append(item)
    else:
        # Single image → one invoice
        bgr = cv2.imdecode(np.frombuffer(open(path, "rb").read(), dtype=np.uint8), cv2.IMREAD_COLOR)
        ocr = _ocr_page(bgr)
        parsed = parse_invoice_from_ocr(ocr)
        inv = _persist_invoice_group(path, document_id, [0], [parsed])
        items.append(inv)

    return {"document_id": document_id, "items": items, "stored_path": path}

@legacy.post("")
async def upload_legacy(file: UploadFile = File(...), kind: Optional[str] = Query(None)):
    return await upload(file=file, doc_type=None, kind=kind)