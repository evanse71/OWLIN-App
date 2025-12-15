# -*- coding: utf-8 -*-
"""
Dashboard Routes
API endpoints for dashboard data: metrics, actions, suppliers, trends, unmatched DNs
"""

from __future__ import annotations
import logging
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
import numpy as np

from backend.app.db import DB_PATH

LOGGER = logging.getLogger("owlin.routes.dashboard")
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def get_date_range_filter(date_range: str) -> tuple[str, str]:
    """Convert date range string to start/end dates"""
    today = datetime.now().date()
    if date_range == 'today':
        start = today
        end = today
    elif date_range == '7d':
        start = today - timedelta(days=7)
        end = today
    elif date_range == '30d':
        start = today - timedelta(days=30)
        end = today
    elif date_range == '180d':
        start = today - timedelta(days=180)
        end = today
    elif date_range == '365d':
        start = today - timedelta(days=365)
        end = today
    else:
        start = today - timedelta(days=30)
        end = today
    return start.isoformat(), end.isoformat()


@router.get("/metrics")
async def get_metrics(
    venue_id: Optional[str] = Query(None),
    date_range: str = Query('30d')
) -> Dict[str, Any]:
    """Get dashboard metrics with period comparisons"""
    try:
        # Verify database exists
        if not os.path.exists(DB_PATH):
            LOGGER.error(f"Database file not found at: {DB_PATH}")
            raise HTTPException(status_code=500, detail=f"Database file not found at: {DB_PATH}")
        
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        start_date, end_date = get_date_range_filter(date_range)
        prev_start = (datetime.fromisoformat(start_date) - (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date))).date().isoformat()

        # Build venue filter
        venue_filter = ""
        params = [start_date, end_date]
        if venue_id:
            venue_filter = " AND i.venue = ?"
            params.append(venue_id)

        # Check if invoices table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        if not cursor.fetchone():
            conn.close()
            return {
                'openIssues': {'count': 0, 'severity': {'high': 0, 'medium': 0, 'low': 0}, 'delta': 0},
                'matchRate': {'value': 0, 'delta': 0, 'sparkline': []},
                'spend': {'total': 0, 'delta': 0, 'sparkline': []},
                'priceVolatility': {'itemsAboveThreshold': 0, 'delta': 0, 'sparkline': []},
            }
        
        # Open Issues - exclude NULL dates
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN COALESCE(i.issues_count, 0) >= 3 THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN COALESCE(i.issues_count, 0) = 2 THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN COALESCE(i.issues_count, 0) = 1 THEN 1 ELSE 0 END) as low
            FROM invoices i
            WHERE i.date IS NOT NULL AND i.date >= ? AND i.date <= ? AND COALESCE(i.issues_count, 0) > 0 {venue_filter}
        """, params[:3] if venue_id else params[:2])

        issues_row = cursor.fetchone()
        open_issues = {
            'count': issues_row[0] or 0,
            'severity': {
                'high': issues_row[1] or 0,
                'medium': issues_row[2] or 0,
                'low': issues_row[3] or 0,
            }
        }

        # Previous period for delta - exclude NULL dates
        prev_params = [prev_start, start_date] + (params[2:] if venue_id else [])
        cursor.execute(f"""
            SELECT COUNT(*) FROM invoices i
            WHERE i.date IS NOT NULL AND i.date >= ? AND i.date < ? AND COALESCE(i.issues_count, 0) > 0 {venue_filter}
        """, prev_params)
        prev_issues = cursor.fetchone()[0] or 0
        open_issues['delta'] = ((open_issues['count'] - prev_issues) / prev_issues * 100) if prev_issues > 0 else 0

        # Match Rate - exclude NULL dates
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN COALESCE(i.paired, 0) = 1 THEN 1 ELSE 0 END) as matched
            FROM invoices i
            WHERE i.date IS NOT NULL AND i.date >= ? AND i.date <= ? {venue_filter}
        """, params[:3] if venue_id else params[:2])

        match_row = cursor.fetchone()
        total_invoices = match_row[0] or 0
        matched_invoices = match_row[1] or 0
        match_rate = {
            'value': (matched_invoices / total_invoices * 100) if total_invoices > 0 else 0,
            'sparkline': [85, 87, 89, 88, 90, 92, 91],  # Mock sparkline data
        }

        cursor.execute(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN COALESCE(i.paired, 0) = 1 THEN 1 ELSE 0 END) as matched
            FROM invoices i
            WHERE i.date IS NOT NULL AND i.date >= ? AND i.date < ? {venue_filter}
        """, prev_params)
        prev_match_row = cursor.fetchone()
        prev_total = prev_match_row[0] or 0
        prev_matched = prev_match_row[1] or 0
        prev_match_rate = (prev_matched / prev_total * 100) if prev_total > 0 else 0
        match_rate['delta'] = match_rate['value'] - prev_match_rate

        # Spend - exclude NULL dates
        cursor.execute(f"""
            SELECT COALESCE(SUM(i.value), 0) as total
            FROM invoices i
            WHERE i.date IS NOT NULL AND i.date >= ? AND i.date <= ? {venue_filter}
        """, params[:3] if venue_id else params[:2])
        spend_total = cursor.fetchone()[0] or 0

        cursor.execute(f"""
            SELECT COALESCE(SUM(i.value), 0) as total
            FROM invoices i
            WHERE i.date IS NOT NULL AND i.date >= ? AND i.date < ? {venue_filter}
        """, prev_params)
        prev_spend = cursor.fetchone()[0] or 0
        spend = {
            'total': spend_total,
            'delta': ((spend_total - prev_spend) / prev_spend * 100) if prev_spend > 0 else 0,
            'sparkline': [1000, 1200, 1100, 1300, 1250, 1400, 1350],  # Mock sparkline data
        }

        # Price Volatility (simplified - count items with price changes > 10%) - exclude NULL dates
        cursor.execute(f"""
            SELECT COUNT(DISTINCT ili.description) as items
            FROM invoice_line_items ili
            JOIN invoices i ON i.id = ili.invoice_id
            WHERE i.date IS NOT NULL AND i.date >= ? AND i.date <= ? {venue_filter}
        """, params[:3] if venue_id else params[:2])
        volatility_items = cursor.fetchone()[0] or 0

        price_volatility = {
            'itemsAboveThreshold': volatility_items,
            'delta': 0,  # Simplified
            'sparkline': [5, 6, 5, 7, 6, 8, 7],  # Mock sparkline data
        }

        conn.close()

        return {
            'openIssues': open_issues,
            'matchRate': match_rate,
            'spend': spend,
            'priceVolatility': price_volatility,
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        LOGGER.error(f"Error getting dashboard metrics: {e}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/actions")
async def get_actions(
    venue_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get action queue items"""
    try:
        # Verify database exists
        if not os.path.exists(DB_PATH):
            LOGGER.error(f"Database file not found at: {DB_PATH}")
            raise HTTPException(status_code=500, detail=f"Database file not found at: {DB_PATH}")
        
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        # Check if invoices table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        if not cursor.fetchone():
            conn.close()
            return {'actions': []}

        actions = []

        # Resolve Mismatch actions
        venue_filter = ""
        params = []
        if venue_id:
            venue_filter = " AND i.venue = ?"
            params.append(venue_id)

        cursor.execute(f"""
            SELECT i.id, i.supplier, i.value, i.issues_count
            FROM invoices i
            WHERE COALESCE(i.issues_count, 0) > 0 AND COALESCE(i.status, '') != 'resolved' {venue_filter}
            ORDER BY i.issues_count DESC, i.date DESC
            LIMIT 10
        """, params)

        for row in cursor.fetchall():
            invoice_id, supplier, value, issues_count = row
            actions.append({
                'id': f'mismatch-{invoice_id}',
                'type': 'resolve_mismatch',
                'title': f'Resolve Mismatch: {supplier}',
                'description': f'Invoice has {issues_count} issue(s) requiring resolution',
                'priority': 'high' if issues_count >= 3 else 'medium',
                'status': 'pending',
                'metadata': {
                    'invoiceId': invoice_id,
                    'suggestedCredit': value * 0.1,  # Mock 10% credit suggestion
                },
                'createdAt': datetime.now().isoformat(),
            })

        # Pair Delivery Note actions
        # Check if columns exist in documents table
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_supplier = 'supplier' in columns
        has_delivery_no = 'delivery_no' in columns
        has_doc_type = 'doc_type' in columns
        has_doc_date = 'doc_date' in columns
        
        # Build query based on available columns
        if has_doc_type:
            where_clause = "d.doc_type = 'delivery_note'"
        else:
            where_clause = "1=1"  # Fallback if doc_type doesn't exist
        
        select_cols = ["d.id"]
        if has_supplier:
            select_cols.append("d.supplier")
        else:
            select_cols.append("NULL as supplier")
        if has_delivery_no:
            select_cols.append("d.delivery_no")
        else:
            select_cols.append("NULL as delivery_no")
        if has_doc_date:
            select_cols.append("d.doc_date")
        else:
            select_cols.append("NULL as doc_date")
        
        cursor.execute(f"""
            SELECT {', '.join(select_cols)}
            FROM documents d
            WHERE {where_clause} AND d.id NOT IN (
                SELECT p.delivery_id FROM pairs p WHERE p.delivery_id IS NOT NULL
            )
            ORDER BY {select_cols[-1] if has_doc_date else 'd.id'} DESC
            LIMIT 10
        """)

        for row in cursor.fetchall():
            dn_id = row[0]
            supplier = row[1] if has_supplier else None
            dn_number = row[2] if has_delivery_no else None
            dn_date = row[3] if has_doc_date else None
            
            # Find most likely invoice (only if supplier exists)
            invoice_match = None
            confidence = 0.0
            if supplier and dn_date:
                try:
                    cursor.execute("""
                        SELECT id, value, date FROM invoices
                        WHERE supplier = ? AND ABS(julianday(date) - julianday(?)) <= 7
                        ORDER BY ABS(julianday(date) - julianday(?))
                        LIMIT 1
                    """, (supplier, dn_date, dn_date))
                    invoice_match = cursor.fetchone()
                    confidence = 0.8 if invoice_match else 0.0
                except Exception:
                    pass  # If query fails, just skip matching

            actions.append({
                'id': f'pair-{dn_id}',
                'type': 'pair_dn',
                'title': f'Pair Delivery Note: {dn_number}',
                'description': f'Delivery note from {supplier} needs pairing',
                'priority': 'medium',
                'status': 'pending',
                'metadata': {
                    'deliveryNoteId': dn_id,
                    'invoiceId': invoice_match[0] if invoice_match else None,
                    'confidence': confidence,
                },
                'createdAt': dn_date or datetime.now().isoformat(),
            })

        # Review Low Confidence OCR
        cursor.execute(f"""
            SELECT d.id, d.filename, d.ocr_confidence
            FROM documents d
            WHERE d.ocr_confidence < 0.7 AND d.status = 'completed'
            ORDER BY d.ocr_confidence ASC
            LIMIT 5
        """)

        for row in cursor.fetchall():
            doc_id, filename, confidence = row
            actions.append({
                'id': f'ocr-{doc_id}',
                'type': 'review_ocr',
                'title': f'Review Low Confidence OCR: {filename}',
                'description': f'OCR confidence: {confidence:.0%}',
                'priority': 'low',
                'status': 'pending',
                'metadata': {
                    'documentId': doc_id,
                    'confidence': confidence,
                    'pages': 1,  # Mock
                },
                'createdAt': datetime.now().isoformat(),
            })

        # Submit Ready Batch
        cursor.execute(f"""
            SELECT COUNT(*) FROM invoices
            WHERE status = 'ready' {venue_filter}
        """, params)
        ready_count = cursor.fetchone()[0] or 0

        if ready_count > 0:
            cursor.execute(f"""
                SELECT id FROM invoices
                WHERE status = 'ready' {venue_filter}
                LIMIT 50
            """, params)
            invoice_ids = [row[0] for row in cursor.fetchall()]

            actions.append({
                'id': 'submit-batch',
                'type': 'submit_batch',
                'title': f'Submit Ready Batch ({ready_count} invoices)',
                'description': f'{ready_count} invoices are ready for submission',
                'priority': 'medium',
                'status': 'pending',
                'metadata': {
                    'count': ready_count,
                    'invoiceIds': invoice_ids,
                },
                'createdAt': datetime.now().isoformat(),
            })

        conn.close()

        # Filter by role
        if role == 'ShiftLead':
            actions = [a for a in actions if a['type'] not in ['resolve_mismatch', 'submit_batch']]

        return {'actions': actions}

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        LOGGER.error(f"Error getting actions: {e}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Failed to get actions: {str(e)}")


@router.get("/suppliers")
async def get_suppliers(
    venue_id: Optional[str] = Query(None),
    date_range: str = Query('30d')
) -> Dict[str, Any]:
    """Get supplier risk board data"""
    try:
        # Verify database exists
        if not os.path.exists(DB_PATH):
            LOGGER.error(f"Database file not found at: {DB_PATH}")
            raise HTTPException(status_code=500, detail=f"Database file not found at: {DB_PATH}")
        
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        # Check if invoices table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        if not cursor.fetchone():
            conn.close()
            return {'suppliers': []}

        start_date, end_date = get_date_range_filter(date_range)
        venue_filter = ""
        params = [start_date, end_date]
        if venue_id:
            venue_filter = " AND i.venue = ?"
            params.append(venue_id)

        # Get suppliers with metrics - exclude NULL dates
        cursor.execute(f"""
            SELECT 
                i.supplier,
                COUNT(*) as invoice_count,
                COALESCE(SUM(i.value), 0) as total_spend,
                SUM(CASE WHEN COALESCE(i.issues_count, 0) > 0 THEN 1 ELSE 0 END) as issues_count,
                SUM(COALESCE(i.issues_count, 0)) as total_issues
            FROM invoices i
            WHERE i.date IS NOT NULL AND i.date >= ? AND i.date <= ? AND i.supplier IS NOT NULL {venue_filter}
            GROUP BY i.supplier
            ORDER BY total_spend DESC
        """, params[:3] if venue_id else params[:2])

        suppliers = []
        for row in cursor.fetchall():
            supplier_name, invoice_count, total_spend, issues_count, total_issues = row

            # Calculate mismatch rate
            mismatch_rate = (issues_count / invoice_count * 100) if invoice_count > 0 else 0

            # Calculate score (A-E)
            if mismatch_rate < 2 and total_issues == 0:
                score = 'A'
            elif mismatch_rate < 5 and total_issues < invoice_count * 0.1:
                score = 'B'
            elif mismatch_rate < 10:
                score = 'C'
            elif mismatch_rate < 20:
                score = 'D'
            else:
                score = 'E'

            # Mock late deliveries and price volatility
            late_deliveries = int(invoice_count * 0.1)  # Mock 10% late
            price_volatility = mismatch_rate * 0.5  # Mock based on mismatch rate

            suppliers.append({
                'id': supplier_name.lower().replace(' ', '-'),
                'name': supplier_name,
                'score': score,
                'mismatchRate': mismatch_rate,
                'lateDeliveries': late_deliveries,
                'priceVolatility': price_volatility,
                'totalSpend': total_spend,
            })

        conn.close()

        return {'suppliers': suppliers}

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        LOGGER.error(f"Error getting suppliers: {e}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Failed to get suppliers: {str(e)}")


@router.get("/trends")
async def get_trends(
    type: str = Query(...),
    venue_id: Optional[str] = Query(None),
    date_range: str = Query('30d'),
    supplier: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    item: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Get trend data for charts"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        start_date, end_date = get_date_range_filter(date_range)
        venue_filter = ""
        params = [start_date, end_date]
        if venue_id:
            venue_filter = " AND i.venue = ?"
            params.append(venue_id)

        # Generate time series data
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        days = (end - start).days + 1

        data_points = []
        for i in range(days):
            date = (start + timedelta(days=i)).isoformat().split('T')[0]
            # Mock data - in real implementation, aggregate actual data
            if type == 'spend':
                value = 1000 + (i * 50) + np.random.randint(-100, 100)
            elif type == 'matchRate':
                value = 85 + (i * 0.5) + np.random.randint(-5, 5)
            elif type == 'issues':
                value = 5 + np.random.randint(-2, 3)
            else:  # price
                value = 100 + (i * 2) + np.random.randint(-10, 10)

            data_points.append({
                'date': date,
                'value': max(0, value),
            })

        # Mock forecast data (next 30 days)
        forecast_points = []
        last_value = data_points[-1]['value'] if data_points else 1000
        for i in range(30):
            date = (end + timedelta(days=i+1)).isoformat().split('T')[0]
            forecast_value = last_value * (1 + 0.01 * (i + 1))  # Mock trend
            forecast_points.append({
                'date': date,
                'forecast': max(0, forecast_value),
                'confidence': max(0.5, 1.0 - (i * 0.01)),
            })

        conn.close()

        unit = 'GBP' if type == 'spend' else '%' if type == 'matchRate' else 'count'

        return {
            'data': data_points,
            'forecast': forecast_points,
            'unit': unit,
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        LOGGER.error(f"Error getting trends: {e}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")


@router.get("/unmatched-dns")
async def get_unmatched_dns(
    venue_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get unmatched delivery notes"""
    try:
        # Verify database exists
        if not os.path.exists(DB_PATH):
            LOGGER.error(f"Database file not found at: {DB_PATH}")
            raise HTTPException(status_code=500, detail=f"Database file not found at: {DB_PATH}")
        
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        # Check if documents table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        if not cursor.fetchone():
            conn.close()
            return {'deliveryNotes': []}

        # Check if columns exist in documents table
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_supplier = 'supplier' in columns
        has_delivery_no = 'delivery_no' in columns
        has_doc_type = 'doc_type' in columns
        has_doc_date = 'doc_date' in columns
        has_uploaded_at = 'uploaded_at' in columns
        
        # Build query based on available columns
        if has_doc_type:
            where_clause = "d.doc_type = 'delivery_note'"
        else:
            where_clause = "1=1"  # Fallback if doc_type doesn't exist
        
        select_cols = ["d.id"]
        if has_delivery_no:
            select_cols.append("d.delivery_no")
        else:
            select_cols.append("NULL as delivery_no")
        if has_supplier:
            select_cols.append("d.supplier")
        else:
            select_cols.append("NULL as supplier")
        if has_doc_date:
            select_cols.append("d.doc_date")
        else:
            select_cols.append("NULL as doc_date")
        if has_uploaded_at:
            select_cols.append("d.uploaded_at")
        else:
            select_cols.append("NULL as uploaded_at")
        
        cursor.execute(f"""
            SELECT {', '.join(select_cols)}
            FROM documents d
            WHERE {where_clause} AND d.id NOT IN (
                SELECT p.delivery_id FROM pairs p WHERE p.delivery_id IS NOT NULL
            )
            ORDER BY {select_cols[3] if has_doc_date else 'd.id'} DESC
        """)

        delivery_notes = []
        for row in cursor.fetchall():
            dn_id = row[0]
            dn_number = row[1] if has_delivery_no else None
            supplier = row[2] if has_supplier else None
            doc_date = row[3] if has_doc_date else None
            uploaded_at = row[4] if has_uploaded_at else None
            upload_date = datetime.fromisoformat(uploaded_at) if uploaded_at and has_uploaded_at else datetime.now()
            age = (datetime.now() - upload_date).days

            # Find most likely invoice (only if supplier exists)
            invoice_match = None
            if supplier:
                try:
                    date_to_match = doc_date if doc_date else upload_date.isoformat().split('T')[0]
                    cursor.execute("""
                        SELECT id FROM invoices
                        WHERE supplier = ? AND ABS(julianday(date) - julianday(?)) <= 7
                        ORDER BY ABS(julianday(date) - julianday(?))
                        LIMIT 1
                    """, (supplier, date_to_match, date_to_match))
                    invoice_match = cursor.fetchone()
                except Exception:
                    pass  # If query fails, just skip matching

            delivery_notes.append({
                'id': dn_id,
                'deliveryNoteNumber': dn_number or f'DN-{dn_id[:8]}',
                'supplier': supplier or 'Unknown',
                'date': doc_date or upload_date.isoformat().split('T')[0],
                'age': age,
                'suggestedInvoice': {
                    'id': invoice_match[0],
                    'confidence': 0.85,
                } if invoice_match else None,
            })

        conn.close()

        return {'deliveryNotes': delivery_notes}

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        LOGGER.error(f"Error getting unmatched DNs: {e}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Failed to get unmatched DNs: {str(e)}")


@router.get("/activity")
async def get_activity(
    venue_id: Optional[str] = Query(None),
    limit: int = Query(20)
) -> Dict[str, Any]:
    """Get recent activity/audit log"""
    try:
        # Verify database exists
        if not os.path.exists(DB_PATH):
            LOGGER.error(f"Database file not found at: {DB_PATH}")
            raise HTTPException(status_code=500, detail=f"Database file not found at: {DB_PATH}")
        
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        # Check if audit_log table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
        if not cursor.fetchone():
            conn.close()
            return {'activities': []}

        query = "SELECT ts, actor, action, detail FROM audit_log WHERE 1=1"
        params = []
        if venue_id:
            query += " AND detail LIKE ?"
            params.append(f'%"venue":"{venue_id}"%')

        query += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        activities = []
        for idx, row in enumerate(cursor.fetchall()):
            ts, actor, action, detail = row
            # Create unique ID by combining timestamp with actor, action, and index
            # This ensures uniqueness even if multiple activities have the same timestamp
            actor_str = (actor or 'system').replace(' ', '-')
            action_str = action.replace(' ', '-')
            unique_id = f'activity-{ts}-{actor_str}-{action_str}-{idx}'
            activities.append({
                'id': unique_id,
                'actor': actor or 'system',
                'action': action,
                'timestamp': ts,
                'detail': detail,
            })

        conn.close()

        return {'activities': activities}

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        LOGGER.error(f"Error getting activity: {e}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Failed to get activity: {str(e)}")


class ResolveRequest(BaseModel):
    creditAmount: Optional[float] = None

@router.post("/actions/{action_id}/resolve")
async def resolve_action(
    action_id: str,
    request: Optional[ResolveRequest] = Body(None)
) -> Dict[str, Any]:
    """Resolve a mismatch action"""
    try:
        # Extract invoice ID from action ID
        if action_id.startswith('mismatch-'):
            invoice_id = action_id.replace('mismatch-', '')
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("UPDATE invoices SET status = 'resolved', issues_count = 0 WHERE id = ?", (invoice_id,))
            conn.commit()
            conn.close()
            return {'success': True}
        raise HTTPException(status_code=400, detail="Invalid action ID")
    except Exception as e:
        LOGGER.error(f"Error resolving action: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resolve action: {str(e)}")


class PairRequest(BaseModel):
    deliveryNoteId: str
    invoiceId: str

class SubmitBatchRequest(BaseModel):
    invoiceIds: List[str]

@router.post("/pair")
async def pair_delivery_note(
    request: PairRequest
) -> Dict[str, Any]:
    """Pair a delivery note with an invoice"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        # Check if pairs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pairs'")
        if cursor.fetchone():
            cursor.execute("""
                INSERT OR REPLACE INTO pairs (invoice_id, delivery_id, status, created_at)
                VALUES (?, ?, 'confirmed', ?)
            """, (request.invoiceId, request.deliveryNoteId, datetime.now().isoformat()))
        else:
            # Create pairs table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pairs (
                    invoice_id TEXT,
                    delivery_id TEXT,
                    status TEXT,
                    created_at TEXT,
                    PRIMARY KEY (invoice_id, delivery_id)
                )
            """)
            cursor.execute("""
                INSERT INTO pairs (invoice_id, delivery_id, status, created_at)
                VALUES (?, ?, 'confirmed', ?)
            """, (request.invoiceId, request.deliveryNoteId, datetime.now().isoformat()))

        # Update invoice paired status
        cursor.execute("UPDATE invoices SET paired = 1 WHERE id = ?", (request.invoiceId,))
        conn.commit()
        conn.close()

        return {'success': True}
    except Exception as e:
        LOGGER.error(f"Error pairing delivery note: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pair delivery note: {str(e)}")


@router.post("/submit-batch")
async def submit_batch(
    request: SubmitBatchRequest
) -> Dict[str, Any]:
    """Submit a batch of ready invoices"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(request.invoiceIds))
        cursor.execute(f"""
            UPDATE invoices SET status = 'submitted' WHERE id IN ({placeholders})
        """, request.invoiceIds)

        conn.commit()
        conn.close()

        return {'success': True, 'count': len(request.invoiceIds)}
    except Exception as e:
        LOGGER.error(f"Error submitting batch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit batch: {str(e)}")

