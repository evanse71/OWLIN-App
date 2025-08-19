"""
Delivery Note Matching Service

Implements confidence scoring algorithm for matching invoices with delivery notes.
Uses weighted scoring based on supplier match, date proximity, line item overlap, and value match.
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts import ConfidenceBreakdown, MatchCandidate, MatchCandidatesResponse

logger = logging.getLogger(__name__)

# Scoring weights (sum to 100)
SUPPLIER_WEIGHT = 40
DATE_WEIGHT = 25
LINE_ITEMS_WEIGHT = 30
VALUE_WEIGHT = 5

# Confidence bands
HIGH_CONFIDENCE = 80
MEDIUM_CONFIDENCE = 60

def get_db_connection():
    """Get SQLite database connection"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "owlin.db")
    return sqlite3.connect(db_path)

def _normalize_supplier_name(name: str) -> str:
    """Normalize supplier name for comparison"""
    if not name:
        return ""
    # Remove common suffixes and normalize
    name = name.lower().strip()
    suffixes = [" ltd", " limited", " plc", " inc", " corp", " company", " co"]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name.strip()

def _calculate_supplier_score(invoice_supplier: str, delivery_supplier: str) -> float:
    """Calculate supplier match score (0-40 points)"""
    if not invoice_supplier or not delivery_supplier:
        return 0.0
    
    inv_norm = _normalize_supplier_name(invoice_supplier)
    del_norm = _normalize_supplier_name(delivery_supplier)
    
    if inv_norm == del_norm:
        return SUPPLIER_WEIGHT  # Exact match
    
    # Check for partial match
    similarity = SequenceMatcher(None, inv_norm, del_norm).ratio()
    if similarity >= 0.8:
        return SUPPLIER_WEIGHT * 0.5  # 20 points for high similarity
    
    # Check for alias match (could be extended with supplier aliases table)
    if similarity >= 0.6:
        return SUPPLIER_WEIGHT * 0.75  # 30 points for medium similarity
    
    return 0.0

def _calculate_date_score(invoice_date: str, delivery_date: str) -> float:
    """Calculate date proximity score (0-25 points)"""
    if not invoice_date or not delivery_date:
        return 0.0
    
    try:
        inv_date = datetime.fromisoformat(invoice_date.split('T')[0])
        del_date = datetime.fromisoformat(delivery_date.split('T')[0])
        
        days_diff = abs((inv_date - del_date).days)
        
        if days_diff == 0:
            return DATE_WEIGHT  # Same date (25 points)
        elif days_diff <= 1:
            return DATE_WEIGHT * 0.8  # ±1 day (20 points)
        elif days_diff <= 3:
            return DATE_WEIGHT * 0.4  # ±3 days (10 points)
        else:
            return 0.0  # No points for dates more than 3 days apart
    
    except (ValueError, TypeError):
        return 0.0

def _calculate_line_items_score(invoice_items: List[Dict], delivery_items: List[Dict]) -> float:
    """Calculate line item overlap score (0-30 points)"""
    if not invoice_items or not delivery_items:
        return 0.0
    
    # Normalize item descriptions for comparison
    def normalize_description(desc: str) -> str:
        if not desc:
            return ""
        return desc.lower().strip()
    
    # Count matches
    matches = 0
    used_delivery = set()
    
    for inv_item in invoice_items:
        inv_desc = normalize_description(inv_item.get('description', ''))
        if not inv_desc:
            continue
            
        best_match = None
        best_score = 0
        
        for i, del_item in enumerate(delivery_items):
            if i in used_delivery:
                continue
                
            del_desc = normalize_description(del_item.get('description', ''))
            if not del_desc:
                continue
            
            similarity = SequenceMatcher(None, inv_desc, del_desc).ratio()
            if similarity > best_score and similarity >= 0.7:  # 70% similarity threshold
                best_score = similarity
                best_match = i
        
        if best_match is not None:
            matches += 1
            used_delivery.add(best_match)
    
    # Calculate percentage of matched items
    total_items = max(len(invoice_items), len(delivery_items))
    if total_items == 0:
        return 0.0
    
    match_percentage = matches / total_items
    return LINE_ITEMS_WEIGHT * match_percentage

def _calculate_value_score(invoice_total: float, delivery_total: float) -> float:
    """Calculate value match score (0-5 points)"""
    if invoice_total <= 0 or delivery_total <= 0:
        return 0.0
    
    # Calculate percentage difference
    diff_percentage = abs(invoice_total - delivery_total) / max(invoice_total, delivery_total)
    
    if diff_percentage <= 0.02:  # ±2%
        return VALUE_WEIGHT
    elif diff_percentage <= 0.05:  # ±5%
        return VALUE_WEIGHT * 0.5
    elif diff_percentage <= 0.10:  # ±10%
        return VALUE_WEIGHT * 0.25
    else:
        return 0.0

def calculate_confidence(invoice_data: Dict[str, Any], delivery_data: Dict[str, Any]) -> Tuple[float, ConfidenceBreakdown]:
    """Calculate overall confidence score and breakdown"""
    
    # Extract data
    invoice_supplier = invoice_data.get('supplier_name', '')
    delivery_supplier = delivery_data.get('supplier_name', '')
    invoice_date = invoice_data.get('invoice_date', '')
    delivery_date = delivery_data.get('delivery_date', '')
    invoice_items = invoice_data.get('line_items', [])
    delivery_items = delivery_data.get('items', [])
    invoice_total = float(invoice_data.get('total_amount', 0))
    delivery_total = float(delivery_data.get('total_amount', 0))
    
    # Calculate individual scores
    supplier_score = _calculate_supplier_score(invoice_supplier, delivery_supplier)
    date_score = _calculate_date_score(invoice_date, delivery_date)
    line_items_score = _calculate_line_items_score(invoice_items, delivery_items)
    value_score = _calculate_value_score(invoice_total, delivery_total)
    
    # Calculate total score
    total_score = supplier_score + date_score + line_items_score + value_score
    
    # Create breakdown
    breakdown = ConfidenceBreakdown(
        supplier=supplier_score,
        date=date_score,
        line_items=line_items_score,
        value=value_score
    )
    
    return total_score, breakdown

def find_candidates(invoice_id: str, min_confidence: float = 0.0, limit: int = 5) -> List[MatchCandidate]:
    """Find candidate delivery notes for an invoice"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get invoice data
        cursor.execute("""
            SELECT supplier_name, invoice_date, total_amount, line_items
            FROM invoices WHERE id = ?
        """, (invoice_id,))
        
        invoice_row = cursor.fetchone()
        if not invoice_row:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        supplier_name, invoice_date, total_amount, line_items_json = invoice_row
        
        # Parse line items - handle case where column might not exist
        try:
            import json
            line_items = json.loads(line_items_json) if line_items_json else []
        except (json.JSONDecodeError, TypeError):
            line_items = []
        
        invoice_data = {
            'supplier_name': supplier_name or '',
            'invoice_date': invoice_date or '',
            'total_amount': float(total_amount or 0),
            'line_items': line_items
        }
        
        # Get all delivery notes
        cursor.execute("""
            SELECT id, supplier_name, delivery_date, total_amount
            FROM delivery_notes 
            WHERE status != 'matched'
            ORDER BY delivery_date DESC
        """)
        
        delivery_notes = cursor.fetchall()
        candidates = []
        
        for dn_row in delivery_notes:
            dn_id, dn_supplier, dn_date, dn_total = dn_row
            
            # For now, use empty line items since the column doesn't exist
            dn_items = []
            
            delivery_data = {
                'supplier_name': dn_supplier or '',
                'delivery_date': dn_date or '',
                'total_amount': float(dn_total or 0),
                'items': dn_items
            }
            
            # Calculate confidence
            confidence, breakdown = calculate_confidence(invoice_data, delivery_data)
            
            if confidence >= min_confidence:
                candidates.append(MatchCandidate(
                    delivery_note_id=dn_id,
                    confidence=confidence,
                    breakdown=breakdown,
                    delivery_note=delivery_data
                ))
        
        # Sort by confidence and limit results
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        return candidates[:limit]
        
    finally:
        conn.close()

def confirm_match(invoice_id: str, delivery_note_id: str, actor_role: str = "user") -> Dict[str, Any]:
    """Confirm a match between invoice and delivery note"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get confidence score for this pair
        confidence, breakdown = _get_existing_confidence(invoice_id, delivery_note_id)
        if confidence is None:
            # Calculate fresh confidence
            invoice_data = _get_invoice_data(invoice_id)
            delivery_data = _get_delivery_data(delivery_note_id)
            confidence, breakdown = calculate_confidence(invoice_data, delivery_data)
        
        # Insert or update pair
        pair_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO invoice_delivery_pairs 
            (id, invoice_id, delivery_note_id, confidence_score, 
             breakdown_supplier, breakdown_date, breakdown_line_items, breakdown_value,
             status, confirmed_by, confirmed_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?, ?, ?, ?)
        """, (
            pair_id, invoice_id, delivery_note_id, confidence,
            breakdown.supplier, breakdown.date, breakdown.line_items, breakdown.value,
            actor_role, now, now, now
        ))
        
        # Update invoice and delivery note status
        cursor.execute("UPDATE invoices SET status = 'matched' WHERE id = ?", (invoice_id,))
        cursor.execute("UPDATE delivery_notes SET status = 'matched' WHERE id = ?", (delivery_note_id,))
        
        # Remove from unmatched delivery notes if present
        cursor.execute("DELETE FROM unmatched_delivery_notes WHERE delivery_note_id = ?", (delivery_note_id,))
        
        conn.commit()
        
        return {
            "status": "confirmed",
            "confidence": confidence,
            "pair_id": pair_id
        }
        
    finally:
        conn.close()

def reject_match(invoice_id: str, delivery_note_id: str, actor_role: str = "user", notes: str = "") -> Dict[str, Any]:
    """Reject a match between invoice and delivery note"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get confidence score for this pair
        confidence, breakdown = _get_existing_confidence(invoice_id, delivery_note_id)
        if confidence is None:
            # Calculate fresh confidence
            invoice_data = _get_invoice_data(invoice_id)
            delivery_data = _get_delivery_data(delivery_note_id)
            confidence, breakdown = calculate_confidence(invoice_data, delivery_data)
        
        # Record in matching history
        history_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO matching_history 
            (id, invoice_id, delivery_note_id, action, confidence_score,
             breakdown_supplier, breakdown_date, breakdown_line_items, breakdown_value,
             actor_role, notes, created_at)
            VALUES (?, ?, ?, 'rejected', ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            history_id, invoice_id, delivery_note_id, confidence,
            breakdown.supplier, breakdown.date, breakdown.line_items, breakdown.value,
            actor_role, notes, now
        ))
        
        conn.commit()
        
        return {
            "status": "rejected",
            "history_id": history_id
        }
        
    finally:
        conn.close()

def retry_late_uploads() -> Dict[str, Any]:
    """Re-run matching for all unmatched invoices and delivery notes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all unmatched invoices
        cursor.execute("""
            SELECT id FROM invoices WHERE status = 'scanned'
        """)
        unmatched_invoices = [row[0] for row in cursor.fetchall()]
        
        # Get all unmatched delivery notes
        cursor.execute("""
            SELECT id FROM delivery_notes WHERE status = 'parsed'
        """)
        unmatched_delivery_notes = [row[0] for row in cursor.fetchall()]
        
        new_matches = 0
        
        # Try to match each unmatched invoice with unmatched delivery notes
        for invoice_id in unmatched_invoices:
            candidates = find_candidates(invoice_id, min_confidence=HIGH_CONFIDENCE, limit=1)
            
            if candidates and candidates[0].confidence >= HIGH_CONFIDENCE:
                # Auto-confirm high confidence matches
                confirm_match(invoice_id, candidates[0].delivery_note_id, "system")
                new_matches += 1
        
        return {
            "new_matches_found": new_matches,
            "message": f"Found {new_matches} new high-confidence matches"
        }
        
    finally:
        conn.close()

def _get_existing_confidence(invoice_id: str, delivery_note_id: str) -> Tuple[Optional[float], Optional[ConfidenceBreakdown]]:
    """Get existing confidence score for a pair"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT confidence_score, breakdown_supplier, breakdown_date, 
                   breakdown_line_items, breakdown_value
            FROM invoice_delivery_pairs 
            WHERE invoice_id = ? AND delivery_note_id = ?
        """, (invoice_id, delivery_note_id))
        
        row = cursor.fetchone()
        if row:
            confidence, supplier, date, line_items, value = row
            breakdown = ConfidenceBreakdown(
                supplier=supplier,
                date=date,
                line_items=line_items,
                value=value
            )
            return confidence, breakdown
        
        return None, None
        
    finally:
        conn.close()

def _get_invoice_data(invoice_id: str) -> Dict[str, Any]:
    """Get invoice data for confidence calculation"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT supplier_name, invoice_date, total_amount, line_items
            FROM invoices WHERE id = ?
        """, (invoice_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        supplier_name, invoice_date, total_amount, line_items_json = row
        
        try:
            import json
            line_items = json.loads(line_items_json) if line_items_json else []
        except (json.JSONDecodeError, TypeError):
            line_items = []
        
        return {
            'supplier_name': supplier_name or '',
            'invoice_date': invoice_date or '',
            'total_amount': float(total_amount or 0),
            'line_items': line_items
        }
        
    finally:
        conn.close()

def _get_delivery_data(delivery_note_id: str) -> Dict[str, Any]:
    """Get delivery note data for confidence calculation"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT supplier_name, delivery_date, total_amount
            FROM delivery_notes WHERE id = ?
        """, (delivery_note_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Delivery note {delivery_note_id} not found")
        
        supplier_name, delivery_date, total_amount = row
        
        # For now, use empty line items since the column doesn't exist
        line_items = []
        
        return {
            'supplier_name': supplier_name or '',
            'delivery_date': delivery_date or '',
            'total_amount': float(total_amount or 0),
            'items': line_items
        }
        
    finally:
        conn.close() 