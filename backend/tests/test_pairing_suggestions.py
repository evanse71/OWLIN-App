#!/usr/bin/env python3
"""
Test delivery note pairing suggestions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# If the function is not exported yet, temporary shim:
def suggest_dn_matches(*_, **__):  # pragma: no cover
    return []

def test_pairing_suggestions_scoring():
    """Test that pairing suggestions score correctly"""
    invoice = {"supplier":"Wildhorse RSE Ltd", "invoice_date":"2024-01-17", "totals":{"subtotal":123.45}}
    dns = [
        {"id":1,"supplier":"R.S.E. Limited","date":"2024-01-16","amount":124.00},
        {"id":2,"supplier":"Fresh Foods Ltd","date":"2024-01-17","amount":123.45},
        {"id":3,"supplier":"Wild Horse","date":"2024-01-26","amount":123.00},
    ]
    out = suggest_dn_matches(invoice, dns)
    assert len(out) == 3
    # Similar supplier names should float to top
    top_suppliers = [dn["supplier"] for score, dn in out[:2]]
    assert any("R.S.E" in s or "Wild" in s for s in top_suppliers)
    print("✅ Pairing suggestions scoring test passed")

def test_pairing_date_window():
    """Test that date window filtering works"""
    invoice = {"supplier":"Test Ltd", "invoice_date":"2024-01-15", "totals":{"subtotal":100.0}}
    dns = [
        {"id":1,"supplier":"Test Ltd","date":"2024-01-10","amount":100.0},  # within 7 days
        {"id":2,"supplier":"Test Ltd","date":"2024-01-25","amount":100.0},  # outside 7 days
    ]
    out = suggest_dn_matches(invoice, dns, date_window_days=7)
    # Should prefer the one within date window
    assert out[0][1]["id"] == 1
    print("✅ Date window test passed")

def test_pairing_amount_tolerance():
    """Test that amount tolerance works"""
    invoice = {"supplier":"Test Ltd", "invoice_date":"2024-01-15", "totals":{"subtotal":100.0}}
    dns = [
        {"id":1,"supplier":"Test Ltd","date":"2024-01-15","amount":102.0},  # within 5%
        {"id":2,"supplier":"Test Ltd","date":"2024-01-15","amount":110.0},  # outside 5%
    ]
    out = suggest_dn_matches(invoice, dns, amount_window=0.05)
    # Should prefer the one within amount tolerance
    assert out[0][1]["id"] == 1
    print("✅ Amount tolerance test passed")

if __name__ == "__main__":
    test_pairing_suggestions_scoring()
    test_pairing_date_window()
    test_pairing_amount_tolerance()
    print("All pairing tests passed!") 