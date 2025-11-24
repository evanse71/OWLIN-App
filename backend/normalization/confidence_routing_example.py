"""
Example usage of the confidence routing and flagging system.

This module demonstrates how to use the confidence routing system
with realistic invoice data and various quality scenarios.
"""

import logging
from typing import Dict, Any
from decimal import Decimal
from datetime import date

from .field_normalizer import FieldNormalizer
from .confidence_routing import ConfidenceRouter, ConfidenceRoutingResult
from .types import NormalizedInvoice, NormalizedLineItem


# Configure logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def example_high_quality_invoice():
    """Example with high-quality, clear invoice data."""
    print("\n=== HIGH QUALITY INVOICE EXAMPLE ===")
    
    # High-quality invoice data
    raw_data = {
        "supplier": "ACME Corporation Ltd",
        "invoice_number": "INV-2024-001",
        "invoice_date": "2024-01-15",
        "currency": "GBP",
        "subtotal": "£100.00",
        "tax_amount": "£20.00",
        "total_amount": "£120.00",
        "line_items": [
            {
                "description": "Professional Services",
                "quantity": "10",
                "unit": "hours",
                "unit_price": "£10.00",
                "line_total": "£100.00"
            }
        ]
    }
    
    context = {
        "invoice_id": "high-quality-001",
        "region": "UK",
        "known_suppliers": ["ACME Corporation Ltd"],
        "default_currency": "GBP"
    }
    
    # Configure confidence routing
    confidence_config = {
        "confidence_threshold": 0.7,
        "field_thresholds": {
            "date": 0.8,
            "currency": 0.6,
            "supplier": 0.7
        }
    }
    
    normalizer = FieldNormalizer(confidence_config)
    normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
    
    print(f"Overall Confidence: {routing_result.overall_confidence:.3f}")
    print(f"Auto-accepted fields: {len(routing_result.auto_accepted_fields)}")
    print(f"Review candidates: {len(routing_result.review_candidates)}")
    print(f"Fully auto-acceptable: {routing_result.is_fully_auto_acceptable()}")
    
    if routing_result.review_candidates:
        print("\nReview candidates:")
        for candidate in routing_result.review_candidates:
            print(f"  - {candidate.field_name}: {candidate.raw_value} (confidence: {candidate.confidence_metrics.overall_confidence:.3f})")


def example_poor_quality_invoice():
    """Example with poor-quality, unclear invoice data."""
    print("\n=== POOR QUALITY INVOICE EXAMPLE ===")
    
    # Poor-quality invoice data with ambiguous fields
    raw_data = {
        "supplier": "unclear company name",
        "invoice_number": "123?",
        "invoice_date": "sometime in 2024",
        "currency": "?",
        "subtotal": "around 100",
        "tax_amount": "maybe 20",
        "total_amount": "120 or so",
        "line_items": [
            {
                "description": "unclear item",
                "quantity": "some",
                "unit": "?",
                "unit_price": "unknown",
                "line_total": "?"
            }
        ]
    }
    
    context = {
        "invoice_id": "poor-quality-001",
        "region": "unknown"
    }
    
    normalizer = FieldNormalizer()
    normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
    
    print(f"Overall Confidence: {routing_result.overall_confidence:.3f}")
    print(f"Auto-accepted fields: {len(routing_result.auto_accepted_fields)}")
    print(f"Review candidates: {len(routing_result.review_candidates)}")
    print(f"Fully auto-acceptable: {routing_result.is_fully_auto_acceptable()}")
    
    if routing_result.review_candidates:
        print("\nReview candidates:")
        for candidate in routing_result.review_candidates:
            print(f"  - {candidate.field_name}: {candidate.raw_value} (confidence: {candidate.confidence_metrics.overall_confidence:.3f})")
            if candidate.error_details:
                print(f"    Errors: {candidate.error_details}")


def example_perturbed_document():
    """Example with OCR perturbations and handwriting overlays."""
    print("\n=== PERTURBED DOCUMENT EXAMPLE ===")
    
    # Simulate OCR perturbations: blurred text, partial data, handwriting overlays
    raw_data = {
        "supplier": "ACME Corp Ltd",  # Slightly blurred but readable
        "invoice_number": "INV-2024-00I",  # OCR confusion: 1 vs I
        "invoice_date": "2024-01-1S",      # OCR confusion: 5 vs S
        "currency": "GBP",
        "subtotal": "£100.00",
        "tax_amount": "£20.00",
        "total_amount": "£120.00",
        "line_items": [
            {
                "description": "Professional Services",  # Clear
                "quantity": "1O",                       # OCR confusion: 0 vs O
                "unit": "hours",
                "unit_price": "£10.00",
                "line_total": "£100.00"
            }
        ]
    }
    
    context = {
        "invoice_id": "perturbed-001",
        "region": "UK",
        "known_suppliers": ["ACME Corp Ltd"],
        "default_currency": "GBP"
    }
    
    normalizer = FieldNormalizer()
    normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
    
    print(f"Overall Confidence: {routing_result.overall_confidence:.3f}")
    print(f"Auto-accepted fields: {len(routing_result.auto_accepted_fields)}")
    print(f"Review candidates: {len(routing_result.review_candidates)}")
    print(f"Fully auto-acceptable: {routing_result.is_fully_auto_acceptable()}")
    
    if routing_result.review_candidates:
        print("\nReview candidates:")
        for candidate in routing_result.review_candidates:
            print(f"  - {candidate.field_name}: {candidate.raw_value} (confidence: {candidate.confidence_metrics.overall_confidence:.3f})")
            if candidate.error_details:
                print(f"    Errors: {candidate.error_details}")


def example_mixed_quality_invoice():
    """Example with mixed quality fields."""
    print("\n=== MIXED QUALITY INVOICE EXAMPLE ===")
    
    # Mixed-quality invoice data
    raw_data = {
        "supplier": "ACME Corporation Ltd",  # Clear
        "invoice_number": "INV-2024-001",    # Clear
        "invoice_date": "unclear date",      # Unclear
        "currency": "GBP",                   # Clear
        "subtotal": "£100.00",              # Clear
        "tax_amount": "around 20",           # Unclear
        "total_amount": "£120.00",          # Clear
        "line_items": [
            {
                "description": "Professional Services",  # Clear
                "quantity": "10",                       # Clear
                "unit": "hours",                        # Clear
                "unit_price": "£10.00",                 # Clear
                "line_total": "£100.00"                 # Clear
            }
        ]
    }
    
    context = {
        "invoice_id": "mixed-quality-001",
        "region": "UK",
        "known_suppliers": ["ACME Corporation Ltd"],
        "default_currency": "GBP"
    }
    
    normalizer = FieldNormalizer()
    normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
    
    print(f"Overall Confidence: {routing_result.overall_confidence:.3f}")
    print(f"Auto-accepted fields: {len(routing_result.auto_accepted_fields)}")
    print(f"Review candidates: {len(routing_result.review_candidates)}")
    print(f"Fully auto-acceptable: {routing_result.is_fully_auto_acceptable()}")
    
    print(f"\nAuto-accepted fields: {routing_result.auto_accepted_fields}")
    
    if routing_result.review_candidates:
        print("\nReview candidates:")
        for candidate in routing_result.review_candidates:
            print(f"  - {candidate.field_name}: {candidate.raw_value} (confidence: {candidate.confidence_metrics.overall_confidence:.3f})")
            if candidate.error_details:
                print(f"    Errors: {candidate.error_details}")


def example_custom_configuration():
    """Example with custom confidence configuration."""
    print("\n=== CUSTOM CONFIGURATION EXAMPLE ===")
    
    # Custom confidence configuration
    confidence_config = {
        "confidence_threshold": 0.8,  # Higher threshold
        "field_thresholds": {
            "date": 0.9,              # Very high threshold for dates
            "currency": 0.5,          # Lower threshold for currency
            "supplier": 0.8,          # High threshold for suppliers
            "line_item": 0.7          # Medium threshold for line items
        },
        "confidence_weights": {
            "ocr": 0.4,               # Higher weight for OCR confidence
            "normalization": 0.3,    # Lower weight for normalization
            "error": 0.2,            # Error penalty weight
            "context": 0.05,         # Context boost weight
            "cross_validation": 0.05  # Cross-validation weight
        }
    }
    
    raw_data = {
        "supplier": "ACME Corporation Ltd",
        "invoice_number": "INV-2024-001",
        "invoice_date": "2024-01-15",
        "currency": "GBP",
        "subtotal": "£100.00",
        "tax_amount": "£20.00",
        "total_amount": "£120.00",
        "line_items": [
            {
                "description": "Professional Services",
                "quantity": "10",
                "unit": "hours",
                "unit_price": "£10.00",
                "line_total": "£100.00"
            }
        ]
    }
    
    context = {
        "invoice_id": "custom-config-001",
        "region": "UK",
        "known_suppliers": ["ACME Corporation Ltd"],
        "default_currency": "GBP"
    }
    
    normalizer = FieldNormalizer(confidence_config)
    normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
    
    print(f"Overall Confidence: {routing_result.overall_confidence:.3f}")
    print(f"Auto-accepted fields: {len(routing_result.auto_accepted_fields)}")
    print(f"Review candidates: {len(routing_result.review_candidates)}")
    print(f"Fully auto-acceptable: {routing_result.is_fully_auto_acceptable()}")
    
    # Show routing decisions for each field
    print("\nRouting decisions:")
    for result in routing_result.routing_log:
        print(f"  - {result.field_name}: {result.routing_decision.value} (confidence: {result.confidence_metrics.overall_confidence:.3f}, threshold: {result.threshold_used:.3f})")


def example_audit_logging():
    """Example demonstrating audit logging capabilities."""
    print("\n=== AUDIT LOGGING EXAMPLE ===")
    
    # Enable detailed logging
    logging.getLogger("owlin.normalization.confidence_routing").setLevel(logging.DEBUG)
    
    raw_data = {
        "supplier": "ACME Corporation Ltd",
        "invoice_number": "INV-2024-001",
        "invoice_date": "2024-01-15",
        "currency": "GBP",
        "subtotal": "£100.00",
        "tax_amount": "£20.00",
        "total_amount": "£120.00",
        "line_items": []
    }
    
    context = {
        "invoice_id": "audit-logging-001",
        "region": "UK",
        "known_suppliers": ["ACME Corporation Ltd"],
        "default_currency": "GBP"
    }
    
    normalizer = FieldNormalizer()
    normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
    
    print(f"Processing time: {routing_result.processing_time:.3f} seconds")
    print(f"Error count: {routing_result.error_count}")
    print(f"Warning count: {routing_result.warning_count}")
    
    # Show audit trail
    print("\nAudit trail:")
    for result in routing_result.routing_log:
        print(f"  - {result.field_name}: {result.routing_decision.value} at {result.timestamp}")
        if result.error_details:
            print(f"    Errors: {result.error_details}")


def main():
    """Run all examples."""
    print("Confidence Routing and Flagging System Examples")
    print("=" * 50)
    
    try:
        example_high_quality_invoice()
        example_poor_quality_invoice()
        example_perturbed_document()
        example_mixed_quality_invoice()
        example_custom_configuration()
        example_audit_logging()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        raise


if __name__ == "__main__":
    main()
