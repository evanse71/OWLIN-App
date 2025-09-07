from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from uuid import UUID
import sqlite3
import os
import uuid as uuid_lib

# Define Insight class locally to avoid circular imports
class Insight:
    def __init__(self, type: str, severity: str, message: str, recommendation: str):
        self.type = type
        self.severity = severity
        self.message = message
        self.recommendation = recommendation

# Import schemas using absolute path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.supplier import (
    SupplierProfile, SupplierMetrics, SupplierTrends, 
    TrendPoint, RiskRating, SupplierScorecard
)
from services.insights_engine import generate_insights

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

def get_supplier_scorecard(*, supplier_id: str, range_days: int = 90) -> SupplierScorecard:
    """
    Get comprehensive supplier scorecard with profile, metrics, trends, insights, and risk rating.
    
    Args:
        supplier_id: The supplier UUID
        range_days: Number of days to analyze (default 90)
        
    Returns:
        SupplierScorecard object with all components
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get supplier profile
        supplier = _get_supplier_profile(cursor, supplier_id)
        if not supplier:
            raise ValueError(f"Supplier not found: {supplier_id}")
        
        # Get metrics
        metrics = _get_supplier_metrics(cursor, supplier.name, range_days)
        
        # Get trends
        trends = _get_supplier_trends(cursor, supplier.name, range_days)
        
        # Generate insights
        insights = generate_insights(supplier_id, range_days)
        
        # Calculate risk rating
        risk_rating = _calculate_risk_rating(metrics, insights)
        
        conn.close()
        
        return SupplierScorecard(
            supplier=supplier,
            metrics=metrics,
            trends=trends,
            insights=insights,
            risk_rating=risk_rating,
            last_updated=datetime.now()
        )
        
    except Exception as e:
        print(f"Error getting supplier scorecard: {e}")
        raise

def _get_supplier_profile(cursor: sqlite3.Cursor, supplier_id: str) -> Optional[SupplierProfile]:
    """Get supplier profile information."""
    try:
        # Get supplier name from ID (simplified approach)
        supplier_name = _get_supplier_name_from_id(cursor, supplier_id)
        if not supplier_name:
            return None
        
        # For now, create a basic profile
        # In a real system, you'd have a proper suppliers table with contact info
        profile = SupplierProfile(
            id=UUID(str(uuid_lib.uuid5(uuid_lib.NAMESPACE_DNS, supplier_id))),  # Generate consistent UUID from name
            name=supplier_name,
            contact_name=None,  # Would come from suppliers table
            contact_email=None,  # Would come from suppliers table
            phone=None,  # Would come from suppliers table
            preferred=False  # Would come from suppliers table
        )
        return profile
        
    except Exception:
        return None

def _get_supplier_name_from_id(cursor: sqlite3.Cursor, supplier_id: str) -> Optional[str]:
    """Get supplier name from supplier ID."""
    try:
        # Check if the supplier exists in invoices table
        cursor.execute("SELECT DISTINCT supplier_name FROM invoices WHERE supplier_name = ?", (supplier_id,))
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
        
        # If not found, return None
        return None
        
    except Exception:
        return None

def _get_supplier_metrics(cursor: sqlite3.Cursor, supplier_name: str, range_days: int) -> SupplierMetrics:
    """Get supplier performance metrics."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=range_days)
        
        # Total spend
        cursor.execute("""
            SELECT SUM(total_amount) as total_spend
            FROM invoices
            WHERE supplier_name = ? 
            AND invoice_date >= ? 
            AND invoice_date <= ?
        """, (supplier_name, start_date.date(), end_date.date()))
        
        total_spend = cursor.fetchone()[0] or 0.0
        
        # Average delivery time (simplified - would need delivery_notes table with actual delivery dates)
        avg_delivery_time_days = 2.3  # Placeholder - would calculate from delivery_notes
        
        # Delivery on-time percentage (simplified - would need delivery_notes table)
        delivery_on_time_pct = 94.2  # Placeholder value
        
        # Mismatch rate (simplified - would need flagged_issues table)
        mismatch_rate_pct = 3.5  # Placeholder value
        
        # Credit response time (simplified)
        credit_response_days = 4.1  # Placeholder - would calculate from flagged_issues resolution times
        
        return SupplierMetrics(
            total_spend=float(total_spend),
            avg_delivery_time_days=avg_delivery_time_days,
            delivery_on_time_pct=delivery_on_time_pct,
            mismatch_rate_pct=mismatch_rate_pct,
            credit_response_days=credit_response_days
        )
        
    except Exception as e:
        print(f"Error getting supplier metrics: {e}")
        # Return default metrics on error
        return SupplierMetrics(
            total_spend=0.0,
            avg_delivery_time_days=0.0,
            delivery_on_time_pct=0.0,
            mismatch_rate_pct=0.0,
            credit_response_days=0.0
        )

def _get_supplier_trends(cursor: sqlite3.Cursor, supplier_name: str, range_days: int) -> SupplierTrends:
    """Get supplier historical trends."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=range_days)
        
        # Price history trends
        cursor.execute("""
            SELECT DATE(i.invoice_date) as date,
                   AVG(ili.unit_price) as avg_price
            FROM invoice_line_items ili
            JOIN invoices i ON ili.invoice_id = i.id
            WHERE i.supplier_name = ? 
            AND i.invoice_date >= ? 
            AND i.invoice_date <= ?
            AND ili.unit_price > 0
            GROUP BY DATE(i.invoice_date)
            ORDER BY date
        """, (supplier_name, start_date.date(), end_date.date()))
        
        price_history = []
        for row in cursor.fetchall():
            try:
                trend_date = datetime.strptime(row[0], '%Y-%m-%d').date()
                price_history.append(TrendPoint(
                    date=trend_date,
                    value=float(row[1] or 0)
                ))
            except Exception:
                continue
        
        # Delivery timeliness trends
        cursor.execute("""
            SELECT DATE(created_at) as date,
                   (SUM(CASE WHEN status = 'matched' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as on_time_pct
            FROM delivery_notes
            WHERE supplier_name = ? 
            AND created_at >= ? 
            AND created_at <= ?
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (supplier_name, start_date.date(), end_date.date()))
        
        delivery_timeliness = []
        for row in cursor.fetchall():
            try:
                trend_date = datetime.strptime(row[0], '%Y-%m-%d').date()
                delivery_timeliness.append(TrendPoint(
                    date=trend_date,
                    value=float(row[1] or 0)
                ))
            except Exception:
                continue
        
        return SupplierTrends(
            price_history=price_history,
            delivery_timeliness=delivery_timeliness
        )
        
    except Exception as e:
        print(f"Error getting supplier trends: {e}")
        return SupplierTrends(
            price_history=[],
            delivery_timeliness=[]
        )

def _calculate_risk_rating(metrics: SupplierMetrics, insights: List) -> RiskRating:
    """Calculate risk rating based on metrics and insights."""
    try:
        # Base risk score calculation
        # Weight: mismatch rate (40%), delivery delays (30%), price volatility (30%)
        
        # Mismatch rate component (40% weight)
        mismatch_score = min(metrics.mismatch_rate_pct * 2, 40)  # 20% mismatch = 40 points
        
        # Delivery delays component (30% weight)
        delivery_score = 0
        if metrics.delivery_on_time_pct < 85:
            delivery_score = (85 - metrics.delivery_on_time_pct) * 2  # 15% drop = 30 points
        delivery_score = min(delivery_score, 30)
        
        # Price volatility component (30% weight) - simplified
        price_score = 15  # Placeholder - would calculate from price history volatility
        
        # Insight severity adjustments
        insight_adjustment = 0
        for insight in insights:
            if insight.severity == "high":
                insight_adjustment += 10
            elif insight.severity == "medium":
                insight_adjustment += 5
            elif insight.severity == "low":
                insight_adjustment += 2
        
        # Calculate final score
        total_score = int(mismatch_score + delivery_score + price_score + insight_adjustment)
        total_score = min(max(total_score, 0), 100)  # Clamp to 0-100
        
        # Determine label and color
        if total_score >= 80:
            label = "High"
            color = "#d73a49"  # Red
        elif total_score >= 60:
            label = "Moderate"
            color = "#f5a623"  # Orange
        elif total_score >= 40:
            label = "Low"
            color = "#28a745"  # Green
        else:
            label = "Minimal"
            color = "#6f42c1"  # Purple
        
        return RiskRating(
            score=total_score,
            label=label,
            color=color
        )
        
    except Exception as e:
        print(f"Error calculating risk rating: {e}")
        return RiskRating(
            score=50,
            label="Unknown",
            color="#6c757d"
        ) 