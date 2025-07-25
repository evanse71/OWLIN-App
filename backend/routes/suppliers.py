from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import sqlite3
import os
from datetime import datetime, timedelta

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

@router.get("/")
async def get_suppliers():
    """Get all suppliers with their basic information."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get unique suppliers with basic stats
        query = """
        SELECT 
            supplier_name,
            COUNT(DISTINCT i.id) as total_invoices,
            SUM(i.total_amount) as total_value,
            AVG(i.total_amount) as avg_invoice_value,
            MIN(i.invoice_date) as first_invoice,
            MAX(i.invoice_date) as last_invoice
        FROM invoices i
        WHERE supplier_name IS NOT NULL AND supplier_name != ''
        GROUP BY supplier_name
        ORDER BY total_value DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        suppliers = []
        for row in rows:
            supplier = {
                "name": row[0],
                "total_invoices": row[1],
                "total_value": float(row[2]) if row[2] else 0.0,
                "avg_invoice_value": float(row[3]) if row[3] else 0.0,
                "first_invoice": row[4],
                "last_invoice": row[5]
            }
            suppliers.append(supplier)
        
        conn.close()
        return {"suppliers": suppliers}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/analytics")
async def get_supplier_analytics():
    """Get comprehensive supplier analytics and performance metrics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get supplier analytics with line item details
        query = """
        SELECT 
            i.supplier_name,
            COUNT(DISTINCT i.id) as total_invoices,
            SUM(i.total_amount) as total_value,
            COUNT(ili.id) as total_line_items,
            SUM(CASE WHEN ili.flagged = 1 THEN 1 ELSE 0 END) as flagged_items,
            AVG(ili.unit_price) as avg_item_price,
            COUNT(DISTINCT ili.item_description) as unique_items
        FROM invoices i
        LEFT JOIN invoice_line_items ili ON i.id = ili.invoice_id
        WHERE i.supplier_name IS NOT NULL AND i.supplier_name != ''
        GROUP BY i.supplier_name
        ORDER BY total_value DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        analytics = []
        for row in rows:
            total_items = row[3] or 0
            flagged_items = row[4] or 0
            mismatch_rate = (flagged_items / total_items * 100) if total_items > 0 else 0
            
            supplier_analytics = {
                "supplier": row[0],
                "total_invoices": row[1],
                "total_value": float(row[2]) if row[2] else 0.0,
                "total_line_items": total_items,
                "flagged_items": flagged_items,
                "mismatch_rate": round(mismatch_rate, 1),
                "avg_item_price": float(row[5]) if row[5] else 0.0,
                "unique_items": row[6] or 0
            }
            analytics.append(supplier_analytics)
        
        conn.close()
        return {"analytics": analytics}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{supplier_name}")
async def get_supplier_detail(supplier_name: str):
    """Get detailed information for a specific supplier."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get supplier invoices
        cursor.execute("""
            SELECT 
                id,
                invoice_number,
                invoice_date,
                total_amount,
                status,
                upload_timestamp,
                venue
            FROM invoices 
            WHERE supplier_name = ?
            ORDER BY invoice_date DESC
        """, (supplier_name,))
        
        invoice_rows = cursor.fetchall()
        invoices = []
        for row in invoice_rows:
            invoice = {
                "id": row[0],
                "invoice_number": row[1],
                "invoice_date": row[2],
                "total_value": float(row[3]) if row[3] else 0.0,
                "status": row[4],
                "upload_timestamp": row[5],
                "venue": row[6]
            }
            invoices.append(invoice)
        
        # Get supplier summary stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_invoices,
                SUM(total_amount) as total_value,
                AVG(total_amount) as avg_invoice_value,
                MIN(invoice_date) as first_invoice,
                MAX(invoice_date) as last_invoice,
                COUNT(DISTINCT venue) as venues_used
            FROM invoices 
            WHERE supplier_name = ?
        """, (supplier_name,))
        
        summary_row = cursor.fetchone()
        summary = {
            "total_invoices": summary_row[0] or 0,
            "total_value": float(summary_row[1]) if summary_row[1] else 0.0,
            "avg_invoice_value": float(summary_row[2]) if summary_row[2] else 0.0,
            "first_invoice": summary_row[3],
            "last_invoice": summary_row[4],
            "venues_used": summary_row[5] or 0
        }
        
        # Get top items from this supplier
        cursor.execute("""
            SELECT 
                ili.item_description,
                COUNT(*) as frequency,
                AVG(ili.unit_price) as avg_price,
                SUM(ili.quantity) as total_qty,
                SUM(CASE WHEN ili.flagged = 1 THEN 1 ELSE 0 END) as flagged_count
            FROM invoice_line_items ili
            JOIN invoices i ON ili.invoice_id = i.id
            WHERE i.supplier_name = ?
            GROUP BY ili.item_description
            ORDER BY frequency DESC
            LIMIT 10
        """, (supplier_name,))
        
        top_items = []
        for item_row in cursor.fetchall():
            item = {
                "item": item_row[0],
                "frequency": item_row[1],
                "avg_price": float(item_row[2]) if item_row[2] else 0.0,
                "total_qty": float(item_row[3]) if item_row[3] else 0.0,
                "flagged_count": item_row[4]
            }
            top_items.append(item)
        
        conn.close()
        
        return {
            "supplier": supplier_name,
            "summary": summary,
            "invoices": invoices,
            "top_items": top_items
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{supplier_name}/performance")
async def get_supplier_performance(supplier_name: str, days: int = 30):
    """Get supplier performance metrics over time."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get performance data over time
        cursor.execute("""
            SELECT 
                DATE(i.invoice_date) as date,
                COUNT(*) as invoice_count,
                SUM(i.total_amount) as daily_value,
                AVG(i.total_amount) as avg_invoice_value,
                COUNT(CASE WHEN i.status = 'matched' THEN 1 END) as matched_invoices,
                COUNT(CASE WHEN i.status = 'discrepancy' THEN 1 END) as discrepancy_invoices
            FROM invoices i
            WHERE i.supplier_name = ? 
            AND i.invoice_date >= ? 
            AND i.invoice_date <= ?
            GROUP BY DATE(i.invoice_date)
            ORDER BY date
        """, (supplier_name, start_date.date(), end_date.date()))
        
        performance_data = []
        for row in cursor.fetchall():
            daily_data = {
                "date": row[0],
                "invoice_count": row[1],
                "daily_value": float(row[2]) if row[2] else 0.0,
                "avg_invoice_value": float(row[3]) if row[3] else 0.0,
                "matched_invoices": row[4],
                "discrepancy_invoices": row[5]
            }
            performance_data.append(daily_data)
        
        conn.close()
        
        return {
            "supplier": supplier_name,
            "period_days": days,
            "performance_data": performance_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/summary/overview")
async def get_suppliers_overview():
    """Get overview statistics for all suppliers."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get overall supplier statistics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT supplier_name) as total_suppliers,
                SUM(total_amount) as total_value,
                AVG(total_amount) as avg_supplier_value,
                COUNT(*) as total_invoices,
                COUNT(CASE WHEN status = 'matched' THEN 1 END) as matched_invoices,
                COUNT(CASE WHEN status = 'discrepancy' THEN 1 END) as discrepancy_invoices
            FROM invoices
            WHERE supplier_name IS NOT NULL AND supplier_name != ''
        """)
        
        row = cursor.fetchone()
        overview = {
            "total_suppliers": row[0] or 0,
            "total_value": float(row[1]) if row[1] else 0.0,
            "avg_supplier_value": float(row[2]) if row[2] else 0.0,
            "total_invoices": row[3] or 0,
            "matched_invoices": row[4] or 0,
            "discrepancy_invoices": row[5] or 0
        }
        
        # Calculate success rate
        if overview["total_invoices"] > 0:
            overview["success_rate"] = round((overview["matched_invoices"] / overview["total_invoices"]) * 100, 1)
        else:
            overview["success_rate"] = 0.0
        
        conn.close()
        return overview
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") 