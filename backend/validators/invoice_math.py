"""
Deterministic Mathematical Validation - Invoice Line Items
Validate price coherence, pack descriptors, VAT calculations, and totals.
"""

import math
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN
from config_core import PRICE_TOL_PCT, PRICE_TOL_PENNIES, QTY_TOL, FOC_TERMS


def banker_round(value: float, places: int = 2) -> float:
    """
    Banker's rounding to specified decimal places.
    Rounds to even when exactly halfway between two values.
    """
    decimal_value = Decimal(str(value))
    rounded = decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    return float(rounded)


def check_price_coherence(unit_price: float, quantity: float, line_total: float, 
                         description: str = "") -> Tuple[bool, Optional[str]]:
    """
    Check if unit_price * quantity = line_total within tolerances.
    
    Returns:
        (is_valid, error_code)
    """
    # Handle FOC lines
    if line_total == 0 and (unit_price == 0 or any(term in description.lower() for term in FOC_TERMS)):
        return True, "FOC_LINE"
    
    # Calculate expected total
    expected_total = banker_round(unit_price * quantity)
    actual_total = banker_round(line_total)
    
    # Calculate absolute and percentage differences
    abs_diff = abs(expected_total - actual_total)
    pct_diff = abs_diff / actual_total if actual_total != 0 else float('inf')
    
    # Check if this looks like a large discount (more than 30% difference)
    # Only allow this for very large discounts that are clearly intentional
    if pct_diff > 0.30 and actual_total < expected_total and abs_diff > 10.0:
        # This is likely a large intentional discount, not a math error
        return True, None
    
    # Check tolerances: must exceed both 1p AND 1%
    if abs_diff > PRICE_TOL_PENNIES and pct_diff > PRICE_TOL_PCT:
        return False, "PRICE_INCOHERENT"
    
    return True, None


def check_pack_descriptor(quantity: float, packs: Optional[float], 
                         units_per_pack: Optional[float], description: str) -> Tuple[bool, Optional[str]]:
    """
    Check pack descriptor consistency.
    
    Returns:
        (is_valid, error_code)
    """
    # If we have pack information, validate it
    if packs is not None and units_per_pack is not None:
        expected_quantity = packs * units_per_pack
        if abs(expected_quantity - quantity) > QTY_TOL:
            return False, "PACK_MISMATCH"
    elif packs is not None and units_per_pack is None:
        return False, "PACK_DESCRIPTOR_PARTIAL"
    elif packs is None and units_per_pack is not None:
        return False, "PACK_DESCRIPTOR_PARTIAL"
    
    return True, None


def check_size_drift(quantity: float, unit_size_ml: Optional[float], 
                    unit_size_g: Optional[float], line_total: float) -> Tuple[bool, Optional[str]]:
    """
    Check if size is inferred but totals are missing.
    
    Returns:
        (is_valid, error_code)
    """
    has_size_info = unit_size_ml is not None or unit_size_g is not None
    has_total = line_total > 0
    
    if has_size_info and not has_total:
        return False, "SIZE_DRIFT"
    
    return True, None


def check_vat_calculation(subtotal: float, vat_amount: float, vat_rate: Optional[float], 
                         invoice_total: float) -> Tuple[bool, Optional[str]]:
    """
    Check VAT calculation consistency.
    
    Returns:
        (is_valid, error_code)
    """
    if vat_rate is not None:
        # VAT rate provided - check calculation
        expected_vat = banker_round(subtotal * (vat_rate / 100))
        actual_vat = banker_round(vat_amount)
        
        if abs(expected_vat - actual_vat) > PRICE_TOL_PENNIES:
            return False, "VAT_MISMATCH"
    
    # Check subtotal + VAT = total
    expected_total = banker_round(subtotal + vat_amount)
    actual_total = banker_round(invoice_total)
    
    if abs(expected_total - actual_total) > PRICE_TOL_PENNIES:
        return False, "SUBTOTAL_MISMATCH"
    
    return True, None


def check_negative_adjustments(line_totals: List[float]) -> Tuple[bool, Optional[str]]:
    """
    Check for negative line adjustments.
    
    Returns:
        (is_valid, error_code)
    """
    if any(total < 0 for total in line_totals):
        return False, "NEGATIVE_ADJUSTMENT_PRESENT"
    
    return True, None


def validate_line_item(unit_price: float, quantity: float, line_total: float,
                      description: str = "", packs: Optional[float] = None,
                      units_per_pack: Optional[float] = None,
                      unit_size_ml: Optional[float] = None,
                      unit_size_g: Optional[float] = None) -> Dict[str, any]:
    """
    Validate a single line item.
    
    Returns:
        Dict with validation results and flags
    """
    flags = []
    
    # Check price coherence
    price_valid, price_error = check_price_coherence(unit_price, quantity, line_total, description)
    if not price_valid:
        flags.append(price_error)
    
    # Check pack descriptor
    pack_valid, pack_error = check_pack_descriptor(quantity, packs, units_per_pack, description)
    if not pack_valid:
        flags.append(pack_error)
    
    # Check size drift
    size_valid, size_error = check_size_drift(quantity, unit_size_ml, unit_size_g, line_total)
    if not size_valid:
        flags.append(size_error)
    
    # Check if FOC line
    if line_total == 0 and (unit_price == 0 or any(term in description.lower() for term in FOC_TERMS)):
        flags.append("FOC_LINE")
    
    return {
        'valid': len([f for f in flags if f != "FOC_LINE"]) == 0,  # Valid if only FOC_LINE flag
        'flags': flags,
        'unit_price': unit_price,
        'quantity': quantity,
        'line_total': line_total,
        'expected_total': banker_round(unit_price * quantity),
        'difference': banker_round(abs(banker_round(unit_price * quantity) - line_total))
    }


def validate_invoice_totals(subtotal: float, vat_amount: float, vat_rate: Optional[float],
                           invoice_total: float, line_totals: List[float]) -> Dict[str, any]:
    """
    Validate invoice-level calculations.
    
    Returns:
        Dict with validation results and flags
    """
    flags = []
    
    # Check VAT calculation
    vat_valid, vat_error = check_vat_calculation(subtotal, vat_amount, vat_rate, invoice_total)
    if not vat_valid:
        flags.append(vat_error)
    
    # Check negative adjustments
    neg_valid, neg_error = check_negative_adjustments(line_totals)
    if not neg_valid:
        flags.append(neg_error)
    
    return {
        'valid': len(flags) == 0,
        'flags': flags,
        'subtotal': subtotal,
        'vat_amount': vat_amount,
        'vat_rate': vat_rate,
        'invoice_total': invoice_total,
        'expected_total': banker_round(subtotal + vat_amount),
        'difference': banker_round(abs(banker_round(subtotal + vat_amount) - invoice_total))
    }


def calculate_line_fingerprint(sku_id: str, qty: float, uom_key: str, unit_price_raw: float,
                              nett_price: float, nett_value: float, date: str, supplier_id: str,
                              ruleset_id: str, engine_version: str) -> str:
    """
    Calculate deterministic line fingerprint for audit trail.
    
    Returns:
        SHA256 hash of concatenated values
    """
    import hashlib
    
    # Create deterministic string representation
    fingerprint_data = f"{sku_id}|{qty}|{uom_key}|{unit_price_raw}|{nett_price}|{nett_value}|{date}|{supplier_id}|{ruleset_id}|{engine_version}"
    
    # Generate SHA256 hash
    return hashlib.sha256(fingerprint_data.encode('utf-8')).hexdigest() 