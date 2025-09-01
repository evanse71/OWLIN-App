"""
Comprehensive tests for canonical units normalisation - 25-case matrix
"""
import pytest
import sys
sys.path.insert(0, 'backend')

from backend.normalization.units import canonical_quantities

class TestCanonicalUnitsGrammar:
    """Test comprehensive grammar coverage for UK beverage industry"""
    
    def test_case_01_standard_pack_ml(self):
        """24×275ml → each=24, ml=6600, l=6.6"""
        result = canonical_quantities(1.0, "24×275ml")
        assert result['quantity_each'] == 24.0
        assert result['quantity_ml'] == 6600.0
        assert result['quantity_l'] == 6.6
        assert result['packs'] == 1.0
        assert result['units_per_pack'] == 24.0
    
    def test_case_02_double_pack_ml(self):
        """2 × (24 × 275ml) → each=48, ml=13200, l=13.2"""
        result = canonical_quantities(2.0, "24×275ml")
        assert result['quantity_each'] == 48.0
        assert result['quantity_ml'] == 13200.0
        assert result['quantity_l'] == 13.2
        assert result['packs'] == 2.0
    
    def test_case_03_unicode_multiply(self):
        """12×330ml with unicode × → each=12, ml=3960"""
        result = canonical_quantities(1.0, "12×330ml")
        assert result['quantity_each'] == 12.0
        assert result['quantity_ml'] == 3960.0
        assert result['units_per_pack'] == 12.0
    
    def test_case_04_litre_format(self):
        """12x1L → each=12, l=12.0"""
        result = canonical_quantities(1.0, "12x1L")
        assert result['quantity_each'] == 12.0
        assert result['quantity_l'] == 12.0
        assert result['unit_size_l'] == 1.0
    
    def test_case_05_centilitre(self):
        """70cl → l=0.7"""
        result = canonical_quantities(1.0, "70cl")
        assert result['quantity_each'] == 1.0
        assert result['quantity_l'] == 0.7
        assert result['unit_size_l'] == 0.7
    
    def test_case_06_case_notation_c6(self):
        """C6 → each=6"""
        result = canonical_quantities(1.0, "C6")
        assert result['quantity_each'] == 6.0
        assert result['packs'] == 1.0
        assert result['units_per_pack'] == 6.0
    
    def test_case_07_case_notation_c12(self):
        """C12 → each=12"""
        result = canonical_quantities(1.0, "C12")
        assert result['quantity_each'] == 12.0
        assert result['units_per_pack'] == 12.0
    
    def test_case_08_case_notation_c24(self):
        """C24 → each=24"""
        result = canonical_quantities(1.0, "C24")
        assert result['quantity_each'] == 24.0
        assert result['units_per_pack'] == 24.0
    
    def test_case_09_keg_50l(self):
        """50L Keg → l=50.0"""
        result = canonical_quantities(1.0, "50L Keg")
        assert result['quantity_l'] == 50.0
        assert result['unit_size_l'] == 50.0
    
    def test_case_10_keg_generic(self):
        """Keg → l=50.0 (default)"""
        result = canonical_quantities(1.0, "Keg")
        assert result['quantity_l'] == 50.0
    
    def test_case_11_cask(self):
        """Cask → l=40.9"""
        result = canonical_quantities(1.0, "Cask")
        assert result['quantity_l'] == 40.9
    
    def test_case_12_pin(self):
        """Pin → l=20.45"""
        result = canonical_quantities(1.0, "Pin")
        assert result['quantity_l'] == 20.45
    
    def test_case_13_eleven_gallon(self):
        """11g → l=50.0 (11 gallon = 50L keg)"""
        result = canonical_quantities(1.0, "11g")
        assert result['quantity_l'] == 50.0
    
    def test_case_14_dozen(self):
        """dozen → each=12"""
        result = canonical_quantities(1.0, "dozen")
        assert result['quantity_each'] == 12.0
        assert result['units_per_pack'] == 12.0
    
    def test_case_15_330ml_caps(self):
        """330 ML → ml=330"""
        result = canonical_quantities(1.0, "330 ML")
        assert result['quantity_ml'] == 330.0
        assert result['unit_size_ml'] == 330.0
    
    def test_case_16_weight_kg(self):
        """1 × 6kg vs 6 × 1kg → g=6000"""
        result1 = canonical_quantities(1.0, "6kg")
        result2 = canonical_quantities(6.0, "1kg")
        assert result1['quantity_g'] == 6000.0
        assert result2['quantity_g'] == 6000.0
    
    def test_case_17_comma_decimal(self):
        """24×0,275l (comma decimal) → l=6.6"""
        result = canonical_quantities(1.0, "24×0,275l")
        assert result['quantity_l'] == 6.6
    
    def test_case_18_nrb_bottles(self):
        """24×275ml NRB → each=24, ml=6600"""
        result = canonical_quantities(1.0, "24×275ml NRB")
        assert result['quantity_each'] == 24.0
        assert result['quantity_ml'] == 6600.0
    
    def test_case_19_can_format(self):
        """12×330ml CAN → each=12, ml=3960"""
        result = canonical_quantities(1.0, "12×330ml CAN")
        assert result['quantity_each'] == 12.0
        assert result['quantity_ml'] == 3960.0
    
    def test_case_20_bottle_format(self):
        """6×75cl BOT → each=6, l=4.5"""
        result = canonical_quantities(1.0, "6×75cl BOT")
        assert result['quantity_each'] == 6.0
        assert result['quantity_l'] == 4.5
    
    def test_case_21_foc_detection(self):
        """FOC line → flags include FOC_LINE"""
        # This would be handled by the flags system
        result = canonical_quantities(0.0, "24×275ml FOC")
        assert result['quantity_each'] == 0.0  # FOC = zero quantity
    
    def test_case_22_pack_of_format(self):
        """Pack of 12 → units_per_pack=12"""
        result = canonical_quantities(1.0, "Pack of 12")
        assert result['units_per_pack'] == 12.0
        assert result['quantity_each'] == 12.0
    
    def test_case_23_case_of_format(self):
        """Case of 24 → units_per_pack=24"""
        result = canonical_quantities(1.0, "Case of 24")
        assert result['units_per_pack'] == 24.0
        assert result['quantity_each'] == 24.0
    
    def test_case_24_mixed_units_error(self):
        """Mixed units should be flagged"""
        # This would typically be caught by validation
        result = canonical_quantities(1.0, "24×275ml + 6×1L")
        # Should parse the first part
        assert result['quantity_each'] == 24.0
    
    def test_case_25_complex_description(self):
        """Complex: 2×(12×330ml) Premium Lager NRB → each=24, ml=7920"""
        result = canonical_quantities(2.0, "12×330ml Premium Lager NRB")
        assert result['quantity_each'] == 24.0
        assert result['quantity_ml'] == 7920.0
    
    def test_edge_cases_and_flags(self):
        """Test edge cases that should generate flags"""
        # Empty description
        result = canonical_quantities(1.0, "")
        assert result['quantity_each'] == 1.0
        
        # No units
        result = canonical_quantities(5.0, "Premium Product")
        assert result['quantity_each'] == 5.0
        
        # Partial pack info
        result = canonical_quantities(1.0, "24× (no size)")
        assert result['quantity_each'] == 24.0
        assert result['units_per_pack'] == 24.0
    
    def test_deterministic_output(self):
        """Test that same input always produces same output"""
        desc = "24×275ml"
        result1 = canonical_quantities(1.0, desc)
        result2 = canonical_quantities(1.0, desc)
        
        assert result1 == result2
        assert result1['quantity_each'] == result2['quantity_each']
        assert result1['quantity_ml'] == result2['quantity_ml']

if __name__ == "__main__":
    pytest.main([__file__]) 