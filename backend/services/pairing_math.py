from __future__ import annotations
from backend.schemas.pairing import CandidateLine, LineScore

def _ratio(a: float, b: float) -> float:
    if a <= 0 or b <= 0:
        return 0.0
    hi, lo = (a, b) if a >= b else (b, a)
    return lo / hi  # 1.0 perfect; shrinks as they diverge

def _softmatch(a: str, b: str) -> float:
    a, b = a.strip().lower(), b.strip().lower()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.8
    sa, sb = set(a.split()), set(b.split())
    union = len(sa | sb) or 1
    return len(sa & sb) / union

def score_line(inv: CandidateLine, dn: CandidateLine) -> LineScore:
    desc  = _softmatch(inv.description, dn.description)
    qty   = _ratio(inv.quantity_each, dn.quantity_each)
    price = _ratio(inv.unit_price_pennies, dn.unit_price_pennies)
    uom   = 1.0 if abs(inv.quantity_l - dn.quantity_l) < 1e-6 else 0.5
    total = 0.45*desc + 0.25*qty + 0.25*price + 0.05*uom
    return LineScore(desc, qty, price, uom, total) 