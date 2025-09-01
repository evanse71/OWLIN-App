from fastapi import APIRouter, HTTPException
import sqlite3
from pathlib import Path
from typing import Dict, Any

invoices_api_bp = APIRouter()

def get_db_connection():
    """Get database connection"""
    db_path = Path(__file__).parent.parent.parent / "data" / "owlin.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

@invoices_api_bp.get('/invoices/{invoice_id}')
def get_invoice(invoice_id: str):
    """Get invoice by ID with full details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get invoice metadata
        cursor.execute("""
            SELECT id, supplier_name, invoice_number, invoice_date, currency, total_amount_pennies,
                   ocr_avg_conf, ocr_min_conf, validation_flags
            FROM invoices WHERE id = ?
        """, (invoice_id,))
        invoice = cursor.fetchone()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get invoice pages
        cursor.execute("""
            SELECT id, page_no, ocr_avg_conf_page, ocr_min_conf_line
            FROM invoice_pages WHERE invoice_id = ?
            ORDER BY page_no
        """, (invoice_id,))
        pages = [dict(row) for row in cursor.fetchall()]
        
        # Get invoice lines
        cursor.execute("""
            SELECT id, description as desc, quantity_each, packs, units_per_pack,
                   quantity_ml, quantity_l, quantity_g, unit_price_pennies/100.0 as unit_price,
                   line_total_pennies/100.0 as line_total, vat_rate,
                   line_flags, line_verdict, discount_kind, discount_value,
                   discount_residual_pennies, implied_discount_pct
            FROM invoice_line_items WHERE invoice_id = ?
            ORDER BY row_idx
        """, (invoice_id,))
        lines = []
        for row in cursor.fetchall():
            line = dict(row)
            
            # Parse line_flags JSON
            try:
                import json
                line['flags'] = json.loads(line.get('line_flags', '[]'))
            except:
                line['flags'] = []
            
            # Add discount info if present
            if line.get('discount_kind'):
                line['discount'] = {
                    'kind': line['discount_kind'],
                    'value': line['discount_value'],
                    'residual_pennies': line['discount_residual_pennies'],
                    'implied_pct': line.get('implied_discount_pct')
                }
            
            # Add pairing info if present
            cursor.execute("""
                SELECT ml.dn_id, mli.qty_match_pct
                FROM match_links ml
                JOIN match_link_items mli ON ml.id = mli.link_id
                WHERE mli.invoice_item_id = ?
            """, (line['id'],))
            pairing = cursor.fetchone()
            if pairing:
                line['pairing'] = {
                    'dn_id': pairing['dn_id'],
                    'qty_match_pct': pairing['qty_match_pct']
                }
            
            lines.append(line)
        
        # Build response
        response = {
            "meta": {
                "supplier": invoice['supplier_name'],
                "invoice_no": invoice['invoice_number'],
                "date_iso": invoice['invoice_date'],
                "currency": invoice['currency'],
                "ocr_avg_conf": invoice['ocr_avg_conf'],
                "ocr_min_conf": invoice['ocr_min_conf'],
                "total_inc": invoice['total_amount_pennies'] / 100.0,
                "pages": pages
            },
            "lines": lines
        }
        
        conn.close()
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 