#!/usr/bin/env python3
"""
Debug Validation Script

Test the validation logic to see what's happening
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ocr.validate import get_document_validator
from ocr.classifier import get_document_classifier

def test_validation():
    """Test validation with sample data"""
    
    # Test invoice data
    invoice_data = {
        'document_type': 'invoice',
        'supplier': 'WILD HORSE BREWING CO LTD',
        'invoice_number': 'INV-2025-001',
        'date': '15/08/2025',
        'total_amount': 118.08,
        'line_items': [
            {
                'description': 'Premium Lager',
                'quantity': 24,
                'unit': 'ea',
                'unit_price': 2.50,
                'line_total': 60.00
            },
            {
                'description': 'Craft IPA',
                'quantity': 12,
                'unit': 'ea',
                'unit_price': 3.20,
                'line_total': 38.40
            }
        ]
    }
    
    print("🧪 Testing Invoice Validation")
    print("=" * 50)
    
    validator = get_document_validator()
    result = validator.validate_document(invoice_data, "")
    
    print(f"Arithmetic OK: {result.arithmetic_ok}")
    print(f"Currency OK: {result.currency_ok}")
    print(f"VAT OK: {result.vat_ok}")
    print(f"Date OK: {result.date_ok}")
    print(f"Supplier OK: {result.supplier_ok}")
    print(f"Overall OK: {result.overall_ok}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Issues: {len(result.issues)}")
    
    for issue in result.issues:
        print(f"  - {issue.issue_type}: {issue.message}")
    
    # Test menu data
    menu_data = {
        'document_type': 'other',
        'supplier': 'THE RED LION PUB',
        'date': '',
        'total_amount': 0.0,
        'line_items': []
    }
    
    print("\n🧪 Testing Menu Validation")
    print("=" * 50)
    
    result = validator.validate_document(menu_data, "")
    
    print(f"Arithmetic OK: {result.arithmetic_ok}")
    print(f"Currency OK: {result.currency_ok}")
    print(f"VAT OK: {result.vat_ok}")
    print(f"Date OK: {result.date_ok}")
    print(f"Supplier OK: {result.supplier_ok}")
    print(f"Overall OK: {result.overall_ok}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Issues: {len(result.issues)}")
    
    for issue in result.issues:
        print(f"  - {issue.issue_type}: {issue.message}")

    # Test future date validation
    future_date_data = {
        'document_type': 'invoice',
        'supplier': 'WILD HORSE BREWING CO LTD',
        'invoice_number': 'INV-2025-002',
        'date': '25/08/2025',
        'total_amount': 60.00,
        'line_items': [
            {
                'description': 'Premium Lager',
                'quantity': 24,
                'unit': 'ea',
                'unit_price': 2.50,
                'line_total': 60.00
            }
        ]
    }
    
    print("\n🧪 Testing Future Date Validation")
    print("=" * 50)
    
    result = validator.validate_document(future_date_data, "")
    
    print(f"Arithmetic OK: {result.arithmetic_ok}")
    print(f"Currency OK: {result.currency_ok}")
    print(f"VAT OK: {result.vat_ok}")
    print(f"Date OK: {result.date_ok}")
    print(f"Supplier OK: {result.supplier_ok}")
    print(f"Overall OK: {result.overall_ok}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Issues: {len(result.issues)}")
    
    for issue in result.issues:
        print(f"  - {issue.issue_type}: {issue.message}")

if __name__ == "__main__":
    test_validation() 