"""
Unit Tests for Units Normalisation
Test canonical unit parsing and conversion.
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from normalization.units import canonical_quantities, parse_pack_quantity, normalize_line_description


class TestPackQuantityParsing:
    """Test pack quantity parsing functionality."""
    
    def test_standard_pack_format(self):
        """Test standard pack format: 24x275ml"""
        result = parse_pack_quantity("24x275ml")
        
        assert result['packs'] == 24.0
        assert result['units_per_pack'] == 1.0
        assert result['quantity_each'] == 6600.0  # 24 * 275
        assert result['unit_size_ml'] == 275.0
        assert result['quantity_ml'] == 6600.0
        assert result['quantity_l'] == 6.6
        assert result['uom_key'] == 'volume_ml'
    
    def test_unicode_multiply(self):
        """Test unicode multiply symbol: 12×330ml"""
        result = parse_pack_quantity("12×330ml")
        
        assert result['packs'] == 12.0
        assert result['units_per_pack'] == 1.0
        assert result['quantity_each'] == 3960.0  # 12 * 330
        assert result['unit_size_ml'] == 330.0
        assert result['quantity_ml'] == 3960.0
        assert result['quantity_l'] == 3.96
        assert result['uom_key'] == 'volume_ml'
    
    def test_case_format(self):
        """Test case format: C6, C12, C24"""
        result = parse_pack_quantity("C24")
        
        assert result['packs'] == 1.0
        assert result['units_per_pack'] == 24.0
        assert result['quantity_each'] == 24.0
        assert result['uom_key'] == 'case'
    
    def test_pack_words(self):
        """Test pack words: pack, case, crate, tray"""
        result = parse_pack_quantity("6 pack")
        
        assert result['packs'] == 6.0
        assert result['units_per_pack'] == 1.0
        assert result['quantity_each'] == 6.0
        assert result['uom_key'] == 'pack'
    
    def test_dozen_format(self):
        """Test dozen format"""
        result = parse_pack_quantity("2 dozen")
        
        assert result['packs'] == 2.0
        assert result['units_per_pack'] == 12.0
        assert result['quantity_each'] == 24.0
        assert result['uom_key'] == 'dozen'
    
    def test_keg_format(self):
        """Test keg/cask/pin format"""
        result = parse_pack_quantity("1 keg")
        
        assert result['packs'] == 1.0
        assert result['units_per_pack'] == 1.0
        assert result['quantity_each'] == 50.0  # 50L keg
        assert result['unit_size_l'] == 50.0
        assert result['quantity_l'] == 50.0
        assert result['quantity_ml'] == 50000.0
        assert result['uom_key'] == 'container_keg'
    
    def test_simple_quantity(self):
        """Test simple quantity with unit"""
        result = parse_pack_quantity("70cl")
        
        assert result['packs'] == 1.0
        assert result['units_per_pack'] == 1.0
        assert result['quantity_each'] == 70.0
        assert result['unit_size_ml'] == 700.0  # 70 * 10 (cl to ml)
        assert result['quantity_ml'] == 700.0
        assert result['quantity_l'] == 0.7
        assert result['uom_key'] == 'volume_cl'
    
    def test_foc_detection(self):
        """Test FOC/Free detection"""
        result = parse_pack_quantity("FOC")
        
        assert result['uom_key'] == 'foc'
        assert result['packs'] is None
        assert result['quantity_each'] is None


class TestCanonicalQuantities:
    """Test canonical quantities calculation."""
    
    def test_complex_pack_quantity(self):
        """Test complex pack quantity: 2 × (24 × 275ml)"""
        result = canonical_quantities(48, "2 × (24 × 275ml)")
        
        assert result['quantity_each'] == 48
        assert result['quantity_ml'] == 13200  # 48 * 275
        assert result['quantity_l'] == 13.2
        assert result['uom_key'] == 'volume_ml'
    
    def test_weight_conversion(self):
        """Test weight conversion: 1 × 6kg vs 6 × 1kg"""
        result1 = canonical_quantities(6, "1 × 6kg")
        result2 = canonical_quantities(6, "6 × 1kg")
        
        # Both should result in 6000g
        assert result1['quantity_g'] == 6000
        assert result2['quantity_g'] == 6000
        assert result1['quantity_l'] == 6.0  # kg equivalent
        assert result2['quantity_l'] == 6.0
    
    def test_keg_litres(self):
        """Test keg litres recognition"""
        result = canonical_quantities(50, "50L Keg")
        
        assert result['quantity_l'] == 50.0
        assert result['quantity_ml'] == 50000.0
        assert result['uom_key'] == 'container_keg'
    
    def test_dozen_conversion(self):
        """Test dozen = 12 units"""
        result = canonical_quantities(24, "2 dozen")
        
        assert result['quantity_each'] == 24
        assert result['packs'] == 2.0
        assert result['units_per_pack'] == 12.0
        assert result['uom_key'] == 'dozen'
    
    def test_foc_detection_in_canonical(self):
        """Test FOC detection in canonical quantities"""
        result = canonical_quantities(0, "FOC")
        
        assert result['uom_key'] == 'foc'
        assert result['quantity_each'] == 0


class TestLineDescriptionNormalization:
    """Test line description normalization."""
    
    def test_sku_extraction(self):
        """Test SKU pattern extraction"""
        result = normalize_line_description("TIA MARIA 70CL TIA001")
        
        assert result['sku'] == "TIA001"
        assert result['brand'] == "Tia"
        assert result['normalized_description'] == "TIA MARIA 70CL TIA001"
    
    def test_brand_extraction(self):
        """Test brand extraction"""
        result = normalize_line_description("Heineken Lager 330ml")
        
        assert result['brand'] == "Heineken"
        assert result['normalized_description'] == "Heineken Lager 330ml"
    
    def test_category_detection(self):
        """Test category detection"""
        # Spirits
        result = normalize_line_description("Grey Goose Vodka 70cl")
        assert result['category'] == 'spirits'
        
        # Wine
        result = normalize_line_description("Chardonnay White Wine 75cl")
        assert result['category'] == 'wine'
        
        # Beer
        result = normalize_line_description("Stella Artois Lager 330ml")
        assert result['category'] == 'beer'
        
        # Softs
        result = normalize_line_description("Coca Cola 330ml")
        assert result['category'] == 'softs_nrb'
    
    def test_no_patterns(self):
        """Test description with no extractable patterns"""
        result = normalize_line_description("Generic Product 500ml")
        
        assert result['sku'] is None
        assert result['brand'] is None
        assert result['category'] is None
        assert result['normalized_description'] == "Generic Product 500ml"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_description(self):
        """Test empty description"""
        result = canonical_quantities(1, "")
        
        assert result['quantity_each'] == 1
        assert result['packs'] == 1.0
        assert result['units_per_pack'] == 1.0
    
    def test_malformed_pack_string(self):
        """Test malformed pack string"""
        result = canonical_quantities(1, "invalid pack string")
        
        assert result['quantity_each'] == 1
        assert result['packs'] == 1.0
        assert result['units_per_pack'] == 1.0
    
    def test_zero_quantity(self):
        """Test zero quantity"""
        result = canonical_quantities(0, "24x275ml")
        
        assert result['quantity_each'] == 0
        assert result['quantity_ml'] == 0
        assert result['quantity_l'] == 0


if __name__ == "__main__":
    pytest.main([__file__]) 