"""
Comprehensive tests for the confidence routing and flagging system.

Tests include:
- Unit tests for confidence calculation
- Integration tests with realistic perturbed documents
- Edge case handling
- Routing decision validation
- Audit logging verification
"""

import pytest
import logging
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, Any, List

from backend.normalization.confidence_routing import (
    ConfidenceRouter, ConfidenceCalculator, ConfidenceMetrics,
    RoutingDecision, ReviewCandidate, ConfidenceRoutingResult
)
from backend.normalization.types import (
    NormalizedInvoice, NormalizedLineItem, ParsedDate, ParsedCurrency,
    ParsedPrice, ParsedVAT, ParsedSupplier, FieldError, FieldErrorType
)
from backend.normalization.field_normalizer import FieldNormalizer


class TestConfidenceCalculator:
    """Test confidence calculation functionality."""
    
    def test_calculate_field_confidence_high_confidence(self):
        """Test confidence calculation for high-confidence field."""
        calculator = ConfidenceCalculator()
        
        # Create a high-confidence parsed date
        parsed_date = ParsedDate(
            date=date(2024, 1, 15),
            raw_value="2024-01-15",
            confidence=0.95,
            format_detected="ISO",
            errors=[]
        )
        
        metrics = calculator.calculate_field_confidence("date", parsed_date)
        
        assert metrics.ocr_confidence == 0.95
        assert metrics.normalization_confidence == 0.9
        assert metrics.error_penalty == 0.0
        assert metrics.overall_confidence > 0.8
    
    def test_calculate_field_confidence_low_confidence(self):
        """Test confidence calculation for low-confidence field."""
        calculator = ConfidenceCalculator()
        
        # Create a low-confidence parsed date with errors
        parsed_date = ParsedDate(
            date=None,
            raw_value="unclear text",
            confidence=0.3,
            format_detected=None,
            errors=[FieldError(
                field_name="date",
                error_type=FieldErrorType.INVALID_FORMAT,
                raw_value="unclear text",
                message="No valid date format detected"
            )]
        )
        
        metrics = calculator.calculate_field_confidence("date", parsed_date)
        
        assert metrics.ocr_confidence == 0.3
        assert metrics.normalization_confidence == 0.3
        assert metrics.error_penalty > 0.0
        assert metrics.overall_confidence < 0.5
    
    def test_calculate_line_item_confidence(self):
        """Test confidence calculation for line items."""
        calculator = ConfidenceCalculator()
        
        line_item = NormalizedLineItem(
            description="Test Product",
            quantity=Decimal("2.0"),
            unit="pcs",
            unit_price=Decimal("10.00"),
            line_total=Decimal("20.00"),
            vat_rate=Decimal("0.20"),
            vat_amount=Decimal("4.00"),
            raw_data={"description": "Test Product", "quantity": "2", "price": "10.00"},
            confidence=0.85,
            errors=[]
        )
        
        metrics = calculator.calculate_line_item_confidence(line_item)
        
        assert metrics.ocr_confidence == 0.85
        assert metrics.normalization_confidence == 0.9
        assert metrics.overall_confidence > 0.7
    
    def test_context_boost_calculation(self):
        """Test context-based confidence boost."""
        calculator = ConfidenceCalculator()
        
        # Test known supplier boost
        supplier = ParsedSupplier(
            name="ACME Corp Ltd",
            aliases=[],
            raw_value="ACME Corp Ltd",
            confidence=0.8,
            errors=[]
        )
        
        context = {"known_suppliers": ["ACME Corp Ltd", "Other Corp"]}
        metrics = calculator.calculate_field_confidence("supplier", supplier, context)
        
        assert metrics.context_boost > 0.0
    
    def test_cross_validation_score(self):
        """Test cross-validation score calculation."""
        calculator = ConfidenceCalculator()
        
        # Test currency cross-validation
        currency = ParsedCurrency(
            currency_code="GBP",
            symbol="£",
            raw_value="£",
            confidence=0.9,
            errors=[]
        )
        
        context = {"other_currencies": ["GBP", "USD"]}
        metrics = calculator.calculate_field_confidence("currency", currency, context)
        
        assert metrics.cross_validation_score > 0.0


class TestConfidenceRouter:
    """Test confidence routing functionality."""
    
    def test_route_field_auto_accept(self):
        """Test auto-accept routing for high-confidence field."""
        router = ConfidenceRouter({"confidence_threshold": 0.7})
        
        parsed_date = ParsedDate(
            date=date(2024, 1, 15),
            raw_value="2024-01-15",
            confidence=0.95,
            format_detected="ISO",
            errors=[]
        )
        
        result = router.route_field("date", parsed_date)
        
        assert result.routing_decision == RoutingDecision.AUTO_ACCEPT
        assert result.is_auto_acceptable()
        assert not result.needs_human_review()
    
    def test_route_field_needs_review(self):
        """Test needs-review routing for low-confidence field."""
        router = ConfidenceRouter({"confidence_threshold": 0.7})
        
        parsed_date = ParsedDate(
            date=None,
            raw_value="unclear",
            confidence=0.3,
            format_detected=None,
            errors=[FieldError(
                field_name="date",
                error_type=FieldErrorType.INVALID_FORMAT,
                raw_value="unclear",
                message="No valid date format detected"
            )]
        )
        
        result = router.route_field("date", parsed_date)
        
        assert result.routing_decision == RoutingDecision.NEEDS_REVIEW
        assert not result.is_auto_acceptable()
        assert result.needs_human_review()
    
    def test_route_line_item(self):
        """Test line item routing."""
        router = ConfidenceRouter({"confidence_threshold": 0.7})
        
        line_item = NormalizedLineItem(
            description="Test Product",
            quantity=Decimal("2.0"),
            unit="pcs",
            unit_price=Decimal("10.00"),
            line_total=Decimal("20.00"),
            vat_rate=None,
            vat_amount=None,
            raw_data={"description": "Test Product"},
            confidence=0.85,
            errors=[]
        )
        
        result = router.route_line_item(line_item)
        
        assert result.routing_decision == RoutingDecision.AUTO_ACCEPT
        assert result.is_auto_acceptable()
    
    def test_custom_field_thresholds(self):
        """Test custom field-specific thresholds."""
        config = {
            "confidence_threshold": 0.7,
            "field_thresholds": {
                "date": 0.8,
                "currency": 0.6
            }
        }
        router = ConfidenceRouter(config)
        
        # Test date with threshold 0.8
        parsed_date = ParsedDate(
            date=date(2024, 1, 15),
            raw_value="2024-01-15",
            confidence=0.75,  # Below 0.8 threshold
            format_detected="ISO",
            errors=[]
        )
        
        result = router.route_field("date", parsed_date)
        assert result.routing_decision == RoutingDecision.NEEDS_REVIEW
        assert result.threshold_used == 0.8
        
        # Test currency with threshold 0.6
        parsed_currency = ParsedCurrency(
            currency_code="GBP",
            symbol="£",
            raw_value="£",
            confidence=0.65,  # Above 0.6 threshold
            errors=[]
        )
        
        result = router.route_field("currency", parsed_currency)
        assert result.routing_decision == RoutingDecision.AUTO_ACCEPT
        assert result.threshold_used == 0.6


class TestConfidenceRoutingIntegration:
    """Integration tests for confidence routing with realistic data."""
    
    def test_high_quality_invoice_routing(self):
        """Test routing for high-quality, clear invoice data."""
        # Create high-quality invoice data
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
            "invoice_id": "test-invoice-001",
            "region": "UK",
            "known_suppliers": ["ACME Corporation Ltd"],
            "default_currency": "GBP"
        }
        
        normalizer = FieldNormalizer()
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
        
        # Should have high confidence and mostly auto-accepted
        assert routing_result.overall_confidence > 0.7
        assert len(routing_result.auto_accepted_fields) > 0
        assert len(routing_result.review_candidates) == 0 or len(routing_result.review_candidates) < len(routing_result.auto_accepted_fields)
    
    def test_poor_quality_invoice_routing(self):
        """Test routing for poor-quality, unclear invoice data."""
        # Create poor-quality invoice data with ambiguous fields
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
            "invoice_id": "test-invoice-002",
            "region": "unknown"
        }
        
        normalizer = FieldNormalizer()
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
        
        # Should have low confidence and mostly needs review
        assert routing_result.overall_confidence < 0.7
        assert len(routing_result.review_candidates) > 0
        assert len(routing_result.auto_accepted_fields) < len(routing_result.review_candidates)
    
    def test_mixed_quality_invoice_routing(self):
        """Test routing for invoice with mixed quality fields."""
        # Create mixed-quality invoice data
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
            "invoice_id": "test-invoice-003",
            "region": "UK",
            "known_suppliers": ["ACME Corporation Ltd"],
            "default_currency": "GBP"
        }
        
        normalizer = FieldNormalizer()
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
        
        # Should have mixed results
        assert len(routing_result.auto_accepted_fields) > 0
        assert len(routing_result.review_candidates) > 0
        
        # Clear fields should be auto-accepted
        assert "supplier_name" in routing_result.auto_accepted_fields or "supplier" in routing_result.auto_accepted_fields
        assert "currency" in routing_result.auto_accepted_fields
        
        # Unclear fields should need review
        review_field_names = [candidate.field_name for candidate in routing_result.review_candidates]
        assert any("date" in name for name in review_field_names)
    
    def test_perturbed_document_routing(self):
        """Test routing for documents with OCR perturbations."""
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
            "invoice_id": "test-invoice-004",
            "region": "UK",
            "known_suppliers": ["ACME Corp Ltd"],
            "default_currency": "GBP"
        }
        
        normalizer = FieldNormalizer()
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
        
        # Should detect perturbations and route appropriately
        assert routing_result.overall_confidence < 0.9  # Not perfect due to perturbations
        
        # Some fields should be auto-accepted (clear ones)
        assert len(routing_result.auto_accepted_fields) > 0
        
        # Some fields should need review (perturbed ones)
        assert len(routing_result.review_candidates) > 0
        
        # Check that specific perturbed fields are flagged
        review_field_names = [candidate.field_name for candidate in routing_result.review_candidates]
        assert any("invoice_number" in name or "date" in name for name in review_field_names)
    
    def test_error_handling_routing(self):
        """Test routing behavior when confidence calculation fails."""
        # Create data that might cause calculation errors
        raw_data = {
            "supplier": None,  # None value
            "invoice_number": "",  # Empty string
            "invoice_date": "invalid date format",
            "currency": "INVALID_CURRENCY",
            "subtotal": "not a number",
            "tax_amount": "also not a number",
            "total_amount": "definitely not a number",
            "line_items": []  # Empty line items
        }
        
        context = {
            "invoice_id": "test-invoice-005",
            "region": "unknown"
        }
        
        normalizer = FieldNormalizer()
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
        
        # Should handle errors gracefully
        assert routing_result.error_count >= 0
        assert routing_result.overall_confidence < 0.5
        
        # Most fields should need review due to errors
        assert len(routing_result.review_candidates) > 0
    
    def test_audit_logging_verification(self):
        """Test that audit logging is working correctly."""
        # Capture log messages
        log_capture = []
        
        class LogCapture(logging.Handler):
            def emit(self, record):
                log_capture.append(record.getMessage())
        
        # Add handler to the confidence router logger
        router_logger = logging.getLogger("owlin.normalization.confidence_routing")
        handler = LogCapture()
        router_logger.addHandler(handler)
        router_logger.setLevel(logging.INFO)
        
        try:
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
                "invoice_id": "test-invoice-006",
                "region": "UK",
                "known_suppliers": ["ACME Corporation Ltd"],
                "default_currency": "GBP"
            }
            
            normalizer = FieldNormalizer()
            normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
            
            # Check that routing decisions were logged
            routing_logs = [log for log in log_capture if "routed as" in log]
            assert len(routing_logs) > 0
            
            # Check that overall result was logged
            summary_logs = [log for log in log_capture if "routing completed" in log]
            assert len(summary_logs) > 0
            
        finally:
            router_logger.removeHandler(handler)


class TestReviewCandidateGeneration:
    """Test review candidate generation and serialization."""
    
    def test_review_candidate_creation(self):
        """Test creation of review candidates."""
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
        
        assert candidate.field_name == "date"
        assert candidate.needs_human_review()
        assert len(candidate.error_details) > 0
    
    def test_review_candidate_serialization(self):
        """Test review candidate JSON serialization."""
        router = ConfidenceRouter()
        
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
        
        # Test serialization
        candidate_dict = candidate.to_dict()
        
        assert candidate_dict["field_name"] == "date"
        assert candidate_dict["field_type"] == "ParsedDate"
        assert candidate_dict["raw_value"] == "unclear date"
        assert candidate_dict["normalized_value"] is None
        assert candidate_dict["confidence"] < 0.7
        assert candidate_dict["routing_decision"] == "needs_review"
        assert len(candidate_dict["error_details"]) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_invoice_data(self):
        """Test routing with completely empty invoice data."""
        raw_data = {}
        context = {"invoice_id": "empty-invoice"}
        
        normalizer = FieldNormalizer()
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
        
        # Should handle empty data gracefully
        assert routing_result.overall_confidence < 0.5
        assert len(routing_result.auto_accepted_fields) == 0
        assert len(routing_result.review_candidates) >= 0
    
    def test_malformed_data(self):
        """Test routing with malformed data structures."""
        raw_data = {
            "supplier": 123,  # Wrong type
            "invoice_number": ["not", "a", "string"],  # Wrong type
            "line_items": "not a list",  # Wrong type
        }
        
        context = {"invoice_id": "malformed-invoice"}
        
        normalizer = FieldNormalizer()
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
        
        # Should handle malformed data gracefully
        assert routing_result.error_count >= 0
        assert routing_result.overall_confidence < 0.5
    
    def test_extremely_large_data(self):
        """Test routing with extremely large data structures."""
        # Create invoice with many line items
        line_items = []
        for i in range(1000):  # 1000 line items
            line_items.append({
                "description": f"Item {i}",
                "quantity": "1",
                "unit": "pcs",
                "unit_price": "10.00",
                "line_total": "10.00"
            })
        
        raw_data = {
            "supplier": "ACME Corporation Ltd",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-01-15",
            "currency": "GBP",
            "subtotal": "£10000.00",
            "tax_amount": "£2000.00",
            "total_amount": "£12000.00",
            "line_items": line_items
        }
        
        context = {"invoice_id": "large-invoice"}
        
        normalizer = FieldNormalizer()
        normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)
        
        # Should handle large data structures
        assert routing_result.processing_time > 0
        assert len(routing_result.review_candidates) >= 0
    
    def test_confidence_calculation_failure(self):
        """Test behavior when confidence calculation fails."""
        # Create a calculator that will fail
        class FailingCalculator(ConfidenceCalculator):
            def calculate_field_confidence(self, field_name, parsed_result, context=None):
                raise Exception("Confidence calculation failed")
        
        # Create router with failing calculator
        router = ConfidenceRouter()
        router.calculator = FailingCalculator()
        
        parsed_date = ParsedDate(
            date=date(2024, 1, 15),
            raw_value="2024-01-15",
            confidence=0.95,
            format_detected="ISO",
            errors=[]
        )
        
        result = router.route_field("date", parsed_date)
        
        # Should handle failure gracefully
        assert result.routing_decision == RoutingDecision.ERROR
        assert len(result.error_details) > 0
        assert "Confidence calculation failed" in result.error_details[0]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
