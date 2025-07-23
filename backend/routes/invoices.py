from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Dict, Optional
import sqlite3
import os
from datetime import datetime
import json

router = APIRouter(prefix="/invoices", tags=["invoices"])

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

@router.get("/")
async def get_invoices():
    """Get all invoices with their status and details."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get invoices with delivery note pairing info
        query = """
        SELECT 
            i.id,
            i.invoice_number,
            i.invoice_date,
            i.supplier,
            i.total_value,
            i.status,
            i.upload_timestamp,
            i.venue,
            dn.id as delivery_note_id,
            dn.delivery_note_number,
            dn.delivery_date,
            dn.status as delivery_status
        FROM invoices i
        LEFT JOIN delivery_notes dn ON i.delivery_note_id = dn.id
        ORDER BY i.upload_timestamp DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        invoices = []
        for row in rows:
            invoice = {
                "id": row[0],
                "invoice_number": row[1],
                "invoice_date": row[2],
                "supplier": row[3],
                "total_value": float(row[4]) if row[4] else 0.0,
                "status": row[5],
                "upload_timestamp": row[6],
                "venue": row[7],
                "delivery_note": {
                    "id": row[8],
                    "delivery_note_number": row[9],
                    "delivery_date": row[10],
                    "status": row[11]
                } if row[8] else None
            }
            invoices.append(invoice)
        
        conn.close()
        return {"invoices": invoices}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/summary")
async def get_invoice_summary():
    """Get invoice processing summary metrics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get summary metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_invoices,
                SUM(total_value) as total_value,
                SUM(CASE WHEN status = 'matched' THEN 1 ELSE 0 END) as matched_count,
                SUM(CASE WHEN status = 'discrepancy' THEN 1 ELSE 0 END) as discrepancy_count,
                SUM(CASE WHEN status = 'not_paired' THEN 1 ELSE 0 END) as not_paired_count,
                SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing_count
            FROM invoices
        """)
        
        row = cursor.fetchone()
        summary = {
            "total_invoices": row[0] or 0,
            "total_value": float(row[1]) if row[1] else 0.0,
            "matched_count": row[2] or 0,
            "discrepancy_count": row[3] or 0,
            "not_paired_count": row[4] or 0,
            "processing_count": row[5] or 0
        }
        
        # Get total error from flagged line items
        cursor.execute("""
            SELECT SUM(ABS(qty * price)) as total_error
            FROM invoices_line_items 
            WHERE flagged = 1
        """)
        
        error_row = cursor.fetchone()
        summary["total_error"] = float(error_row[0]) if error_row[0] else 0.0
        
        conn.close()
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{invoice_id}")
async def get_invoice_detail(invoice_id: int):
    """Get detailed information for a specific invoice."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get invoice details
        cursor.execute("""
            SELECT 
                i.*,
                dn.id as delivery_note_id,
                dn.delivery_note_number,
                dn.delivery_date,
                dn.status as delivery_status,
                dn.file_path as delivery_file_path
            FROM invoices i
            LEFT JOIN delivery_notes dn ON i.delivery_note_id = dn.id
            WHERE i.id = ?
        """, (invoice_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get line items
        cursor.execute("""
            SELECT id, item, qty, price, flagged, source
            FROM invoices_line_items 
            WHERE invoice_id = ?
            ORDER BY id
        """, (invoice_id,))
        
        line_items = []
        for item_row in cursor.fetchall():
            line_items.append({
                "id": item_row[0],
                "item": item_row[1],
                "qty": float(item_row[2]) if item_row[2] else 0.0,
                "price": float(item_row[3]) if item_row[3] else 0.0,
                "flagged": bool(item_row[4]),
                "source": item_row[5]
            })
        
        invoice_detail = {
            "id": row[0],
            "invoice_number": row[1],
            "invoice_date": row[2],
            "supplier": row[3],
            "total_value": float(row[4]) if row[4] else 0.0,
            "status": row[5],
            "upload_timestamp": row[6],
            "venue": row[7],
            "file_path": row[8],
            "delivery_note": {
                "id": row[9],
                "delivery_note_number": row[10],
                "delivery_date": row[11],
                "status": row[12],
                "file_path": row[13]
            } if row[9] else None,
            "line_items": line_items
        }
        
        conn.close()
        return invoice_detail
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/{invoice_id}/pair")
async def pair_invoice_with_delivery_note(invoice_id: int, delivery_note_id: int):
    """Pair an invoice with a delivery note."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update invoice with delivery note ID
        cursor.execute("""
            UPDATE invoices 
            SET delivery_note_id = ?, status = 'matched'
            WHERE id = ?
        """, (delivery_note_id, invoice_id))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        conn.commit()
        conn.close()
        
        return {"message": "Invoice paired successfully", "invoice_id": invoice_id, "delivery_note_id": delivery_note_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: int):
    """Delete an invoice and its associated data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete line items first
        cursor.execute("DELETE FROM invoices_line_items WHERE invoice_id = ?", (invoice_id,))
        
        # Delete invoice
        cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        conn.commit()
        conn.close()
        
        return {"message": "Invoice deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") 