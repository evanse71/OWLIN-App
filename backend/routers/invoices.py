from __future__ import annotations
from fastapi import APIRouter, HTTPException, Body
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
import uuid

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

@router.get("")
def list_invoices():
    rows = fetch_all("SELECT id, supplier, invoice_date, status, currency FROM invoices ORDER BY ROWID DESC", ())
    out = []
    for r in rows:
        pages = fetch_all("SELECT page_no FROM invoice_pages WHERE invoice_id=? ORDER BY page_no ASC", (r["id"],))
        out.append({**dict(r), "pages":[p["page_no"] for p in pages], "page_count": len(pages)})
    return {"items": out}

@router.get("/{invoice_id}")
def get_invoice(invoice_id: str):
    inv = fetch_one("SELECT id, supplier, invoice_date, status, currency FROM invoices WHERE id=?", (invoice_id,))
    if not inv: raise HTTPException(404, "invoice not found")
    pages = fetch_all("SELECT page_no FROM invoice_pages WHERE invoice_id=? ORDER BY page_no ASC", (invoice_id,))
    return {**dict(inv), "pages":[p["page_no"] for p in pages], "page_count": len(pages)}

@router.post("/manual")
def create_manual(inv: InvoiceManualIn):
    inv_id = uuid_str()
    execute(
        "INSERT INTO invoices (id, supplier, invoice_date, status, currency, document_id, page_no, total_value) VALUES (?,?,?,?,?,?,?,?)",
        (inv_id, inv.supplier, inv.invoice_date, "manual", inv.currency, None, 0, None)
    )
    for li in inv.line_items or []:
        tot = float(li.quantity) * float(li.unit_price)
        line_id = uuid_str()
        execute("INSERT INTO invoice_line_items (id, invoice_id, description, quantity, unit_price, total, uom, vat_rate, source) VALUES (?,?,?,?,?,?,?,?,?)",
                   (line_id, inv_id, li.description, li.quantity, li.unit_price, tot, li.uom, li.vat_rate, "manual"))
    return {"id": inv_id, "status": "manual"}

@router.get("/{invoice_id}/line-items")
def get_line_items(invoice_id: str):
    rows = fetch_all("SELECT id, description, quantity, unit_price, total, uom, vat_rate, source FROM invoice_line_items WHERE invoice_id=? ORDER BY id ASC", (invoice_id,))
    return {"items": [dict(r) for r in rows]}

@router.post("/{invoice_id}/line-items")
def add_line_items(invoice_id: str, items: List[Dict[str,Any]]):
    for li in items or []:
        q = float(li.get("quantity") or 0)
        up = float(li.get("unit_price") or 0)
        execute("INSERT INTO invoice_line_items (id, invoice_id, description, quantity, unit_price, total, uom, vat_rate, source) VALUES (?,?,?,?,?,?,?,?,?)",
                   (uuid_str(), invoice_id, li.get("description"), q, up, q*up, li.get("uom"), float(li.get("vat_rate") or 0), li.get("source") or "manual"))
    return {"ok": True}

@router.post("/{invoice_id}/rescan")
def rescan_invoice(invoice_id: str):
    inv = fetch_one("SELECT document_id FROM invoices WHERE id=?", (invoice_id,))
    if not inv or not inv["document_id"]:
        raise HTTPException(400, "no source document")
    doc = fetch_one("SELECT path FROM documents WHERE id=?", (inv["document_id"],))
    if not doc: raise HTTPException(400, "document not found")
    pages = fetch_all("SELECT page_no FROM invoice_pages WHERE invoice_id=? ORDER BY page_no ASC", (invoice_id,))
    if not pages: raise HTTPException(400, "no pages recorded")

    # wipe items, rerun OCR+parse for all pages, merge
    execute("DELETE FROM invoice_line_items WHERE invoice_id=?", (invoice_id,))
    for p in pages:
        bgr = render_pdf_page_bgr(doc["path"], p["page_no"])
        ocr = UnifiedOCREngine.instance().run_ocr(bgr)
        parsed = parse_invoice_from_ocr(ocr)
        for li in parsed.get("line_items", []):
            q = float(li.get("quantity") or 0)
            up = float(li.get("unit_price") or 0)
            execute(
              "INSERT INTO invoice_line_items (id, invoice_id, description, quantity, unit_price, total, uom, vat_rate, source) VALUES (?,?,?,?,?,?,?,?,?)",
              (uuid_str(), invoice_id, li.get("description"), q, up, q*up, li.get("uom"), float(li.get("vat_rate") or 0), li.get("source") or "ocr")
            )
    return {"ok": True}

@router.put("/{invoice_id}/line-items/{line_id}")
def update_line_item(invoice_id: str, line_id: str, body: Dict[str,Any] = Body(...)):
    row = fetch_one("SELECT id FROM invoice_line_items WHERE id=? AND invoice_id=?", (line_id, invoice_id))
    if not row: raise HTTPException(404, "not found")
    q = float(body.get("quantity") or 0)
    up = float(body.get("unit_price") or 0)
    execute(
        "UPDATE invoice_line_items SET description=?, quantity=?, unit_price=?, total=?, uom=?, vat_rate=? WHERE id=? AND invoice_id=?",
        (body.get("description"), q, up, q*up, body.get("uom"), float(body.get("vat_rate") or 0), line_id, invoice_id)
    )
    return {"ok": True}

@router.delete("/{invoice_id}/line-items/{line_id}")
def delete_line_item(invoice_id: str, line_id: str):
    execute("DELETE FROM invoice_line_items WHERE id=? AND invoice_id=?", (line_id, invoice_id))
    return {"ok": True}