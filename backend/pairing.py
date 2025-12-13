"""
Document Pairing Service - Invoice and Delivery Note Matching

Implements sophisticated scoring algorithm for document pairing:
- Supplier match (exact/alias): 0.6 weight
- Date distance (≤ 3 days): 0.2 weight  
- Amount proximity (≤ 2.5%): 0.2 weight
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from db_manager_unified import get_db_manager

logger = logging.getLogger(__name__)

def get_pairing_suggestions(invoice_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Get pairing suggestions for an invoice
    
    Args:
        invoice_id: Invoice ID to find pairs for
        top_k: Number of top suggestions to return
        
    Returns:
        List of suggestions with dn_id, score, and rationale
    """
    db_manager = get_db_manager()
    
    try:
        with db_manager.get_connection() as conn:
            # Get invoice details
            invoice = conn.execute("""
                SELECT supplier_name, invoice_date, total_amount_pennies
                FROM invoices 
                WHERE id = ?
            """, (invoice_id,)).fetchone()
            
            if not invoice:
                logger.error(f"Invoice {invoice_id} not found")
                return []
            
            # Get unmatched delivery notes
            delivery_notes = conn.execute("""
                SELECT id, supplier_name, delivery_date, total_items, 
                       matched_invoice_id, confidence
                FROM delivery_notes 
                WHERE matched_invoice_id IS NULL
                ORDER BY delivery_date DESC
            """).fetchall()
            
            if not delivery_notes:
                return []
            
            suggestions = []
            
            for dn in delivery_notes:
                score_details = _calculate_pairing_score(
                    invoice_supplier=invoice['supplier_name'],
                    invoice_date=invoice['invoice_date'],
                    invoice_amount=invoice['total_amount_pennies'],
                    dn_supplier=dn['supplier_name'],
                    dn_date=dn['delivery_date'],
                    dn_items=dn['total_items']
                )
                
                if score_details['score'] > 0.1:  # Only include meaningful matches
                    suggestions.append({
                        'dn_id': dn['id'],
                        'score': score_details['score'],
                        'rationale': score_details['rationale']
                    })
            
            # Sort by score and return top_k
            suggestions.sort(key=lambda x: x['score'], reverse=True)
            return suggestions[:top_k]
            
    except Exception as e:
        logger.error(f"Failed to get pairing suggestions: {e}")
        return []

def _calculate_pairing_score(invoice_supplier: str, invoice_date: str, invoice_amount: int,
                           dn_supplier: str, dn_date: str, dn_items: int) -> Dict[str, Any]:
    """
    Calculate pairing score between invoice and delivery note
    
    Returns:
        Dictionary with score and rationale details
    """
    rationale = []
    
    # Supplier match (0.7 weight - increased for delivery notes)
    supplier_score = _calculate_supplier_match(invoice_supplier, dn_supplier)
    supplier_weight = 0.7
    
    if supplier_score == 1.0:
        rationale.append("Exact supplier match")
    elif supplier_score > 0.8:
        rationale.append("Similar supplier name")
    elif supplier_score > 0.5:
        rationale.append("Partial supplier match")
    else:
        rationale.append("Different suppliers")
    
    # Date distance (0.3 weight - increased for delivery notes)
    date_score = _calculate_date_proximity(invoice_date, dn_date)
    date_weight = 0.3
    
    if date_score == 1.0:
        rationale.append("Same date")
    elif date_score > 0.8:
        rationale.append("Within 1 day")
    elif date_score > 0.5:
        rationale.append("Within 3 days")
    else:
        rationale.append("Date mismatch")
    
    # Amount proximity (0.0 weight for delivery notes)
    amount_score = 0.0  # Not applicable for delivery notes
    amount_weight = 0.0
    rationale.append("Amount not applicable (delivery note)")
    
    # Calculate weighted score
    total_score = (
        supplier_score * supplier_weight +
        date_score * date_weight +
        amount_score * amount_weight
    )
    
    return {
        'score': round(total_score, 3),
        'rationale': rationale,
        'details': {
            'supplier_score': supplier_score,
            'date_score': date_score,
            'amount_score': amount_score
        }
    }

def _calculate_supplier_match(supplier1: str, supplier2: str) -> float:
    """Calculate supplier name similarity"""
    if not supplier1 or not supplier2:
        return 0.0
    
    # Normalize names
    name1 = supplier1.lower().strip()
    name2 = supplier2.lower().strip()
    
    # Exact match
    if name1 == name2:
        return 1.0
    
    # Simple similarity using common words
    words1 = set(name1.split())
    words2 = set(name2.split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0

def _calculate_date_proximity(date1_str: str, date2_str: str) -> float:
    """Calculate date proximity score"""
    try:
        # Parse dates
        date1 = datetime.strptime(date1_str, '%Y-%m-%d')
        date2 = datetime.strptime(date2_str, '%Y-%m-%d')
        
        # Calculate difference
        diff_days = abs((date1 - date2).days)
        
        if diff_days == 0:
            return 1.0
        elif diff_days == 1:
            return 0.8
        elif diff_days <= 3:
            return 0.6
        elif diff_days <= 7:
            return 0.3
        else:
            return 0.1
    except:
        return 0.0

def _calculate_amount_proximity(amount1: int, amount2: int) -> float:
    """Calculate amount proximity score"""
    if amount1 == 0 or amount2 == 0:
        return 0.0
    
    # Calculate percentage difference
    diff_percent = abs(amount1 - amount2) / max(amount1, amount2)
    
    if diff_percent <= 0.025:  # ≤ 2.5%
        return 1.0
    elif diff_percent <= 0.05:  # ≤ 5%
        return 0.8
    elif diff_percent <= 0.10:  # ≤ 10%
        return 0.5
    else:
        return 0.1

def confirm_pairing(invoice_id: str, delivery_note_id: str) -> bool:
    """
    Confirm pairing between invoice and delivery note
    
    Args:
        invoice_id: Invoice ID
        delivery_note_id: Delivery note ID
        
    Returns:
        True if pairing was successful
    """
    db_manager = get_db_manager()
    
    try:
        with db_manager.get_connection() as conn:
            # Update both documents
            conn.execute("""
                UPDATE invoices 
                SET paired = TRUE, updated_at = datetime('now')
                WHERE id = ?
            """, (invoice_id,))
            
            conn.execute("""
                UPDATE delivery_notes 
                SET matched_invoice_id = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (invoice_id, delivery_note_id))
            
            conn.commit()
            
            # Log audit event
            db_manager.log_audit_event(
                action='pairing_confirmed',
                entity_type='invoice',
                entity_id=invoice_id,
                metadata_json=f'{{"delivery_note_id": "{delivery_note_id}"}}'
            )
            
            logger.info(f"Pairing confirmed: invoice {invoice_id} <-> delivery note {delivery_note_id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to confirm pairing: {e}")
        return False

def auto_pair_if_threshold_met(invoice_id: str, threshold: float = 0.92) -> Optional[str]:
    """
    Auto-pair if score meets threshold and no conflicts
    
    Args:
        invoice_id: Invoice ID to check for auto-pairing
        threshold: Minimum score for auto-pairing (default 0.92)
        
    Returns:
        Delivery note ID if auto-paired, None otherwise
    """
    suggestions = get_pairing_suggestions(invoice_id, top_k=3)
    
    if not suggestions:
        return None
    
    best_match = suggestions[0]
    
    # Check if best match meets threshold
    if best_match['score'] >= threshold:
        # Check for conflicts (no other high-scoring matches)
        if len(suggestions) == 1 or suggestions[1]['score'] < threshold - 0.1:
            # Auto-pair
            if confirm_pairing(invoice_id, best_match['dn_id']):
                logger.info(f"Auto-paired invoice {invoice_id} with delivery note {best_match['dn_id']} (score: {best_match['score']})")
                return best_match['dn_id']
    
    return None 