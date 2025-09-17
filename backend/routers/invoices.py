from __future__ import annotations
from fastapi import APIRouter, HTTPException, Body, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import io
try:
    from ..db import execute, fetch_one, fetch_all, uuid_str
    from ..ocr.unified_ocr_engine import UnifiedOCREngine
    from ..extraction.parsers.invoice_parser import parse_invoice_from_ocr
    from ..utils.pdf_to_image import render_pdf_page_bgr
    from ..services.audit import write_audit
    from ..services.recompute import recompute_invoice_totals
except ImportError:
    try:
        from backend.db import execute, fetch_one, fetch_all, uuid_str
        from backend.ocr.unified_ocr_engine import UnifiedOCREngine
        from backend.extraction.parsers.invoice_parser import parse_invoice_from_ocr
        from backend.utils.pdf_to_image import render_pdf_page_bgr
        from backend.services.audit import write_audit
        from backend.services.recompute import recompute_invoice_totals
    except ImportError:
        from db import execute, fetch_one, fetch_all, uuid_str
        from ocr.unified_ocr_engine import UnifiedOCREngine
        from extraction.parsers.invoice_parser import parse_invoice_from_ocr
        from utils.pdf_to_image import render_pdf_page_bgr
        from services.audit import write_audit
        from services.recompute import recompute_invoice_totals
import uuid
import cv2

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
    rows = fetch_all("""
        SELECT
          i.id, i.supplier, i.invoice_date, i.status, i.currency, i.total_value,
          GROUP_CONCAT(ip.page_no) AS pages_csv,
          COUNT(ip.id) AS page_count
        FROM invoices i
        LEFT JOIN invoice_pages ip ON ip.invoice_id = i.id
        GROUP BY i.id
        ORDER BY i.rowid DESC
    """)
    
    items = []
    for r in rows:
        pages = []
        if r.get("pages_csv"):
            pages = sorted({int(x) for x in r["pages_csv"].split(",") if x != ""})
        items.append({
            "id": r["id"],
            "supplier": r.get("supplier") or "Unknown",
            "invoice_date": r.get("invoice_date"),
            "status": r.get("status"),
            "currency": r.get("currency") or "GBP",
            "total_value": r.get("total_value"),
            "pages": pages,
            "page_count": int(r.get("page_count") or 0),
        })
    return {"items": items}

@router.get("/{invoice_id}")
def get_invoice(invoice_id: str):
    inv = fetch_one("SELECT id, supplier, invoice_date, status, currency, total_value FROM invoices WHERE id=?", (invoice_id,))
    if not inv: raise HTTPException(404, "invoice not found")
    pages = fetch_all("SELECT page_no FROM invoice_pages WHERE invoice_id=? ORDER BY page_no ASC", (invoice_id,))
    
    # Safeguard: ensure pages are always returned
    page_nos = [p["page_no"] for p in pages] if pages else [0]
    
    return {
        **dict(inv), 
        "pages": page_nos, 
        "page_count": len(page_nos)
    }

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
    
    # Recompute totals and log audit
    recompute_invoice_totals(invoice_id)
    write_audit(
        actor="system",  # TODO: Get from auth context
        action="ADD_LINE_ITEMS",
        meta={"invoice_id": invoice_id, "item_count": len(items)},
        resource_type="invoice",
        resource_id=invoice_id
    )
    
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
    # Recompute total after rescan
    recompute_invoice_totals(invoice_id)
    write_audit(
        actor="system",  # TODO: Get from auth context
        action="RESCAN_INVOICE",
        meta={"invoice_id": invoice_id, "page_count": len(pages)},
        resource_type="invoice",
        resource_id=invoice_id
    )
    return {"ok": True}

def _recompute_invoice_total(invoice_id: str):
    """Recompute and persist total_value from line items if currently null."""
    # Get current total_value
    inv = fetch_one("SELECT total_value FROM invoices WHERE id=?", (invoice_id,))
    if not inv: return
    
    # Only update if total_value is null
    if inv.get("total_value") is not None: return
    
    # Compute subtotal from line items
    items = fetch_all("SELECT quantity, unit_price FROM invoice_line_items WHERE invoice_id=?", (invoice_id,))
    subtotal = sum(float(item.get("quantity") or 0) * float(item.get("unit_price") or 0) for item in items)
    
    # Update if we have a meaningful total
    if subtotal > 0:
        execute("UPDATE invoices SET total_value=? WHERE id=?", (subtotal, invoice_id))

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
    # Recompute total after line item update
    recompute_invoice_totals(invoice_id)
    write_audit(
        actor="system",  # TODO: Get from auth context
        action="UPDATE_LINE_ITEM",
        meta={"invoice_id": invoice_id, "line_id": line_id, "changes": body},
        resource_type="invoice",
        resource_id=invoice_id
    )
    return {"ok": True}

@router.delete("/{invoice_id}/line-items/{line_id}")
def delete_line_item(invoice_id: str, line_id: str):
    execute("DELETE FROM invoice_line_items WHERE id=? AND invoice_id=?", (line_id, invoice_id))
    # Recompute total after line item deletion
    recompute_invoice_totals(invoice_id)
    write_audit(
        actor="system",  # TODO: Get from auth context
        action="DELETE_LINE_ITEM",
        meta={"invoice_id": invoice_id, "line_id": line_id},
        resource_type="invoice",
        resource_id=invoice_id
    )
    return {"ok": True}

@router.get("/{invoice_id}/pages/{page_no}/thumb")
def get_page_thumbnail(invoice_id: str, page_no: int):
    # Get the document path for this invoice
    inv = fetch_one("SELECT document_id FROM invoices WHERE id=?", (invoice_id,))
    if not inv or not inv["document_id"]:
        raise HTTPException(404, "invoice or document not found")
    
    doc = fetch_one("SELECT path FROM documents WHERE id=?", (inv["document_id"],))
    if not doc:
        raise HTTPException(404, "document not found")
    
    try:
        # Render the page as BGR image
        bgr = render_pdf_page_bgr(doc["path"], page_no)
        if bgr is None:
            raise HTTPException(404, "page not found")
        
        # Resize to ~300px width while maintaining aspect ratio
        height, width = bgr.shape[:2]
        target_width = 300
        target_height = int((target_width * height) / width)
        resized = cv2.resize(bgr, (target_width, target_height))
        
        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Encode as PNG
        _, buffer = cv2.imencode('.png', rgb)
        img_bytes = buffer.tobytes()
        
        return StreamingResponse(
            io.BytesIO(img_bytes),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        # Log the error and return a placeholder
        print(f"Thumbnail generation failed for {invoice_id} page {page_no}: {e}")
        raise HTTPException(404, "thumbnail generation failed")