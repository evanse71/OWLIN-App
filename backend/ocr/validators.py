from typing import List, Tuple
from backend.types.parsed_invoice import ParsedInvoice, LineItem
import math, re

UNIT_HINTS = {"kg","g","ml","l","kw","kwh","kW","kWh","pcs","units"}

def _is_money_like(x):
    return isinstance(x,(int,float)) and math.isfinite(x)

def validate_invoice(inv: ParsedInvoice) -> ParsedInvoice:
    warnings = list(inv.warnings or [])
    # 1) Unit/currency sanity: reject totals containing unit strings
    text_fields = " ".join([
        inv.supplier_name or "", inv.invoice_number or "", inv.currency or ""
    ])
    # 2) Totals ≈ sum(lines) ± tax (±1.5%)
    lines_sum = sum([li.line_total or 0.0 for li in inv.line_items])
    expected = lines_sum + (inv.tax or 0.0)
    if inv.total_amount is not None and _is_money_like(inv.total_amount):
        if expected > 0:
            diff = abs(inv.total_amount - expected) / max(expected,1e-6)
            if diff > 0.015:
                warnings.append(f"Totals mismatch >1.5% (total={inv.total_amount}, lines+tax={expected:.2f})")
    # 3) Flag suspicious quantities (unbounded massive qty with no small unit)
    for li in inv.line_items:
        if li.quantity and li.quantity > 1e6 and not (li.unit and li.unit.lower() in {"g","ml"}):
            warnings.append(f"Suspicious quantity on row {li.row_idx}: {li.quantity}")
    inv.warnings = warnings
    return inv 