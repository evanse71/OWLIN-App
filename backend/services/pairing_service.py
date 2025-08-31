# backend/services/pairing_service.py
"""
Document pairing service for matching invoices with delivery notes
"""

import re
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from db_manager_unified import get_db_manager

logger = logging.getLogger(__name__)

# Get unified database manager
db_manager = get_db_manager()

class PairingService:
    """Service for pairing invoices with delivery notes"""
    
    # Deterministic scoring weights (committed in code)
    SCORING_WEIGHTS = {
        'supplier_match': 0.6,
        'date_proximity': 0.2,
        'amount_proximity': 0.2
    }
    
    # Auto-confirm threshold
    AUTO_CONFIRM_THRESHOLD = 85.0
    SUGGESTION_THRESHOLD = 55.0
    
    @staticmethod
    def normalize_supplier_name(name: str) -> str:
        """Normalize supplier name for comparison"""
        if not name:
            return ""
        
        # Remove common suffixes and prefixes
        name = re.sub(r'\b(ltd|limited|inc|corp|corporation|co|company|plc)\b', '', name.lower())
        name = re.sub(r'[^\w\s]', '', name)  # Remove punctuation
        name = re.sub(r'\s+', ' ', name).strip()  # Normalize whitespace
        
        return name
    
    @staticmethod
    def calculate_supplier_score(invoice_supplier: str, dn_supplier: str) -> float:
        """Calculate supplier name similarity score (0-1)"""
        if not invoice_supplier or not dn_supplier:
            return 0.0
        
        norm_inv = PairingService.normalize_supplier_name(invoice_supplier)
        norm_dn = PairingService.normalize_supplier_name(dn_supplier)
        
        if norm_inv == norm_dn:
            return 1.0
        
        # Use sequence matcher for fuzzy matching
        similarity = SequenceMatcher(None, norm_inv, norm_dn).ratio()
        
        # Boost exact matches and high similarity
        if similarity > 0.8:
            return min(1.0, similarity + 0.1)
        
        return similarity
    
    @staticmethod
    def calculate_date_score(invoice_date: str, dn_date: str) -> float:
        """Calculate date proximity score (0-1)"""
        if not invoice_date or not dn_date:
            return 0.0
        
        try:
            # Parse dates (assuming YYYY-MM-DD format)
            inv_date = datetime.strptime(invoice_date, '%Y-%m-%d')
            dn_date = datetime.strptime(dn_date, '%Y-%m-%d')
            
            # Calculate days difference
            days_diff = abs((inv_date - dn_date).days)
            
            # Score based on proximity (±3 days = 1.0, ±7 days = 0.5, >7 days = 0.0)
            if days_diff <= 3:
                return 1.0
            elif days_diff <= 7:
                return 0.5
            else:
                return max(0.0, 1.0 - (days_diff - 7) * 0.1)
                
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def calculate_amount_score(invoice_amount: float, dn_amount: float) -> float:
        """Calculate amount proximity score (0-1)"""
        if not invoice_amount or not dn_amount or invoice_amount == 0:
            return 0.0
        
        # Calculate percentage difference
        diff_pct = abs(invoice_amount - dn_amount) / invoice_amount
        
        # Score based on percentage difference (±2.5% = 1.0, ±5% = 0.5, >5% = 0.0)
        if diff_pct <= 0.025:
            return 1.0
        elif diff_pct <= 0.05:
            return 0.5
        else:
            return max(0.0, 1.0 - (diff_pct - 0.05) * 10)
    
    @staticmethod
    def calculate_overall_score(supplier_score: float, date_score: float, amount_score: float) -> float:
        """Calculate overall pairing score (0-100) using deterministic weights"""
        weights = PairingService.SCORING_WEIGHTS
        
        overall_score = (
            supplier_score * weights['supplier_match'] +
            date_score * weights['date_proximity'] +
            amount_score * weights['amount_proximity']
        )
        
        return min(100.0, overall_score * 100)
    
    @staticmethod
    def get_pairing_suggestions(limit: int = 10, db_conn=None):
        """Get all pairing suggestions with scores"""
        try:
            if db_conn is None:
                with db_manager.get_connection() as conn:
                    return PairingService._get_pairing_suggestions_internal(conn, limit)
            else:
                return PairingService._get_pairing_suggestions_internal(db_conn, limit)
                
        except Exception as e:
            logger.error(f"Error getting pairing suggestions: {e}")
            return []
    
    @staticmethod
    def _get_pairing_suggestions_internal(conn, limit: int = 10):
        """Internal method for getting pairing suggestions"""
        # Get unmatched invoices and delivery notes
        invoices = conn.execute("""
            SELECT id, supplier_name, invoice_date, total_amount_pennies
            FROM invoices 
            WHERE paired = 0
            ORDER BY created_at DESC
        """).fetchall()
        
        delivery_notes = conn.execute("""
            SELECT id, supplier_name, delivery_date, total_items
            FROM delivery_notes 
            WHERE matched_invoice_id IS NULL
            ORDER BY created_at DESC
        """).fetchall()
        
        suggestions = []
        
        for inv in invoices:
            for dn in delivery_notes:
                # Calculate individual scores
                supplier_score = PairingService.calculate_supplier_score(
                    inv['supplier_name'], dn['supplier_name']
                )
                
                date_score = PairingService.calculate_date_score(
                    inv['invoice_date'], dn['delivery_date']
                )
                
                amount_score = PairingService.calculate_amount_score(
                    inv['total_amount_pennies'] / 100 if inv['total_amount_pennies'] else 0,
                    dn['total_items'] if dn['total_items'] else 0
                )
                
                # Calculate overall score
                overall_score = PairingService.calculate_overall_score(
                    supplier_score, date_score, amount_score
                )
                
                # Only include if score is above suggestion threshold
                if overall_score >= PairingService.SUGGESTION_THRESHOLD:
                    reasons = []
                    if supplier_score > 0.8:
                        reasons.append(f"Strong supplier match ({supplier_score:.2f})")
                    if date_score > 0.5:
                        reasons.append(f"Close delivery date ({date_score:.2f})")
                    if amount_score > 0.5:
                        reasons.append(f"Similar amount ({amount_score:.2f})")
                    
                    suggestions.append({
                        'delivery_note_id': dn['id'],
                        'invoice_id': inv['id'],
                        'score': int(overall_score),
                        'reasons': reasons
                    })
        
        # Sort by score and return top limit
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:limit]
    
    @staticmethod
    def confirm_pairing(delivery_note_id: str, invoice_id: str, db_conn=None):
        """Confirm pairing between delivery note and invoice"""
        try:
            if db_conn is None:
                with db_manager.get_connection() as conn:
                    return PairingService._confirm_pairing_internal(delivery_note_id, invoice_id, conn)
            else:
                return PairingService._confirm_pairing_internal(delivery_note_id, invoice_id, db_conn)
                
        except Exception as e:
            logger.error(f"Error confirming pairing: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _confirm_pairing_internal(delivery_note_id: str, invoice_id: str, conn):
        """Internal method for confirming pairing"""
        # Get the documents
        dn = conn.execute("""
            SELECT id, supplier_name, delivery_date, total_items
            FROM delivery_notes WHERE id = ?
        """, (delivery_note_id,)).fetchone()
        
        inv = conn.execute("""
            SELECT id, supplier_name, invoice_date, total_amount_pennies
            FROM invoices WHERE id = ?
        """, (invoice_id,)).fetchone()
        
        if not dn or not inv:
            return {"error": "Document not found"}
        
        # Calculate score
        supplier_score = PairingService.calculate_supplier_score(
            inv['supplier_name'], dn['supplier_name']
        )
        date_score = PairingService.calculate_date_score(
            inv['invoice_date'], dn['delivery_date']
        )
        amount_score = PairingService.calculate_amount_score(
            inv['total_amount_pennies'] / 100 if inv['total_amount_pennies'] else 0,
            dn['total_items'] if dn['total_items'] else 0
        )
        overall_score = PairingService.calculate_overall_score(
            supplier_score, date_score, amount_score
        )
        
        # Update both documents
        conn.execute("""
            UPDATE delivery_notes 
            SET matched_invoice_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (invoice_id, delivery_note_id))
        
        conn.execute("""
            UPDATE invoices 
            SET paired = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (invoice_id,))
        
        # Create audit log entry
        conn.execute("""
            INSERT INTO audit_log (timestamp, action, entity_type, entity_id, metadata_json)
            VALUES (CURRENT_TIMESTAMP, 'pairing_confirmed', 'delivery_note', ?, ?)
        """, (delivery_note_id, json.dumps({
            'invoice_id': invoice_id,
            'score': overall_score,
            'supplier_score': supplier_score,
            'date_score': date_score,
            'amount_score': amount_score
        })))
        
        conn.commit()
        
        logger.info(f"Confirmed pairing: {delivery_note_id} ↔ {invoice_id} (score: {overall_score})")
        
        return {
            "delivery_note_id": delivery_note_id,
            "invoice_id": invoice_id,
            "score": int(overall_score),
            "matched": True
        }
    
    @staticmethod
    def reject_pairing(suggestion_id: str, db_conn=None):
        """Reject a pairing suggestion"""
        try:
            if db_conn is None:
                with db_manager.get_connection() as conn:
                    return PairingService._reject_pairing_internal(suggestion_id, conn)
            else:
                return PairingService._reject_pairing_internal(suggestion_id, db_conn)
                
        except Exception as e:
            logger.error(f"Error rejecting pairing: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _reject_pairing_internal(suggestion_id: str, conn):
        """Internal method for rejecting pairing"""
        # Create audit log entry
        conn.execute("""
            INSERT INTO audit_log (timestamp, action, entity_type, entity_id, metadata_json)
            VALUES (CURRENT_TIMESTAMP, 'pairing_rejected', 'suggestion', ?, ?)
        """, (suggestion_id, json.dumps({'reason': 'manual_rejection'})))
        
        conn.commit()
        
        return {
            "suggestion_id": suggestion_id,
            "rejected": True
        }
    
    @staticmethod
    def auto_pair_high_confidence(db_conn=None):
        """Auto-pair documents with high confidence scores"""
        try:
            if db_conn is None:
                with db_manager.get_connection() as conn:
                    return PairingService._auto_pair_high_confidence_internal(conn)
            else:
                return PairingService._auto_pair_high_confidence_internal(db_conn)
                
        except Exception as e:
            logger.error(f"Error in auto-pairing: {e}")
            return []
    
    @staticmethod
    def _auto_pair_high_confidence_internal(conn):
        """Internal method for auto-pairing"""
        suggestions = PairingService._get_pairing_suggestions_internal(conn, limit=100)
        auto_paired = []
        
        for suggestion in suggestions:
            if suggestion['score'] >= PairingService.AUTO_CONFIRM_THRESHOLD:
                result = PairingService._confirm_pairing_internal(
                    suggestion['delivery_note_id'], 
                    suggestion['invoice_id'],
                    conn
                )
                if "error" not in result:
                    auto_paired.append(result)
        
        logger.info(f"Auto-paired {len(auto_paired)} documents")
        return auto_paired 