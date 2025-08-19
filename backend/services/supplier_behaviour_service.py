from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import sqlite3
import os
import json

from contracts import (
    SupplierEventRequest, SupplierEventResponse, SupplierEvent,
    SupplierEventsResponse, SupplierInsight, SupplierInsightsResponse,
    SupplierAlert, SupplierAlertsResponse
)


def get_db_connection():
    """Get database connection for supplier behaviour data."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "owlin.db")
    return sqlite3.connect(db_path)


def log_event(request: SupplierEventRequest, user_id: str) -> SupplierEventResponse:
    """
    Log a supplier event and trigger insights recalculation.
    
    Args:
        request: Event details
        user_id: ID of user creating the event
        
    Returns:
        Event creation response
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Ensure tables exist
        _ensure_tables(cursor)
        
        event_id = str(uuid4())
        created_at = datetime.utcnow().isoformat()
        
        # Insert event
        cursor.execute("""
            INSERT INTO supplier_events 
            (id, supplier_id, event_type, severity, description, source, created_at, created_by, is_acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            str(request.supplier_id),
            request.event_type,
            request.severity,
            request.description,
            request.source,
            created_at,
            user_id,
            False
        ))
        
        # Trigger insights recalculation
        recalculate_insights(str(request.supplier_id), conn)
        
        # Log audit
        _log_audit(cursor, user_id, "supplier.event", "supplier_event", event_id)
        
        conn.commit()
        conn.close()
        
        return SupplierEventResponse(
            ok=True,
            event_id=UUID(event_id),
            created_at=created_at
        )
        
    except Exception as e:
        print(f"Error logging supplier event: {e}")
        raise


def list_events(supplier_id: str, limit: int = 20) -> SupplierEventsResponse:
    """
    List events for a supplier.
    
    Args:
        supplier_id: Supplier ID
        limit: Maximum number of events to return (max 200)
        
    Returns:
        List of events
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Ensure tables exist
        _ensure_tables(cursor)
        
        # Cap limit at 200
        limit = min(limit, 200)
        
        cursor.execute("""
            SELECT id, event_type, severity, description, source, created_at, is_acknowledged
            FROM supplier_events 
            WHERE supplier_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (supplier_id, limit))
        
        events = []
        for row in cursor.fetchall():
            event_id, event_type, severity, description, source, created_at, is_acknowledged = row
            events.append(SupplierEvent(
                id=UUID(event_id),
                event_type=event_type,
                severity=severity,
                description=description,
                source=source,
                created_at=created_at,
                is_acknowledged=bool(is_acknowledged)
            ))
        
        conn.close()
        
        return SupplierEventsResponse(
            supplier_id=UUID(supplier_id),
            events=events
        )
        
    except Exception as e:
        print(f"Error listing supplier events: {e}")
        raise


def recalculate_insights(supplier_id: str, conn: sqlite3.Connection = None) -> List[SupplierInsight]:
    """
    Recalculate insights for a supplier based on recent events.
    
    Args:
        supplier_id: Supplier ID
        conn: Optional database connection (if None, creates new one)
        
    Returns:
        List of calculated insights
    """
    should_close = False
    try:
        if conn is None:
            conn = get_db_connection()
            should_close = True
        
        cursor = conn.cursor()
        
        # Ensure tables exist
        _ensure_tables(cursor)
        
        insights = []
        last_updated = datetime.utcnow().isoformat()
        
        # Get supplier name
        supplier_name = _get_supplier_name(cursor, supplier_id)
        if not supplier_name:
            return insights
        
        # Calculate missed deliveries percentage (90 days)
        missed_delivery_rate = _calculate_missed_delivery_rate(cursor, supplier_id, 90)
        if missed_delivery_rate is not None:
            trend = _calculate_trend(cursor, supplier_id, "missed_delivery_rate", missed_delivery_rate, 90)
            insights.append(SupplierInsight(
                metric_name="Missed Deliveries %",
                metric_value=missed_delivery_rate,
                trend_direction=trend["direction"],
                trend_percentage=trend["percentage"],
                period_days=90,
                last_updated=last_updated
            ))
        
        # Calculate invoice mismatch rate (90 days)
        mismatch_rate = _calculate_mismatch_rate(cursor, supplier_id, 90)
        if mismatch_rate is not None:
            trend = _calculate_trend(cursor, supplier_id, "mismatch_rate", mismatch_rate, 90)
            insights.append(SupplierInsight(
                metric_name="Invoice Mismatch Rate",
                metric_value=mismatch_rate,
                trend_direction=trend["direction"],
                trend_percentage=trend["percentage"],
                period_days=90,
                last_updated=last_updated
            ))
        
        # Calculate price spike detection (90 days)
        price_spike_rate = _calculate_price_spike_rate(cursor, supplier_id, 90)
        if price_spike_rate is not None:
            trend = _calculate_trend(cursor, supplier_id, "price_spike_rate", price_spike_rate, 90)
            insights.append(SupplierInsight(
                metric_name="Price Spike Rate",
                metric_value=price_spike_rate,
                trend_direction=trend["direction"],
                trend_percentage=trend["percentage"],
                period_days=90,
                last_updated=last_updated
            ))
        
        # Store insights
        _store_insights(cursor, supplier_id, insights)
        
        if should_close:
            conn.commit()
            conn.close()
        
        return insights
        
    except Exception as e:
        print(f"Error recalculating insights: {e}")
        if should_close and conn:
            conn.close()
        return []


def get_insights(supplier_id: str) -> SupplierInsightsResponse:
    """
    Get stored insights for a supplier.
    
    Args:
        supplier_id: Supplier ID
        
    Returns:
        Stored insights
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Ensure tables exist
        _ensure_tables(cursor)
        
        cursor.execute("""
            SELECT metric_name, metric_value, trend_direction, trend_percentage, period_days, last_updated
            FROM supplier_insights 
            WHERE supplier_id = ?
            ORDER BY last_updated DESC
        """, (supplier_id,))
        
        insights = []
        for row in cursor.fetchall():
            metric_name, metric_value, trend_direction, trend_percentage, period_days, last_updated = row
            insights.append(SupplierInsight(
                metric_name=metric_name,
                metric_value=metric_value,
                trend_direction=trend_direction,
                trend_percentage=trend_percentage,
                period_days=period_days,
                last_updated=last_updated
            ))
        
        conn.close()
        
        return SupplierInsightsResponse(
            supplier_id=UUID(supplier_id),
            insights=insights
        )
        
    except Exception as e:
        print(f"Error getting supplier insights: {e}")
        raise


def list_alerts() -> SupplierAlertsResponse:
    """
    List suppliers with high severity or repeated recent issues.
    
    Returns:
        List of alerts
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Ensure tables exist
        _ensure_tables(cursor)
        
        alerts = []
        
        # Get suppliers with high severity events in last 30 days
        cursor.execute("""
            SELECT DISTINCT se.supplier_id, s.name as supplier_name
            FROM supplier_events se
            LEFT JOIN suppliers s ON se.supplier_id = s.id
            WHERE se.severity = 'high' 
            AND se.created_at >= datetime('now', '-30 days')
        """)
        
        high_severity_suppliers = cursor.fetchall()
        
        for supplier_id, supplier_name in high_severity_suppliers:
            if not supplier_name:
                supplier_name = f"Supplier {supplier_id[:8]}"
            
            # Count high severity events
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM supplier_events 
                WHERE supplier_id = ? 
                AND severity = 'high' 
                AND created_at >= datetime('now', '-30 days')
            """, (supplier_id,))
            
            count = cursor.fetchone()[0]
            
            if count >= 2:
                alerts.append(SupplierAlert(
                    supplier_id=UUID(supplier_id),
                    supplier_name=supplier_name,
                    alert_type="high_severity_cluster",
                    severity="high",
                    summary=f"{count} high severity events in 30 days"
                ))
        
        # Get suppliers with missed delivery clusters
        cursor.execute("""
            SELECT DISTINCT se.supplier_id, s.name as supplier_name
            FROM supplier_events se
            LEFT JOIN suppliers s ON se.supplier_id = s.id
            WHERE se.event_type = 'missed_delivery' 
            AND se.created_at >= datetime('now', '-45 days')
        """)
        
        missed_delivery_suppliers = cursor.fetchall()
        
        for supplier_id, supplier_name in missed_delivery_suppliers:
            if not supplier_name:
                supplier_name = f"Supplier {supplier_id[:8]}"
            
            # Count missed deliveries
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM supplier_events 
                WHERE supplier_id = ? 
                AND event_type = 'missed_delivery' 
                AND created_at >= datetime('now', '-45 days')
            """, (supplier_id,))
            
            count = cursor.fetchone()[0]
            
            if count >= 3:
                alerts.append(SupplierAlert(
                    supplier_id=UUID(supplier_id),
                    supplier_name=supplier_name,
                    alert_type="missed_deliveries_cluster",
                    severity="medium",
                    summary=f"{count} missed deliveries in 45 days"
                ))
        
        conn.close()
        
        return SupplierAlertsResponse(alerts=alerts)
        
    except Exception as e:
        print(f"Error listing alerts: {e}")
        raise


def _ensure_tables(cursor: sqlite3.Cursor):
    """Ensure required tables exist."""
    # supplier_events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier_events (
            id TEXT PRIMARY KEY,
            supplier_id TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type IN ('missed_delivery', 'invoice_mismatch', 'late_delivery', 'quality_issue', 'price_spike')),
            severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
            description TEXT,
            source TEXT NOT NULL CHECK (source IN ('invoice_audit', 'manual', 'system')),
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            is_acknowledged BOOLEAN DEFAULT FALSE
        )
    """)
    
    # supplier_insights table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier_insights (
            id TEXT PRIMARY KEY,
            supplier_id TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            trend_direction TEXT NOT NULL CHECK (trend_direction IN ('up', 'down', 'flat')),
            trend_percentage REAL NOT NULL,
            period_days INTEGER NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_supplier_events_sup_type ON supplier_events(supplier_id, event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_supplier_events_created ON supplier_events(created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_supplier_insights_sup_updated ON supplier_insights(supplier_id, last_updated)")


def _get_supplier_name(cursor: sqlite3.Cursor, supplier_id: str) -> Optional[str]:
    """Get supplier name from ID."""
    try:
        # Try suppliers table first
        cursor.execute("SELECT name FROM suppliers WHERE id = ?", (supplier_id,))
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
        
        # Fallback to invoices table
        cursor.execute("SELECT DISTINCT supplier_name FROM invoices WHERE supplier_name IS NOT NULL LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None
        
    except Exception:
        return None


def _calculate_missed_delivery_rate(cursor: sqlite3.Cursor, supplier_id: str, days: int) -> Optional[float]:
    """Calculate missed delivery rate for a supplier."""
    try:
        # Count missed delivery events
        cursor.execute("""
            SELECT COUNT(*) 
            FROM supplier_events 
            WHERE supplier_id = ? 
            AND event_type = 'missed_delivery' 
            AND created_at >= datetime('now', '-{} days')
        """.format(days), (supplier_id,))
        
        missed_count = cursor.fetchone()[0]
        
        # Count total delivery events (missed + successful)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM supplier_events 
            WHERE supplier_id = ? 
            AND event_type IN ('missed_delivery', 'late_delivery') 
            AND created_at >= datetime('now', '-{} days')
        """.format(days), (supplier_id,))
        
        total_count = cursor.fetchone()[0]
        
        if total_count == 0:
            return 0.0
        
        return (missed_count / total_count) * 100
        
    except Exception:
        return None


def _calculate_mismatch_rate(cursor: sqlite3.Cursor, supplier_id: str, days: int) -> Optional[float]:
    """Calculate invoice mismatch rate for a supplier."""
    try:
        # Count mismatch events
        cursor.execute("""
            SELECT COUNT(*) 
            FROM supplier_events 
            WHERE supplier_id = ? 
            AND event_type = 'invoice_mismatch' 
            AND created_at >= datetime('now', '-{} days')
        """.format(days), (supplier_id,))
        
        mismatch_count = cursor.fetchone()[0]
        
        # Count total invoices (approximate from events)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM supplier_events 
            WHERE supplier_id = ? 
            AND created_at >= datetime('now', '-{} days')
        """.format(days), (supplier_id,))
        
        total_count = cursor.fetchone()[0]
        
        if total_count == 0:
            return 0.0
        
        return (mismatch_count / total_count) * 100
        
    except Exception:
        return None


def _calculate_price_spike_rate(cursor: sqlite3.Cursor, supplier_id: str, days: int) -> Optional[float]:
    """Calculate price spike rate for a supplier."""
    try:
        # Count price spike events
        cursor.execute("""
            SELECT COUNT(*) 
            FROM supplier_events 
            WHERE supplier_id = ? 
            AND event_type = 'price_spike' 
            AND created_at >= datetime('now', '-{} days')
        """.format(days), (supplier_id,))
        
        spike_count = cursor.fetchone()[0]
        
        # Count total events
        cursor.execute("""
            SELECT COUNT(*) 
            FROM supplier_events 
            WHERE supplier_id = ? 
            AND created_at >= datetime('now', '-{} days')
        """.format(days), (supplier_id,))
        
        total_count = cursor.fetchone()[0]
        
        if total_count == 0:
            return 0.0
        
        return (spike_count / total_count) * 100
        
    except Exception:
        return None


def _calculate_trend(cursor: sqlite3.Cursor, supplier_id: str, metric_name: str, current_value: float, days: int) -> Dict[str, Any]:
    """Calculate trend for a metric."""
    try:
        # Get previous period value
        cursor.execute("""
            SELECT metric_value 
            FROM supplier_insights 
            WHERE supplier_id = ? 
            AND metric_name = ? 
            AND period_days = ?
            ORDER BY last_updated DESC 
            LIMIT 1
        """, (supplier_id, metric_name, days))
        
        row = cursor.fetchone()
        if not row:
            return {"direction": "flat", "percentage": 0.0}
        
        previous_value = row[0]
        
        if previous_value == 0:
            if current_value > 0:
                return {"direction": "up", "percentage": 100.0}
            else:
                return {"direction": "flat", "percentage": 0.0}
        
        change_percentage = ((current_value - previous_value) / previous_value) * 100
        
        if change_percentage > 5:
            return {"direction": "up", "percentage": abs(change_percentage)}
        elif change_percentage < -5:
            return {"direction": "down", "percentage": abs(change_percentage)}
        else:
            return {"direction": "flat", "percentage": abs(change_percentage)}
            
    except Exception:
        return {"direction": "flat", "percentage": 0.0}


def _store_insights(cursor: sqlite3.Cursor, supplier_id: str, insights: List[SupplierInsight]):
    """Store insights in database."""
    for insight in insights:
        insight_id = str(uuid4())
        cursor.execute("""
            INSERT OR REPLACE INTO supplier_insights 
            (id, supplier_id, metric_name, metric_value, trend_direction, trend_percentage, period_days, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            insight_id,
            supplier_id,
            insight.metric_name,
            insight.metric_value,
            insight.trend_direction,
            insight.trend_percentage,
            insight.period_days,
            insight.last_updated
        ))


def _log_audit(cursor: sqlite3.Cursor, user_id: str, action: str, entity_type: str, entity_id: str):
    """Log audit event."""
    try:
        cursor.execute("""
            INSERT INTO audit_log (user_id, action, entity_type, entity_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, action, entity_type, entity_id, datetime.utcnow().isoformat()))
    except Exception:
        # Audit logging is optional
        pass 