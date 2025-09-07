import math
from datetime import date
from typing import Dict, List, Any

def today_iso():
    return date.today().isoformat()

def run_checks(inv, items):
    """Generic, vendor-agnostic data integrity checks"""
    issues = []
    
    # Get totals with safe defaults
    subtotal = inv.get("subtotal_p") or sum(i.get("total", 0) for i in items)
    total = inv.get("total_p") or 0
    vat = inv.get("vat_total_p")
    if vat is None and total and subtotal:
        vat = max(0, total - subtotal)

    # Check 1: SUM_MISMATCH - |subtotal + vat − total| > 2 (minor units)
    if subtotal is not None and total is not None and vat is not None:
        expected_total = subtotal + vat
        if abs(expected_total - total) > 2:  # > £0.02
            issues.append({
                "code": "SUM_MISMATCH",
                "sev": "high",
                "msg": f"Subtotal + VAT ≠ Total (off by £{abs(expected_total - total)/100:.2f})"
            })
    elif subtotal is None or total is None:
        issues.append({
            "code": "MISSING_TOTALS",
            "sev": "high",
            "msg": "Missing essential totals"
        })

    # Check 2: LINE_MISMATCH - any line |qty×unit − total| > 2
    for i, item in enumerate(items):
        qty = item.get("qty", 0)
        unit_price = item.get("unit_price", 0)
        line_total = item.get("total", 0)
        
        if qty and unit_price and line_total:
            expected_total = int(round(qty * unit_price))
            if abs(expected_total - line_total) > 2:  # > £0.02
                issues.append({
                    "code": "LINE_MISMATCH",
                    "sev": "med",
                    "msg": f"Line {i+1}: qty×unit ≠ total (off by £{abs(expected_total - line_total)/100:.2f})"
                })

    # Check 3: NEGATIVE_VALUE - negative qty/price/total
    for i, item in enumerate(items):
        if item.get("qty", 0) < 0:
            issues.append({
                "code": "NEGATIVE_VALUE",
                "sev": "high",
                "msg": f"Line {i+1}: negative quantity ({item.get('qty')})"
            })
        if item.get("unit_price", 0) < 0:
            issues.append({
                "code": "NEGATIVE_VALUE", 
                "sev": "high",
                "msg": f"Line {i+1}: negative unit price (£{item.get('unit_price', 0)/100:.2f})"
            })
        if item.get("total", 0) < 0:
            issues.append({
                "code": "NEGATIVE_VALUE",
                "sev": "high", 
                "msg": f"Line {i+1}: negative line total (£{item.get('total', 0)/100:.2f})"
            })

    # Check 4: LOW_CONFIDENCE - invoice median confidence < threshold
    confidence_threshold = 60
    if inv.get("confidence", 0) < confidence_threshold:
        issues.append({
            "code": "LOW_CONFIDENCE",
            "sev": "med",
            "msg": f"Low OCR confidence ({inv.get('confidence', 0)}% < {confidence_threshold}%)"
        })

    # Check 5: FUTURE_DATE - invoice date > today
    inv_date = inv.get("invoice_date")
    if inv_date and inv_date > today_iso():
        issues.append({
            "code": "FUTURE_DATE",
            "sev": "med",
            "msg": "Invoice date is in the future"
        })

    # Check 6: VAT_INCONSISTENT - most items one rate, but invoice ratio suggests another
    if items and subtotal and vat is not None and subtotal > 0:
        # Calculate invoice-level VAT rate
        invoice_vat_rate = round((vat / subtotal) * 100)
        
        # Get item VAT rates
        item_rates = [item.get("vat_rate") for item in items if item.get("vat_rate") is not None]
        
        if item_rates:
            # Find most common rate
            from collections import Counter
            rate_counts = Counter(item_rates)
            most_common_rate = rate_counts.most_common(1)[0][0]
            
            # Check if invoice rate differs significantly from most common item rate
            if abs(invoice_vat_rate - most_common_rate) > 3:  # > 3% difference
                issues.append({
                    "code": "VAT_INCONSISTENT",
                    "sev": "med", 
                    "msg": f"Invoice VAT rate ({invoice_vat_rate}%) differs from items ({most_common_rate}%)"
                })

    # Check 7: NO_ITEMS - no line items or all zero totals
    if not items or sum(i.get("total", 0) for i in items) == 0:
        issues.append({
            "code": "NO_ITEMS",
            "sev": "high",
            "msg": "No line items detected"
        })

    # Check 8: MISSING_SUPPLIER - no supplier name
    if not inv.get("supplier_name") or inv["supplier_name"].strip() == "":
        issues.append({
            "code": "NO_SUPPLIER",
            "sev": "med",
            "msg": "No supplier name detected"
        })

    # Check 9: UNUSUAL_TOTALS - very large or very small amounts
    if total and total > 100000000:  # > £1M
        issues.append({
            "code": "UNUSUAL_TOTALS",
            "sev": "med",
            "msg": f"Unusually large total (£{total/100:,.2f})"
        })
    elif total and total < 1:  # < £0.01
        issues.append({
            "code": "UNUSUAL_TOTALS",
            "sev": "med", 
            "msg": f"Unusually small total (£{total/100:.2f})"
        })

    return issues 