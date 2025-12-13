"""
Tests for invoice math validation including ±1p and ±1% tolerance checks
"""
import pytest
import sys
sys.path.insert(0, 'backend')

from backend.validators.invoice_math import (
    validate_line_item, validate_invoice_totals, check_price_coherence,
    check_vat_calculation, check_pack_descriptor, banker_round
)

class TestInvoiceMathValidation:
    
    def test_price_coherence_within_tolerance(self):
        """Test price coherence within ±1p and ±1% tolerance"""
        # Exactly correct
        is_valid, error = check_price_coherence(10.0, 2.0, 20.0)
        assert is_valid == True
        assert error is None
        
        # Within 1p tolerance
        is_valid, error = check_price_coherence(10.0, 2.0, 20.01)  # 1p over
        assert is_valid == True
        
        # Within 1% tolerance
        is_valid, error = check_price_coherence(10.0, 2.0, 19.80)  # 1% under
        assert is_valid == True
    
    def test_price_incoherent_exceeds_both_tolerances(self):
        """Test PRICE_INCOHERENT only when exceeds BOTH ±1p AND ±1%"""
        # Exceeds 1p but not 1% (should pass)
        is_valid, error = check_price_coherence(100.0, 1.0, 100.02)  # 2p on £100 = 0.02%
        assert is_valid == True
        
        # Exceeds 1% but not 1p (should pass)  
        is_valid, error = check_price_coherence(0.50, 1.0, 0.495)  # 1% on 50p = 0.5p
        assert is_valid == True
        
        # Exceeds BOTH 1p AND 1% (should fail)
        is_valid, error = check_price_coherence(10.0, 2.0, 18.0)  # £2 and 10% difference
        assert is_valid == False
        assert error == "PRICE_INCOHERENT"
    
    def test_pack_mismatch_detection(self):
        """Test pack quantity mismatch detection"""
        # Correct pack calculation
        is_valid, error = check_pack_descriptor(24.0, 2.0, 12.0, "2×12 pack")
        assert is_valid == True
        
        # Pack mismatch
        is_valid, error = check_pack_descriptor(20.0, 2.0, 12.0, "2×12 pack")  # Should be 24
        assert is_valid == False
        assert error == "PACK_MISMATCH"
        
        # Partial pack descriptor
        is_valid, error = check_pack_descriptor(24.0, 2.0, None, "2 packs")
        assert is_valid == False
        assert error == "PACK_DESCRIPTOR_PARTIAL"
    
    def test_vat_reconciliation_per_line(self):
        """Test VAT reconciliation when per-line VAT rates available"""
        # Correct VAT calculation
        is_valid, error = check_vat_calculation(100.0, 20.0, 20.0, 120.0)
        assert is_valid == True
        
        # VAT mismatch
        is_valid, error = check_vat_calculation(100.0, 25.0, 20.0, 120.0)  # Wrong VAT amount
        assert is_valid == False
        assert error == "VAT_MISMATCH"
    
    def test_vat_reconciliation_subtotal(self):
        """Test VAT reconciliation using subtotal method"""
        # Correct subtotal + VAT = total
        is_valid, error = check_vat_calculation(100.0, 20.0, None, 120.0)
        assert is_valid == True
        
        # Subtotal mismatch
        is_valid, error = check_vat_calculation(100.0, 20.0, None, 125.0)  # Wrong total
        assert is_valid == False
        assert error == "SUBTOTAL_MISMATCH"
    
    def test_negative_adjustment_detection(self):
        """Test detection of negative line adjustments"""
        from backend.validators.invoice_math import check_negative_adjustments
        
        # No negative lines
        is_valid, error = check_negative_adjustments([10.0, 20.0, 30.0])
        assert is_valid == True
        
        # Has negative adjustment
        is_valid, error = check_negative_adjustments([10.0, -5.0, 30.0])
        assert is_valid == False
        assert error == "NEGATIVE_ADJUSTMENT_PRESENT"
    
    def test_foc_line_handling(self):
        """Test FOC (free of charge) line handling"""
        # FOC with zero price and total
        is_valid, error = check_price_coherence(0.0, 1.0, 0.0, "FOC sample")
        assert is_valid == True
        assert error == "FOC_LINE"
        
        # FOC with unit price but zero total
        is_valid, error = check_price_coherence(10.0, 1.0, 0.0, "Free sample FOC")
        assert is_valid == True
        assert error == "FOC_LINE"
    
    def test_bankers_rounding(self):
        """Test banker's rounding implementation"""
        assert banker_round(2.125, 2) == 2.12  # Round to even
        assert banker_round(2.135, 2) == 2.14  # Round to even
        assert banker_round(2.5, 0) == 2.0     # Round to even
        assert banker_round(3.5, 0) == 4.0     # Round to even
    
    def test_line_item_validation_comprehensive(self):
        """Test comprehensive line item validation"""
        # Valid line item
        result = validate_line_item(10.0, 2.0, 20.0, "Test item")
        assert result['valid'] == True
        assert result['flags'] == []
        
        # Price incoherent line item
        result = validate_line_item(10.0, 2.0, 15.0, "Test item")  # £5 and 25% off
        assert result['valid'] == False
        assert "PRICE_INCOHERENT" in result['flags']
        
        # FOC line item
        result = validate_line_item(0.0, 1.0, 0.0, "FOC sample")
        assert "FOC_LINE" in result['flags']
        # FOC lines are considered valid
        assert result['valid'] == True
    
    def test_invoice_totals_validation_comprehensive(self):
        """Test comprehensive invoice totals validation"""
        # Valid invoice
        result = validate_invoice_totals(100.0, 20.0, 20.0, 120.0, [50.0, 30.0, 20.0])
        assert result['valid'] == True
        assert result['flags'] == []
        
        # VAT mismatch
        result = validate_invoice_totals(100.0, 25.0, 20.0, 120.0, [50.0, 30.0, 20.0])
        assert result['valid'] == False
        assert "VAT_MISMATCH" in result['flags']
        
        # Negative adjustment present
        result = validate_invoice_totals(100.0, 20.0, None, 120.0, [50.0, -10.0, 60.0])
        assert result['valid'] == False
        assert "NEGATIVE_ADJUSTMENT_PRESENT" in result['flags']
    
    def test_deliberate_2_percent_drift_triggers_flag(self):
        """Test that deliberate 2% drift triggers PRICE_INCOHERENT"""
        # 2% drift on significant amount (exceeds both 1p and 1%)
        is_valid, error = check_price_coherence(50.0, 1.0, 49.0)  # £1 and 2% difference
        assert is_valid == False
        assert error == "PRICE_INCOHERENT"
        
        # Large discount (>30%) should not trigger PRICE_INCOHERENT
        is_valid, error = check_price_coherence(60.55, 1.0, 32.22)  # Tia Maria case
        assert is_valid == True  # Recognized as discount, not math error

if __name__ == "__main__":
    pytest.main([__file__]) 