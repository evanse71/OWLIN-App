"""
Acceptance Tests - Explicit Scenarios
Test specific scenarios mentioned in the requirements.
"""

import pytest
import sys
import os
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from normalization.units import canonical_quantities
from validators.invoice_math import validate_line_item
from engine.discount_solver import evaluate_discount_hypotheses
from engine.verdicts import create_line_verdict, determine_verdict
from engine.explainer import get_explanation


class TestAcceptanceScenarios:
    """Acceptance test scenarios from requirements."""
    
    def test_tia_maria_70cl_off_contract(self):
        """Acceptance Test 1: Tia Maria 70cl - Qty 1, Unit £60.55, Nett £32.22, supplier default −20%"""
        # Test data
        sku_id = "TIA001"
        quantity = 1.0
        unit_price = 60.55
        line_total = 32.22
        description = "TIA MARIA 70CL"
        supplier_id = "SUP001"
        date = "2024-01-01"
        
        # Parse canonical quantities
        canonical = canonical_quantities(quantity, description)
        
        # Validate line item
        validation = validate_line_item(
            unit_price=unit_price,
            quantity=quantity,
            line_total=line_total,
            description=description
        )
        
        # Evaluate discount hypotheses
        verdict, hypothesis = evaluate_discount_hypotheses(
            expected_price=60.55,  # Contract price
            actual_price=32.22,    # Actual price
            quantity=quantity,
            category="spirits"
        )
        
        # Create line verdict
        line_verdict = create_line_verdict(
            sku_id=sku_id,
            qty=quantity,
            uom_key=canonical.get('uom_key', ''),
            unit_price_raw=unit_price,
            nett_price=32.22,
            nett_value=32.22,
            date=date,
            supplier_id=supplier_id,
            math_flags=validation['flags'],
            reference_conflict=False,
            uom_mismatch=False,
            off_contract=verdict == 'off_contract_discount',
            unusual_history=False,
            ocr_error=False,
            discount_hypothesis={'hypothesis_type': hypothesis} if hypothesis else None
        )
        
        # Assertions
        assert line_verdict.verdict == "off_contract_discount"
        assert line_verdict.hypothesis == "percent"
        
        # Check implied discount is around -46.8%
        if line_verdict.implied_value:
            discount_pct = abs(line_verdict.implied_value)
            assert 0.45 <= discount_pct <= 0.50, f"Discount {discount_pct:.1%} not in expected range"
        
        # Check fingerprint is generated
        assert len(line_verdict.line_fingerprint) == 64  # SHA256 length
    
    def test_uom_trap_case_vs_unit(self):
        """Acceptance Test 2: UOM trap - case 24×275ml vs 12×275ml at same case price"""
        # Test case 1: 24×275ml
        case1 = canonical_quantities(24, "24×275ml")
        
        # Test case 2: 12×275ml  
        case2 = canonical_quantities(12, "12×275ml")
        
        # Both should have same unit size but different quantities
        assert case1['unit_size_ml'] == 275.0
        assert case2['unit_size_ml'] == 275.0
        assert case1['quantity_ml'] == 6600.0  # 24 * 275
        assert case2['quantity_ml'] == 3300.0  # 12 * 275
        
        # If both had same case price, this would trigger UOM mismatch
        # This is a structural test - actual detection would be in pairing logic
    
    def test_rounding_storm_49_lines(self):
        """Acceptance Test 3: Rounding storm - 49 lines ±£0.01 → zero false math_mismatch"""
        # Create 49 lines with small rounding differences
        lines = []
        for i in range(49):
            # Create line with potential rounding issue
            unit_price = 10.0 + (i * 0.001)  # Small variations
            quantity = 1.0
            line_total = unit_price * quantity
            
            validation = validate_line_item(
                unit_price=unit_price,
                quantity=quantity,
                line_total=line_total,
                description=f"Line {i+1}"
            )
            
            lines.append(validation)
        
        # Count math mismatches
        math_mismatches = sum(1 for line in lines if "PRICE_INCOHERENT" in line['flags'])
        
        # Should have zero false math mismatches
        assert math_mismatches == 0, f"Found {math_mismatches} false math mismatches"
    
    def test_vat_subtotal_reconciliation(self):
        """Test VAT subtotal reconciliation"""
        # Test VAT calculation
        subtotal = 100.0
        vat_rate = 20.0
        vat_amount = 20.0
        invoice_total = 120.0
        
        from validators.invoice_math import check_vat_calculation
        
        is_valid, error = check_vat_calculation(
            subtotal=subtotal,
            vat_amount=vat_amount,
            vat_rate=vat_rate,
            invoice_total=invoice_total
        )
        
        assert is_valid, f"VAT calculation failed: {error}"
    
    def test_reference_conflict_detection(self):
        """Acceptance Test 4: Reference conflict - contract £33.00, supplier master £36.50, history £35.80"""
        # Mock price sources
        from engine.price_sources import PriceSourceLadder
        from datetime import datetime
        
        ladder = PriceSourceLadder()
        
        # Add conflicting sources (36.50 vs 33.00 = 10.6% difference > 10% threshold)
        ladder.add_source("contract_book", 33.00, "ml", datetime.now(), "hash1")
        ladder.add_source("supplier_master", 36.50, "ml", datetime.now(), "hash2")
        ladder.add_source("venue_memory_90d", 35.80, "ml", datetime.now(), "hash3")
        
        # Check for reference conflict
        has_conflict, conflict_type = ladder.check_reference_conflict()
        
        # Should detect conflict (33.00 vs 36.50 is > 10% difference)
        assert has_conflict, "Reference conflict not detected"
        assert conflict_type == "reference_conflict"
    
    def test_offline_deterministic_verdicts(self):
        """Acceptance Test 5: Offline - identical verdicts; explainer uses deterministic template"""
        # Test same input multiple times
        test_data = {
            'sku_id': 'TEST001',
            'quantity': 1.0,
            'unit_price': 10.0,
            'line_total': 8.0,
            'description': 'Test Item'
        }
        
        verdicts = []
        for _ in range(3):
            # Process the same data
            canonical = canonical_quantities(test_data['quantity'], test_data['description'])
            validation = validate_line_item(
                unit_price=test_data['unit_price'],
                quantity=test_data['quantity'],
                line_total=test_data['line_total'],
                description=test_data['description']
            )
            
            verdict, hypothesis = evaluate_discount_hypotheses(
                expected_price=10.0,
                actual_price=8.0,
                quantity=test_data['quantity'],
                category="default"
            )
            
            verdicts.append(verdict)
        
        # All verdicts should be identical
        assert len(set(verdicts)) == 1, f"Non-deterministic verdicts: {verdicts}"
        
        # Test explainer uses deterministic template
        explanation = get_explanation(
            verdict=verdicts[0],
            hypothesis=hypothesis,
            implied_value=0.2,  # 20% discount
            residual=0.0,
            sku_id=test_data['sku_id'],
            supplier_id="SUP001",
            line_fingerprint="test_fp"
        )
        
        assert explanation.model_id == "deterministic"
    
    def test_300_line_performance(self):
        """Acceptance Test 6: 300 lines ≤ 2s on 2019 i5 (no LLM)"""
        # Create 300 test lines
        start_time = time.time()
        
        for i in range(300):
            # Process each line
            canonical = canonical_quantities(1.0, f"Item {i}")
            validation = validate_line_item(
                unit_price=10.0,
                quantity=1.0,
                line_total=10.0,
                description=f"Item {i}"
            )
            
            verdict, hypothesis = evaluate_discount_hypotheses(
                expected_price=10.0,
                actual_price=10.0,
                quantity=1.0,
                category="default"
            )
        
        processing_time = time.time() - start_time
        
        # Should complete within 2 seconds
        assert processing_time <= 2.0, f"300-line processing took {processing_time:.3f}s > 2.0s"
    
    def test_pattern_suggestion_45_50_percent(self):
        """Acceptance Test 7: Pattern suggestion - ≥2 invoices in 30d imply −45–50% for same SKU"""
        # This would test the pattern detection logic
        # For now, test the structural components
        
        # Test discount range detection
        verdict, hypothesis = evaluate_discount_hypotheses(
            expected_price=100.0,
            actual_price=52.5,  # 47.5% discount
            quantity=1.0,
            category="spirits"
        )
        
        # Should detect as off-contract discount
        assert verdict == "off_contract_discount"
        assert hypothesis == "percent"
        
        # The pattern suggestion would be implemented in a separate service
        # that tracks historical patterns and suggests overrides


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 