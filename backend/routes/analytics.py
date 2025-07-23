from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import sqlite3
import os
from datetime import datetime, timedelta

router = APIRouter(prefix="/analytics", tags=["analytics"])

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

@router.get("/dashboard")
async def get_dashboard_analytics():
    """Get comprehensive dashboard analytics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get overall system metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_invoices,
                SUM(total_value) as total_value,
                COUNT(CASE WHEN status = 'matched' THEN 1 END) as matched_invoices,
                COUNT(CASE WHEN status = 'discrepancy' THEN 1 END) as discrepancy_invoices,
                COUNT(CASE WHEN status = 'not_paired' THEN 1 END) as not_paired_invoices,
                COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_invoices,
                COUNT(DISTINCT supplier) as total_suppliers,
                COUNT(DISTINCT venue) as total_venues
            FROM invoices
        """)
        
        row = cursor.fetchone()
        system_metrics = {
            "total_invoices": row[0] or 0,
            "total_value": float(row[1]) if row[1] else 0.0,
            "matched_invoices": row[2] or 0,
            "discrepancy_invoices": row[3] or 0,
            "not_paired_invoices": row[4] or 0,
            "processing_invoices": row[5] or 0,
            "total_suppliers": row[6] or 0,
            "total_venues": row[7] or 0
        }
        
        # Calculate success rate
        if system_metrics["total_invoices"] > 0:
            system_metrics["success_rate"] = round((system_metrics["matched_invoices"] / system_metrics["total_invoices"]) * 100, 1)
        else:
            system_metrics["success_rate"] = 0.0
        
        # Get flagged issues summary
        cursor.execute("""
            SELECT 
                COUNT(*) as total_flagged,
                SUM(ABS(qty * price)) as total_error_value,
                COUNT(DISTINCT invoice_id) as affected_invoices
            FROM invoices_line_items 
            WHERE flagged = 1
        """)
        
        flagged_row = cursor.fetchone()
        flagged_summary = {
            "total_flagged": flagged_row[0] or 0,
            "total_error_value": float(flagged_row[1]) if flagged_row[1] else 0.0,
            "affected_invoices": flagged_row[2] or 0
        }
        
        # Get recent activity (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        cursor.execute("""
            SELECT 
                DATE(upload_timestamp) as date,
                COUNT(*) as invoice_count,
                SUM(total_value) as daily_value
            FROM invoices 
            WHERE upload_timestamp >= ?
            GROUP BY DATE(upload_timestamp)
            ORDER BY date DESC
        """, (seven_days_ago.date(),))
        
        recent_activity = []
        for activity_row in cursor.fetchall():
            activity = {
                "date": activity_row[0],
                "invoice_count": activity_row[1],
                "daily_value": float(activity_row[2]) if activity_row[2] else 0.0
            }
            recent_activity.append(activity)
        
        # Get top suppliers by value
        cursor.execute("""
            SELECT 
                supplier,
                COUNT(*) as invoice_count,
                SUM(total_value) as total_value
            FROM invoices 
            WHERE supplier IS NOT NULL AND supplier != ''
            GROUP BY supplier
            ORDER BY total_value DESC
            LIMIT 5
        """)
        
        top_suppliers = []
        for supplier_row in cursor.fetchall():
            supplier = {
                "name": supplier_row[0],
                "invoice_count": supplier_row[1],
                "total_value": float(supplier_row[2]) if supplier_row[2] else 0.0
            }
            top_suppliers.append(supplier)
        
        # Get venue breakdown
        cursor.execute("""
            SELECT 
                venue,
                COUNT(*) as invoice_count,
                SUM(total_value) as total_value
            FROM invoices 
            WHERE venue IS NOT NULL AND venue != ''
            GROUP BY venue
            ORDER BY total_value DESC
        """)
        
        venue_breakdown = []
        for venue_row in cursor.fetchall():
            venue = {
                "name": venue_row[0],
                "invoice_count": venue_row[1],
                "total_value": float(venue_row[2]) if venue_row[2] else 0.0
            }
            venue_breakdown.append(venue)
        
        conn.close()
        
        return {
            "system_metrics": system_metrics,
            "flagged_summary": flagged_summary,
            "recent_activity": recent_activity,
            "top_suppliers": top_suppliers,
            "venue_breakdown": venue_breakdown
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/trends")
async def get_analytics_trends(days: int = 30):
    """Get trend data over a specified period."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get daily trends
        cursor.execute("""
            SELECT 
                DATE(upload_timestamp) as date,
                COUNT(*) as invoice_count,
                SUM(total_value) as daily_value,
                COUNT(CASE WHEN status = 'matched' THEN 1 END) as matched_count,
                COUNT(CASE WHEN status = 'discrepancy' THEN 1 END) as discrepancy_count,
                COUNT(CASE WHEN status = 'not_paired' THEN 1 END) as not_paired_count
            FROM invoices 
            WHERE upload_timestamp >= ?
            GROUP BY DATE(upload_timestamp)
            ORDER BY date
        """, (start_date.date(),))
        
        trends = []
        for row in cursor.fetchall():
            trend = {
                "date": row[0],
                "invoice_count": row[1],
                "daily_value": float(row[2]) if row[2] else 0.0,
                "matched_count": row[3],
                "discrepancy_count": row[4],
                "not_paired_count": row[5]
            }
            trends.append(trend)
        
        # Get weekly summary
        cursor.execute("""
            SELECT 
                strftime('%Y-%W', upload_timestamp) as week,
                COUNT(*) as invoice_count,
                SUM(total_value) as weekly_value,
                AVG(total_value) as avg_invoice_value
            FROM invoices 
            WHERE upload_timestamp >= ?
            GROUP BY strftime('%Y-%W', upload_timestamp)
            ORDER BY week
        """, (start_date.date(),))
        
        weekly_summary = []
        for week_row in cursor.fetchall():
            week = {
                "week": week_row[0],
                "invoice_count": week_row[1],
                "weekly_value": float(week_row[2]) if week_row[2] else 0.0,
                "avg_invoice_value": float(week_row[3]) if week_row[3] else 0.0
            }
            weekly_summary.append(week)
        
        conn.close()
        
        return {
            "period_days": days,
            "daily_trends": trends,
            "weekly_summary": weekly_summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/performance")
async def get_system_performance():
    """Get system performance metrics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get processing performance metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_processed,
                COUNT(CASE WHEN status = 'matched' THEN 1 END) as successful,
                COUNT(CASE WHEN status = 'discrepancy' THEN 1 END) as with_discrepancies,
                COUNT(CASE WHEN status = 'not_paired' THEN 1 END) as unpaired,
                AVG(total_value) as avg_invoice_value,
                MIN(upload_timestamp) as first_upload,
                MAX(upload_timestamp) as last_upload
            FROM invoices
        """)
        
        row = cursor.fetchone()
        performance = {
            "total_processed": row[0] or 0,
            "successful": row[1] or 0,
            "with_discrepancies": row[2] or 0,
            "unpaired": row[3] or 0,
            "avg_invoice_value": float(row[4]) if row[4] else 0.0,
            "first_upload": row[5],
            "last_upload": row[6]
        }
        
        # Calculate success rate
        if performance["total_processed"] > 0:
            performance["success_rate"] = round((performance["successful"] / performance["total_processed"]) * 100, 1)
            performance["discrepancy_rate"] = round((performance["with_discrepancies"] / performance["total_processed"]) * 100, 1)
        else:
            performance["success_rate"] = 0.0
            performance["discrepancy_rate"] = 0.0
        
        # Get processing time metrics (if available)
        cursor.execute("""
            SELECT 
                AVG(processing_time) as avg_processing_time,
                MAX(processing_time) as max_processing_time,
                MIN(processing_time) as min_processing_time
            FROM invoices 
            WHERE processing_time IS NOT NULL
        """)
        
        time_row = cursor.fetchone()
        if time_row and time_row[0]:
            performance["avg_processing_time"] = float(time_row[0])
            performance["max_processing_time"] = float(time_row[1]) if time_row[1] else 0.0
            performance["min_processing_time"] = float(time_row[2]) if time_row[2] else 0.0
        else:
            performance["avg_processing_time"] = 0.0
            performance["max_processing_time"] = 0.0
            performance["min_processing_time"] = 0.0
        
        conn.close()
        
        return performance
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/health")
async def get_system_health():
    """Get system health metrics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check database health
        cursor.execute("SELECT COUNT(*) FROM invoices")
        total_invoices = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM invoices_line_items")
        total_line_items = cursor.fetchone()[0]
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        cursor.execute("SELECT COUNT(*) FROM invoices WHERE upload_timestamp >= ?", (yesterday,))
        recent_uploads = cursor.fetchone()[0]
        
        # Get error rate
        cursor.execute("SELECT COUNT(*) FROM invoices_line_items WHERE flagged = 1")
        flagged_items = cursor.fetchone()[0]
        
        error_rate = 0.0
        if total_line_items > 0:
            error_rate = round((flagged_items / total_line_items) * 100, 2)
        
        health_metrics = {
            "database_status": "healthy",
            "total_invoices": total_invoices,
            "total_line_items": total_line_items,
            "recent_uploads_24h": recent_uploads,
            "error_rate_percent": error_rate,
            "last_check": datetime.now().isoformat()
        }
        
        # Determine overall health status
        if error_rate > 10:  # More than 10% error rate
            health_metrics["overall_status"] = "warning"
        elif error_rate > 20:  # More than 20% error rate
            health_metrics["overall_status"] = "critical"
        else:
            health_metrics["overall_status"] = "healthy"
        
        conn.close()
        
        return health_metrics
        
    except Exception as e:
        return {
            "database_status": "error",
            "error": str(e),
            "overall_status": "critical",
            "last_check": datetime.now().isoformat()
        } 