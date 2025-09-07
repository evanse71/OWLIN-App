from fastapi import APIRouter, HTTPException, Request
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