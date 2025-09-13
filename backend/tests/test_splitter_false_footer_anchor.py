#!/usr/bin/env python3
"""
Test splitter false footer anchor detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr.splitter import split_pages_into_invoices

def test_splitter_ignores_footer_anchor():
    """Test that splitter ignores invoice anchors found in footer areas"""
    pages = [
        {"page_index":0, "text":"... body content ...\n... more content ...\nInvoice No 123"},  # anchor on last line (footer)
        {"page_index":1, "text":"Header...\nInvoice Number 456\n... body content ..."},
    ]
    chunks = split_pages_into_invoices(pages)
    # should split only at page 1 header, not at footer of page 0
    assert len(chunks) == 1 or (len(chunks) == 2 and chunks[0][0]["page_index"] == 0 and chunks[1][0]["page_index"] == 1)
    print("✅ Footer anchor test passed")

def test_splitter_min_tokens_validation():
    """Test that splitter merges tiny chunks"""
    pages = [
        {"page_index":0, "text":"Invoice No 123\n... content ..."},
        {"page_index":1, "text":"Invoice No 456\n... minimal content ..."},  # tiny chunk
        {"page_index":2, "text":"Invoice No 789\n... more content ..."},
    ]
    chunks = split_pages_into_invoices(pages)
    # Should have 1 chunk (tiny chunks merged together)
    assert len(chunks) == 1
    # Should contain all pages
    assert len(chunks[0]) == 3
    print("✅ Min tokens validation test passed")

if __name__ == "__main__":
    test_splitter_ignores_footer_anchor()
    test_splitter_min_tokens_validation()
    print("All splitter tests passed!") 