#!/usr/bin/env python3
"""
Debug pattern detection
"""

import re

def test_pattern_detection():
    """Test what patterns are being detected"""
    print("🔍 Debug Pattern Detection")
    print("=" * 40)
    
    # Test with the single invoice content
    single_invoice = """
    INVOICE #73318
    WILD HORSE BREWING CO LTD
    123 Main Street, Cardiff, CF1 1AA
    
    Invoice Date: Friday, 4 July 2025
    Due Date: Friday, 18 July 2025
    
    QTY CODE ITEM UNIT PRICE TOTAL
    2 BUCK-EK30 Buckskin - 30L E-keg £98.50 £197.00
    1 WINE-BTL Red Wine Bottle £15.75 £15.75
    3 BEER-CAN Premium Lager £2.50 £7.50
    
    Subtotal: £220.25
    VAT (20%): £44.05
    Total (inc. VAT): £264.30
    """
    
    # Test invoice patterns
    invoice_patterns = [
        r'\b(?:invoice|inv)[\s#:]*([A-Za-z0-9\-]+)',
        r'\b(INV[0-9\-]+)\b',
        r'\b([A-Z]{2,3}[0-9]{3,8})\b',
        r'(?:page|p)\s+\d+\s+of\s+\d+',  # Page numbering
        r'(?:continued|cont\.)',  # Continuation indicators
    ]
    
    found_invoices = []
    for i, pattern in enumerate(invoice_patterns):
        matches = re.findall(pattern, single_invoice, re.IGNORECASE)
        if matches:
            print(f"Pattern {i+1}: {pattern}")
            print(f"  Matches: {matches}")
            found_invoices.extend(matches)
    
    print(f"\nAll found invoices: {found_invoices}")
    unique_invoices = set(found_invoices)
    print(f"Unique invoices: {unique_invoices}")
    print(f"Count: {len(unique_invoices)}")
    
    # Test supplier patterns
    supplier_patterns = [
        r'(?:WILD HORSE BREWING CO LTD|RED DRAGON DISPENSE LIMITED|SNOWDONIA HOSPITALITY)',
        r'([A-Za-z\s&\.]+)\s*(?:Ltd|Limited|Inc|Corp)',
    ]
    
    found_suppliers = []
    for i, pattern in enumerate(supplier_patterns):
        matches = re.findall(pattern, single_invoice, re.IGNORECASE)
        if matches:
            print(f"\nSupplier Pattern {i+1}: {pattern}")
            print(f"  Matches: {matches}")
            found_suppliers.extend(matches)
    
    print(f"\nAll found suppliers: {found_suppliers}")
    unique_suppliers = set(found_suppliers)
    print(f"Unique suppliers: {unique_suppliers}")
    print(f"Count: {len(unique_suppliers)}")
    
    # Test page markers
    page_markers = re.findall(r'---\s*PAGE\s*\d+', single_invoice, re.IGNORECASE)
    print(f"\nPage markers: {page_markers}")
    print(f"Count: {len(page_markers)}")

if __name__ == "__main__":
    test_pattern_detection() 