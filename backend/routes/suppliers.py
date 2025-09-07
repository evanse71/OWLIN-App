from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Optional
import sqlite3
import os
from datetime import datetime, timedelta
import uuid
from uuid import UUID

# Import schemas using absolute path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.supplier import SupplierScorecard
from services.supplier_service import get_supplier_scorecard
from services.permissions import require_permission

try:
	from contracts import SupplierScorecard as SupplierScorecardV2
	from services.supplier_insights_service import compute_scorecard, recompute_metrics, list_insights as list_insights_feed, generate_insights_rules
	_HAS_V2 = True
except Exception:
	_HAS_V2 = False

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

@router.get("/scorecard")
async def get_supplier_scorecard():
    """Aggregated supplier scorecard metrics.
    Returns an array of objects with:
      supplier_id, supplier_name, total_invoices, match_rate, avg_invoice_confidence,
      total_flagged_issues, credit_value_pending, delivery_reliability_score, last_updated
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
 
        # Indexes for performance (idempotent)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_supplier ON invoices(supplier_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_delivery_supplier ON delivery_notes(supplier_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_delivery_status ON delivery_notes(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_flagged_supplier ON flagged_issues(supplier_id)")
 
        # Load suppliers list from invoices table (distinct)
        cursor.execute("SELECT DISTINCT COALESCE(supplier_name, '') FROM invoices WHERE supplier_name IS NOT NULL AND supplier_name != ''")
        supplier_rows = [r[0] for r in cursor.fetchall()]
 
        results: List[Dict] = []
        for supplier_name in supplier_rows:
            # Stable UUID from supplier name
            supplier_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"owlin:{supplier_name}"))
 
            # Total invoices
            cursor.execute("SELECT COUNT(*), SUM(CASE WHEN status='matched' THEN 1 ELSE 0 END), AVG(COALESCE(confidence,0)) FROM invoices WHERE supplier_name = ?", (supplier_name,))
            row = cursor.fetchone() or (0, 0, 0)
            total_invoices = int(row[0] or 0)
            matched_invoices = int(row[1] or 0)
            avg_conf = float(row[2] or 0.0)
            match_rate = round(100.0 * matched_invoices / total_invoices, 1) if total_invoices > 0 else 0.0
 
            # Flagged issues by supplier_id (may be 0 if supplier_id not set in issues)
            cursor.execute("SELECT COUNT(*) FROM flagged_issues WHERE supplier_id = ?", (supplier_id,))
            total_flagged = int((cursor.fetchone() or (0,))[0] or 0)
 
            # Credit value pending: conservative default 0.0 due to missing monetary linkage
            credit_value_pending = 0.0
 
            # Delivery reliability: percent of delivery notes with status 'matched' for this supplier
            cursor.execute("SELECT COUNT(*), SUM(CASE WHEN status='matched' THEN 1 ELSE 0 END) FROM delivery_notes WHERE supplier_name = ?", (supplier_name,))
            drow = cursor.fetchone() or (0, 0)
            total_dn = int(drow[0] or 0)
            matched_dn = int(drow[1] or 0)
            delivery_reliability = round(100.0 * matched_dn / total_dn, 1) if total_dn > 0 else 0.0
 
            # Last updated = latest invoice or delivery note timestamp if available; fallback now
            cursor.execute("SELECT MAX(COALESCE(updated_at, upload_timestamp)) FROM invoices WHERE supplier_name = ?", (supplier_name,))
            inv_ts = (cursor.fetchone() or (None,))[0]
            cursor.execute("SELECT MAX(updated_at) FROM delivery_notes WHERE supplier_name = ?", (supplier_name,))
            dn_ts = (cursor.fetchone() or (None,))[0]
            last_updated = inv_ts or dn_ts or datetime.utcnow().isoformat()
 
            results.append({
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "total_invoices": total_invoices,
                "match_rate": match_rate,
                "avg_invoice_confidence": round(avg_conf, 1),
                "total_flagged_issues": total_flagged,
                "credit_value_pending": credit_value_pending,
                "delivery_reliability_score": delivery_reliability,
                "last_updated": last_updated,
            })
 
        conn.close()
        return {"items": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{supplier_id}/scorecard", response_model=SupplierScorecardV2)
async def get_supplier_scorecard_v2(supplier_id: str, range_days: int = Query(90, ge=1, le=365)):
	"""Return SupplierScorecard per spec (overall score, categories, insights)."""
	try:
		if not _HAS_V2:
			raise HTTPException(status_code=500, detail="Scorecard service unavailable")
		# Compute fresh and generate insights (lightweight)
		generate_insights_rules(supplier_id)
		result = compute_scorecard(supplier_id)
		return result
	except HTTPException:
		raise
	except ValueError:
		raise HTTPException(status_code=404, detail="SUPPLIER_NOT_FOUND")
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"SCORECARD_FAILED: {e}")


@router.post("/{supplier_id}/resync-metrics")
async def resync_supplier_metrics(supplier_id: str, window: int = Query(90, ge=7, le=365)):
	"""Trigger recomputation of supplier metrics and insights."""
	try:
		if not _HAS_V2:
			raise HTTPException(status_code=500, detail="Service unavailable")
		recompute_metrics(supplier_id, window_days=window)
		generate_insights_rules(supplier_id)
		return {"ok": True}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Resync failed: {e}")


@router.get("/{supplier_id}/insights")
async def get_supplier_insights_feed(supplier_id: str, limit: int = Query(50, ge=1, le=200)):
	"""List latest narrative insights for a supplier."""
	try:
		if not _HAS_V2:
			raise HTTPException(status_code=500, detail="Service unavailable")
		items = list_insights_feed(supplier_id, limit=limit)
		return {"items": [i.dict() for i in items]}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to load insights: {e}") 