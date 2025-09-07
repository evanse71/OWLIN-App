from fastapi import APIRouter, HTTPException
import sqlite3
from db_manager_unified import get_db_manager

router = APIRouter()

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
