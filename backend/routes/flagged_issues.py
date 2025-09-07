from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import sqlite3
import os
from datetime import datetime

router = APIRouter(prefix="/flagged-issues", tags=["flagged-issues"])

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

@router.get("/")
async def get_flagged_issues():
    """Get all flagged issues with their details."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get flagged line items with invoice context
        query = """
        SELECT 
            ili.id,
            ili.item_description,
            ili.quantity,
            ili.unit_price,
            ili.flagged,
            ili.source,
            i.upload_timestamp,
            i.invoice_number,
            i.supplier_name,
            i.invoice_date,
            i.venue
        FROM invoice_line_items ili
        JOIN invoices i ON ili.invoice_id = i.id
        WHERE ili.flagged = 1
        ORDER BY i.upload_timestamp DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        flagged_issues = []
        for row in rows:
            issue = {
                "id": row[0],
                "item": row[1],
                "qty": float(row[2]) if row[2] else 0.0,
                "price": float(row[3]) if row[3] else 0.0,
                "flagged": bool(row[4]),
                "source": row[5],
                "upload_timestamp": row[6],
                "invoice_number": row[7],
                "supplier": row[8],
                "invoice_date": row[9],
                "venue": row[10],
                "total_value": float(row[2] * row[3]) if row[2] and row[3] else 0.0
            }
            flagged_issues.append(issue)
        
        conn.close()
        return {"flagged_issues": flagged_issues, "count": len(flagged_issues)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/summary")
async def get_flagged_issues_summary():
    """Get summary statistics for flagged issues."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get summary metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_issues,
                SUM(ABS(quantity * unit_price)) as total_error_value,
                COUNT(DISTINCT invoice_id) as affected_invoices,
                COUNT(DISTINCT i.supplier_name) as affected_suppliers
            FROM invoice_line_items ili
            JOIN invoices i ON ili.invoice_id = i.id
            WHERE ili.flagged = 1
        """)
        
        row = cursor.fetchone()
        summary = {
            "total_issues": row[0] or 0,
            "total_error_value": float(row[1]) if row[1] else 0.0,
            "affected_invoices": row[2] or 0,
            "affected_suppliers": row[3] or 0
        }
        
        # Get issues by supplier
        cursor.execute("""
            SELECT 
                i.supplier_name,
                COUNT(*) as issue_count,
                SUM(ABS(ili.quantity * ili.unit_price)) as total_error
            FROM invoice_line_items ili
            JOIN invoices i ON ili.invoice_id = i.id
            WHERE ili.flagged = 1
            GROUP BY i.supplier_name
            ORDER BY issue_count DESC
        """)
        
        supplier_issues = []
        for supplier_row in cursor.fetchall():
            supplier_issues.append({
                "supplier": supplier_row[0],
                "issue_count": supplier_row[1],
                "total_error": float(supplier_row[2]) if supplier_row[2] else 0.0
            })
        
        summary["supplier_breakdown"] = supplier_issues
        
        conn.close()
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/{issue_id}/resolve")
async def resolve_flagged_issue(issue_id: int):
    """Mark a flagged issue as resolved."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update the flagged status
        cursor.execute("""
            UPDATE invoices_line_items 
            SET flagged = 0, resolved_timestamp = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), issue_id))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Flagged issue not found")
        
        conn.commit()
        conn.close()
        
        return {"message": "Issue resolved successfully", "issue_id": issue_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/{issue_id}/escalate")
async def escalate_flagged_issue(issue_id: int, reason: str = "Manual escalation"):
    """Escalate a flagged issue for review."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add escalation record (you might want to create an escalations table)
        # For now, we'll just update the item with an escalation flag
        cursor.execute("""
            UPDATE invoices_line_items 
            SET escalated = 1, escalation_reason = ?, escalation_timestamp = ?
            WHERE id = ?
        """, (reason, datetime.now().isoformat(), issue_id))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Flagged issue not found")
        
        conn.commit()
        conn.close()
        
        return {"message": "Issue escalated successfully", "issue_id": issue_id, "reason": reason}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{issue_id}")
async def get_flagged_issue_detail(issue_id: int):
    """Get detailed information for a specific flagged issue."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get issue details with invoice context
        cursor.execute("""
            SELECT 
                li.*,
                i.invoice_number,
                i.supplier,
                i.invoice_date,
                i.venue,
                i.total_value as invoice_total
            FROM invoices_line_items li
            JOIN invoices i ON li.invoice_id = i.id
            WHERE li.id = ? AND li.flagged = 1
        """, (issue_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Flagged issue not found")
        
        issue_detail = {
            "id": row[0],
            "invoice_id": row[1],
            "item": row[2],
            "qty": float(row[3]) if row[3] else 0.0,
            "price": float(row[4]) if row[4] else 0.0,
            "flagged": bool(row[5]),
            "source": row[6],
            "upload_timestamp": row[7],
            "resolved_timestamp": row[8],
            "escalated": bool(row[9]) if row[9] else False,
            "escalation_reason": row[10],
            "escalation_timestamp": row[11],
            "invoice_number": row[12],
            "supplier": row[13],
            "invoice_date": row[14],
            "venue": row[15],
            "invoice_total": float(row[16]) if row[16] else 0.0,
            "item_total": float(row[3] * row[4]) if row[3] and row[4] else 0.0
        }
        
        conn.close()
        return issue_detail
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") 