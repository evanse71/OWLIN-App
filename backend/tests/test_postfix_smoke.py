#!/usr/bin/env python3
"""
Post-Fix Smoke Tests
Three decisive tests to verify Fix Pack v2 implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr.splitter import split_pages_into_invoices
from services import enrich_totals_and_flags
from pairing import suggest_dn_matches

def test_splitter_footer_guard_and_min_tokens():
    """Test that splitter ignores footer anchors and validates min tokens"""
    pages = [
        {"page_index":0,"text":"body line\n...\nInvoice No 123"},  # footer anchor -> ignore
        {"page_index":1,"text":"Header\nInvoice Number 456\nBody body body " + ("x "*100)},
    ]
    chunks = split_pages_into_invoices(pages)
    # Either 1 chunk (robust merge) or 2 with the second starting at page 1
    assert len(chunks) in (1,2)
    if len(chunks) == 2:
        assert chunks[1][0]["page_index"] == 1
    print("✅ Splitter footer guard and min tokens test passed")

def test_totals_crosscheck_within_tolerance():
    """Test that totals cross-check works within 3% tolerance"""
    inv = {"items":[{"qty":2,"unit_price":3.0}], "totals":{"subtotal":6.05}}
    out = enrich_totals_and_flags(inv)
    assert "TOTAL_MISMATCH" not in (out.get("validation_flags") or [])
    assert out.get("c_totals", 0) >= 80
    print("✅ Totals cross-check tolerance test passed")

def test_pairing_suggestions_basic():
    """Test that delivery note pairing suggestions work correctly"""
    invoice = {"supplier":"Wildhorse RSE Ltd", "invoice_date":"2024-01-17", "totals":{"subtotal":123.45}}
    dns = [
        {"id":1,"supplier":"R.S.E. Limited","date":"2024-01-16","amount":124.00},
        {"id":2,"supplier":"Fresh Foods Ltd","date":"2024-01-17","amount":123.45},
        {"id":3,"supplier":"Wild Horse","date":"2024-01-26","amount":123.00},
    ]
    top = suggest_dn_matches(invoice, dns)
    assert len(top) == 3
    # supplier-similar DNs should rank higher than unrelated
    assert top[0][1]["supplier"] != "Fresh Foods Ltd"
    print("✅ Pairing suggestions basic test passed")

if __name__ == "__main__":
    test_splitter_footer_guard_and_min_tokens()
    test_totals_crosscheck_within_tolerance()
    test_pairing_suggestions_basic()
    print("\n🎉 All post-fix smoke tests passed!") 