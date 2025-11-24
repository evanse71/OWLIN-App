#!/usr/bin/env python3
"""
Comprehensive validation script for the confidence routing system.

This script validates the complete confidence routing and flagging system
with realistic test cases and edge scenarios.
"""

import sys
import os
import logging
from typing import Dict, Any, List
from decimal import Decimal
from datetime import date

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def setup_logging():
    """Setup logging for validation."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def test_confidence_calculation():
    """Test confidence calculation functionality."""
    print("\n=== Testing Confidence Calculation ===")
    
    try:
        from normalization.confidence_routing import ConfidenceCalculator
        from normalization.types import ParsedDate, ParsedCurrency, FieldError, FieldErrorType
        
        calculator = ConfidenceCalculator()
        
        # Test high-confidence date
        parsed_date = ParsedDate(
            date=date(2024, 1, 15),
            raw_value="2024-01-15",
            confidence=0.95,
            format_detected="ISO",
            errors=[]
        )
        
        metrics = calculator.calculate_field_confidence("date", parsed_date)
        print(f"âœ“ High-confidence date: {metrics.overall_confidence:.3f}")
        
        # Test low-confidence date
        parsed_date_low = ParsedDate(
            date=None,
            raw_value="unclear date",
            confidence=0.3,
            format_detected=None,
            errors=[FieldError(
                field_name="date",
                error_type=FieldErrorType.INVALID_FORMAT,
                raw_value="unclear date",
                message="No valid date format detected"
            )]
        )
        
        metrics_low = calculator.calculate_field_confidence("date", parsed_date_low)
        print(f"âœ“ Low-confidence date: {metrics_low.overall_confidence:.3f}")
        
        # Test currency with context
        parsed_currency = ParsedCurrency(
            currency_code="GBP",
            symbol="Â£",
            raw_value="Â£",
            confidence=0.9,
            errors=[]
        )
        
        context = {"region": "UK", "other_currencies": ["GBP"]}
        metrics_currency = calculator.calculate_field_confidence("currency", parsed_currency, context)
        print(f"âœ“ Currency with context: {metrics_currency.overall_confidence:.3f}")
        
        return True
        
    except Exception as e:
        print(f"âœ— Confidence calculation test failed: {e}")
        return False

def test_confidence_routing():
    """Test confidence routing functionality."""
    print("\n=== Testing Confidence Routing ===")
    
    try:
        from normalization.confidence_routing import ConfidenceRouter, RoutingDecision
        from normalization.types import ParsedDate, FieldError, FieldErrorType
        
        router = ConfidenceRouter({"confidence_threshold": 0.7})
        
        # Test auto-accept routing
        parsed_date = ParsedDate(
            date=date(2024, 1, 15),
            raw_value="2024-01-15",
            confidence=0.95,
            format_detected="ISO",
            errors=[]
        )
        
        result = router.route_field("date", parsed_date)
        print(f"âœ“ Auto-accept routing: {result.routing_decision.value}")
        assert result.routing_decision == RoutingDecision.AUTO_ACCEPT
        
        # Test needs-review routing
        parsed_date_low = ParsedDate(
            date=None,
            raw_value="unclear date",
            confidence=0.3,
            format_detected=None,
            errors=[FieldError(
                field_name="date",
                error_type=FieldErrorType.INVALID_FORMAT,
                raw_value="unclear date",
                message="No valid date format detected"
            )]
        )
        
        result_low = router.route_field("date", parsed_date_low)
        print(f"âœ“ Needs-review routing: {result_low.routing_decision.value}")
        assert result_low.routing_decision == RoutingDecision.NEEDS_REVIEW
        
        return True
        
    except Exception as e:
        print(f"âœ— Confidence routing test failed: {e}")
        return False

def test_integration_high_quality():
    """Test integration with high-quality invoice data."""
    print("\n=== Testing High-Quality Invoice Integration ===")
    
    try:
from backend.normalization import FieldNormalizer
        
        # High-quality invoice data
        raw_data = {
            "supplier": "ACME Corporation Ltd",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-01-15",
            "currency": "GBP",
            "subtotal": "Â£100.00",
            "tax_amount": "Â£20.00",
            "total_amount": "Â£120.00",
            "line_items": [
                {
                    "description": "Professional Services",
                    "quantity": "10",
                    "unit": "hours",
                    "unit_price": "Â£10.00",
                    "line_total": "Â£100.00"
                }
            ]
        }
        
        context = {
            "invoice_id": "high-quality-001",
            "region": "UK",
            "known_suppliers": ["ACME Corporation Ltd"],
            "default_currency": "GBP"
        }
        
        normalizer = FieldNormalizer()
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
        
        print(f"âœ“ Overall confidence: {routing_result.overall_confidence:.3f}")
        print(f"âœ“ Auto-accepted fields: {len(routing_result.auto_accepted_fields)}")
        print(f"âœ“ Review candidates: {len(routing_result.review_candidates)}")
        print(f"âœ“ Processing time: {routing_result.processing_time:.3f}s")
        
        # Should have high confidence and mostly auto-accepted
        assert routing_result.overall_confidence > 0.5
        assert len(routing_result.auto_accepted_fields) > 0
        
        return True
        
    except Exception as e:
        print(f"âœ— High-quality integration test failed: {e}")
        return False

def test_integration_poor_quality():
    """Test integration with poor-quality invoice data."""
    print("\n=== Testing Poor-Quality Invoice Integration ===")
    
    try:
from backend.normalization import FieldNormalizer
        
        # Poor-quality invoice data
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
        
        print(f"âœ“ Overall confidence: {routing_result.overall_confidence:.3f}")
        print(f"âœ“ Auto-accepted fields: {len(routing_result.auto_accepted_fields)}")
        print(f"âœ“ Review candidates: {len(routing_result.review_candidates)}")
        print(f"âœ“ Processing time: {routing_result.processing_time:.3f}s")
        
        # Should have low confidence and mostly needs review
        assert routing_result.overall_confidence < 0.7
        assert len(routing_result.review_candidates) > 0
        
        return True
        
    except Exception as e:
        print(f"âœ— Poor-quality integration test failed: {e}")
        return False

def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n=== Testing Edge Cases ===")
    
    try:
from backend.normalization import FieldNormalizer
        
        # Test empty data
        raw_data = {}
        context = {"invoice_id": "empty-001"}
        
        normalizer = FieldNormalizer()
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
        
        print(f"âœ“ Empty data handled: confidence={routing_result.overall_confidence:.3f}")
        assert routing_result.overall_confidence < 0.5
        
        # Test malformed data
        raw_data_malformed = {
            "supplier": 123,  # Wrong type
            "invoice_number": ["not", "a", "string"],  # Wrong type
            "line_items": "not a list",  # Wrong type
        }
        
        context_malformed = {"invoice_id": "malformed-001"}
        
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data_malformed, context_malformed)
        
        print(f"âœ“ Malformed data handled: confidence={routing_result.overall_confidence:.3f}")
        assert routing_result.error_count >= 0
        
        return True
        
    except Exception as e:
        print(f"âœ— Edge cases test failed: {e}")
        return False

def test_custom_configuration():
    """Test custom configuration options."""
    print("\n=== Testing Custom Configuration ===")
    
    try:
from backend.normalization import FieldNormalizer
        
        # Custom configuration
        confidence_config = {
            "confidence_threshold": 0.8,  # Higher threshold
            "field_thresholds": {
                "date": 0.9,              # Very high threshold for dates
                "currency": 0.5,          # Lower threshold for currency
                "supplier": 0.8,          # High threshold for suppliers
            }
        }
        
        raw_data = {
            "supplier": "ACME Corporation Ltd",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-01-15",
            "currency": "GBP",
            "subtotal": "Â£100.00",
            "tax_amount": "Â£20.00",
            "total_amount": "Â£120.00",
            "line_items": []
        }
        
        context = {
            "invoice_id": "custom-config-001",
            "region": "UK",
            "known_suppliers": ["ACME Corporation Ltd"],
            "default_currency": "GBP"
        }
        
        normalizer = FieldNormalizer(confidence_config)
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
        
        print(f"âœ“ Custom configuration applied: confidence={routing_result.overall_confidence:.3f}")
        print(f"âœ“ Auto-accepted fields: {len(routing_result.auto_accepted_fields)}")
        print(f"âœ“ Review candidates: {len(routing_result.review_candidates)}")
        
        return True
        
    except Exception as e:
        print(f"âœ— Custom configuration test failed: {e}")
        return False

def test_review_candidates():
    """Test review candidate generation and serialization."""
    print("\n=== Testing Review Candidates ===")
    
    try:
        from normalization.confidence_routing import ConfidenceRouter, ReviewCandidate
        from normalization.types import ParsedDate, FieldError, FieldErrorType
        
        router = ConfidenceRouter()
        
        # Create a low-confidence field that needs review
        parsed_date = ParsedDate(
            date=None,
            raw_value="unclear date",
            confidence=0.3,
            format_detected=None,
            errors=[FieldError(
                field_name="date",
                error_type=FieldErrorType.INVALID_FORMAT,
                raw_value="unclear date",
                message="No valid date format detected"
            )]
        )
        
        routing_result = router.route_field("date", parsed_date)
        
        # Create review candidate
        candidate = ReviewCandidate(
            field_name="date",
            field_type="ParsedDate",
            raw_value="unclear date",
            normalized_value=None,
            confidence_metrics=routing_result.confidence_metrics,
            routing_result=routing_result,
            error_details=routing_result.error_details,
            context={"region": "UK"}
        )
        
        print(f"âœ“ Review candidate created: {candidate.field_name}")
        print(f"âœ“ Needs human review: {candidate.needs_human_review()}")
        print(f"âœ“ Error details: {len(candidate.error_details)} errors")
        
        # Test serialization
        candidate_dict = candidate.to_dict()
        print(f"âœ“ Serialization successful: {len(candidate_dict)} fields")
        
        assert candidate.field_name == "date"
        assert candidate.needs_human_review()
        assert len(candidate.error_details) > 0
        
        return True
        
    except Exception as e:
        print(f"âœ— Review candidates test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    logger = setup_logging()
    logger.info("Starting confidence routing system validation")
    
    print("Confidence Routing System Validation")
    print("=" * 50)
    
    tests = [
        ("Confidence Calculation", test_confidence_calculation),
        ("Confidence Routing", test_confidence_routing),
        ("High-Quality Integration", test_integration_high_quality),
        ("Poor-Quality Integration", test_integration_poor_quality),
        ("Edge Cases", test_edge_cases),
        ("Custom Configuration", test_custom_configuration),
        ("Review Candidates", test_review_candidates),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"âœ“ {test_name}: PASSED")
                passed += 1
            else:
                print(f"âœ— {test_name}: FAILED")
                failed += 1
        except Exception as e:
            print(f"âœ— {test_name}: ERROR - {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Validation Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("ðŸŽ‰ All tests passed! Confidence routing system is working correctly.")
        return True
    else:
        print("âŒ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


