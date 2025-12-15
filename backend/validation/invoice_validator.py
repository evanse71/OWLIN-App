"""
Invoice Numeric Consistency Validator

Validates extracted invoice data for internal consistency without requiring LLM.
Catches common OCR errors like misread decimals (£1.50 vs £1,504.32).
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("owlin.validation")


@dataclass
class ValidationResult:
    """Result of invoice validation"""
    is_consistent: bool
    integrity_score: float  # 0.0 - 1.0
    issues: List[str]
    corrections: Dict[str, Any]
    details: Dict[str, Any]


def validate_invoice_consistency(
    line_items: List[Dict[str, Any]],
    subtotal: Optional[float],
    vat_amount: Optional[float],
    vat_rate: Optional[float],
    total: Optional[float],
    ocr_confidence: float = 0.9,
    raw_ocr_text: Optional[str] = None,
    tolerance: float = 0.05  # £0.05 tolerance for rounding
) -> ValidationResult:
    """
    Validate invoice numeric consistency.
    
    Args:
        line_items: List of line items with qty, unit_price, total fields
        subtotal: Extracted subtotal from header
        vat_amount: Extracted VAT amount from header
        vat_rate: Extracted VAT rate (e.g., 0.20 for 20%)
        total: Extracted grand total from header
        ocr_confidence: OCR confidence score
        tolerance: Tolerance for rounding differences (default £0.05)
    
    Returns:
        ValidationResult with consistency check and corrections
    """
    issues = []
    corrections = {}
    details = {}
    
    # Step 1: Compute items subtotal
    items_subtotal = 0.0
    items_with_totals = 0
    items_missing_data = []
    
    for i, item in enumerate(line_items):
        # Try to get line total
        line_total = None
        if 'total' in item and item['total']:
            try:
                line_total = float(item['total'])
            except (ValueError, TypeError):
                pass
        elif 'line_total' in item and item['line_total']:
            try:
                line_total = float(item['line_total'])
            except (ValueError, TypeError):
                pass
        elif 'total_price' in item and item['total_price']:
            try:
                line_total = float(item['total_price'])
            except (ValueError, TypeError):
                pass
        
        # If no line total, try to derive from qty * unit_price
        if line_total is None:
            qty = None
            unit_price = None
            
            if 'qty' in item and item['qty']:
                try:
                    qty = float(item['qty'])
                except (ValueError, TypeError):
                    pass
            elif 'quantity' in item and item['quantity']:
                try:
                    qty = float(item['quantity'])
                except (ValueError, TypeError):
                    pass
            
            if 'unit_price' in item and item['unit_price']:
                try:
                    unit_price = float(item['unit_price'])
                except (ValueError, TypeError):
                    pass
            elif 'price' in item and item['price']:
                try:
                    unit_price = float(item['price'])
                except (ValueError, TypeError):
                    pass
            
            if qty is not None and unit_price is not None and qty > 0:
                line_total = round(qty * unit_price, 2)
                logger.info(f"[VALIDATE] Derived line total for item {i}: {qty} × £{unit_price} = £{line_total}")
        
        if line_total is not None:
            items_subtotal += line_total
            items_with_totals += 1
        else:
            items_missing_data.append(i)
            logger.warning(f"[VALIDATE] Item {i} missing qty/price/total: {item.get('description', 'Unknown')[:50]}")
    
    items_subtotal = round(items_subtotal, 2)
    details['items_subtotal'] = items_subtotal
    details['items_with_totals'] = items_with_totals
    details['items_missing_data'] = items_missing_data
    
    logger.info(f"[VALIDATE] Computed items subtotal: £{items_subtotal} from {items_with_totals}/{len(line_items)} items")
    
    # Step 2: Compare with extracted subtotal
    if subtotal is not None:
        diff_subtotal = abs(subtotal - items_subtotal)
        details['diff_subtotal'] = diff_subtotal
        
        if diff_subtotal > tolerance:
            issues.append(f"Subtotal mismatch: header £{subtotal:.2f} vs items £{items_subtotal:.2f} (diff: £{diff_subtotal:.2f})")
            logger.warning(f"[VALIDATE] Subtotal mismatch: header={subtotal}, items={items_subtotal}, diff={diff_subtotal}")
            
            # Suggest correction: if items subtotal is more reasonable, use it
            if items_with_totals >= len(line_items) * 0.8:  # At least 80% of items have data
                corrections['subtotal'] = items_subtotal
        else:
            logger.info(f"[VALIDATE] Subtotal consistent: £{subtotal:.2f} (diff: £{diff_subtotal:.2f})")
    
    # Step 3: Validate VAT
    vat_expected = None
    if vat_rate is not None and items_subtotal > 0:
        vat_expected = round(items_subtotal * vat_rate, 2)
        details['vat_expected'] = vat_expected
        
        if vat_amount is not None:
            diff_vat = abs(vat_amount - vat_expected)
            details['diff_vat'] = diff_vat
            
            if diff_vat > tolerance:
                issues.append(f"VAT mismatch: header £{vat_amount:.2f} vs expected £{vat_expected:.2f} (diff: £{diff_vat:.2f})")
                logger.warning(f"[VALIDATE] VAT mismatch: header={vat_amount}, expected={vat_expected}, diff={diff_vat}")
                corrections['vat_amount'] = vat_expected
            else:
                logger.info(f"[VALIDATE] VAT consistent: £{vat_amount:.2f} (diff: £{diff_vat:.2f})")
    
    # Step 4: Infer VAT rate if not provided
    if vat_rate is None and subtotal is not None and vat_amount is not None and subtotal > 0:
        inferred_vat_rate = vat_amount / subtotal
        details['inferred_vat_rate'] = inferred_vat_rate
        
        # Check if it's close to common VAT rates
        common_rates = {0.0: "0%", 0.05: "5%", 0.20: "20%", 0.175: "17.5%"}
        for rate, label in common_rates.items():
            if abs(inferred_vat_rate - rate) < 0.01:
                logger.info(f"[VALIDATE] Inferred VAT rate: {label} (calculated: {inferred_vat_rate:.4f})")
                corrections['vat_rate'] = rate
                break
    
    # Step 5: Validate total (ENHANCED for Red Dragon case)
    if total is not None:
        # Compute expected total
        base = subtotal if subtotal is not None else items_subtotal
        vat = vat_amount if vat_amount is not None else (vat_expected if vat_expected is not None else 0)
        total_expected = round(base + vat, 2)
        details['total_expected'] = total_expected
        
        diff_total = abs(total - total_expected)
        details['diff_total'] = diff_total
        
        if diff_total > tolerance:
            issues.append(f"Total mismatch: header £{total:.2f} vs expected £{total_expected:.2f} (diff: £{diff_total:.2f})")
            logger.warning(f"[VALIDATE] Total mismatch: header={total}, expected={total_expected}, diff={diff_total}")
            
            # ENHANCED: Check for common OCR errors
            # Case 1: £1.50 vs £1,504.32 (missed thousands separator or decimal point)
            if total < 10 and total_expected > 1000:
                # Likely missed thousands separator
                issues.append(f"CRITICAL OCR ERROR: total £{total:.2f} seems too low (expected ~£{total_expected:.2f})")
                
                # Try to find the correct value in raw text
                corrected_from_text = None
                if raw_ocr_text:
                    corrected_from_text = _scan_text_for_total(raw_ocr_text, total_expected)
                
                if corrected_from_text:
                    corrections['total'] = corrected_from_text
                    corrections['total_source'] = 'raw_text_scan'
                    logger.error(f"[VALIDATE] Critical: Total corrected from raw text (£{total} → £{corrected_from_text})")
                else:
                    corrections['total'] = total_expected
                    corrections['total_source'] = 'computed_from_items'
                    logger.error(f"[VALIDATE] Critical: Total corrected from items (£{total} → £{total_expected})")
                    
            elif total > total_expected * 100:
                # Likely decimal point in wrong place (£150,432 vs £1,504.32)
                issues.append(f"CRITICAL OCR ERROR: total £{total:.2f} seems too high (expected ~£{total_expected:.2f})")
                corrections['total'] = total_expected
                corrections['total_source'] = 'computed_from_items'
                logger.error(f"[VALIDATE] Critical: Total likely misread (£{total} vs £{total_expected})")
            elif diff_total > 1.0:
                # Significant difference (> £1)
                issues.append(f"Significant total difference: £{diff_total:.2f}")
                corrections['total'] = total_expected
                corrections['total_source'] = 'computed_from_items'
                logger.warning(f"[VALIDATE] Significant total mismatch: {diff_total}")
            else:
                # Small difference, likely rounding
                corrections['total'] = total_expected
                corrections['total_source'] = 'rounding_adjustment'
        else:
            logger.info(f"[VALIDATE] Total consistent: £{total:.2f} (diff: £{diff_total:.2f})")
    
    # Step 6: Calculate integrity score (ENHANCED with strict bonuses/penalties)
    integrity_score = 0.5  # Start neutral, build up from evidence
    
    # Add OCR confidence as base (weighted)
    integrity_score += (ocr_confidence * 0.3)  # Max +0.3 from OCR
    
    # BONUSES for consistency (max +0.6 total)
    if subtotal is not None and abs((subtotal if subtotal else 0) - items_subtotal) < 0.01:
        integrity_score += 0.2
        logger.debug(f"[VALIDATE] +0.2 bonus: subtotal matches (£{subtotal:.2f})")
    
    if vat_amount is not None and vat_expected is not None and abs(vat_amount - vat_expected) < 0.01:
        integrity_score += 0.2
        logger.debug(f"[VALIDATE] +0.2 bonus: VAT matches (£{vat_amount:.2f})")
    
    if total is not None:
        base = subtotal if subtotal is not None else items_subtotal
        vat = vat_amount if vat_amount is not None else (vat_expected if vat_expected is not None else 0)
        total_expected = round(base + vat, 2)
        if abs(total - total_expected) < 0.01:
            integrity_score += 0.2
            logger.debug(f"[VALIDATE] +0.2 bonus: total matches (£{total:.2f})")
    
    # BONUS for data completeness
    if items_with_totals >= len(line_items) * 0.8:
        integrity_score += 0.1
        logger.debug(f"[VALIDATE] +0.1 bonus: {items_with_totals}/{len(line_items)} items have data")
    
    # PENALTIES for issues
    critical_issues = sum(1 for issue in issues if 'CRITICAL' in issue)
    if critical_issues > 0:
        penalty = critical_issues * 0.3
        integrity_score -= penalty
        logger.warning(f"[VALIDATE] -{penalty} penalty: {critical_issues} critical issue(s)")
    
    regular_issues = len(issues) - critical_issues
    if regular_issues > 0:
        penalty = regular_issues * 0.1
        integrity_score -= penalty
        logger.debug(f"[VALIDATE] -{penalty} penalty: {regular_issues} issue(s)")
    
    # Clamp to [0.0, 1.0]
    integrity_score = max(0.0, min(1.0, integrity_score))
    details['integrity_score'] = integrity_score
    details['score_breakdown'] = {
        'ocr_confidence_contribution': ocr_confidence * 0.3,
        'critical_issues': critical_issues,
        'regular_issues': regular_issues,
        'items_complete': f"{items_with_totals}/{len(line_items)}"
    }
    
    # Determine if consistent
    is_consistent = len(issues) == 0 or all('mismatch' not in issue.lower() for issue in issues)
    
    logger.info(f"[VALIDATE] Validation complete: consistent={is_consistent}, score={integrity_score:.3f}, issues={len(issues)}")
    
    return ValidationResult(
        is_consistent=is_consistent,
        integrity_score=integrity_score,
        issues=issues,
        corrections=corrections,
        details=details
    )


def should_request_llm_verification(validation: ValidationResult, threshold: float = 0.75) -> bool:
    """
    Determine if LLM verification is needed based on validation results.
    
    Args:
        validation: ValidationResult from validate_invoice_consistency
        threshold: Integrity score threshold (default 0.75)
    
    Returns:
        True if LLM verification recommended, False otherwise
    """
    # Request LLM if:
    # 1. Integrity score is below threshold
    # 2. There are critical issues (total misread)
    # 3. Many items are missing data
    
    if validation.integrity_score < threshold:
        logger.info(f"[LLM_CHECK] Recommending LLM verification: low integrity score ({validation.integrity_score:.3f})")
        return True
    
    # Check for critical issues
    critical_keywords = ['critical', 'misread', 'too low', 'too high']
    for issue in validation.issues:
        if any(keyword in issue.lower() for keyword in critical_keywords):
            logger.info(f"[LLM_CHECK] Recommending LLM verification: critical issue found")
            return True
    
    # Check if too many items are missing data
    items_missing = len(validation.details.get('items_missing_data', []))
    items_total = validation.details.get('items_with_totals', 0) + items_missing
    if items_total > 0 and items_missing / items_total > 0.3:  # More than 30% missing
        logger.info(f"[LLM_CHECK] Recommending LLM verification: {items_missing}/{items_total} items missing data")
        return True
    
    logger.info(f"[LLM_CHECK] No LLM verification needed: integrity score {validation.integrity_score:.3f}, no critical issues")
    return False


def _scan_text_for_total(raw_text: str, expected_total: float) -> Optional[float]:
    """
    Scan raw OCR text for a total value near the expected amount.
    Helps correct misread totals like £1.50 vs £1,504.32
    """
    import re
    
    # Look for patterns near "Total", "TOTAL", "Grand Total", "Balance Due"
    total_patterns = [
        r'total[\s:]*£?([0-9,]+\.?\d{0,2})',
        r'grand[\s]+total[\s:]*£?([0-9,]+\.?\d{0,2})',
        r'balance[\s]+due[\s:]*£?([0-9,]+\.?\d{0,2})',
        r'amount[\s]+due[\s:]*£?([0-9,]+\.?\d{0,2})',
    ]
    
    candidates = []
    for pattern in total_patterns:
        matches = re.finditer(pattern, raw_text, re.IGNORECASE)
        for match in matches:
            value_str = match.group(1).replace(',', '')
            try:
                value = float(value_str)
                # Check if this value is close to expected
                if abs(value - expected_total) < 1.0:  # Within £1
                    candidates.append(value)
                    logger.info(f"[TEXT_SCAN] Found candidate total: £{value} (expected: £{expected_total})")
            except ValueError:
                continue
    
    if candidates:
        # Return the closest match
        closest = min(candidates, key=lambda x: abs(x - expected_total))
        logger.info(f"[TEXT_SCAN] Selected total from raw text: £{closest}")
        return closest
    
    logger.warning(f"[TEXT_SCAN] No matching total found in raw text (expected: £{expected_total})")
    return None


def format_validation_badge(validation: ValidationResult) -> Dict[str, str]:
    """
    Format validation result as UI badge data.
    
    Returns:
        Dict with 'status', 'label', and 'color' for UI display
    """
    # Check for critical issues
    has_critical = any('CRITICAL' in issue for issue in validation.issues)
    
    if has_critical:
        return {
            'status': 'critical',
            'label': 'Needs Review',
            'color': 'yellow',
            'tooltip': 'Critical OCR error detected. Review and correct before submitting.'
        }
    elif validation.is_consistent and validation.integrity_score >= 0.9:
        return {
            'status': 'verified',
            'label': 'Math-verified',
            'color': 'green',
            'tooltip': f'Totals are internally consistent (score: {validation.integrity_score:.2f})'
        }
    elif validation.is_consistent and validation.integrity_score >= 0.7:
        return {
            'status': 'good',
            'label': 'Verified',
            'color': 'blue',
            'tooltip': f'Totals match within tolerance (score: {validation.integrity_score:.2f})'
        }
    elif validation.integrity_score >= 0.4:
        return {
            'status': 'needs_review',
            'label': 'Needs Review',
            'color': 'yellow',
            'tooltip': f'{len(validation.issues)} issue(s) found. Review recommended.'
        }
    else:
        return {
            'status': 'unverified',
            'label': 'Unverified',
            'color': 'gray',
            'tooltip': 'Insufficient data for validation'
        }

