from typing import List, Dict
from difflib import SequenceMatcher
from datetime import datetime
from supplier_aliases import normalize_supplier_name
from matching_config import MATCH_WEIGHTS

def fuzzy_supplier_name_match(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    a_norm = normalize_supplier_name(a)
    b_norm = normalize_supplier_name(b)
    return SequenceMatcher(None, a_norm.lower().strip(), b_norm.lower().strip()).ratio()

def compare_line_items(invoice_lines: List[Dict], delivery_lines: List[Dict]) -> float:
    if not invoice_lines or not delivery_lines:
        return 0.0
    invoice_descs = set(i.get('description', '').lower().strip() for i in invoice_lines if i.get('description'))
    delivery_descs = set(d.get('description', '').lower().strip() for d in delivery_lines if d.get('description'))
    if not invoice_descs or not delivery_descs:
        return 0.0
    overlap = invoice_descs & delivery_descs
    union = invoice_descs | delivery_descs
    return len(overlap) / len(union) if union else 0.0

def match_total_value(a: float, b: float) -> float:
    if not a or not b:
        return 0.0
    diff = abs(a - b)
    avg = (a + b) / 2
    if avg == 0:
        return 0.0
    return max(0.0, 1.0 - diff / avg)

def compare_dates(invoice_date: str, delivery_date: str, max_days: int = 7) -> float:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y"):
        try:
            d1 = datetime.strptime(invoice_date, fmt)
            d2 = datetime.strptime(delivery_date, fmt)
            days = abs((d1 - d2).days)
            return max(0.0, 1.0 - days / max_days)
        except Exception:
            continue
    return 0.0

def score_invoice_delivery_match(invoice_data: dict, delivery_data: dict) -> dict:
    """
    Compares two documents and returns match_score (0-1), breakdown of:
    - supplier_match
    - item_overlap
    - total_value_similarity
    - date_proximity
    """
    supplier_score = fuzzy_supplier_name_match(
        invoice_data.get('supplier_name', ''),
        delivery_data.get('supplier_name', '')
    )
    invoice_lines = invoice_data.get('line_items', [])
    delivery_lines = delivery_data.get('items', [])
    item_overlap = compare_line_items(invoice_lines, delivery_lines)
    try:
        val1 = float(invoice_data.get('total_amount', 0))
        val2 = float(delivery_data.get('total_amount', 0))
    except Exception:
        val1 = val2 = 0.0
    value_score = match_total_value(val1, val2)
    date_score = compare_dates(
        invoice_data.get('invoice_date', ''),
        delivery_data.get('delivery_date', '')
    )
    # Weighted sum using config
    match_score = (
        MATCH_WEIGHTS["supplier"] * supplier_score +
        MATCH_WEIGHTS["items"] * item_overlap +
        MATCH_WEIGHTS["value"] * value_score +
        MATCH_WEIGHTS["date"] * date_score
    )
    return {
        "match_score": round(match_score, 2),
        "breakdown": {
            "supplier_match": round(supplier_score, 2),
            "item_overlap": round(item_overlap, 2),
            "total_value_similarity": round(value_score, 2),
            "date_proximity": round(date_score, 2)
        }
    } 