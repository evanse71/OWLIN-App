#!/usr/bin/env python3
"""
Test script for the comprehensive normalization system.

This script validates the normalization module with real-world examples
and provides detailed reporting on parsing accuracy and performance.
"""

import sys
import os
import json
import time
from pathlib import Path
from decimal import Decimal
from datetime import date

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from normalization.field_normalizer import FieldNormalizer
from normalization.types import NormalizationResult


def test_basic_normalization():
    """Test basic normalization functionality."""
    print("Testing basic normalization...")
    
    normalizer = FieldNormalizer()
    
    # Test data
    raw_data = {
        "supplier": "ABC Company Ltd",
        "invoice_number": "INV-2024-001",
        "invoice_date": "15/01/2024",
        "currency": "GBP",
        "subtotal": "£100.00",
        "vat_amount": "£20.00",
        "total": "£120.00",
        "line_items": [
            {
                "description": "Office Supplies",
                "quantity": "2",
                "unit_price": "£25.00",
                "line_total": "£50.00"
            },
            {
                "description": "Consulting Services",
                "quantity": "5",
                "unit_price": "£10.00",
                "line_total": "£50.00"
            }
        ]
    }
    
    context = {"region": "UK", "industry": "general"}
    
    start_time = time.time()
    result = normalizer.normalize_invoice(raw_data, context)
    processing_time = time.time() - start_time
    
    print(f"[OK] Processing time: {processing_time:.3f} seconds")
    print(f"[OK] Success: {result.is_successful()}")
    print(f"[OK] Confidence: {result.normalized_invoice.overall_confidence:.3f}")
    print(f"[OK] Supplier: {result.normalized_invoice.supplier_name}")
    print(f"[OK] Total: {result.normalized_invoice.total_amount}")
    print(f"[OK] Line items: {len(result.normalized_invoice.line_items)}")
    
    return result


def test_date_parsing():
    """Test date parsing with various formats."""
    print("\nTesting date parsing...")
    
    normalizer = FieldNormalizer()
    
    test_dates = [
        "15/01/2024",  # DD/MM/YYYY
        "01/15/2024",  # MM/DD/YYYY
        "2024-01-15",  # ISO format
        "15 January 2024",  # Month name
        "15.01.2024",  # European format
        "15/01/24",    # Two-digit year
    ]
    
    for date_str in test_dates:
        result = normalizer.normalize_single_field("date", date_str)
        if result and result.is_valid():
            print(f"[OK] {date_str} -> {result.date}")
        else:
            print(f"[FAIL] {date_str} -> Failed")


def test_currency_parsing():
    """Test currency parsing with various formats."""
    print("\nTesting currency parsing...")
    
    normalizer = FieldNormalizer()
    
    test_currencies = [
        "£", "€", "$", "GBP", "EUR", "USD",
        "Pound", "Euro", "Dollar"
    ]
    
    for currency_str in test_currencies:
        result = normalizer.normalize_single_field("currency", currency_str)
        if result and result.is_valid():
            print(f"[OK] {currency_str} -> {result.currency_code}")
        else:
            print(f"[FAIL] {currency_str} -> Failed")


def test_price_parsing():
    """Test price parsing with various formats."""
    print("\nTesting price parsing...")
    
    normalizer = FieldNormalizer()
    
    test_prices = [
        "£123.45", "€99.99", "$1,234.56",
        "123.45£", "99.99 EUR", "1,234.56 USD",
        "123.45", "1,234.56"
    ]
    
    for price_str in test_prices:
        result = normalizer.normalize_single_field("price", price_str)
        if result and result.is_valid():
            print(f"[OK] {price_str} -> {result.amount} {result.currency_code}")
        else:
            print(f"[FAIL] {price_str} -> Failed")


def test_vat_parsing():
    """Test VAT parsing with various formats."""
    print("\nTesting VAT parsing...")
    
    normalizer = FieldNormalizer()
    
    test_vats = [
        "VAT @ 20%", "Tax @ 19%", "20% VAT", "19% Tax",
        "VAT: £24.50", "Tax: €19.99", "VAT £24.50"
    ]
    
    for vat_str in test_vats:
        result = normalizer.normalize_single_field("vat", vat_str)
        if result and result.is_valid():
            if result.rate:
                print(f"[OK] {vat_str} -> Rate: {result.rate}")
            if result.amount:
                print(f"[OK] {vat_str} -> Amount: {result.amount}")
        else:
            print(f"[FAIL] {vat_str} -> Failed")


def test_supplier_parsing():
    """Test supplier parsing with various formats."""
    print("\nTesting supplier parsing...")
    
    normalizer = FieldNormalizer()
    
    test_suppliers = [
        "ABC Company Ltd",
        "XYZ Corporation Inc",
        "Supplier: Test Company",
        "Vendor: Another Corp",
        "Mr. John Smith Ltd"
    ]
    
    for supplier_str in test_suppliers:
        result = normalizer.normalize_single_field("supplier", supplier_str)
        if result and result.is_valid():
            print(f"[OK] {supplier_str} -> {result.name}")
        else:
            print(f"[FAIL] {supplier_str} -> Failed")


def test_unit_parsing():
    """Test unit parsing with various formats."""
    print("\nTesting unit parsing...")
    
    normalizer = FieldNormalizer()
    
    test_units = [
        "kg", "kilogram", "kilograms",
        "l", "litre", "litres",
        "pcs", "pieces", "units",
        "hr", "hour", "hours",
        "m", "metre", "metres"
    ]
    
    for unit_str in test_units:
        result = normalizer.normalize_single_field("unit", unit_str)
        if result and result.is_valid():
            print(f"[OK] {unit_str} -> {result.unit}")
        else:
            print(f"[FAIL] {unit_str} -> Failed")


def test_complex_invoice():
    """Test complex invoice with multiple line items."""
    print("\nTesting complex invoice...")
    
    normalizer = FieldNormalizer()
    
    # Complex invoice data
    raw_data = {
        "supplier": "Complex Corp Ltd",
        "invoice_number": "COMP-2024-001",
        "invoice_date": "15/01/2024",
        "currency": "GBP",
        "subtotal": "£500.00",
        "vat_rate": "20%",
        "vat_amount": "£100.00",
        "total": "£600.00",
        "line_items": [
            {
                "description": "Software License",
                "quantity": "1",
                "unit": "license",
                "unit_price": "£200.00",
                "line_total": "£200.00"
            },
            {
                "description": "Consulting Services",
                "quantity": "20",
                "unit": "hours",
                "unit_price": "£15.00",
                "line_total": "£300.00"
            }
        ]
    }
    
    context = {
        "region": "UK",
        "industry": "technology",
        "known_suppliers": ["Complex Corp Ltd"]
    }
    
    start_time = time.time()
    result = normalizer.normalize_invoice(raw_data, context)
    processing_time = time.time() - start_time
    
    print(f"[OK] Processing time: {processing_time:.3f} seconds")
    print(f"[OK] Success: {result.is_successful()}")
    print(f"[OK] Confidence: {result.normalized_invoice.overall_confidence:.3f}")
    print(f"[OK] Supplier: {result.normalized_invoice.supplier_name}")
    print(f"[OK] Invoice number: {result.normalized_invoice.invoice_number}")
    print(f"[OK] Date: {result.normalized_invoice.invoice_date}")
    print(f"[OK] Currency: {result.normalized_invoice.currency}")
    print(f"[OK] Subtotal: {result.normalized_invoice.subtotal}")
    print(f"[OK] Tax amount: {result.normalized_invoice.tax_amount}")
    print(f"[OK] Total: {result.normalized_invoice.total_amount}")
    print(f"[OK] Line items: {len(result.normalized_invoice.line_items)}")
    
    for i, item in enumerate(result.normalized_invoice.line_items):
        print(f"  Item {i+1}: {item.description}")
        print(f"    Quantity: {item.quantity} {item.unit}")
        print(f"    Unit price: {item.unit_price}")
        print(f"    Line total: {item.line_total}")
        print(f"    Confidence: {item.confidence:.3f}")
    
    return result


def test_error_handling():
    """Test error handling with invalid data."""
    print("\nTesting error handling...")
    
    normalizer = FieldNormalizer()
    
    # Invalid data
    raw_data = {
        "supplier": "",  # Empty supplier
        "invoice_date": "invalid date",
        "currency": "XYZ",  # Invalid currency
        "total": "not a number"
    }
    
    result = normalizer.normalize_invoice(raw_data)
    
    print(f"[OK] Success: {result.is_successful()}")
    print(f"[OK] Confidence: {result.normalized_invoice.overall_confidence:.3f}")
    print(f"[OK] Errors: {len(result.normalized_invoice.errors)}")
    print(f"[OK] Fallback used: {result.fallback_used}")
    
    for error in result.normalized_invoice.errors[:3]:  # Show first 3 errors
        print(f"  Error: {error.field_name} - {error.message}")


def test_performance():
    """Test performance with multiple invoices."""
    print("\nTesting performance...")
    
    normalizer = FieldNormalizer()
    
    # Generate test data
    test_invoices = []
    for i in range(10):
        test_invoices.append({
            "supplier": f"Test Company {i} Ltd",
            "invoice_number": f"TEST-{i:03d}",
            "invoice_date": "15/01/2024",
            "currency": "GBP",
            "total": f"£{100 + i * 10}.00",
            "line_items": [
                {
                    "description": f"Item {i+1}",
                    "quantity": "1",
                    "unit_price": f"£{100 + i * 10}.00",
                    "line_total": f"£{100 + i * 10}.00"
                }
            ]
        })
    
    start_time = time.time()
    results = []
    
    for invoice_data in test_invoices:
        result = normalizer.normalize_invoice(invoice_data)
        results.append(result)
    
    total_time = time.time() - start_time
    avg_time = total_time / len(test_invoices)
    success_count = sum(1 for r in results if r.is_successful())
    
    print(f"[OK] Processed {len(test_invoices)} invoices in {total_time:.3f} seconds")
    print(f"[OK] Average time per invoice: {avg_time:.3f} seconds")
    print(f"[OK] Success rate: {success_count}/{len(test_invoices)} ({success_count/len(test_invoices)*100:.1f}%)")


def test_json_serialization():
    """Test JSON serialization of results."""
    print("\nTesting JSON serialization...")
    
    normalizer = FieldNormalizer()
    
    raw_data = {
        "supplier": "JSON Test Ltd",
        "invoice_number": "JSON-001",
        "date": "15/01/2024",
        "currency": "GBP",
        "total": "£100.00"
    }
    
    result = normalizer.normalize_invoice(raw_data)
    
    # Test to_dict method
    invoice_dict = result.normalized_invoice.to_dict()
    print(f"[OK] to_dict() works: {isinstance(invoice_dict, dict)}")
    print(f"[OK] Keys: {list(invoice_dict.keys())}")
    
    # Test summary method
    summary = result.get_summary()
    print(f"[OK] get_summary() works: {isinstance(summary, dict)}")
    print(f"[OK] Summary keys: {list(summary.keys())}")
    
    # Test JSON serialization
    try:
        json_str = json.dumps(invoice_dict, default=str)
        print(f"[OK] JSON serialization works: {len(json_str)} characters")
    except Exception as e:
        print(f"[FAIL] JSON serialization failed: {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("COMPREHENSIVE NORMALIZATION SYSTEM TEST")
    print("=" * 60)
    
    try:
        # Basic functionality test
        test_basic_normalization()
        
        # Individual parser tests
        test_date_parsing()
        test_currency_parsing()
        test_price_parsing()
        test_vat_parsing()
        test_supplier_parsing()
        test_unit_parsing()
        
        # Complex scenario test
        test_complex_invoice()
        
        # Error handling test
        test_error_handling()
        
        # Performance test
        test_performance()
        
        # JSON serialization test
        test_json_serialization()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
