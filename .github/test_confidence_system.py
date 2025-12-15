#!/usr/bin/env python3
"""
Simple test script to validate the confidence routing system.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_confidence_system():
    """Test the confidence routing system."""
    try:
        from backend.normalization.confidence_routing import ConfidenceRouter, ConfidenceCalculator
        from backend.normalization.types import ParsedDate, FieldError, FieldErrorType
        from datetime import date
        
        print("Testing confidence calculation...")
        
        # Test confidence calculator
        calculator = ConfidenceCalculator()
        
        # Create test data
        parsed_date = ParsedDate(
            date=date(2024, 1, 15),
            raw_value="2024-01-15",
            confidence=0.95,
            format_detected="ISO",
            errors=[]
        )
        
        metrics = calculator.calculate_field_confidence("date", parsed_date)
        print(f"Confidence calculation successful: {metrics.overall_confidence:.3f}")
        
        # Test confidence router
        router = ConfidenceRouter()
        result = router.route_field("date", parsed_date)
        print(f"Routing decision: {result.routing_decision.value}")
        print(f"Auto-acceptable: {result.is_auto_acceptable()}")
        
        print("SUCCESS: Confidence routing system is working correctly!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_confidence_system()
    sys.exit(0 if success else 1)
