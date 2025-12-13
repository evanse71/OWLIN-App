"""
invoice_query.py
===============

Advanced invoice query service with filtering, sorting, and role-aware defaults.
Supports SQLite-backed queries with performance optimizations.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional
from db_manager_unified import get_db_manager

logger = logging.getLogger(__name__)

def _pounds(pennies: int) -> float:
    return pennies / 100.0

def _dict_from_row(row: Any) -> Dict[str, Any]:
    return dict(zip(row.keys(), row))

def _dict_from_row_safe(row: Any) -> Dict[str, Any]:
    return dict(zip(row.keys(), row))

def fetch_invoice(invoice_id: str) -> Optional[Dict[str, Any]]:
    """Fetch invoice with all line items"""
    try:
        db = get_db_manager()
        conn = db.get_conn()
        
        logger.info(f"🔍 Fetching invoice {invoice_id}")
        
        # Get invoice metadata
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, supplier_name, invoice_number, invoice_date, 
                   currency, total_amount_pennies, ocr_avg_conf, ocr_min_conf
            FROM invoices WHERE id = ?
        """, (invoice_id,))
        
        invoice_row = cursor.fetchone()
        if not invoice_row:
            logger.warning(f"❌ No invoice found with ID: {invoice_id}")
            return None
            
        invoice = _dict_from_row(invoice_row)
        logger.info(f"📄 Invoice data: {invoice}")
        
        # Get line items
        cursor.execute("""
            SELECT description, quantity_each, quantity, unit_price_pennies, 
                   line_total_pennies, quantity_l, sku, line_flags
            FROM invoice_line_items 
            WHERE invoice_id = ? 
            ORDER BY row_idx
        """, (invoice_id,))
        
        lines = [_dict_from_row_safe(row) for row in cursor.fetchall()]
        logger.info(f"📋 Found {len(lines)} line items")
        
        # Build response - include id and keep pennies for conversion at edge
        response = {
            "id": invoice["id"],
            "meta": {
                "supplier": invoice.get("supplier_name"),
                "invoice_no": invoice.get("invoice_number"),
                "date_iso": invoice.get("invoice_date"),
                "currency": invoice.get("currency"),
                "ocr_avg_conf": invoice.get("ocr_avg_conf"),
                "ocr_min_conf": invoice.get("ocr_min_conf"),
                "total_amount_pennies": invoice.get("total_amount_pennies")  # Keep pennies for edge conversion
            },
            "lines": lines
        }
        
        logger.info(f"✅ Built response: {response}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error fetching invoice {invoice_id}: {e}")
        return None

def fetch_invoice_summary(invoice_id: str) -> Optional[Dict[str, Any]]:
    """Fetch just invoice summary without line items"""
    try:
        db = get_db_manager()
        conn = db.get_conn()
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, supplier_name, invoice_number, invoice_date, 
                   currency, total_amount_pennies, ocr_avg_conf, ocr_min_conf
            FROM invoices WHERE id = ?
        """, (invoice_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
            
        invoice = _dict_from_row(row)
        
        return {
            "id": invoice["id"],
            "supplier": invoice.get("supplier_name"),
            "invoice_no": invoice.get("invoice_number"),
            "date": invoice.get("invoice_date"),
            "total": _pounds(invoice.get("total_amount_pennies") or 0),
            "ocr_avg_conf": invoice.get("ocr_avg_conf"),
            "ocr_min_conf": invoice.get("ocr_min_conf")
        }
        
    except Exception as e:
        logger.error(f"Error fetching invoice summary {invoice_id}: {e}")
        return None 