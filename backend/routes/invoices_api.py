from fastapi import APIRouter, HTTPException
import sqlite3
from db_manager_unified import get_db_manager
from uuid import uuid4

router = APIRouter()

@router.get("/invoices")
def list_invoices():
    """List all invoices with status and filename"""
    try:
        conn = sqlite3.connect("data/owlin.db")
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT i.id, i.document_id, i.supplier, i.invoice_date, i.total_value,
                   i.matched_delivery_note_id, i.status, d.path AS filename
            FROM invoices i
            LEFT JOIN documents d ON d.id = i.document_id
            ORDER BY COALESCE(i.invoice_date,'1970-01-01') DESC
        """).fetchall()
        conn.close()
        return {"items": [dict(r) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    m = get_db_manager()
    conn = sqlite3.connect(m.db_path)
    conn.row_factory = sqlite3.Row
    try:
        inv = conn.execute(
            "SELECT id, currency, total_amount_pennies, ocr_avg_conf, ocr_min_conf "
            "FROM invoices WHERE id = ?",
            (invoice_id,)
        ).fetchone()
        if not inv:
            raise HTTPException(status_code=404, detail="invoice not found")

        rows = conn.execute(
            "SELECT description, quantity, unit_price_pennies, line_total_pennies "
            "FROM invoice_line_items WHERE invoice_id = ? ORDER BY row_idx",
            (invoice_id,)
        ).fetchall()

        meta = {
            "supplier": None,
            "invoice_no": None,
            "date_iso": None,
            "currency": inv["currency"] if "currency" in inv.keys() else "GBP",
            "ocr_avg_conf": inv["ocr_avg_conf"],
            "ocr_min_conf": inv["ocr_min_conf"],
            "total_inc": (inv["total_amount_pennies"] or 0) / 100.0,
        }

        lines = []
        for r in rows:
            lines.append({
                "desc": r["description"],
                "qty": float(r["quantity"]) if r["quantity"] is not None else None,
                "unit_price": (r["unit_price_pennies"] or 0) / 100.0,
                "line_total": (r["line_total_pennies"] or 0) / 100.0,
                "flags": [],
            })

        return {"id": inv["id"], "meta": meta, "lines": lines}
    finally:
        conn.close()

@router.get("/invoices/{invoice_id}/line-items")
def invoice_lines(invoice_id: str):
    """Get line items for an invoice"""
    try:
        conn = sqlite3.connect("data/owlin.db")
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT description, qty, unit_price, total
            FROM invoice_line_items
            WHERE invoice_id=? ORDER BY rowid
        """, (invoice_id,)).fetchall()
        conn.close()
        return {"items": [dict(r) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/invoices/manual")
def create_manual_invoice(body: dict):
    """Create manual invoice"""
    try:
        conn = sqlite3.connect("data/owlin.db")
        cursor = conn.cursor()
        inv_id = str(uuid4())
        cursor.execute("""
            INSERT INTO invoices (id, file_id, supplier_name, invoice_date, total_amount, status, upload_timestamp)
            VALUES (?, NULL, ?, ?, ?, 'manual', datetime('now'))
        """, (inv_id, body.get("supplier") or "Unknown", body.get("invoice_date"), body.get("total_value")))
        conn.commit()
        conn.close()
        return {"id": inv_id, "status": "manual"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
