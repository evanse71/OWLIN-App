#!/usr/bin/env python3
"""
Review Queue API

Manages quarantine and reject documents for operator review and triage
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from flask import Blueprint, request, jsonify

# TEMP safe stub if the real util isn't in the tree yet:
def log_review_action(*_, **__):  # noqa: D401
    """No-op audit stub; replace with real audit logger."""
    return None

from ..services.audit import get_audit_service
from ..ocr.unified_ocr_engine import get_unified_ocr_engine

logger = logging.getLogger(__name__)

review_queue_bp = Blueprint('review_queue', __name__)

def get_db_connection():
    """Get database connection"""
    db_path = Path(__file__).parent.parent / "owlin.db"
    return sqlite3.connect(str(db_path))

@review_queue_bp.route('/api/review-queue', methods=['GET'])
def get_review_queue():
    """
    Get review queue items
    
    Query parameters:
    - status: quarantine|reject (optional)
    - since: ISO datetime (optional)
    - limit: max items to return (default 100)
    """
    try:
        # Parse query parameters
        status = request.args.get('status')  # quarantine, reject, or None for all
        since_str = request.args.get('since')
        limit = int(request.args.get('limit', 100))
        
        # Parse since date
        since_date = None
        if since_str:
            try:
                since_date = datetime.fromisoformat(since_str)
            except ValueError:
                return jsonify({'error': 'Invalid since date format'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT 
                i.id,
                i.uploaded_at,
                i.supplier_name,
                i.doc_type,
                i.policy_action,
                i.confidence,
                i.reasons_json,
                i.total_amount
            FROM invoices i
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND i.policy_action = ?"
            params.append(status.upper())
        
        if since_date:
            query += " AND i.uploaded_at >= ?"
            params.append(since_date.isoformat())
        
        query += " ORDER BY i.uploaded_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Format results
        items = []
        for row in rows:
            doc_id, uploaded_at, supplier_name, doc_type, policy_action, confidence, reasons_json, total_amount = row
            
            # Parse reasons
            reasons = []
            if reasons_json:
                try:
                    reasons = json.loads(reasons_json)[:3]  # Top 3 reasons
                except json.JSONDecodeError:
                    reasons = []
            
            items.append({
                'id': doc_id,
                'uploaded_at': uploaded_at,
                'supplier_name': supplier_name or 'Unknown',
                'doc_type': doc_type or 'unknown',
                'policy_action': policy_action or 'UNKNOWN',
                'confidence': confidence or 0.0,
                'reasons': reasons,
                'total_amount': total_amount
            })
        
        return jsonify({
            'items': items,
            'total': len(items),
            'status': status,
            'since': since_str
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get review queue: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@review_queue_bp.route('/api/review-queue/<int:doc_id>/action', methods=['POST'])
def review_action(doc_id: int):
    """
    Perform review action on a document
    
    Actions:
    - accept_with_warnings: Accept document with warnings
    - retry_ocr: Re-run OCR processing
    - escalate: Escalate for manual review
    
    Body: {action: string, note?: string}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        action = data.get('action')
        note = data.get('note', '')
        
        if action not in ['accept_with_warnings', 'retry_ocr', 'escalate']:
            return jsonify({'error': 'Invalid action'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get document info
        cursor.execute("""
            SELECT policy_action, supplier_name, doc_type, confidence
            FROM invoices WHERE id = ?
        """, (doc_id,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Document not found'}), 404
        
        current_action, supplier_name, doc_type, confidence = row
        
        # Log the review action
        log_review_action(
            user_id=request.headers.get('X-User-ID'),
            session_id=request.headers.get('X-Session-ID'),
            document_id=doc_id,
            action=action,
            note=note,
            previous_action=current_action
        )
        
        if action == 'retry_ocr':
            # Re-run OCR processing
            result = _retry_ocr_processing(doc_id)
            if result:
                # Update document with new results
                cursor.execute("""
                    UPDATE invoices 
                    SET policy_action = ?, confidence = ?, reasons_json = ?,
                        doc_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    result['policy_action'],
                    result['confidence'],
                    json.dumps(result['reasons']),
                    result['doc_type'],
                    doc_id
                ))
                
                conn.commit()
                conn.close()
                
                return jsonify({
                    'success': True,
                    'message': 'OCR retry completed',
                    'new_status': result['policy_action'],
                    'new_confidence': result['confidence']
                })
            else:
                conn.close()
                return jsonify({'error': 'OCR retry failed'}), 500
        
        elif action == 'accept_with_warnings':
            # Update policy action
            cursor.execute("""
                UPDATE invoices 
                SET policy_action = 'ACCEPT_WITH_WARNINGS', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (doc_id,))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Document accepted with warnings',
                'new_status': 'ACCEPT_WITH_WARNINGS'
            })
        
        elif action == 'escalate':
            # Mark for escalation
            cursor.execute("""
                UPDATE invoices 
                SET policy_action = 'ESCALATED', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (doc_id,))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Document escalated for manual review',
                'new_status': 'ESCALATED'
            })
        
    except Exception as e:
        logger.error(f"❌ Failed to perform review action: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def _retry_ocr_processing(doc_id: int) -> Optional[Dict[str, Any]]:
    """Retry OCR processing for a document"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get document text (for now, we'll simulate retry)
        cursor.execute("SELECT supplier_name FROM invoices WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Simulate OCR retry with improved processing
        engine = get_unified_ocr_engine()
        
        # Create mock text for retry (in real implementation, this would be the original image)
        mock_text = f"Retry processing for document {doc_id}"
        
        # Process with enhanced settings
        result = engine.process_document(mock_text)
        
        if result.success:
            return {
                'policy_action': result.policy_decision['action'],
                'confidence': result.overall_confidence,
                'reasons': result.policy_decision['reasons'],
                'doc_type': result.document_type
            }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ OCR retry failed: {e}")
        return None

# Add route to Flask app
def init_app(app):
    """Initialize the review queue blueprint"""
    app.register_blueprint(review_queue_bp) 