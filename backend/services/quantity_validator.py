"""
Quantity Validation Service

Validates quantity matches between invoices and delivery notes before pairing.
Uses fuzzy matching to align line items by description and compares quantities.
"""
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import logging
from backend.app.db import get_line_items_for_invoice, get_line_items_for_doc

LOGGER = logging.getLogger("owlin.services.quantity_validator")
LOGGER.setLevel(logging.INFO)

# Constants
QUANTITY_TOLERANCE = 0.01  # Allow small rounding differences
DESCRIPTION_SIMILARITY_THRESHOLD = 0.8  # Minimum similarity for item matching
QUANTITY_MATCH_THRESHOLD = 0.8  # Minimum match score for valid pairing


def _normalize_description(desc: str) -> str:
    """Normalize description for comparison"""
    if not desc:
        return ""
    return desc.lower().strip()


def _calculate_description_similarity(desc1: str, desc2: str) -> float:
    """Calculate similarity between two descriptions using SequenceMatcher"""
    norm1 = _normalize_description(desc1)
    norm2 = _normalize_description(desc2)
    
    if not norm1 or not norm2:
        return 0.0
    
    if norm1 == norm2:
        return 1.0
    
    return SequenceMatcher(None, norm1, norm2).ratio()


def _match_items_by_description(
    invoice_items: List[Dict], 
    delivery_items: List[Dict]
) -> List[Tuple[Dict, Optional[Dict], float]]:
    """
    Match invoice items to delivery items by description.
    
    Returns list of tuples: (invoice_item, matched_delivery_item, similarity_score)
    """
    matched = []
    used_delivery_indices = set()
    
    for inv_item in invoice_items:
        inv_desc = inv_item.get("desc", "") or inv_item.get("description", "")
        best_match = None
        best_similarity = 0.0
        best_index = -1
        
        for idx, del_item in enumerate(delivery_items):
            if idx in used_delivery_indices:
                continue
            
            del_desc = del_item.get("desc", "") or del_item.get("description", "")
            similarity = _calculate_description_similarity(inv_desc, del_desc)
            
            if similarity > best_similarity and similarity >= DESCRIPTION_SIMILARITY_THRESHOLD:
                best_similarity = similarity
                best_match = del_item
                best_index = idx
        
        if best_match:
            used_delivery_indices.add(best_index)
        
        matched.append((inv_item, best_match, best_similarity))
    
    return matched


def calculate_quantity_match_score(
    invoice_items: List[Dict], 
    delivery_items: List[Dict]
) -> float:
    """
    Calculate overall quantity match score between invoice and delivery items.
    
    Returns score between 0.0 and 1.0, where 1.0 means perfect match.
    """
    if not invoice_items:
        return 0.0 if delivery_items else 1.0
    
    if not delivery_items:
        return 0.0
    
    matched = _match_items_by_description(invoice_items, delivery_items)
    
    if not matched:
        return 0.0
    
    total_score = 0.0
    matched_count = 0
    
    for inv_item, del_item, similarity in matched:
        if del_item is None:
            # Item exists in invoice but not in delivery note
            total_score += 0.0
            matched_count += 1
        else:
            inv_qty = inv_item.get("qty", 0) or 0
            del_qty = del_item.get("qty", 0) or 0
            
            if inv_qty == 0 and del_qty == 0:
                # Both zero, consider as match
                item_score = 1.0
            elif inv_qty == 0 or del_qty == 0:
                # One is zero, other is not
                item_score = 0.0
            else:
                # Calculate quantity match ratio
                qty_diff = abs(inv_qty - del_qty)
                max_qty = max(inv_qty, del_qty)
                
                if qty_diff <= QUANTITY_TOLERANCE:
                    item_score = 1.0
                else:
                    # Penalize based on difference ratio
                    item_score = max(0.0, 1.0 - (qty_diff / max_qty))
            
            # Weight by description similarity
            weighted_score = item_score * similarity
            total_score += weighted_score
            matched_count += 1
    
    if matched_count == 0:
        return 0.0
    
    return total_score / matched_count


def validate_quantity_match(
    invoice_id: str, 
    delivery_id: str
) -> Dict:
    """
    Validate quantity match between invoice and delivery note.
    
    Args:
        invoice_id: Invoice ID (from invoices table)
        delivery_id: Delivery note ID (from documents table, as doc_id)
    
    Returns:
        Dict with:
            - is_valid: bool - True if quantities match within tolerance
            - match_score: float - Overall match score (0.0-1.0)
            - discrepancies: List[Dict] - Items with quantity differences
            - warnings: List[str] - Human-readable warnings
    """
    try:
        # Get line items for both documents
        # For delivery notes, pass invoice_id=None to filter by invoice_id IS NULL
        invoice_items = get_line_items_for_invoice(invoice_id)
        delivery_items = get_line_items_for_doc(delivery_id, invoice_id=None)
        
        # Handle edge case: both empty
        if not invoice_items and not delivery_items:
            return {
                "is_valid": True,
                "match_score": 1.0,
                "discrepancies": [],
                "warnings": ["No line items to compare in either document"]
            }
        
        if not invoice_items:
            return {
                "is_valid": False,
                "match_score": 0.0,
                "discrepancies": [],
                "warnings": ["Invoice has no line items"]
            }
        
        if not delivery_items:
            return {
                "is_valid": False,
                "match_score": 0.0,
                "discrepancies": [],
                "warnings": ["Delivery note has no line items"]
            }
        
        # Match items and find discrepancies
        matched = _match_items_by_description(invoice_items, delivery_items)
        discrepancies = []
        warnings = []
        
        for inv_item, del_item, similarity in matched:
            inv_desc = inv_item.get("desc", "") or inv_item.get("description", "")
            inv_qty = inv_item.get("qty", 0) or 0
            
            if del_item is None:
                # Item missing in delivery note
                discrepancies.append({
                    "description": inv_desc,
                    "invoice_qty": float(inv_qty),
                    "delivery_qty": 0.0,
                    "difference": float(inv_qty),
                    "severity": "critical" if inv_qty > 0 else "warning"
                })
                warnings.append(f"Item '{inv_desc}' (qty: {inv_qty}) not found in delivery note")
            else:
                del_qty = del_item.get("qty", 0) or 0
                qty_diff = abs(inv_qty - del_qty)
                
                if qty_diff > QUANTITY_TOLERANCE:
                    # Determine severity
                    if inv_qty > 0:
                        diff_ratio = qty_diff / inv_qty
                        if diff_ratio > 0.2:  # More than 20% difference
                            severity = "critical"
                        elif diff_ratio > 0.1:  # More than 10% difference
                            severity = "warning"
                        else:
                            severity = "info"
                    else:
                        severity = "warning"
                    
                    discrepancies.append({
                        "description": inv_desc,
                        "invoice_qty": float(inv_qty),
                        "delivery_qty": float(del_qty),
                        "difference": float(qty_diff if inv_qty > del_qty else -qty_diff),
                        "severity": severity
                    })
                    
                    if inv_qty > del_qty:
                        warnings.append(
                            f"Item '{inv_desc}': Invoice has {inv_qty}, delivery note has {del_qty} "
                            f"(shortage of {qty_diff})"
                        )
                    else:
                        warnings.append(
                            f"Item '{inv_desc}': Invoice has {inv_qty}, delivery note has {del_qty} "
                            f"(over-delivery of {qty_diff})"
                        )
        
        # Check for items in delivery note but not in invoice
        matched_delivery_descs = {
            _normalize_description(del_item.get("desc", "") or del_item.get("description", ""))
            for _, del_item, _ in matched
            if del_item is not None
        }
        
        for del_item in delivery_items:
            del_desc = del_item.get("desc", "") or del_item.get("description", "")
            del_desc_norm = _normalize_description(del_desc)
            
            if del_desc_norm not in matched_delivery_descs:
                del_qty = del_item.get("qty", 0) or 0
                if del_qty > 0:
                    discrepancies.append({
                        "description": del_desc,
                        "invoice_qty": 0.0,
                        "delivery_qty": float(del_qty),
                        "difference": float(-del_qty),
                        "severity": "info"
                    })
                    warnings.append(f"Item '{del_desc}' (qty: {del_qty}) in delivery note but not in invoice")
        
        # Calculate overall match score
        match_score = calculate_quantity_match_score(invoice_items, delivery_items)
        
        # Determine if valid (match score above threshold and no critical discrepancies)
        critical_count = sum(1 for d in discrepancies if d["severity"] == "critical")
        is_valid = match_score >= QUANTITY_MATCH_THRESHOLD and critical_count == 0
        
        if not is_valid and not warnings:
            warnings.append(f"Quantity match score: {match_score:.1%} (below {QUANTITY_MATCH_THRESHOLD:.0%} threshold)")
        
        LOGGER.info(
            f"Quantity validation: invoice={invoice_id}, delivery={delivery_id}, "
            f"score={match_score:.2f}, valid={is_valid}, discrepancies={len(discrepancies)}"
        )
        
        return {
            "is_valid": is_valid,
            "match_score": match_score,
            "discrepancies": discrepancies,
            "warnings": warnings
        }
        
    except Exception as e:
        LOGGER.error(f"Error validating quantity match: {e}", exc_info=True)
        return {
            "is_valid": False,
            "match_score": 0.0,
            "discrepancies": [],
            "warnings": [f"Error validating quantities: {str(e)}"]
        }

