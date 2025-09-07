"""
Module for matching invoice line items to delivery note line items.
Uses fuzzy matching to pair products and detects quantity discrepancies.
"""

import logging
from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass

from ocr.parse_invoice import LineItem
from ocr.parse_delivery_note import DeliveryLineItem

logger = logging.getLogger(__name__)

@dataclass
class MatchedItem:
    """Represents a matched pair of invoice and delivery note items"""
    invoice_item: LineItem
    delivery_item: DeliveryLineItem
    similarity_score: float
    quantity_mismatch: bool
    price_mismatch: bool
    quantity_difference: Optional[float] = None
    price_difference: Optional[float] = None

@dataclass
class MatchingResult:
    """Complete result of invoice-delivery note matching"""
    matched_items: List[MatchedItem]
    invoice_only_items: List[LineItem]
    delivery_only_items: List[DeliveryLineItem]
    overall_confidence: float
    total_matches: int
    total_discrepancies: int

def _similarity(a: str, b: str) -> float:
    """
    Compute a similarity ratio between two strings.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def _normalize_description(description: str) -> str:
    """
    Normalize product description for better matching.
    
    Args:
        description: Raw product description
        
    Returns:
        Normalized description
    """
    # Convert to lowercase
    normalized = description.lower()
    
    # Remove common punctuation
    normalized = normalized.replace(',', ' ').replace('.', ' ')
    
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    
    # Remove common words that don't help with matching
    stop_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
    words = normalized.split()
    words = [word for word in words if word not in stop_words]
    
    return ' '.join(words)

def match_items(
    invoice_items: List[LineItem],
    delivery_items: List[DeliveryLineItem],
    threshold: float = 0.8,
    normalize_descriptions: bool = True
) -> MatchingResult:
    """
    Match invoice line items to delivery note line items.
    
    Args:
        invoice_items: List of invoice line items
        delivery_items: List of delivery note line items
        threshold: Minimum similarity score for matching (0.0 to 1.0)
        normalize_descriptions: Whether to normalize descriptions before matching
        
    Returns:
        MatchingResult with matched pairs and discrepancies
    """
    logger.info(f"🔄 Starting item matching: {len(invoice_items)} invoice items, {len(delivery_items)} delivery items")
    
    matched_items = []
    unmatched_invoice = []
    unmatched_delivery = delivery_items.copy()
    
    # Normalize descriptions if requested
    if normalize_descriptions:
        for item in invoice_items:
            item.description = _normalize_description(item.description)
        for item in delivery_items:
            item.description = _normalize_description(item.description)
    
    # Match each invoice item to the best delivery item
    for inv_item in invoice_items:
        best_ratio = 0.0
        best_match = None
        
        for del_item in unmatched_delivery:
            ratio = _similarity(inv_item.description, del_item.description)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = del_item
        
        if best_ratio >= threshold and best_match:
            # Check for quantity mismatch
            quantity_mismatch = False
            quantity_difference = None
            
            if inv_item.quantity is not None and best_match.quantity is not None:
                if abs(inv_item.quantity - best_match.quantity) > 0.01:  # Allow for small floating point differences
                    quantity_mismatch = True
                    quantity_difference = inv_item.quantity - best_match.quantity
            
            # Check for price mismatch (if delivery item has price info)
            price_mismatch = False
            price_difference = None
            
            # Create matched item
            matched_item = MatchedItem(
                invoice_item=inv_item,
                delivery_item=best_match,
                similarity_score=best_ratio,
                quantity_mismatch=quantity_mismatch,
                price_mismatch=price_mismatch,
                quantity_difference=quantity_difference,
                price_difference=price_difference
            )
            
            matched_items.append(matched_item)
            unmatched_delivery.remove(best_match)
            
            logger.debug(f"✅ Matched: '{inv_item.description}' -> '{best_match.description}' (similarity: {best_ratio:.3f})")
            
            if quantity_mismatch:
                logger.warning(f"⚠️ Quantity mismatch: Invoice {inv_item.quantity} vs Delivery {best_match.quantity}")
        else:
            unmatched_invoice.append(inv_item)
            logger.debug(f"❌ No match found for invoice item: '{inv_item.description}' (best similarity: {best_ratio:.3f})")
    
    # Calculate overall confidence
    total_items = len(invoice_items) + len(delivery_items)
    matched_count = len(matched_items)
    overall_confidence = matched_count / total_items if total_items > 0 else 0.0
    
    # Count discrepancies
    total_discrepancies = sum(1 for item in matched_items if item.quantity_mismatch or item.price_mismatch)
    
    result = MatchingResult(
        matched_items=matched_items,
        invoice_only_items=unmatched_invoice,
        delivery_only_items=unmatched_delivery,
        overall_confidence=overall_confidence,
        total_matches=matched_count,
        total_discrepancies=total_discrepancies
    )
    
    logger.info(f"✅ Matching completed: {matched_count} matches, {len(unmatched_invoice)} invoice-only, {len(unmatched_delivery)} delivery-only")
    logger.info(f"📊 Overall confidence: {overall_confidence:.3f}, Discrepancies: {total_discrepancies}")
    
    return result

def match_documents(
    invoice_data: Dict[str, Any],
    delivery_data: Dict[str, Any],
    threshold: float = 0.8
) -> Dict[str, Any]:
    """
    Match invoice and delivery note documents at the document level.
    
    Args:
        invoice_data: Parsed invoice data
        delivery_data: Parsed delivery note data
        threshold: Minimum similarity score for matching
        
    Returns:
        Dictionary with matching results and document-level analysis
    """
    logger.info("🔄 Starting document-level matching")
    
    # Extract line items
    invoice_items = invoice_data.get('line_items', [])
    delivery_items = delivery_data.get('line_items', [])
    
    # Perform item-level matching
    matching_result = match_items(invoice_items, delivery_items, threshold)
    
    # Document-level analysis
    supplier_match = invoice_data.get('supplier', '').lower() == delivery_data.get('supplier', '').lower()
    date_match = invoice_data.get('date') == delivery_data.get('date')
    
    # Calculate document-level confidence
    doc_confidence = 0.0
    confidence_factors = 0
    
    if supplier_match:
        doc_confidence += 0.4
        confidence_factors += 1
    
    if date_match:
        doc_confidence += 0.3
        confidence_factors += 1
    
    # Add item matching confidence
    doc_confidence += matching_result.overall_confidence * 0.3
    confidence_factors += 1
    
    if confidence_factors > 0:
        doc_confidence = doc_confidence / confidence_factors
    
    # Prepare result
    result = {
        'document_matching': {
            'supplier_match': supplier_match,
            'date_match': date_match,
            'overall_confidence': doc_confidence
        },
        'item_matching': {
            'matched_items': [
                {
                    'invoice_description': item.invoice_item.description,
                    'delivery_description': item.delivery_item.description,
                    'similarity_score': item.similarity_score,
                    'quantity_mismatch': item.quantity_mismatch,
                    'price_mismatch': item.price_mismatch,
                    'quantity_difference': item.quantity_difference,
                    'price_difference': item.price_difference
                }
                for item in matching_result.matched_items
            ],
            'invoice_only_items': [
                {
                    'description': item.description,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'total_price': item.total_price
                }
                for item in matching_result.invoice_only_items
            ],
            'delivery_only_items': [
                {
                    'description': item.description,
                    'quantity': item.quantity,
                    'unit': item.unit
                }
                for item in matching_result.delivery_only_items
            ],
            'total_matches': matching_result.total_matches,
            'total_discrepancies': matching_result.total_discrepancies,
            'overall_confidence': matching_result.overall_confidence
        },
        'summary': {
            'total_invoice_items': len(invoice_items),
            'total_delivery_items': len(delivery_items),
            'matched_percentage': (matching_result.total_matches / max(len(invoice_items), len(delivery_items))) * 100 if max(len(invoice_items), len(delivery_items)) > 0 else 0,
            'discrepancy_percentage': (matching_result.total_discrepancies / matching_result.total_matches) * 100 if matching_result.total_matches > 0 else 0
        }
    }
    
    logger.info(f"✅ Document matching completed: {result['summary']['matched_percentage']:.1f}% matched, {result['summary']['discrepancy_percentage']:.1f}% with discrepancies")
    
    return result

def suggest_matches(
    invoice_items: List[LineItem],
    delivery_items: List[DeliveryLineItem],
    threshold: float = 0.6
) -> List[Dict[str, Any]]:
    """
    Suggest potential matches below the main threshold for manual review.
    
    Args:
        invoice_items: List of invoice line items
        delivery_items: List of delivery note line items
        threshold: Lower threshold for suggestions
        
    Returns:
        List of suggested matches with similarity scores
    """
    suggestions = []
    
    for inv_item in invoice_items:
        for del_item in delivery_items:
            similarity = _similarity(inv_item.description, del_item.description)
            
            if 0.3 <= similarity < threshold:  # Suggest matches below main threshold but above noise level
                suggestions.append({
                    'invoice_item': inv_item.description,
                    'delivery_item': del_item.description,
                    'similarity_score': similarity,
                    'confidence': 'low' if similarity < 0.5 else 'medium'
                })
    
    # Sort by similarity score (highest first)
    suggestions.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    logger.info(f"💡 Generated {len(suggestions)} match suggestions")
    
    return suggestions

def validate_matching_result(result: MatchingResult) -> Dict[str, Any]:
    """
    Validate and analyze a matching result for quality assessment.
    
    Args:
        result: MatchingResult to validate
        
    Returns:
        Dictionary with validation metrics and recommendations
    """
    validation = {
        'quality_metrics': {
            'match_rate': result.overall_confidence,
            'discrepancy_rate': result.total_discrepancies / result.total_matches if result.total_matches > 0 else 0,
            'coverage_rate': result.total_matches / max(len(result.matched_items) + len(result.invoice_only_items), 
                                                      len(result.matched_items) + len(result.delivery_only_items)) if max(len(result.matched_items) + len(result.invoice_only_items), 
                                                                                                                      len(result.matched_items) + len(result.delivery_only_items)) > 0 else 0
        },
        'recommendations': []
    }
    
    # Generate recommendations based on metrics
    if result.overall_confidence < 0.5:
        validation['recommendations'].append("Low match rate - consider manual review of all items")
    
    if result.total_discrepancies > result.total_matches * 0.3:
        validation['recommendations'].append("High discrepancy rate - review quantity and price mismatches")
    
    if len(result.invoice_only_items) > len(result.matched_items) * 0.5:
        validation['recommendations'].append("Many invoice-only items - check for missing delivery items")
    
    if len(result.delivery_only_items) > len(result.matched_items) * 0.5:
        validation['recommendations'].append("Many delivery-only items - check for extra delivery items")
    
    if not validation['recommendations']:
        validation['recommendations'].append("Matching quality appears good - proceed with confidence")
    
    return validation 