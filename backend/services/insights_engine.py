from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from uuid import UUID
import sqlite3
import os
import statistics

# Define Insight class locally to avoid circular imports
class Insight:
    def __init__(self, type: str, severity: str, message: str, recommendation: str):
        self.type = type
        self.severity = severity
        self.message = message
        self.recommendation = recommendation

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

def generate_insights(supplier_id: UUID, range_days: int = 90) -> List[Insight]:
    """
    Generate insights for a supplier based on their performance data.
    
    Args:
        supplier_id: The supplier UUID
        range_days: Number of days to analyze (default 90)
        
    Returns:
        List of Insight objects with type, severity, message, and recommendation
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get supplier name from ID
        supplier_name = _get_supplier_name_from_id(cursor, str(supplier_id))
        if not supplier_name:
            return []
        
        insights = []
        
        # 1. Price increase detection
        price_insight = _detect_price_increases(cursor, supplier_name, range_days)
        if price_insight:
            insights.append(price_insight)
        
        # 2. Delivery delays detection
        delivery_insight = _detect_delivery_delays(cursor, supplier_name, range_days)
        if delivery_insight:
            insights.append(delivery_insight)
        
        # 3. Credit response time detection
        credit_insight = _detect_credit_slow_response(cursor, supplier_name, range_days)
        if credit_insight:
            insights.append(credit_insight)
        
        # 4. Preferred supplier inactivity detection
        inactivity_insight = _detect_preferred_inactivity(cursor, supplier_name, range_days)
        if inactivity_insight:
            insights.append(inactivity_insight)
        
        # 5. Aggregate multiple low-severity issues
        aggregated_insight = _aggregate_low_severity_insights(insights)
        if aggregated_insight:
            # Remove individual low-severity insights and add aggregated one
            insights = [insight for insight in insights if insight.severity != "low"]
            insights.append(aggregated_insight)
        
        conn.close()
        return insights
        
    except Exception as e:
        print(f"Error generating insights: {e}")
        return []

def _get_supplier_name_from_id(cursor: sqlite3.Cursor, supplier_id: str) -> Optional[str]:
    """Get supplier name from supplier ID."""
    try:
        # Try to get from flagged_issues table first
        cursor.execute("SELECT DISTINCT supplier_name FROM flagged_issues WHERE supplier_id = ?", (supplier_id,))
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
        
        # Fallback: try to find by UUID hash (this is a simplified approach)
        # In a real system, you'd have a proper suppliers table
        cursor.execute("SELECT DISTINCT supplier_name FROM invoices WHERE supplier_name IS NOT NULL LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None
        
    except Exception:
        return None

def _detect_price_increases(cursor: sqlite3.Cursor, supplier_name: str, range_days: int) -> Optional[Insight]:
    """Detect significant price increases over the last 60 days."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        # Get average prices for recent vs previous period
        cursor.execute("""
            SELECT AVG(ili.unit_price) as avg_price
            FROM invoice_line_items ili
            JOIN invoices i ON ili.invoice_id = i.id
            WHERE i.supplier_name = ? 
            AND i.invoice_date >= ? 
            AND i.invoice_date <= ?
            AND ili.unit_price > 0
        """, (supplier_name, start_date.date(), end_date.date()))
        
        recent_avg = cursor.fetchone()[0] or 0
        
        # Get average prices for previous 60 days
        prev_start = start_date - timedelta(days=60)
        cursor.execute("""
            SELECT AVG(ili.unit_price) as avg_price
            FROM invoice_line_items ili
            JOIN invoices i ON ili.invoice_id = i.id
            WHERE i.supplier_name = ? 
            AND i.invoice_date >= ? 
            AND i.invoice_date < ?
            AND ili.unit_price > 0
        """, (supplier_name, prev_start.date(), start_date.date()))
        
        previous_avg = cursor.fetchone()[0] or 0
        
        if previous_avg > 0 and recent_avg > 0:
            increase_pct = ((recent_avg - previous_avg) / previous_avg) * 100
            
            if increase_pct > 10:
                severity = "high" if increase_pct > 20 else "medium"
                return Insight(
                    type="price_increase",
                    severity=severity,
                    message=f"Average item price has increased by {increase_pct:.1f}% over the last 60 days.",
                    recommendation="Review pricing agreements and consider negotiating better rates."
                )
        
        return None
        
    except Exception:
        return None

def _detect_delivery_delays(cursor: sqlite3.Cursor, supplier_name: str, range_days: int) -> Optional[Insight]:
    """Detect delivery delays and on-time delivery drops."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Get recent delivery performance
        cursor.execute("""
            SELECT COUNT(*) as total_deliveries,
                   SUM(CASE WHEN status = 'matched' THEN 1 ELSE 0 END) as on_time_deliveries
            FROM delivery_notes
            WHERE supplier_name = ? 
            AND created_at >= ?
            AND created_at <= ?
        """, (supplier_name, start_date.date(), end_date.date()))
        
        row = cursor.fetchone()
        if not row or row[0] == 0:
            return None
            
        total_deliveries = row[0]
        on_time_deliveries = row[1] or 0
        recent_on_time_pct = (on_time_deliveries / total_deliveries) * 100
        
        # Get previous period for comparison
        prev_start = start_date - timedelta(days=30)
        cursor.execute("""
            SELECT COUNT(*) as total_deliveries,
                   SUM(CASE WHEN status = 'matched' THEN 1 ELSE 0 END) as on_time_deliveries
            FROM delivery_notes
            WHERE supplier_name = ? 
            AND created_at >= ?
            AND created_at < ?
        """, (supplier_name, prev_start.date(), start_date.date()))
        
        prev_row = cursor.fetchone()
        if prev_row and prev_row[0] > 0:
            prev_on_time_pct = ((prev_row[1] or 0) / prev_row[0]) * 100
            drop_pct = prev_on_time_pct - recent_on_time_pct
            
            if drop_pct > 5:
                severity = "high" if drop_pct > 15 else "medium" if drop_pct > 10 else "low"
                return Insight(
                    type="delivery_delays",
                    severity=severity,
                    message=f"On-time delivery dropped from {prev_on_time_pct:.0f}% to {recent_on_time_pct:.0f}% in the past month.",
                    recommendation="Contact supplier to discuss delivery performance and set improvement targets."
                )
        
        # Check if current on-time rate is below threshold
        if recent_on_time_pct < 85:
            severity = "high" if recent_on_time_pct < 70 else "medium"
            return Insight(
                type="delivery_delays",
                severity=severity,
                message=f"On-time delivery rate is {recent_on_time_pct:.0f}%, below the 85% threshold.",
                recommendation="Escalate delivery issues and consider alternative suppliers if performance doesn't improve."
            )
        
        return None
        
    except Exception:
        return None

def _detect_credit_slow_response(cursor: sqlite3.Cursor, supplier_name: str, range_days: int) -> Optional[Insight]:
    """Detect slow credit response times (average > 5 days over last 60 days)."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        # Get flagged issues with credit response times
        cursor.execute("""
            SELECT AVG(JULIANDAY(resolved_at) - JULIANDAY(created_at)) as avg_response_days
            FROM flagged_issues
            WHERE supplier_name = ? 
            AND created_at >= ?
            AND created_at <= ?
            AND resolved_at IS NOT NULL
            AND type IN ('PRICE_MISMATCH','MISSING_ITEM','EXTRA_ITEM')
        """, (supplier_name, start_date.date(), end_date.date()))
        
        avg_response_days = cursor.fetchone()[0]
        
        if avg_response_days and avg_response_days > 5:
            severity = "high" if avg_response_days > 10 else "medium"
            return Insight(
                type="credit_slow",
                severity=severity,
                message=f"Average credit response time is {avg_response_days:.1f} days, exceeding the 5-day target.",
                recommendation="Follow up on pending credit requests and establish clear response time expectations."
            )
        
        return None
        
    except Exception:
        return None

def _detect_preferred_inactivity(cursor: sqlite3.Cursor, supplier_name: str, range_days: int) -> Optional[Insight]:
    """Detect if preferred supplier spend has dropped significantly."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # Get current quarter spend
        cursor.execute("""
            SELECT SUM(total_amount) as current_spend
            FROM invoices
            WHERE supplier_name = ? 
            AND invoice_date >= ?
            AND invoice_date <= ?
        """, (supplier_name, start_date.date(), end_date.date()))
        
        current_spend = cursor.fetchone()[0] or 0
        
        # Get previous quarter spend
        prev_start = start_date - timedelta(days=90)
        cursor.execute("""
            SELECT SUM(total_amount) as previous_spend
            FROM invoices
            WHERE supplier_name = ? 
            AND invoice_date >= ?
            AND invoice_date < ?
        """, (supplier_name, prev_start.date(), start_date.date()))
        
        previous_spend = cursor.fetchone()[0] or 0
        
        if previous_spend > 0 and current_spend > 0:
            drop_pct = ((previous_spend - current_spend) / previous_spend) * 100
            
            if drop_pct > 50:
                return Insight(
                    type="preferred_inactivity",
                    severity="medium",
                    message=f"Spend with this preferred supplier has dropped by {drop_pct:.0f}% compared to the previous quarter.",
                    recommendation="Review supplier relationship and consider re-engaging or finding alternative suppliers."
                )
        
        return None
        
    except Exception:
        return None

def _aggregate_low_severity_insights(insights: List[Insight]) -> Optional[Insight]:
    """Aggregate multiple low-severity insights into a single insight."""
    low_severity_insights = [insight for insight in insights if insight.severity == "low"]
    
    if len(low_severity_insights) >= 2:
        issue_types = [insight.type for insight in low_severity_insights]
        unique_issues = list(set(issue_types))
        
        return Insight(
            type="multiple_issues",
            severity="medium",
            message=f"Multiple minor issues detected: {', '.join(unique_issues)}. Consider addressing these proactively.",
            recommendation="Schedule a supplier review meeting to address these issues before they escalate."
        )
    
    return None 