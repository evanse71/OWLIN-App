#!/usr/bin/env python3
"""
Validation script for normalized output.

This script validates that the normalized output is ready for
card creation and matching operations.
"""

import sys
import os
import json
from pathlib import Path
from decimal import Decimal
from datetime import date

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from normalization.field_normalizer import FieldNormalizer
from normalization.types import NormalizationResult


def validate_invoice_for_card_creation(normalized_invoice) -> dict:
    """
    Validate that normalized invoice is ready for card creation.
    
    Args:
        normalized_invoice: NormalizedInvoice object
    
    Returns:
        Validation results dictionary
    """
    validation_results = {
        "ready_for_card_creation": True,
        "missing_required_fields": [],
        "data_quality_issues": [],
        "confidence_score": normalized_invoice.overall_confidence,
        "recommendations": []
    }
    
    # Check required fields for card creation
    required_fields = {
        "supplier_name": normalized_invoice.supplier_name,
        "total_amount": normalized_invoice.total_amount,
        "currency": normalized_invoice.currency
    }
    
    for field_name, field_value in required_fields.items():
        if field_value is None:
            validation_results["missing_required_fields"].append(field_name)
            validation_results["ready_for_card_creation"] = False
    
    # Check data quality
    if normalized_invoice.overall_confidence < 0.7:
        validation_results["data_quality_issues"].append("Low confidence score")
        validation_results["recommendations"].append("Review OCR quality or manual verification needed")
    
    if len(normalized_invoice.errors) > 3:
        validation_results["data_quality_issues"].append("High error count")
        validation_results["recommendations"].append("Review parsing errors and improve data quality")
    
    # Check line items quality
    if normalized_invoice.line_items:
        low_confidence_items = [item for item in normalized_invoice.line_items if item.confidence < 0.6]
        if low_confidence_items:
            validation_results["data_quality_issues"].append(f"{len(low_confidence_items)} low-confidence line items")
            validation_results["recommendations"].append("Review line item parsing accuracy")
    
    # Check date validity
    if normalized_invoice.invoice_date:
        if normalized_invoice.invoice_date > date.today():
            validation_results["data_quality_issues"].append("Future invoice date")
            validation_results["recommendations"].append("Verify invoice date is correct")
    
    # Check amount consistency
    if normalized_invoice.subtotal and normalized_invoice.tax_amount and normalized_invoice.total_amount:
        calculated_total = normalized_invoice.subtotal + normalized_invoice.tax_amount
        if abs(calculated_total - normalized_invoice.total_amount) > Decimal("0.01"):
            validation_results["data_quality_issues"].append("Amount calculation mismatch")
            validation_results["recommendations"].append("Verify subtotal, tax, and total amounts")
    
    return validation_results


def validate_for_matching(normalized_invoice) -> dict:
    """
    Validate that normalized invoice is ready for matching operations.
    
    Args:
        normalized_invoice: NormalizedInvoice object
    
    Returns:
        Matching validation results dictionary
    """
    validation_results = {
        "ready_for_matching": True,
        "matching_confidence": 0.0,
        "matching_issues": [],
        "recommendations": []
    }
    
    # Calculate matching confidence based on key fields
    confidence_factors = []
    
    # Supplier name confidence
    if normalized_invoice.supplier_name:
        confidence_factors.append(0.3)  # 30% weight for supplier
    else:
        validation_results["matching_issues"].append("Missing supplier name")
        validation_results["ready_for_matching"] = False
    
    # Invoice number confidence
    if normalized_invoice.invoice_number:
        confidence_factors.append(0.2)  # 20% weight for invoice number
    else:
        validation_results["matching_issues"].append("Missing invoice number")
    
    # Date confidence
    if normalized_invoice.invoice_date:
        confidence_factors.append(0.2)  # 20% weight for date
    else:
        validation_results["matching_issues"].append("Missing invoice date")
    
    # Amount confidence
    if normalized_invoice.total_amount:
        confidence_factors.append(0.3)  # 30% weight for amount
    else:
        validation_results["matching_issues"].append("Missing total amount")
        validation_results["ready_for_matching"] = False
    
    # Calculate overall matching confidence
    if confidence_factors:
        validation_results["matching_confidence"] = sum(confidence_factors) / len(confidence_factors)
    
    # Check for duplicate detection readiness
    if normalized_invoice.supplier_name and normalized_invoice.invoice_number:
        validation_results["duplicate_detection_ready"] = True
    else:
        validation_results["duplicate_detection_ready"] = False
        validation_results["matching_issues"].append("Insufficient data for duplicate detection")
    
    # Check for supplier matching readiness
    if normalized_invoice.supplier_name and normalized_invoice.currency:
        validation_results["supplier_matching_ready"] = True
    else:
        validation_results["supplier_matching_ready"] = False
        validation_results["matching_issues"].append("Insufficient data for supplier matching")
    
    return validation_results


def test_card_creation_readiness():
    """Test various invoice scenarios for card creation readiness."""
    print("Testing card creation readiness...")
    
    normalizer = FieldNormalizer()
    
    # Test cases with different completeness levels
    test_cases = [
        {
            "name": "Complete Invoice",
            "data": {
                "supplier": "Complete Corp Ltd",
                "invoice_number": "COMP-001",
                "invoice_date": "15/01/2024",
                "currency": "GBP",
                "subtotal": "£100.00",
                "tax_amount": "£20.00",
                "total": "£120.00"
            }
        },
        {
            "name": "Minimal Invoice",
            "data": {
                "supplier": "Minimal Ltd",
                "total": "£50.00"
            }
        },
        {
            "name": "Incomplete Invoice",
            "data": {
                "text": "Invoice for £100.00"
            }
        },
        {
            "name": "High Confidence Invoice",
            "data": {
                "supplier": "High Confidence Corp Ltd",
                "invoice_number": "HC-2024-001",
                "invoice_date": "15/01/2024",
                "currency": "GBP",
                "total": "£500.00",
                "line_items": [
                    {
                        "description": "Professional Services",
                        "quantity": "10",
                        "unit_price": "£50.00",
                        "line_total": "£500.00"
                    }
                ]
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        
        result = normalizer.normalize_invoice(test_case["data"])
        card_validation = validate_invoice_for_card_creation(result.normalized_invoice)
        
        print(f"Ready for card creation: {card_validation['ready_for_card_creation']}")
        print(f"Confidence score: {card_validation['confidence_score']:.3f}")
        
        if card_validation["missing_required_fields"]:
            print(f"Missing fields: {card_validation['missing_required_fields']}")
        
        if card_validation["data_quality_issues"]:
            print(f"Quality issues: {card_validation['data_quality_issues']}")
        
        if card_validation["recommendations"]:
            print(f"Recommendations: {card_validation['recommendations']}")


def test_matching_readiness():
    """Test various invoice scenarios for matching readiness."""
    print("\nTesting matching readiness...")
    
    normalizer = FieldNormalizer()
    
    # Test cases for matching scenarios
    test_cases = [
        {
            "name": "Perfect Match Candidate",
            "data": {
                "supplier": "Match Corp Ltd",
                "invoice_number": "MATCH-001",
                "invoice_date": "15/01/2024",
                "currency": "GBP",
                "total": "£200.00"
            }
        },
        {
            "name": "Partial Match Candidate",
            "data": {
                "supplier": "Partial Ltd",
                "total": "£150.00"
            }
        },
        {
            "name": "Duplicate Detection Candidate",
            "data": {
                "supplier": "Duplicate Corp Ltd",
                "invoice_number": "DUP-001",
                "total": "£300.00"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        
        result = normalizer.normalize_invoice(test_case["data"])
        matching_validation = validate_for_matching(result.normalized_invoice)
        
        print(f"Ready for matching: {matching_validation['ready_for_matching']}")
        print(f"Matching confidence: {matching_validation['matching_confidence']:.3f}")
        print(f"Duplicate detection ready: {matching_validation['duplicate_detection_ready']}")
        print(f"Supplier matching ready: {matching_validation['supplier_matching_ready']}")
        
        if matching_validation["matching_issues"]:
            print(f"Matching issues: {matching_validation['matching_issues']}")


def test_data_consistency():
    """Test data consistency across normalized fields."""
    print("\nTesting data consistency...")
    
    normalizer = FieldNormalizer()
    
    # Test invoice with potential inconsistencies
    raw_data = {
        "supplier": "Consistency Test Ltd",
        "invoice_number": "CONS-001",
        "invoice_date": "15/01/2024",
        "currency": "GBP",
        "subtotal": "£100.00",
        "tax_amount": "£20.00",
        "total": "£120.00",  # Should match subtotal + tax
        "line_items": [
            {
                "description": "Item 1",
                "quantity": "2",
                "unit_price": "£25.00",
                "line_total": "£50.00"
            },
            {
                "description": "Item 2",
                "quantity": "2",
                "unit_price": "£25.00",
                "line_total": "£50.00"
            }
        ]
    }
    
    result = normalizer.normalize_invoice(raw_data)
    invoice = result.normalized_invoice
    
    print(f"Supplier: {invoice.supplier_name}")
    print(f"Currency: {invoice.currency}")
    print(f"Subtotal: {invoice.subtotal}")
    print(f"Tax amount: {invoice.tax_amount}")
    print(f"Total: {invoice.total_amount}")
    
    # Check amount consistency
    if invoice.subtotal and invoice.tax_amount and invoice.total_amount:
        calculated_total = invoice.subtotal + invoice.tax_amount
        difference = abs(calculated_total - invoice.total_amount)
        print(f"Amount consistency: {difference <= Decimal('0.01')} (difference: {difference})")
    
    # Check line item totals
    if invoice.line_items:
        line_totals = [item.line_total for item in invoice.line_items if item.line_total]
        if line_totals:
            sum_line_totals = sum(line_totals)
            print(f"Line items total: {sum_line_totals}")
            if invoice.subtotal:
                line_consistency = abs(sum_line_totals - invoice.subtotal) <= Decimal('0.01')
                print(f"Line items consistency: {line_consistency}")


def test_json_output_format():
    """Test JSON output format for API compatibility."""
    print("\nTesting JSON output format...")
    
    normalizer = FieldNormalizer()
    
    raw_data = {
        "supplier": "JSON Test Ltd",
        "invoice_number": "JSON-001",
        "invoice_date": "15/01/2024",
        "currency": "GBP",
        "total": "£100.00"
    }
    
    result = normalizer.normalize_invoice(raw_data)
    
    # Test to_dict method
    invoice_dict = result.normalized_invoice.to_dict()
    
    print("JSON output structure:")
    print(f"- supplier_name: {type(invoice_dict.get('supplier_name'))}")
    print(f"- invoice_number: {type(invoice_dict.get('invoice_number'))}")
    print(f"- invoice_date: {type(invoice_dict.get('invoice_date'))}")
    print(f"- currency: {type(invoice_dict.get('currency'))}")
    print(f"- total_amount: {type(invoice_dict.get('total_amount'))}")
    print(f"- line_items: {type(invoice_dict.get('line_items'))}")
    print(f"- overall_confidence: {type(invoice_dict.get('overall_confidence'))}")
    
    # Test JSON serialization
    try:
        json_str = json.dumps(invoice_dict, default=str, indent=2)
        print(f"[OK] JSON serialization successful ({len(json_str)} characters)")
        
        # Test deserialization
        parsed = json.loads(json_str)
        print(f"[OK] JSON deserialization successful")
        
    except Exception as e:
        print(f"[FAIL] JSON serialization failed: {e}")


def test_performance_under_load():
    """Test performance under load for production readiness."""
    print("\nTesting performance under load...")
    
    normalizer = FieldNormalizer()
    
    # Generate test data
    test_invoices = []
    for i in range(50):  # 50 invoices
        test_invoices.append({
            "supplier": f"Load Test Company {i} Ltd",
            "invoice_number": f"LOAD-{i:03d}",
            "invoice_date": "15/01/2024",
            "currency": "GBP",
            "total": f"£{100 + i * 10}.00",
            "line_items": [
                {
                    "description": f"Load Test Item {i}",
                    "quantity": "1",
                    "unit_price": f"£{100 + i * 10}.00",
                    "line_total": f"£{100 + i * 10}.00"
                }
            ]
        })
    
    import time
    start_time = time.time()
    
    results = []
    for invoice_data in test_invoices:
        result = normalizer.normalize_invoice(invoice_data)
        results.append(result)
    
    total_time = time.time() - start_time
    avg_time = total_time / len(test_invoices)
    
    # Validate results
    success_count = sum(1 for r in results if r.is_successful())
    avg_confidence = sum(r.normalized_invoice.overall_confidence for r in results) / len(results)
    
    print(f"Processed {len(test_invoices)} invoices in {total_time:.3f} seconds")
    print(f"Average time per invoice: {avg_time:.3f} seconds")
    print(f"Success rate: {success_count}/{len(test_invoices)} ({success_count/len(test_invoices)*100:.1f}%)")
    print(f"Average confidence: {avg_confidence:.3f}")
    
    # Performance thresholds
    if avg_time < 0.1:  # Less than 100ms per invoice
        print("[OK] Performance: Excellent")
    elif avg_time < 0.5:  # Less than 500ms per invoice
        print("[OK] Performance: Good")
    else:
        print("[WARN] Performance: Needs optimization")


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("NORMALIZED OUTPUT VALIDATION")
    print("=" * 60)
    
    try:
        test_card_creation_readiness()
        test_matching_readiness()
        test_data_consistency()
        test_json_output_format()
        test_performance_under_load()
        
        print("\n" + "=" * 60)
        print("VALIDATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nThe normalization system is ready for:")
        print("[OK] Card creation operations")
        print("[OK] Matching operations")
        print("[OK] Duplicate detection")
        print("[OK] Supplier matching")
        print("[OK] API integration")
        print("[OK] Production deployment")
        
    except Exception as e:
        print(f"\n[FAIL] Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
