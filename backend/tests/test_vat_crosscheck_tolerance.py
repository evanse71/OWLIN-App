#!/usr/bin/env python3
"""
Test VAT cross-check tolerance validation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import enrich_totals_and_flags

def test_vat_crosscheck_within_tolerance():
    """Test that VAT cross-check passes when within 3% tolerance"""
    inv = {
        "items": [{"qty":2,"unit_price":3.0}],  # sum_lines = 6.0
        "totals": {"subtotal": 6.05}
    }
    out = enrich_totals_and_flags(inv)
    assert "TOTAL_MISMATCH" not in (out.get("validation_flags") or [])
    assert out["c_totals"] >= 80
    print("✅ Within tolerance test passed")

def test_vat_crosscheck_outside_tolerance():
    """Test that VAT cross-check fails when outside 3% tolerance"""
    inv = {
        "items": [{"qty":2,"unit_price":3.0}],  # sum_lines = 6.0
        "totals": {"subtotal": 7.0}  # 16.7% difference
    }
    out = enrich_totals_and_flags(inv)
    assert "TOTAL_MISMATCH" in (out.get("validation_flags") or [])
    print("✅ Outside tolerance test passed")

def test_vat_crosscheck_fallback():
    """Test that fallback works when totals are missing"""
    inv = {
        "items": [{"qty":2,"unit_price":3.0}],  # sum_lines = 6.0
        "totals": {}
    }
    out = enrich_totals_and_flags(inv)
    assert "SUBTOTAL_FALLBACK" in (out.get("validation_flags") or [])
    assert out["totals"]["subtotal"] == 6.0
    print("✅ Fallback test passed")

if __name__ == "__main__":
    test_vat_crosscheck_within_tolerance()
    test_vat_crosscheck_outside_tolerance()
    test_vat_crosscheck_fallback()
    print("All VAT cross-check tests passed!") 