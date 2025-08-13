"""
Confidence Scoring Module for Owlin Agent

Evaluates the reliability and completeness of parsed invoice data.
Provides granular scoring based on metadata quality, line item completeness,
and OCR confidence to determine if manual review is required.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def score_confidence(
    metadata: Dict[str, Any],
    line_items: List[Dict[str, Any]],
    ocr_confidence: float
) -> Dict[str, Any]:
    """
    Score the confidence of parsed invoice data.
    
    Evaluates multiple factors to determine data quality:
    - Metadata completeness (supplier, date, totals)
    - Line item quality and quantity
    - OCR confidence score
    - Data consistency and reasonableness
    
    Args:
        metadata: Dictionary containing invoice metadata
        line_items: List of line item dictionaries
        ocr_confidence: OCR confidence score (0-100)
        
    Returns:
        Dictionary with confidence score and flags:
        {
            "score": float,                    # 0-100 confidence score
            "manual_review_required": bool,    # True if score < 60
            "flags": List[Dict]               # List of confidence-related flags
        }
    """
    logger.debug("🔍 Starting confidence scoring")
    
    # Handle None values gracefully
    if metadata is None:
        metadata = {}
    if line_items is None:
        line_items = []
    
    flags = []
    score_components = {}
    
    # Component 1: Metadata Quality (30 points max)
    metadata_score, metadata_flags = _score_metadata(metadata)
    score_components['metadata'] = metadata_score
    flags.extend(metadata_flags)
    
    # Component 2: Line Items Quality (40 points max)
    line_items_score, line_items_flags = _score_line_items(line_items)
    score_components['line_items'] = line_items_score
    flags.extend(line_items_flags)
    
    # Component 3: OCR Confidence (20 points max)
    ocr_score, ocr_flags = _score_ocr_confidence(ocr_confidence)
    score_components['ocr'] = ocr_score
    flags.extend(ocr_flags)
    
    # Component 4: Data Consistency (10 points max)
    consistency_score, consistency_flags = _score_data_consistency(metadata, line_items)
    score_components['consistency'] = consistency_score
    flags.extend(consistency_flags)
    
    # Calculate total score
    total_score = sum(score_components.values())
    total_score = min(max(total_score, 0.0), 100.0)  # Clamp to 0-100
    
    # Determine if manual review is required
    manual_review_required = total_score < 60.0
    
    logger.debug(f"📊 Confidence scoring completed:")
    logger.debug(f"   Metadata: {metadata_score:.1f}/30")
    logger.debug(f"   Line Items: {line_items_score:.1f}/40")
    logger.debug(f"   OCR: {ocr_score:.1f}/20")
    logger.debug(f"   Consistency: {consistency_score:.1f}/10")
    logger.debug(f"   Total: {total_score:.1f}/100")
    
    return {
        "score": round(total_score, 1),
        "manual_review_required": manual_review_required,
        "flags": flags,
        "score_breakdown": score_components
    }

def _score_metadata(metadata: Dict[str, Any]) -> tuple[float, List[Dict[str, Any]]]:
    """
    Score metadata completeness and quality.
    
    Args:
        metadata: Invoice metadata dictionary
        
    Returns:
        Tuple of (score, flags)
    """
    score = 0.0
    flags = []
    
    # Check supplier name
    supplier_name = metadata.get('supplier_name', '')
    if supplier_name and supplier_name != 'Unknown':
        score += 8.0
    else:
        flags.append({
            "type": "missing_supplier",
            "severity": "warning",
            "field": "supplier_name",
            "message": "Supplier name not found or is 'Unknown'",
            "suggested_action": "Manually verify supplier name from invoice"
        })
    
    # Check invoice number
    invoice_number = metadata.get('invoice_number', '')
    if invoice_number and invoice_number != 'Unknown':
        score += 6.0
    else:
        flags.append({
            "type": "missing_invoice_number",
            "severity": "warning",
            "field": "invoice_number",
            "message": "Invoice number not found or is 'Unknown'",
            "suggested_action": "Manually verify invoice number"
        })
    
    # Check invoice date
    invoice_date = metadata.get('invoice_date', '')
    if invoice_date:
        score += 6.0
    else:
        flags.append({
            "type": "missing_date",
            "severity": "warning",
            "field": "invoice_date",
            "message": "Invoice date not found",
            "suggested_action": "Manually verify invoice date"
        })
    
    # Check total amount
    total_amount = metadata.get('total_amount', 0.0)
    if total_amount > 0.0:
        score += 5.0
    else:
        flags.append({
            "type": "missing_total",
            "severity": "critical",
            "field": "total_amount",
            "message": "Invoice total amount is £0.00 or missing",
            "suggested_action": "Manually verify total amount - this is critical"
        })
    
    # Check VAT information
    vat_amount = metadata.get('vat', 0.0)
    vat_rate = metadata.get('vat_rate', 0.0)
    if vat_amount > 0.0 and vat_rate > 0.0:
        score += 5.0
    elif vat_amount == 0.0 and vat_rate > 0.0:
        score += 2.0  # Partial credit for having VAT rate
        flags.append({
            "type": "missing_vat_amount",
            "severity": "warning",
            "field": "vat",
            "message": "VAT amount is £0.00 but VAT rate is present",
            "suggested_action": "Verify VAT calculation"
        })
    else:
        flags.append({
            "type": "missing_vat_info",
            "severity": "warning",
            "field": "vat",
            "message": "VAT information incomplete or missing",
            "suggested_action": "Verify VAT rate and amount"
        })
    
    return score, flags

def _score_line_items(line_items: List[Dict[str, Any]]) -> tuple[float, List[Dict[str, Any]]]:
    """
    Score line items quality and completeness.
    
    Args:
        line_items: List of line item dictionaries
        
    Returns:
        Tuple of (score, flags)
    """
    score = 0.0
    flags = []
    
    if not line_items:
        flags.append({
            "type": "no_line_items",
            "severity": "critical",
            "field": "line_items",
            "message": "No line items found in invoice",
            "suggested_action": "Manual review required - check if OCR missed line items"
        })
        return 0.0, flags
    
    # Score based on number of line items (more items = higher score)
    item_count = len(line_items)
    if item_count >= 5:
        score += 15.0
    elif item_count >= 3:
        score += 12.0
    elif item_count >= 1:
        score += 8.0
    
    # Check quality of each line item
    valid_items = 0
    for i, item in enumerate(line_items):
        item_score = _score_single_line_item(item)
        if item_score > 0:
            valid_items += 1
        score += item_score
    
    # Average quality score (max 25 points)
    if line_items:
        avg_quality = score / len(line_items)
        score = min(avg_quality, 25.0) + (valid_items * 2.0)  # Bonus for valid items
    
    # Check for missing critical fields
    for i, item in enumerate(line_items):
        item_flags = _check_line_item_flags(item, i)
        flags.extend(item_flags)
    
    return score, flags

def _score_single_line_item(item: Dict[str, Any]) -> float:
    """
    Score a single line item for quality.
    
    Args:
        item: Line item dictionary
        
    Returns:
        Quality score (0-10)
    """
    if item is None:
        return 0.0
    
    score = 0.0
    
    # Check item name/description
    item_name = item.get('item', '') or item.get('description', '')
    if item_name and len(str(item_name).strip()) > 2:
        score += 3.0
    
    # Check quantity - handle string quantities
    quantity = item.get('quantity', 0.0)
    try:
        quantity = float(quantity) if quantity is not None else 0.0
    except (ValueError, TypeError):
        quantity = 0.0
    
    if quantity > 0.0:
        score += 2.0
    
    # Check unit price - handle string prices
    unit_price = item.get('unit_price_excl_vat', 0.0) or item.get('unit_price', 0.0)
    try:
        unit_price = float(unit_price) if unit_price is not None else 0.0
    except (ValueError, TypeError):
        unit_price = 0.0
    
    if unit_price > 0.0:
        score += 3.0
    
    # Check line total - handle string totals
    line_total = item.get('line_total_excl_vat', 0.0) or item.get('total_price', 0.0)
    try:
        line_total = float(line_total) if line_total is not None else 0.0
    except (ValueError, TypeError):
        line_total = 0.0
    
    if line_total > 0.0:
        score += 2.0
    
    return score

def _check_line_item_flags(item: Dict[str, Any], index: int) -> List[Dict[str, Any]]:
    """
    Check a line item for potential issues and create flags.
    
    Args:
        item: Line item dictionary
        index: Line item index
        
    Returns:
        List of flags for this line item
    """
    if item is None:
        return []
    
    flags = []
    
    # Check for missing item name
    item_name = item.get('item', '') or item.get('description', '')
    if not item_name or len(str(item_name).strip()) < 3:
        flags.append({
            "type": "vague_item_description",
            "severity": "warning",
            "field": f"line_items[{index}].item",
            "message": f"Line item {index + 1} has vague or missing description",
            "suggested_action": "Manually verify item description"
        })
    
    # Check for zero quantity - handle string quantities
    quantity = item.get('quantity', 0.0)
    try:
        quantity = float(quantity) if quantity is not None else 0.0
    except (ValueError, TypeError):
        quantity = 0.0
    
    if quantity <= 0.0:
        flags.append({
            "type": "zero_quantity",
            "severity": "warning",
            "field": f"line_items[{index}].quantity",
            "message": f"Line item {index + 1} has zero or negative quantity",
            "suggested_action": "Verify quantity is correct"
        })
    
    # Check for zero unit price - handle string prices
    unit_price = item.get('unit_price_excl_vat', 0.0) or item.get('unit_price', 0.0)
    try:
        unit_price = float(unit_price) if unit_price is not None else 0.0
    except (ValueError, TypeError):
        unit_price = 0.0
    
    if unit_price <= 0.0:
        flags.append({
            "type": "zero_unit_price",
            "severity": "warning",
            "field": f"line_items[{index}].unit_price",
            "message": f"Line item {index + 1} has zero unit price",
            "suggested_action": "Verify unit price is correct"
        })
    
    return flags

def _score_ocr_confidence(ocr_confidence: float) -> tuple[float, List[Dict[str, Any]]]:
    """
    Score based on OCR confidence.
    
    Args:
        ocr_confidence: OCR confidence score (0-100)
        
    Returns:
        Tuple of (score, flags)
    """
    score = 0.0
    flags = []
    
    # Handle string OCR confidence values
    try:
        ocr_confidence = float(ocr_confidence) if ocr_confidence is not None else 0.0
    except (ValueError, TypeError):
        ocr_confidence = 0.0
    
    if ocr_confidence >= 90.0:
        score = 20.0
    elif ocr_confidence >= 80.0:
        score = 16.0
    elif ocr_confidence >= 70.0:
        score = 12.0
    elif ocr_confidence >= 60.0:
        score = 8.0
    elif ocr_confidence >= 40.0:
        score = 4.0
    else:
        score = 0.0
        flags.append({
            "type": "low_ocr_confidence",
            "severity": "critical",
            "field": "ocr_confidence",
            "message": f"OCR confidence is very low ({ocr_confidence:.1f}%)",
            "suggested_action": "Consider re-scanning invoice for better quality"
        })
    
    return score, flags

def _score_data_consistency(metadata: Dict[str, Any], line_items: List[Dict[str, Any]]) -> tuple[float, List[Dict[str, Any]]]:
    """
    Score data consistency and reasonableness.
    
    Args:
        metadata: Invoice metadata
        line_items: List of line items
        
    Returns:
        Tuple of (score, flags)
    """
    score = 0.0
    flags = []
    
    # Check if line items total matches invoice total
    if line_items and metadata.get('total_amount', 0.0) > 0.0:
        calculated_total = sum(
            item.get('line_total_excl_vat', 0.0) or item.get('total_price', 0.0)
            for item in line_items
        )
        
        if calculated_total > 0.0:
            total_amount = metadata.get('total_amount', 0.0)
            difference = abs(calculated_total - total_amount)
            
            if difference < 0.01:  # Perfect match
                score += 10.0
            elif difference < total_amount * 0.05:  # Within 5%
                score += 7.0
                flags.append({
                    "type": "subtotal_mismatch",
                    "severity": "warning",
                    "field": "total_amount",
                    "message": f"Line items total ({calculated_total:.2f}) doesn't match invoice total ({total_amount:.2f})",
                    "suggested_action": "Verify line items and total amount"
                })
            else:
                flags.append({
                    "type": "major_subtotal_mismatch",
                    "severity": "critical",
                    "field": "total_amount",
                    "message": f"Major mismatch: line items total ({calculated_total:.2f}) vs invoice total ({total_amount:.2f})",
                    "suggested_action": "Critical review required - check for missing line items or errors"
                })
    
    # Check for reasonable date (not in future, not too old)
    invoice_date = metadata.get('invoice_date', '')
    if invoice_date:
        try:
            date_obj = datetime.strptime(invoice_date, "%Y-%m-%d")
            today = datetime.now()
            days_diff = (today - date_obj).days
            
            if days_diff < 0:  # Future date
                flags.append({
                    "type": "future_date",
                    "severity": "warning",
                    "field": "invoice_date",
                    "message": f"Invoice date ({invoice_date}) is in the future",
                    "suggested_action": "Verify invoice date is correct"
                })
            elif days_diff > 365:  # Very old
                flags.append({
                    "type": "old_invoice",
                    "severity": "info",
                    "field": "invoice_date",
                    "message": f"Invoice date ({invoice_date}) is over 1 year old",
                    "suggested_action": "Consider if this invoice is still relevant"
                })
            else:
                score += 5.0  # Reasonable date
        except ValueError:
            flags.append({
                "type": "invalid_date",
                "severity": "warning",
                "field": "invoice_date",
                "message": f"Invalid invoice date format: {invoice_date}",
                "suggested_action": "Verify date format is YYYY-MM-DD"
            })
    
    return score, flags


if __name__ == "__main__":
    # Test confidence scoring
    logging.basicConfig(level=logging.INFO)
    
    # Test case 1: Good invoice
    good_metadata = {
        "supplier_name": "Quality Foods Ltd",
        "invoice_number": "INV-2024-001",
        "invoice_date": "2024-12-01",
        "total_amount": 150.00,
        "subtotal": 125.00,
        "vat": 25.00,
        "vat_rate": 20.0
    }
    
    good_line_items = [
        {
            "item": "Beef Sirloin",
            "quantity": 5.0,
            "unit_price_excl_vat": 20.00,
            "line_total_excl_vat": 100.00
        },
        {
            "item": "Chicken Breast",
            "quantity": 2.5,
            "unit_price_excl_vat": 10.00,
            "line_total_excl_vat": 25.00
        }
    ]
    
    result = score_confidence(good_metadata, good_line_items, 85.0)
    print("✅ Good Invoice Test:")
    print(f"   Score: {result['score']:.1f}%")
    print(f"   Manual Review: {result['manual_review_required']}")
    print(f"   Flags: {len(result['flags'])}")
    
    # Test case 2: Poor invoice
    poor_metadata = {
        "supplier_name": "Unknown",
        "invoice_number": "Unknown",
        "invoice_date": "",
        "total_amount": 0.0,
        "subtotal": 0.0,
        "vat": 0.0,
        "vat_rate": 0.0
    }
    
    poor_line_items = []
    
    result = score_confidence(poor_metadata, poor_line_items, 25.0)
    print("\n❌ Poor Invoice Test:")
    print(f"   Score: {result['score']:.1f}%")
    print(f"   Manual Review: {result['manual_review_required']}")
    print(f"   Flags: {len(result['flags'])}") 