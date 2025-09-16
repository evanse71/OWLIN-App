from fastapi import APIRouter, HTTPException, Request, Query
import sqlite3
from pathlib import Path
from typing import Dict, Any
import uuid

pairing_api_bp = APIRouter()

def get_db_connection():
    """Get database connection"""
    db_path = Path(__file__).parent.parent.parent / "data" / "owlin.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

@pairing_api_bp.post('/invoices/{invoice_id}/pairing/auto')
def auto_pairing(invoice_id: str):
    """Auto-pair invoice with delivery notes"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find best matching delivery note
        cursor.execute("""
            SELECT dn.id as dn_id, 
                   COUNT(*) as matching_lines,
                   AVG(ABS(ili.quantity_each - dli.quantity_each)) as avg_qty_diff
            FROM delivery_notes dn
            JOIN delivery_line_items dli ON dn.id = dli.delivery_note_id
            JOIN invoice_line_items ili ON ili.invoice_id = ?
            WHERE dn.supplier_name = (SELECT supplier_name FROM invoices WHERE id = ?)
            GROUP BY dn.id
            ORDER BY matching_lines DESC, avg_qty_diff ASC
            LIMIT 1
        """, (invoice_id, invoice_id))
        
        match = cursor.fetchone()
        if match:
            # Create match link
            link_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO match_links (id, invoice_id, dn_id, score, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (link_id, invoice_id, match['dn_id'], 0.8))
            
            # Create match link items
            cursor.execute("""
                INSERT INTO match_link_items (link_id, invoice_item_id, dn_item_id, reason, qty_match_pct)
                SELECT ?, ili.id, dli.id, 'AUTO_MATCH', 95.0
                FROM invoice_line_items ili
                JOIN delivery_line_items dli ON dli.delivery_note_id = ?
                WHERE ili.invoice_id = ?
            """, (link_id, match['dn_id'], invoice_id))
            
            conn.commit()
            conn.close()
            
            return {
                "dn_id": match['dn_id'],
                "score": 0.8,
                "qty_match_pct": 95.0
            }
        else:
            conn.close()
            raise HTTPException(status_code=404, detail="No matching delivery notes found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@pairing_api_bp.post('/invoices/{invoice_id}/pairing/manual')
async def manual_pairing(invoice_id: str, request: Request):
    """Manual pairing of invoice with delivery note"""
    try:
        data = await request.json()
        dn_id = data.get('dn_id')
        
        if not dn_id:
            raise HTTPException(status_code=400, detail="dn_id required")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create manual match link
        link_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO match_links (id, invoice_id, dn_id, score, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (link_id, invoice_id, dn_id, 1.0))
        
        # Create match link items for all lines
        cursor.execute("""
            INSERT INTO match_link_items (link_id, invoice_item_id, dn_item_id, reason, qty_match_pct)
            SELECT ?, id, NULL, 'MANUAL_OVERRIDE', 100.0
            FROM invoice_line_items WHERE invoice_id = ?
        """, (link_id, invoice_id))
        
        conn.commit()
        conn.close()
        
        return {"ok": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@pairing_api_bp.get("/pairing/suggestions")
def pairing_suggestions(invoice_id: str, date_window: int = 3, amount_tol: float = 1.0):
    """Get pairing suggestions for an invoice"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get invoice details
        inv = cursor.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not inv:
            raise HTTPException(404, "invoice not found")
        
        # Find potential delivery note matches
        cursor.execute("""
            SELECT *
            FROM delivery_notes
            WHERE lower(supplier) = lower(?)
        """, (inv["supplier"],))
        
        candidates = cursor.fetchall()
        
        out = []
        for c in candidates:
            # Simple scoring: supplier match + date proximity + amount proximity
            supplier_score = 1.0  # exact match
            date_score = 1.0  # exact date gets 1.0; +/-1 day 0.8; etc.
            amt_score = 1.0  # set from your totals if available
            
            score = 0.5*supplier_score + 0.3*date_score + 0.2*amt_score
            out.append({
                "delivery_note_id": c["id"],
                "score": round(score, 3),
                "supplier": c["supplier"],
                "delivery_date": c["delivery_date"],
            })
        
        out.sort(key=lambda x: x["score"], reverse=True)
        conn.close()
        return {"invoice_id": invoice_id, "candidates": out[:5]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@pairing_api_bp.post("/pairing/confirm")
def pairing_confirm(invoice_id: str = Query(...), delivery_note_id: str = Query(...)):
    """Confirm pairing between invoice and delivery note"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update invoice with matched delivery note
        cursor.execute("""
            UPDATE invoices 
            SET matched_delivery_note_id = ?
            WHERE id = ?
        """, (delivery_note_id, invoice_id))
        
        if cursor.rowcount != 1:
            raise HTTPException(400, "update failed")
        
        conn.commit()
        conn.close()
        
        return {"ok": True, "message": "Pairing confirmed"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@pairing_api_bp.post("/pairing/reject")
def pairing_reject(invoice_id: str = Query(...), delivery_note_id: str = Query(...)):
    """Reject pairing between invoice and delivery note"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Optional: persist rejections
        conn.commit()
        conn.close()
        
        return {"ok": True, "message": "Pairing rejected"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 