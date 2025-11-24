# -*- coding: utf-8 -*-
"""
Metrics Route

This module implements the GET /api/metrics/overview endpoint that returns
dashboard KPIs as specified in System Bible Section 2.11 (line 230).
"""

from __future__ import annotations
import logging
import sqlite3
from typing import Any, Dict
from fastapi import APIRouter, Query
from datetime import datetime, timedelta

from backend.app.db import DB_PATH

LOGGER = logging.getLogger("owlin.routes.metrics")
router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/overview")
async def get_metrics_overview(
    venue_id: str = Query("royal-oak-1", description="Venue ID"),
    days: int = Query(30, description="Number of days to include in metrics")
) -> Dict[str, Any]:
    """
    Get dashboard KPIs and metrics overview.
    
    Returns:
        Dictionary with:
        - Total spend
        - Invoice count
        - Supplier count
        - Match rate
        - Issue rate
        - Average confidence
        - Top suppliers
        - Issues by type
    """
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        
        # Calculate date range
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Total spend
        cursor.execute("""
            SELECT COALESCE(SUM(value), 0)
            FROM invoices
            WHERE date >= ? AND status = 'submitted'
        """, (cutoff_date,))
        
        total_spend = cursor.fetchone()[0] or 0.0
        
        # Invoice count
        cursor.execute("""
            SELECT COUNT(*)
            FROM invoices
            WHERE date >= ? AND status = 'submitted'
        """, (cutoff_date,))
        
        invoice_count = cursor.fetchone()[0] or 0
        
        # Supplier count
        cursor.execute("""
            SELECT COUNT(DISTINCT supplier)
            FROM invoices
            WHERE date >= ? AND status = 'submitted' AND supplier IS NOT NULL
        """, (cutoff_date,))
        
        supplier_count = cursor.fetchone()[0] or 0
        
        # Match rate (invoices with paired delivery notes)
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT i.id) as total,
                COUNT(DISTINCT CASE WHEN p.id IS NOT NULL THEN i.id END) as matched
            FROM invoices i
            LEFT JOIN pairs p ON p.invoice_id = i.id AND p.status = 'confirmed'
            WHERE i.date >= ? AND i.status = 'submitted'
        """, (cutoff_date,))
        
        match_row = cursor.fetchone()
        total_invoices = match_row[0] or 0
        matched_invoices = match_row[1] or 0
        match_rate = (matched_invoices / total_invoices * 100) if total_invoices > 0 else 0.0
        
        # Issue rate
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT i.id) as total,
                COUNT(DISTINCT CASE WHEN iss.id IS NOT NULL THEN i.id END) as with_issues
            FROM invoices i
            LEFT JOIN issues iss ON iss.invoice_id = i.id AND iss.status = 'open'
            WHERE i.date >= ? AND i.status = 'submitted'
        """, (cutoff_date,))
        
        issue_row = cursor.fetchone()
        total_for_issues = issue_row[0] or 0
        invoices_with_issues = issue_row[1] or 0
        issue_rate = (invoices_with_issues / total_for_issues * 100) if total_for_issues > 0 else 0.0
        
        # Average confidence
        cursor.execute("""
            SELECT COALESCE(AVG(confidence), 0)
            FROM invoices
            WHERE date >= ? AND status = 'submitted'
        """, (cutoff_date,))
        
        avg_confidence = cursor.fetchone()[0] or 0.0
        
        # Top suppliers by spend
        cursor.execute("""
            SELECT supplier, SUM(value) as total_spend, COUNT(*) as invoice_count
            FROM invoices
            WHERE date >= ? AND status = 'submitted' AND supplier IS NOT NULL
            GROUP BY supplier
            ORDER BY total_spend DESC
            LIMIT 10
        """, (cutoff_date,))
        
        top_suppliers = []
        for row in cursor.fetchall():
            top_suppliers.append({
                "supplier": row[0],
                "total_spend": float(row[1] or 0),
                "invoice_count": row[2] or 0
            })
        
        # Issues by type
        cursor.execute("""
            SELECT type, COUNT(*) as count, AVG(value_delta) as avg_delta
            FROM issues
            WHERE status = 'open'
            GROUP BY type
        """)
        
        issues_by_type = []
        for row in cursor.fetchall():
            issues_by_type.append({
                "type": row[0],
                "count": row[1] or 0,
                "avg_delta": float(row[2] or 0),
                "severity": "high" if abs(row[2] or 0) > 50 else "medium" if abs(row[2] or 0) > 10 else "low"
            })
        
        conn.close()
        
        return {
            "venue_id": venue_id,
            "period_days": days,
            "total_spend": float(total_spend),
            "invoice_count": invoice_count,
            "supplier_count": supplier_count,
            "match_rate": round(match_rate, 2),
            "issue_rate": round(issue_rate, 2),
            "avg_confidence": round(avg_confidence, 3),
            "top_suppliers": top_suppliers,
            "issues_by_type": issues_by_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        LOGGER.error(f"Error getting metrics overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

