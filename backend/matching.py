from typing import List, Dict, Any
from difflib import SequenceMatcher
from datetime import datetime

def fuzzy_match_supplier(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def value_proximity(val1: float, val2: float) -> float:
    if not val1 or not val2:
        return 0.0
    diff = abs(val1 - val2)
    avg = (val1 + val2) / 2
    if avg == 0:
        return 0.0
    return max(0.0, 1.0 - diff / avg)

def date_distance_score(date1: str, date2: str, max_days: int = 7) -> float:
    # Accepts ISO or common date formats
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y"):
        try:
            d1 = datetime.strptime(date1, fmt)
            d2 = datetime.strptime(date2, fmt)
            days = abs((d1 - d2).days)
            return max(0.0, 1.0 - days / max_days)
        except Exception:
            continue
    return 0.0

def compare_line_items(invoice_lines: List[Dict], delivery_lines: List[Dict]) -> float:
    # Simple overlap ratio based on description
    if not invoice_lines or not delivery_lines:
        return 0.0
    invoice_descs = set(i.get('description', '').lower().strip() for i in invoice_lines)
    delivery_descs = set(d.get('description', '').lower().strip() for d in delivery_lines)
    if not invoice_descs or not delivery_descs:
        return 0.0
    overlap = invoice_descs & delivery_descs
    union = invoice_descs | delivery_descs
    return len(overlap) / len(union) if union else 0.0

def score_match(invoice_data: Dict[str, Any], delivery_data: Dict[str, Any], threshold: float = 0.75) -> Dict[str, Any]:
    supplier_score = fuzzy_match_supplier(
        invoice_data.get('supplier_name', ''),
        delivery_data.get('supplier_name', '')
    )
    # Try to extract line items if present
    invoice_lines = invoice_data.get('line_items', [])
    delivery_lines = delivery_data.get('items', [])
    line_item_score = compare_line_items(invoice_lines, delivery_lines)
    # Try to extract values
    try:
        val1 = float(invoice_data.get('total_amount', 0))
        val2 = float(delivery_data.get('total_amount', 0))
    except Exception:
        val1 = val2 = 0.0
    value_score = value_proximity(val1, val2)
    # Dates
    date_score = date_distance_score(
        invoice_data.get('invoice_date', ''),
        delivery_data.get('delivery_date', '')
    )
    # Weighted sum (tune as needed)
    match_score = 0.4 * supplier_score + 0.2 * line_item_score + 0.2 * value_score + 0.2 * date_score
    return {
        "match_score": round(match_score, 2),
        "matched": match_score >= threshold,
        "breakdown": {
            "supplier_match": round(supplier_score, 2),
            "line_item_similarity": round(line_item_score, 2),
            "value_similarity": round(value_score, 2),
            "date_proximity": round(date_score, 2)
        }
    } 