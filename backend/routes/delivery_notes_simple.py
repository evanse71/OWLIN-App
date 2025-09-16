from fastapi import APIRouter, HTTPException
import sqlite3
from uuid import uuid4

router = APIRouter()

@router.get("/delivery-notes")
def list_dns():
    """List all delivery notes with filename"""
    try:
        conn = sqlite3.connect("data/owlin.db")
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT dn.id, dn.document_id, dn.supplier,
                   dn.delivery_date AS note_date, d.path AS filename
            FROM delivery_notes dn
            LEFT JOIN documents d ON d.id = dn.document_id
            ORDER BY COALESCE(dn.delivery_date,'1970-01-01') DESC
        """).fetchall()
        conn.close()
        return {"items": [dict(r) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/delivery-notes/{dn_id}/line-items")
def dn_lines(dn_id: str):
    """Get line items for a delivery note"""
    try:
        conn = sqlite3.connect("data/owlin.db")
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT description, qty
            FROM delivery_note_line_items
            WHERE delivery_note_id=? ORDER BY rowid
        """, (dn_id,)).fetchall()
        conn.close()
        return {"items": [dict(r) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delivery-notes/manual")
def create_manual_dn(body: dict):
    """Create manual delivery note"""
    try:
        conn = sqlite3.connect("data/owlin.db")
        cursor = conn.cursor()
        dn_id = str(uuid4())
        cursor.execute("""
            INSERT INTO delivery_notes (id, document_id, supplier, delivery_date)
            VALUES (?, NULL, ?, ?)
        """, (dn_id, body.get("supplier") or "Unknown", body.get("delivery_date")))
        conn.commit()
        conn.close()
        return {"id": dn_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))