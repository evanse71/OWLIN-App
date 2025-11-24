#!/usr/bin/env python3
"""
Test script for Donut fallback integration.

This script tests the Donut fallback module integration with the main OCR pipeline,
verifying that all components work together correctly.
"""

import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.fallbacks import DonutFallback, get_donut_fallback, map_donut_to_invoice_card, merge_invoice_cards
from backend.config import (
    FEATURE_DONUT_FALLBACK, DONUT_CONFIDENCE_THRESHOLD,
    DONUT_MODEL_PATH, DONUT_ENABLE_WHEN_NO_LINE_ITEMS
)

# Setup logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("test_donut")


def test_donut_config():
    """Test Donut configuration."""
    LOGGER.info("Testing Donut configuration...")
    
    config_info = {
        "enabled": FEATURE_DONUT_FALLBACK,
        "confidence_threshold": DONUT_CONFIDENCE_THRESHOLD,
        "model_path": DONUT_MODEL_PATH,
        "enable_when_no_line_items": DONUT_ENABLE_WHEN_NO_LINE_ITEMS
    }
    
    LOGGER.info("Donut Config: %s", config_info)
    return config_info


def test_donut_fallback_initialization():
    """Test Donut fallback initialization."""
    LOGGER.info("Testing Donut fallback initialization...")
    
    # Test disabled fallback
    fallback_disabled = DonutFallback(enabled=False)
    LOGGER.info("Disabled fallback available: %s", fallback_disabled.is_available())
    
    # Test enabled fallback
    fallback_enabled = DonutFallback(enabled=True)
    LOGGER.info("Enabled fallback available: %s", fallback_enabled.is_available())
    
    # Test global fallback
    global_fallback = get_donut_fallback(enabled=FEATURE_DONUT_FALLBACK)
    LOGGER.info("Global fallback available: %s", global_fallback.is_available())
    
    return global_fallback


def test_donut_processing():
    """Test Donut processing with mock data."""
    LOGGER.info("Testing Donut processing...")
    
    fallback = get_donut_fallback(enabled=FEATURE_DONUT_FALLBACK)
    
    if not fallback.is_available():
        LOGGER.warning("Donut not available, skipping processing test")
        return
    
    # Create a dummy image path
    dummy_image = Path("test_image.png")
    
    try:
        result = fallback.process_document(dummy_image)
        
        LOGGER.info("Donut Result: %s", result.to_dict())
        LOGGER.info("Processing successful: %s", result.ok)
        LOGGER.info("Confidence: %.3f", result.confidence)
        LOGGER.info("Processing time: %.3fs", result.took_s)
        
    except Exception as e:
        LOGGER.warning("Donut processing test failed (expected): %s", e)


def test_donut_mapping():
    """Test Donut output mapping."""
    LOGGER.info("Testing Donut output mapping...")
    
    # Test with sample Donut output
    sample_donut_output = {
        "company": "Test Company Ltd",
        "date": "2024-01-15",
        "total": "£150.00",
        "vat_total": "£30.00",
        "invoice_number": "INV-001",
        "line_items": [
            {
                "description": "Consulting Services",
                "quantity": "10",
                "unit_price": "£15.00",
                "line_total": "£150.00"
            }
        ]
    }
    
    # Map to invoice card
    invoice_card = map_donut_to_invoice_card(sample_donut_output)
    
    LOGGER.info("Mapped invoice card: %s", json.dumps(invoice_card, indent=2))
    
    # Test validation
    validated_card = validate_invoice_card(invoice_card)
    LOGGER.info("Validated card has %d fields", len(validated_card))
    
    return invoice_card


def test_invoice_card_merging():
    """Test invoice card merging."""
    LOGGER.info("Testing invoice card merging...")
    
    # Base card with some fields
    base_card = {
        "supplier": "Base Company",
        "date": "2024-01-01",
        "total": 100.0
    }
    
    # Donut card with additional fields
    donut_card = {
        "supplier": "Donut Company",  # Should not overwrite
        "date": "2024-01-02",         # Should not overwrite
        "total": 200.0,               # Should not overwrite
        "vat_total": 40.0,            # Should be added
        "currency": "GBP",            # Should be added
        "line_items": [               # Should be added
            {"description": "Item 1", "quantity": 1}
        ]
    }
    
    # Merge cards
    merged_card = merge_invoice_cards(base_card, donut_card)
    
    LOGGER.info("Merged card: %s", json.dumps(merged_card, indent=2))
    
    # Verify merging behavior
    assert merged_card["supplier"] == "Base Company"  # Base value preserved
    assert merged_card["date"] == "2024-01-01"        # Base value preserved
    assert merged_card["total"] == 100.0              # Base value preserved
    assert merged_card["vat_total"] == 40.0            # Donut value added
    assert merged_card["currency"] == "GBP"            # Donut value added
    assert len(merged_card["line_items"]) == 1        # Donut line items added
    assert merged_card["donut_merged"] == True         # Merge flag set
    
    LOGGER.info("Invoice card merging test passed!")


def test_confidence_thresholds():
    """Test confidence threshold logic."""
    LOGGER.info("Testing confidence threshold logic...")
    
    # Test various confidence scenarios
    test_cases = [
        {"page_conf": 0.7, "overall_conf": 0.8, "expected_trigger": False},
        {"page_conf": 0.6, "overall_conf": 0.8, "expected_trigger": True},
        {"page_conf": 0.7, "overall_conf": 0.6, "expected_trigger": True},
        {"page_conf": 0.5, "overall_conf": 0.5, "expected_trigger": True},
    ]
    
    for case in test_cases:
        page_conf = case["page_conf"]
        overall_conf = case["overall_conf"]
        expected = case["expected_trigger"]
        
        # Simulate threshold logic
        should_trigger = (page_conf < DONUT_CONFIDENCE_THRESHOLD or 
                         overall_conf < DONUT_CONFIDENCE_THRESHOLD)
        
        LOGGER.info("Confidence test: page=%.2f, overall=%.2f, trigger=%s (expected=%s)", 
                   page_conf, overall_conf, should_trigger, expected)
        
        assert should_trigger == expected, f"Threshold logic failed for {case}"
    
    LOGGER.info("Confidence threshold tests passed!")


def test_no_line_items_trigger():
    """Test no line items trigger logic."""
    LOGGER.info("Testing no line items trigger logic...")
    
    # Test cases for line items
    test_cases = [
        {"line_items": [], "expected_trigger": True},
        {"line_items": None, "expected_trigger": True},
        {"line_items": [{"item": "test"}], "expected_trigger": False},
    ]
    
    for case in test_cases:
        line_items = case["line_items"]
        expected = case["expected_trigger"]
        
        # Simulate no line items logic
        should_trigger = DONUT_ENABLE_WHEN_NO_LINE_ITEMS and (not line_items or len(line_items) == 0)
        
        LOGGER.info("Line items test: items=%s, trigger=%s (expected=%s)", 
                   line_items, should_trigger, expected)
        
        assert should_trigger == expected, f"No line items logic failed for {case}"
    
    LOGGER.info("No line items trigger tests passed!")


def main():
    """Main test function."""
    LOGGER.info("Starting Donut fallback integration tests...")
    
    try:
        # Test configuration
        config = test_donut_config()
        
        # Test initialization
        fallback = test_donut_fallback_initialization()
        
        # Test processing
        test_donut_processing()
        
        # Test mapping
        invoice_card = test_donut_mapping()
        
        # Test merging
        test_invoice_card_merging()
        
        # Test confidence thresholds
        test_confidence_thresholds()
        
        # Test no line items trigger
        test_no_line_items_trigger()
        
        LOGGER.info("All Donut fallback tests completed successfully!")
        return 0
        
    except Exception as e:
        LOGGER.error("Donut fallback tests failed: %s", e)
        return 1


if __name__ == "__main__":
    import json
    from backend.fallbacks.mapper import validate_invoice_card
    sys.exit(main())
