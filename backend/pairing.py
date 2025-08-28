#!/usr/bin/env python3
"""
Delivery note pairing suggestions
Suggests matches between invoices and delivery notes based on similarity scoring
"""

from difflib import SequenceMatcher
from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger(__name__)

def _norm(s: str) -> str:
    """Normalize string for comparison"""
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

def _similar(a: str, b: str) -> float:
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()

def suggest_dn_matches(invoice: dict, delivery_notes: list, date_window_days=7, amount_window=0.05):
    """
    Suggest delivery note matches for an invoice
    
    Args:
        invoice: {"supplier": str, "invoice_date": str|date, "totals": {"subtotal": float}}
        delivery_notes: [{"id":..., "supplier":..., "date":..., "amount":...}, ...]
        date_window_days: tolerance for date matching (default 7 days)
        amount_window: tolerance for amount matching (default 5%)
        
    Returns:
        List of (score, delivery_note) tuples, sorted by score descending
    """
    inv_sup = invoice.get("supplier")
    inv_date_raw = invoice.get("invoice_date")
    inv_amt = (invoice.get("totals") or {}).get("subtotal")
    
    try:
        inv_date = datetime.fromisoformat(str(inv_date_raw))
    except Exception:
        inv_date = None

    out = []
    for dn in delivery_notes:
        sup_score = _similar(inv_sup, dn.get("supplier"))
        date_score = 0.0
        if inv_date and dn.get("date"):
            try:
                dn_date = datetime.fromisoformat(str(dn["date"]))
                if abs((dn_date - inv_date).days) <= date_window_days:
                    date_score = 1.0
            except Exception:
                pass
        amt_score = 0.0
        if inv_amt and dn.get("amount") is not None:
            try:
                dn_amt = float(dn["amount"])
                if inv_amt == 0:
                    amt_score = 0.0
                else:
                    if abs(dn_amt - inv_amt) / max(1.0, inv_amt) <= amount_window:
                        amt_score = 1.0
            except Exception:
                pass
        # weighted score: supplier 0.6, date 0.2, amount 0.2
        score = 0.6*sup_score + 0.2*date_score + 0.2*amt_score
        out.append((score, dn))
    out.sort(key=lambda x: x[0], reverse=True)
    return out[:3] 