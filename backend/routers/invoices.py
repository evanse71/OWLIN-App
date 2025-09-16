from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
try:
    from ..db import execute, fetch_one, fetch_all, uuid_str
    from ..ocr.unified_ocr_engine import UnifiedOCREngine
    from ..extraction.parsers.invoice_parser import parse_invoice_from_ocr
    from ..utils.pdf_to_image import render_pdf_page_bgr
except ImportError:
    from backend.db import execute, fetch_one, fetch_all, uuid_str
    from backend.ocr.unified_ocr_engine import UnifiedOCREngine
    from backend.extraction.parsers.invoice_parser import parse_invoice_from_ocr
    from backend.utils.pdf_to_image import render_pdf_page_bgr

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

class InvoiceLineItemIn(BaseModel):
    description: Optional[str] = None
    quantity: float = 0
    unit_price: float = 0
    uom: Optional[str] = None
    vat_rate: float = 0

class InvoiceManualIn(BaseModel):
    supplier: str
    invoice_date: Optional[str] = None
    reference: Optional[str] = None
    currency: Optional[str] = "GBP"
    line_items: Optional[List[InvoiceLineItemIn]] = None

@router.post("/manual")
def create_manual(inv: InvoiceManualIn):
    inv_id = uuid_str()
    execute(
        "INSERT INTO invoices (id, supplier, invoice_date, status, currency, document_id, page_no, total_value) VALUES (?,?,?,?,?,?,?,?)",
        (inv_id, inv.supplier, inv.invoice_date, "manual", inv.currency, None, 0, None)
    )
    for li in inv.line_items or []:
        tot = float(li.quantity) * float(li.unit_price)
        execute("INSERT INTO invoice_line_items (invoice_id, description, quantity, unit_price, total, uom, vat_rate, source) VALUES (?,?,?,?,?,?,?,?)",
                   (inv_id, li.description, li.quantity, li.unit_price, tot, li.uom, li.vat_rate, "manual"))
    return {"id": inv_id, "status": "manual"}

@router.get("/{invoice_id}/line-items")
def get_items(invoice_id: str):
    rows = fetch_all("SELECT id, description, quantity, unit_price, total, uom, vat_rate, source FROM invoice_line_items WHERE invoice_id=? ORDER BY id ASC", (invoice_id,))
    return {"items": rows}

@router.post("/{invoice_id}/line-items")
def add_items(invoice_id: str, items: List[InvoiceLineItemIn]):
    for li in items or []:
        tot = float(li.quantity) * float(li.unit_price)
        execute("INSERT INTO invoice_line_items (invoice_id, description, quantity, unit_price, total, uom, vat_rate, source) VALUES (?,?,?,?,?,?,?,?)",
                   (invoice_id, li.description, li.quantity, li.unit_price, tot, li.uom, li.vat_rate, "manual"))
    return {"ok": True}

@router.post("/{invoice_id}/rescan")
def rescan(invoice_id: str):
    inv = fetch_one("SELECT document_id, page_no FROM invoices WHERE id=?", (invoice_id,))
    if not inv or not inv["document_id"]:
        raise HTTPException(400, "No source document for this invoice")
    doc = fetch_one("SELECT path FROM documents WHERE id=?", (inv["document_id"],))
    if not doc: raise HTTPException(400, "Document not found")
    img_bgr = render_pdf_page_bgr(doc["path"], inv["page_no"] or 0)
    ocr = UnifiedOCREngine.instance().run_ocr(img_bgr)
    parsed = parse_invoice_from_ocr(ocr)
    execute("DELETE FROM invoice_line_items WHERE invoice_id=?", (invoice_id,))
    for li in parsed.get("line_items", []):
        qty = float(li.get("quantity") or 0)
        up  = float(li.get("unit_price") or 0)
        tot = qty * up
        execute("INSERT INTO invoice_line_items (invoice_id, description, quantity, unit_price, total, uom, vat_rate, source) VALUES (?,?,?,?,?,?,?,?)",
                   (invoice_id, li.get("description"), qty, up, tot, li.get("uom"), li.get("vat_rate") or 0, "ocr"))
    return {"ok": True}