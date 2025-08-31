"""
Unit Tests for Invoice Mathematical Validation
Test deterministic mathematical validation of invoice line items.
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from validators.invoice_math import (
    check_price_coherence, check_pack_descriptor, check_vat_calculation,
    check_negative_adjustments, validate_line_item, validate_invoice_totals,
    calculate_line_fingerprint, banker_round
)


class TestPriceCoherence:
    """Test price coherence validation."""
    
    def test_exact_match(self):
        """Test exact price match"""
        is_valid, error = check_price_coherence(10.0, 5.0, 50.0)
        assert is_valid
        assert error is None
    
    def test_within_tolerance_pennies(self):
        """Test within 1p tolerance"""
        is_valid, error = check_price_coherence(10.0, 5.0, 50.01)
        assert is_valid
        assert error is None
    
    def test_within_tolerance_percentage(self):
        """Test within 1% tolerance"""
        is_valid, error = check_price_coherence(10.0, 5.0, 50.5)  # 1% of 50
        assert is_valid
        assert error is None
    
    def test_exceeds_both_tolerances(self):
        """Test exceeds both 1p and 1% tolerances"""
        is_valid, error = check_price_coherence(10.0, 5.0, 55.0)  # 5p difference, 10% difference
        assert not is_valid
        assert error == "PRICE_INCOHERENT"
    
    def test_foc_line(self):
        """Test FOC line detection"""
        is_valid, error = check_price_coherence(0.0, 5.0, 0.0, "FOC")
        assert is_valid
        assert error == "FOC_LINE"
    
    def test_free_line(self):
        """Test free line detection"""
        is_valid, error = check_price_coherence(10.0, 5.0, 0.0, "Free sample")
        assert is_valid
        assert error == "FOC_LINE"
    
    def test_zero_expected(self):
        """Test zero expected price"""
        is_valid, error = check_price_coherence(0.0, 5.0, 0.0)
        assert is_valid
        assert error == "FOC_LINE"


class TestPackDescriptor:
    """Test pack descriptor validation."""
    
    def test_valid_pack_info(self):
        """Test valid pack information"""
        is_valid, error = check_pack_descriptor(24.0, 2.0, 12.0, "24 units")
        assert is_valid
        assert error is None
    
    def test_pack_mismatch(self):
        """Test pack mismatch"""
        is_valid, error = check_pack_descriptor(24.0, 2.0, 10.0, "24 units")  # 2*10 != 24
        assert not is_valid
        assert error == "PACK_MISMATCH"
    
    def test_partial_pack_info_packs_only(self):
        """Test partial pack info - packs only"""
        is_valid, error = check_pack_descriptor(24.0, 2.0, None, "24 units")
        assert not is_valid
        assert error == "PACK_DESCRIPTOR_PARTIAL"
    
    def test_partial_pack_info_units_only(self):
        """Test partial pack info - units only"""
        is_valid, error = check_pack_descriptor(24.0, None, 12.0, "24 units")
        assert not is_valid
        assert error == "PACK_DESCRIPTOR_PARTIAL"
    
    def test_no_pack_info(self):
        """Test no pack information"""
        is_valid, error = check_pack_descriptor(24.0, None, None, "24 units")
        assert is_valid
        assert error is None


class TestVATCalculation:
    """Test VAT calculation validation."""
    
    def test_valid_vat_calculation(self):
        """Test valid VAT calculation"""
        is_valid, error = check_vat_calculation(100.0, 20.0, 20.0, 120.0)
        assert is_valid
        assert error is None
    
    def test_vat_mismatch(self):
        """Test VAT mismatch"""
        is_valid, error = check_vat_calculation(100.0, 25.0, 20.0, 125.0)  # Should be 20.0 VAT
        assert not is_valid
        assert error == "VAT_MISMATCH"
    
    def test_subtotal_mismatch(self):
        """Test subtotal mismatch"""
        is_valid, error = check_vat_calculation(100.0, 20.0, None, 125.0)  # 100+20 != 125
        assert not is_valid
        assert error == "SUBTOTAL_MISMATCH"
    
    def test_no_vat_rate(self):
        """Test no VAT rate provided"""
        is_valid, error = check_vat_calculation(100.0, 20.0, None, 120.0)
        assert is_valid
        assert error is None
    
    def test_zero_vat(self):
        """Test zero VAT"""
        is_valid, error = check_vat_calculation(100.0, 0.0, 0.0, 100.0)
        assert is_valid
        assert error is None


class TestNegativeAdjustments:
    """Test negative adjustment detection."""
    
    def test_no_negative_lines(self):
        """Test no negative lines"""
        is_valid, error = check_negative_adjustments([10.0, 20.0, 30.0])
        assert is_valid
        assert error is None
    
    def test_negative_line_present(self):
        """Test negative line present"""
        is_valid, error = check_negative_adjustments([10.0, -5.0, 30.0])
        assert not is_valid
        assert error == "NEGATIVE_ADJUSTMENT_PRESENT"
    
    def test_all_negative_lines(self):
        """Test all negative lines"""
        is_valid, error = check_negative_adjustments([-10.0, -5.0, -30.0])
        assert not is_valid
        assert error == "NEGATIVE_ADJUSTMENT_PRESENT"
    
    def test_zero_lines(self):
        """Test zero lines"""
        is_valid, error = check_negative_adjustments([0.0, 10.0, 0.0])
        assert is_valid
        assert error is None


class TestLineItemValidation:
    """Test complete line item validation."""
    
    def test_valid_line_item(self):
        """Test valid line item"""
        result = validate_line_item(
            unit_price=10.0,
            quantity=5.0,
            line_total=50.0,
            description="Test item"
        )
        
        assert result['valid']
        assert result['flags'] == []
        assert result['expected_total'] == 50.0
        assert result['difference'] == 0.0
    
    def test_price_incoherent_line(self):
        """Test price incoherent line"""
        result = validate_line_item(
            unit_price=10.0,
            quantity=5.0,
            line_total=60.0,  # Should be 50.0
            description="Test item"
        )
        
        assert not result['valid']
        assert "PRICE_INCOHERENT" in result['flags']
    
    def test_pack_mismatch_line(self):
        """Test pack mismatch line"""
        result = validate_line_item(
            unit_price=10.0,
            quantity=24.0,
            line_total=240.0,
            description="Test item",
            packs=2.0,
            units_per_pack=10.0  # 2*10 != 24
        )
        
        assert not result['valid']
        assert "PACK_MISMATCH" in result['flags']
    
    def test_foc_line(self):
        """Test FOC line"""
        result = validate_line_item(
            unit_price=0.0,
            quantity=5.0,
            line_total=0.0,
            description="FOC item"
        )
        
        assert result['valid']
        assert "FOC_LINE" in result['flags']


class TestInvoiceTotalsValidation:
    """Test invoice totals validation."""
    
    def test_valid_invoice_totals(self):
        """Test valid invoice totals"""
        result = validate_invoice_totals(
            subtotal=100.0,
            vat_amount=20.0,
            vat_rate=20.0,
            invoice_total=120.0,
            line_totals=[50.0, 30.0, 20.0]
        )
        
        assert result['valid']
        assert result['flags'] == []
        assert result['expected_total'] == 120.0
        assert result['difference'] == 0.0
    
    def test_vat_mismatch_invoice(self):
        """Test VAT mismatch in invoice"""
        result = validate_invoice_totals(
            subtotal=100.0,
            vat_amount=25.0,  # Should be 20.0
            vat_rate=20.0,
            invoice_total=125.0,
            line_totals=[50.0, 30.0, 20.0]
        )
        
        assert not result['valid']
        assert "VAT_MISMATCH" in result['flags']
    
    def test_negative_adjustment_invoice(self):
        """Test negative adjustment in invoice"""
        result = validate_invoice_totals(
            subtotal=100.0,
            vat_amount=20.0,
            vat_rate=20.0,
            invoice_total=120.0,
            line_totals=[50.0, -5.0, 30.0, 20.0, 25.0]
        )
        
        assert not result['valid']
        assert "NEGATIVE_ADJUSTMENT_PRESENT" in result['flags']


class TestBankerRounding:
    """Test banker's rounding function."""
    
    def test_exact_rounding(self):
        """Test exact rounding"""
        assert banker_round(10.0) == 10.0
        assert banker_round(10.5) == 10.5
        assert banker_round(10.51) == 10.51
    
    def test_banker_rounding_rules(self):
        """Test banker's rounding rules"""
        # 0.5 rounds to even
        assert banker_round(10.5) == 10.5
        assert banker_round(11.5) == 11.5
        
        # Other values round normally
        assert banker_round(10.4) == 10.4
        assert banker_round(10.6) == 10.6
    
    def test_precision(self):
        """Test precision handling"""
        assert banker_round(10.123, 2) == 10.12
        assert banker_round(10.125, 2) == 10.13
        assert banker_round(10.126, 2) == 10.13


class TestLineFingerprint:
    """Test line fingerprint calculation."""
    
    def test_deterministic_fingerprint(self):
        """Test fingerprint is deterministic"""
        fp1 = calculate_line_fingerprint("SKU001", 5.0, "ml", 10.0, 8.0, 40.0, "2024-01-01", "SUP001", "RULESET1", "1.0.0")
        fp2 = calculate_line_fingerprint("SKU001", 5.0, "ml", 10.0, 8.0, 40.0, "2024-01-01", "SUP001", "RULESET1", "1.0.0")
        
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA256 hex length
    
    def test_different_inputs_different_fingerprints(self):
        """Test different inputs produce different fingerprints"""
        fp1 = calculate_line_fingerprint("SKU001", 5.0, "ml", 10.0, 8.0, 40.0, "2024-01-01", "SUP001", "RULESET1", "1.0.0")
        fp2 = calculate_line_fingerprint("SKU002", 5.0, "ml", 10.0, 8.0, 40.0, "2024-01-01", "SUP001", "RULESET1", "1.0.0")
        
        assert fp1 != fp2


if __name__ == "__main__":
    pytest.main([__file__]) 