from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional, Any
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
        
        # Check if venue column exists
        cursor.execute("PRAGMA table_info(invoices)")
        columns = [col[1] for col in cursor.fetchall()]
        has_venue = 'venue' in columns
        
        # Get overall system metrics
        if has_venue:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_invoices,
                    SUM(total_amount) as total_value,
                    COUNT(CASE WHEN status = 'matched' THEN 1 END) as matched_invoices,
                    COUNT(CASE WHEN status = 'discrepancy' THEN 1 END) as discrepancy_invoices,
                    COUNT(CASE WHEN status = 'not_paired' THEN 1 END) as not_paired_invoices,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_invoices,
                    COUNT(DISTINCT supplier_name) as total_suppliers,
                    COUNT(DISTINCT venue) as total_venues
                FROM invoices
            """)
        else:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_invoices,
                    SUM(total_amount) as total_value,
                    COUNT(CASE WHEN status = 'matched' THEN 1 END) as matched_invoices,
                    COUNT(CASE WHEN status = 'discrepancy' THEN 1 END) as discrepancy_invoices,
                    COUNT(CASE WHEN status = 'not_paired' THEN 1 END) as not_paired_invoices,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_invoices,
                    COUNT(DISTINCT supplier_name) as total_suppliers,
                    0 as total_venues
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
        
        # Check if invoice_line_items table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoice_line_items'")
        has_line_items = cursor.fetchone() is not None
        
        # Get flagged issues summary
        if has_line_items:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_flagged,
                    SUM(ABS(quantity * unit_price)) as total_error_value,
                    COUNT(DISTINCT invoice_id) as affected_invoices
                FROM invoice_line_items 
                WHERE flagged = 1
            """)
            flagged_row = cursor.fetchone()
        else:
            # If no line_items table, return zeros
            flagged_row = (0, 0.0, 0)
        
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
                SUM(total_amount) as daily_value
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
                supplier_name,
                COUNT(*) as invoice_count,
                SUM(total_amount) as total_value
            FROM invoices 
            WHERE supplier_name IS NOT NULL AND supplier_name != ''
            GROUP BY supplier_name
            ORDER BY total_value DESC
            LIMIT 10
        """)
        
        top_suppliers = []
        for supplier_row in cursor.fetchall():
            supplier = {
                "name": supplier_row[0],
                "invoice_count": supplier_row[1],
                "total_value": float(supplier_row[2]) if supplier_row[2] else 0.0
            }
            top_suppliers.append(supplier)
        
        # Get venue breakdown (if venue column exists)
        venue_breakdown = []
        if has_venue:
            cursor.execute("""
                SELECT 
                    venue,
                    COUNT(*) as invoice_count,
                    SUM(total_amount) as total_value
                FROM invoices 
                WHERE venue IS NOT NULL AND venue != ''
                GROUP BY venue
                ORDER BY total_value DESC
            """)
            
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
                SUM(total_amount) as daily_value,
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
                SUM(total_amount) as weekly_value,
                AVG(total_amount) as avg_invoice_value
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
                AVG(total_amount) as avg_invoice_value,
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
        
        # Check if invoice_line_items table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoice_line_items'")
        has_line_items = cursor.fetchone() is not None
        
        # Get line items count
        if has_line_items:
            cursor.execute("SELECT COUNT(*) FROM invoice_line_items")
            line_items_count = cursor.fetchone()[0] or 0
        else:
            line_items_count = 0
        
        # Get flagged items count
        if has_line_items:
            cursor.execute("SELECT COUNT(*) FROM invoice_line_items WHERE flagged = 1")
            flagged_items_count = cursor.fetchone()[0] or 0
        else:
            flagged_items_count = 0
        
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
        
        cursor.execute("SELECT COUNT(*) FROM invoice_line_items")
        total_line_items = cursor.fetchone()[0]
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        cursor.execute("SELECT COUNT(*) FROM invoices WHERE upload_timestamp >= ?", (yesterday,))
        recent_uploads = cursor.fetchone()[0]
        
        # Get error rate
        cursor.execute("SELECT COUNT(*) FROM invoice_line_items WHERE flagged = 1")
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

@router.get("/spend-summary")
async def get_spend_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    venue: Optional[str] = None,
    supplier: Optional[str] = None
):
    """Total spend for a range with prior period delta."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if venue column exists
        cursor.execute("PRAGMA table_info(invoices)")
        columns = [col[1] for col in cursor.fetchall()]
        has_venue = 'venue' in columns

        conditions = []
        params: List[Any] = []

        if start_date:
            conditions.append("DATE(invoice_date) >= DATE(?)")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(invoice_date) <= DATE(?)")
            params.append(end_date)
        if venue and has_venue:
            conditions.append("venue = ?")
            params.append(venue)
        if supplier:
            conditions.append("supplier_name = ?")
            params.append(supplier)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Current period spend
        cursor.execute(
            f"""
            SELECT IFNULL(SUM(total_amount), 0)
            FROM invoices
            {where_clause}
            """,
            params,
        )
        current_spend_row = cursor.fetchone()
        current_spend = float(current_spend_row[0] or 0.0)

        # Compute prior period window if date range provided
        prior_spend = 0.0
        if start_date and end_date:
            cursor.execute("SELECT julianday(?) - julianday(?)", (end_date, start_date))
            days_range_row = cursor.fetchone()
            try:
                days_len = int(round(days_range_row[0])) if days_range_row and days_range_row[0] else 0
            except Exception:
                days_len = 0
            if days_len > 0:
                prior_conditions = []
                prior_params = []
                if start_date:
                    prior_conditions.append("DATE(invoice_date) >= DATE(?, -?)")
                    prior_params.extend([start_date, days_len])
                if start_date:
                    prior_conditions.append("DATE(invoice_date) < DATE(?)")
                    prior_params.append(start_date)
                if venue and has_venue:
                    prior_conditions.append("venue = ?")
                    prior_params.append(venue)
                if supplier:
                    prior_conditions.append("supplier_name = ?")
                    prior_params.append(supplier)
                
                prior_where = f"WHERE {' AND '.join(prior_conditions)}" if prior_conditions else ""
                
                cursor.execute(
                    f"""
                    SELECT IFNULL(SUM(total_amount), 0)
                    FROM invoices
                    {prior_where}
                    """,
                    prior_params,
                )
                row = cursor.fetchone()
                prior_spend = float(row[0] or 0.0)

        delta_pct = 0.0 if prior_spend == 0 else round(((current_spend - prior_spend) / prior_spend) * 100.0, 1)

        conn.close()
        return {
            "total_spend": current_spend,
            "prior_spend": prior_spend,
            "delta_percent": delta_pct,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/spend-by-supplier")
async def get_spend_by_supplier(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    venue: Optional[str] = None,
    limit: int = 10
):
    """Top suppliers by spend with 'other' bucket."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if venue column exists
        cursor.execute("PRAGMA table_info(invoices)")
        columns = [col[1] for col in cursor.fetchall()]
        has_venue = 'venue' in columns

        conditions = []
        params: List[Any] = []
        if start_date:
            conditions.append("DATE(invoice_date) >= DATE(?)")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(invoice_date) <= DATE(?)")
            params.append(end_date)
        if venue and has_venue:
            conditions.append("venue = ?")
            params.append(venue)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor.execute(
            f"""
            SELECT supplier_name, IFNULL(SUM(total_amount), 0) AS total_value
            FROM invoices
            {where_clause}
            GROUP BY supplier_name
            ORDER BY total_value DESC
            """,
            params,
        )
        rows = cursor.fetchall()

        total_sum = sum(float(r[1] or 0.0) for r in rows)
        top = []
        other_sum = 0.0
        for idx, r in enumerate(rows):
            value = float(r[1] or 0.0)
            if idx < max(0, limit):
                top.append({"supplier": r[0] or "Unknown", "total_value": value})
            else:
                other_sum += value
        if other_sum > 0:
            top.append({"supplier": "Other", "total_value": other_sum})

        conn.close()
        return {"total": total_sum, "suppliers": top}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/match-rate")
async def get_match_rate(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    venue: Optional[str] = None,
    supplier: Optional[str] = None
):
    """3-Way match rate breakdown: Passed / Issues / Failed."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if venue column exists
        cursor.execute("PRAGMA table_info(invoices)")
        columns = [col[1] for col in cursor.fetchall()]
        has_venue = 'venue' in columns

        conditions = []
        params: List[Any] = []
        if start_date:
            conditions.append("DATE(invoice_date) >= DATE(?)")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(invoice_date) <= DATE(?)")
            params.append(end_date)
        if venue and has_venue:
            conditions.append("venue = ?")
            params.append(venue)
        if supplier:
            conditions.append("supplier_name = ?")
            params.append(supplier)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor.execute(
            f"""
            SELECT 
              COUNT(*) AS total,
              COUNT(CASE WHEN status = 'matched' THEN 1 END) AS passed,
              COUNT(CASE WHEN status = 'discrepancy' THEN 1 END) AS issues,
              COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed
            FROM invoices
            {where_clause}
            """,
            params,
        )
        row = cursor.fetchone()
        total = int(row[0] or 0)
        passed = int(row[1] or 0)
        issues = int(row[2] or 0)
        failed = int(row[3] or 0)
        rate = 0.0 if total == 0 else round((passed / total) * 100.0, 1)
        conn.close()
        return {"total": total, "passed": passed, "issues": issues, "failed": failed, "rate_percent": rate}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/issues-by-type")
async def get_issues_by_type(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    venue: Optional[str] = None,
):
    """Issues by type based on invoice_line_items.flagged and source field if available."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if invoice_line_items table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoice_line_items'")
        has_line_items = cursor.fetchone() is not None
        
        if has_line_items:
            # Get issues by type from invoice_line_items
            cursor.execute("""
                SELECT 
                    COALESCE(source, 'unknown') as issue_type,
                    COUNT(*) as count
                FROM invoice_line_items ili
                WHERE flagged = 1
                GROUP BY COALESCE(source, 'unknown')
                ORDER BY count DESC
            """)
            
            issues = []
            for row in cursor.fetchall():
                issues.append({
                    "issue_type": row[0],
                    "count": row[1]
                })
            
            total_flagged_items = sum(issue["count"] for issue in issues)
        else:
            # If no line_items table, return empty results
            issues = []
            total_flagged_items = 0

        conn.close()
        return {"issues": issues, "total_flagged_items": total_flagged_items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/duplicates-summary")
async def get_duplicates_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Count potential duplicate invoices and sum of blocked totals (beyond first occurrence)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        conditions = []
        params: List[Any] = []
        if start_date:
            conditions.append("DATE(invoice_date) >= DATE(?)")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(invoice_date) <= DATE(?)")
            params.append(end_date)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor.execute(
            f"""
            SELECT supplier_name, invoice_number, COUNT(*) as cnt, SUM(total_amount) as sum_amount
            FROM invoices
            {where_clause}
            GROUP BY supplier_name, invoice_number
            HAVING cnt > 1
            ORDER BY cnt DESC
            """,
            params,
        )
        rows = cursor.fetchall()
        duplicate_groups = []
        prevented_value = 0.0
        prevented_count = 0
        for r in rows:
            cnt = int(r[2] or 0)
            total_sum = float(r[3] or 0.0)
            # Assume first is legitimate, extras are prevented
            if cnt > 1:
                prevented_count += (cnt - 1)
                avg_value = total_sum / cnt if cnt else 0.0
                prevented_value += avg_value * (cnt - 1)
                duplicate_groups.append({
                    "supplier_name": r[0] or "Unknown",
                    "invoice_number": r[1] or "Unknown",
                    "count": cnt,
                    "total_sum": total_sum,
                })
        conn.close()
        return {
            "duplicates_prevented": prevented_count,
            "prevented_value": round(prevented_value, 2),
            "groups": duplicate_groups,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/unmatched-counts")
async def get_unmatched_counts(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    venue: Optional[str] = None,
):
    """Counts of paired / needs review / unmatched based on invoice status fields."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if venue column exists
        cursor.execute("PRAGMA table_info(invoices)")
        columns = [col[1] for col in cursor.fetchall()]
        has_venue = 'venue' in columns

        conditions = []
        params: List[Any] = []
        if start_date:
            conditions.append("DATE(invoice_date) >= DATE(?)")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(invoice_date) <= DATE(?)")
            params.append(end_date)
        if venue and has_venue:
            conditions.append("venue = ?")
            params.append(venue)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Define mapping of statuses to buckets
        cursor.execute(
            f"""
            SELECT 
              COUNT(CASE WHEN status = 'matched' THEN 1 END) as paired,
              COUNT(CASE WHEN status IN ('discrepancy','review','processing') THEN 1 END) as needs_review,
              COUNT(CASE WHEN status IN ('not_paired','unmatched','failed') THEN 1 END) as unmatched
            FROM invoices
            {where_clause}
            """,
            params,
        )
        row = cursor.fetchone()
        conn.close()
        return {
            "paired": int(row[0] or 0),
            "needs_review": int(row[1] or 0),
            "unmatched": int(row[2] or 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/low-ocr")
async def get_low_ocr_summary(
    threshold: float = 0.7,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Count invoices where OCR confidence is below threshold (0-1 or 0-100 tolerant)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        conditions = []
        params: List[Any] = []
        if start_date:
            conditions.append("DATE(invoice_date) >= DATE(?)")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(invoice_date) <= DATE(?)")
            params.append(end_date)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Normalize threshold to 0-100
        thr_100 = threshold * 100.0 if threshold <= 1.0 else threshold

        cursor.execute(
            f"""
            SELECT 
              COUNT(*) as total,
              COUNT(CASE WHEN (CASE WHEN confidence <= 1.0 THEN confidence*100 ELSE confidence END) < ? THEN 1 END) as low_count
            FROM invoices
            {where_clause}
            """,
            params + [thr_100],
        )
        row = cursor.fetchone()
        total = int(row[0] or 0)
        low = int(row[1] or 0)
        conn.close()
        return {"total": total, "low_confidence": low, "threshold": thr_100}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/volatile-products")
async def get_volatile_products(
    days: int = 90,
    limit: int = 10,
):
    """Top volatile products by price over rolling N days using coefficient of variation (std/mean)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if invoice_line_items table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoice_line_items'")
        has_line_items = cursor.fetchone() is not None
        
        if not has_line_items:
            conn.close()
            return {"products": []}
        
        # Get products with price volatility
        cursor.execute("""
            SELECT 
                ili.item_description as product,
                i.supplier_name as supplier,
                AVG(ili.unit_price) as current_price,
                COUNT(*) as transactions
            FROM invoice_line_items ili
            JOIN invoices i ON ili.invoice_id = i.id
            WHERE ili.unit_price > 0
            AND i.invoice_date >= DATE('now', '-90 days')
            GROUP BY ili.item_description, i.supplier_name
            HAVING COUNT(*) >= 2
            ORDER BY COUNT(*) DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()

        # For stddev/mean we need per-transaction prices; compute with subqueries
        results: List[Dict[str, Any]] = []
        for r in rows:
            item = r[0]
            supplier = r[1]
            cursor.execute(
                """
                SELECT ili.unit_price
                FROM invoice_line_items ili
                JOIN invoices i ON ili.invoice_id = i.id
                WHERE ili.item_description = ?
                  AND i.supplier_name = ?
                  AND ili.unit_price IS NOT NULL
                  AND DATE(i.invoice_date) >= DATE('now', ?)
                """,
                (item, supplier, f"-{days} days"),
            )
            prices = [float(x[0]) for x in cursor.fetchall() if x and x[0] is not None]
            if len(prices) >= 3:
                import statistics
                mean_price = statistics.mean(prices)
                try:
                    std_price = statistics.pstdev(prices)
                except statistics.StatisticsError:
                    std_price = 0.0
                volatility = 0.0 if mean_price == 0 else std_price / mean_price
                results.append({
                    "product": item,
                    "supplier": supplier,
                    "current_price": round(prices[-1], 2),
                    "volatility_90d": round(volatility, 3),
                    "transactions": len(prices),
                })
        # Sort by volatility desc then limit
        results.sort(key=lambda x: x["volatility_90d"], reverse=True)
        conn.close()
        return {"products": results[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") 