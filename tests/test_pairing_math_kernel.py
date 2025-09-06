import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from schemas.pairing import CandidateLine
from services.pairing_math import score_line

def cl(desc: str, qty: float, price: int, l: float = 0.0) -> CandidateLine:
    return CandidateLine(None, desc, qty, price, l)

def test_exact_match_scores_1():
    s = score_line(cl("TIA MARIA 1L", 6, 1200, 6.0), cl("TIA MARIA 1L", 6, 1200, 6.0))
    assert 0.99 <= s.total <= 1.0

def test_price_or_qty_drift_penalizes():
    s = score_line(cl("TIA MARIA 1L", 6, 1200, 6.0), cl("TIA MARIA 1L", 6, 1400, 6.0))
    assert s.price_score < 1.0 and s.total < 1.0 