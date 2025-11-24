# -*- coding: utf-8 -*-
"""
Suppliers Route

This module implements the GET /api/suppliers/{id}/scorecard endpoint that returns
supplier summary metrics as specified in System Bible Section 3.9 (line 251) and
Section 5.4 (Supplier Scorecard Algorithm).
"""

from __future__ import annotations
import logging
import sqlite3
from typing import Any, Dict
from fastapi import APIRouter, HTTPException
import numpy as np

from backend.app.db import DB_PATH

LOGGER = logging.getLogger("owlin.routes.suppliers")
router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("/{supplier_id}/scorecard")
async def get_supplier_scorecard(supplier_id: str) -> Dict[str, Any]:
    """
    Get supplier scorecard with key metrics.
    
    Implements Section 5.4 formulas:
    - Mismatch Rate: mismatched_lines ÷ total_lines
    - Delivery Delays: late deliveries ÷ total deliveries
    - Price Volatility: σ(price change)
    - Issue Resolution Time: avg days(open→closed)
    
    Args:
        supplier_id: Supplier ID or name
    
    Returns:
        Dictionary with supplier scorecard metrics
    """
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        
        # Get supplier invoices
        cursor.execute("""
            SELECT id, value, date, status
            FROM invoices
            WHERE supplier = ? AND status = 'submitted'
            ORDER BY date DESC
        """, (supplier_id,))
        
        invoices = cursor.fetchall()
        
        if not invoices:
            raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
        
        invoice_ids = [row[0] for row in invoices]
        
        # Mismatch Rate: mismatched_lines ÷ total_lines
        cursor.execute("""
            SELECT 
                COUNT(*) as total_lines,
                COUNT(CASE WHEN iss.id IS NOT NULL THEN 1 END) as mismatched_lines
            FROM invoice_line_items ili
            LEFT JOIN issues iss ON iss.invoice_id = ili.invoice_id 
                AND iss.type IN ('price_mismatch', 'quantity_discrepancy')
                AND iss.status = 'open'
            WHERE ili.invoice_id IN ({})
        """.format(','.join('?' * len(invoice_ids))), invoice_ids)
        
        mismatch_row = cursor.fetchone()
        total_lines = mismatch_row[0] or 0
        mismatched_lines = mismatch_row[1] or 0
        mismatch_rate = (mismatched_lines / total_lines * 100) if total_lines > 0 else 0.0
        
        # Delivery Delays: late deliveries ÷ total deliveries
        # (This would require delivery_date vs invoice_date comparison)
        # For now, we'll use a simplified calculation
        cursor.execute("""
            SELECT COUNT(*)
            FROM pairs p
            JOIN invoices i ON i.id = p.invoice_id
            WHERE i.supplier = ? AND p.status = 'confirmed'
        """, (supplier_id,))
        
        total_deliveries = cursor.fetchone()[0] or 0
        
        # Calculate date differences for delays
        cursor.execute("""
            SELECT 
                i.date as invoice_date,
                d.doc_date as delivery_date
            FROM pairs p
            JOIN invoices i ON i.id = p.invoice_id
            JOIN documents d ON d.id = p.delivery_id
            WHERE i.supplier = ? AND p.status = 'confirmed'
        """, (supplier_id,))
        
        delays = []
        for row in cursor.fetchall():
            try:
                if row[0] and row[1]:
                    from datetime import datetime
                    inv_date = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
                    del_date = datetime.fromisoformat(row[1].replace('Z', '+00:00'))
                    delay_days = (inv_date - del_date).days
                    if delay_days > 0:
                        delays.append(delay_days)
            except Exception:
                pass
        
        late_deliveries = len([d for d in delays if d > 0])
        delivery_delay_rate = (late_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0.0
        
        # Price Volatility: σ(price change % per item)
        cursor.execute("""
            SELECT item_id, price_ex_vat, observed_at
            FROM supplier_price_history
            WHERE item_id IN (
                SELECT DISTINCT description
                FROM invoice_line_items
                WHERE invoice_id IN ({})
            )
            ORDER BY item_id, observed_at
        """.format(','.join('?' * len(invoice_ids))), invoice_ids)
        
        price_changes = []
        current_item = None
        prev_price = None
        
        for row in cursor.fetchall():
            item_id, price, obs_date = row
            if item_id != current_item:
                current_item = item_id
                prev_price = price
                continue
            
            if prev_price and price:
                change_pct = abs((price - prev_price) / prev_price * 100)
                price_changes.append(change_pct)
            
            prev_price = price
        
        price_volatility = float(np.std(price_changes)) if price_changes else 0.0
        
        # Issue Resolution Time: avg days(open→closed)
        cursor.execute("""
            SELECT 
                created_at,
                resolved_at
            FROM issues
            WHERE invoice_id IN ({}) AND status = 'resolved'
        """.format(','.join('?' * len(invoice_ids))), invoice_ids)
        
        resolution_times = []
        for row in cursor.fetchall():
            try:
                if row[0] and row[1]:
                    from datetime import datetime
                    created = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
                    resolved = datetime.fromisoformat(row[1].replace('Z', '+00:00'))
                    days = (resolved - created).days
                    resolution_times.append(days)
            except Exception:
                pass
        
        avg_resolution_time = float(np.mean(resolution_times)) if resolution_times else 0.0
        
        conn.close()
        
        # Color coding as per Section 5.4
        mismatch_color = "amber" if mismatch_rate > 3.0 else "green"
        delivery_color = "red" if delivery_delay_rate > 5.0 else "amber" if delivery_delay_rate > 2.0 else "green"
        volatility_color = "amber" if price_volatility > 10.0 else "green"
        resolution_color = "grey" if avg_resolution_time > 7.0 else "green"
        
        return {
            "supplier_id": supplier_id,
            "metrics": {
                "mismatch_rate": round(mismatch_rate, 2),
                "mismatch_rate_color": mismatch_color,
                "delivery_delay_rate": round(delivery_delay_rate, 2),
                "delivery_delay_rate_color": delivery_color,
                "price_volatility": round(price_volatility, 2),
                "price_volatility_color": volatility_color,
                "avg_issue_resolution_days": round(avg_resolution_time, 1),
                "issue_resolution_color": resolution_color
            },
            "summary": {
                "total_invoices": len(invoices),
                "total_lines": total_lines,
                "mismatched_lines": mismatched_lines,
                "total_deliveries": total_deliveries,
                "late_deliveries": late_deliveries,
                "price_observations": len(price_changes),
                "resolved_issues": len(resolution_times)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Error getting supplier scorecard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get supplier scorecard: {str(e)}")


@router.get("/aliases/pending")
async def get_pending_aliases() -> Dict[str, Any]:
    """
    Get pending supplier alias reviews.
    
    Returns:
        Dictionary with pending reviews
    """
    try:
        reviews = get_pending_reviews()
        stats = get_review_statistics()
        
        return {
            "reviews": reviews,
            "statistics": stats
        }
        
    except Exception as e:
        LOGGER.error(f"Error getting pending aliases: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pending aliases: {str(e)}")


@router.post("/aliases/{review_id}/approve")
async def approve_supplier_alias(review_id: int, reviewed_by: str = "system") -> Dict[str, Any]:
    """
    Approve a supplier alias match.
    
    Args:
        review_id: Review ID
        reviewed_by: User who approved
    
    Returns:
        Success status
    """
    try:
        success = approve_alias(review_id, reviewed_by)
        
        if success:
            return {"success": True, "message": f"Alias review {review_id} approved"}
        else:
            raise HTTPException(status_code=404, detail=f"Alias review {review_id} not found or already processed")
        
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Error approving alias: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve alias: {str(e)}")


@router.post("/aliases/{review_id}/reject")
async def reject_supplier_alias(review_id: int, reviewed_by: str = "system") -> Dict[str, Any]:
    """
    Reject a supplier alias match and create new supplier.
    
    Args:
        review_id: Review ID
        reviewed_by: User who rejected
    
    Returns:
        Success status
    """
    try:
        success = reject_alias(review_id, reviewed_by)
        
        if success:
            return {"success": True, "message": f"Alias review {review_id} rejected, new supplier created"}
        else:
            raise HTTPException(status_code=404, detail=f"Alias review {review_id} not found or already processed")
        
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Error rejecting alias: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reject alias: {str(e)}")

