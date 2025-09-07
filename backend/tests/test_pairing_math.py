#!/usr/bin/env python3
"""
Test line-level pairing functionality
"""

import sys
import os
import tempfile
import sqlite3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pairing_service import PairingService
from db_manager_unified import DatabaseManager

def test_quantity_matching():
    """Test quantity matching with canonical units"""
    service = PairingService()
    
    # Test exact quantity match
    inv_line = {'quantity': 24, 'description': '24x330ml cans'}
    dn_line = {'quantity': 24, 'description': '24x330ml cans'}
    
    score, reasons = service._match_quantities(inv_line, dn_line)
    assert score > 0.9
    assert any("Quantity match" in reason for reason in reasons)
    
    # Test quantity mismatch
    inv_line = {'quantity': 24, 'description': '24x330ml cans'}
    dn_line = {'quantity': 12, 'description': '12x330ml cans'}
    
    score, reasons = service._match_quantities(inv_line, dn_line)
    assert score < 0.5
    assert any("Quantity mismatch" in reason for reason in reasons)
    
    print("✅ Quantity matching test passed")

def test_description_matching():
    """Test description similarity matching"""
    service = PairingService()
    
    # Test similar descriptions
    inv_line = {'description': 'Heineken Lager 330ml'}
    dn_line = {'description': 'Heineken Lager 330ml cans'}
    
    score, reasons = service._match_descriptions(inv_line, dn_line)
    assert score > 0.8
    assert any("Description similarity" in reason for reason in reasons)
    
    # Test different descriptions
    inv_line = {'description': 'Heineken Lager 330ml'}
    dn_line = {'description': 'Corona Extra 330ml'}
    
    score, reasons = service._match_descriptions(inv_line, dn_line)
    assert score < 0.5
    assert any("Description mismatch" in reason for reason in reasons)
    
    print("✅ Description matching test passed")

def test_price_matching():
    """Test price proximity matching"""
    service = PairingService()
    
    # Test similar prices
    inv_line = {'unit_price': 1.50}
    dn_line = {'unit_price': 1.55}
    
    score, reasons = service._match_prices(inv_line, dn_line)
    assert score > 0.8
    assert any("Price match" in reason for reason in reasons)
    
    # Test different prices
    inv_line = {'unit_price': 1.50}
    dn_line = {'unit_price': 2.00}
    
    score, reasons = service._match_prices(inv_line, dn_line)
    assert score < 0.5
    assert any("Price mismatch" in reason for reason in reasons)
    
    print("✅ Price matching test passed")

def test_sku_matching():
    """Test SKU matching"""
    service = PairingService()
    
    # Test exact SKU match
    inv_line = {'sku': 'HEINEKEN001'}
    dn_line = {'sku': 'HEINEKEN001'}
    
    score, reasons = service._match_skus(inv_line, dn_line)
    assert score == 1.0
    assert any("SKU exact match" in reason for reason in reasons)
    
    # Test similar SKUs
    inv_line = {'sku': 'HEINEKEN001'}
    dn_line = {'sku': 'HEINEKEN002'}
    
    score, reasons = service._match_skus(inv_line, dn_line)
    assert score > 0.8
    assert any("SKU similarity" in reason for reason in reasons)
    
    print("✅ SKU matching test passed")

def test_line_pairing():
    """Test complete line pairing functionality"""
    service = PairingService()
    
    # Test data
    invoice_lines = [
        {
            'id': 1,
            'quantity': 24,
            'description': 'Heineken Lager 330ml',
            'unit_price': 1.50,
            'sku': 'HEINEKEN001'
        },
        {
            'id': 2,
            'quantity': 12,
            'description': 'Corona Extra 330ml',
            'unit_price': 1.75,
            'sku': 'CORONA001'
        }
    ]
    
    delivery_lines = [
        {
            'id': 101,
            'quantity': 24,
            'description': 'Heineken Lager 330ml cans',
            'unit_price': 1.55,
            'sku': 'HEINEKEN001'
        },
        {
            'id': 102,
            'quantity': 12,
            'description': 'Corona Extra 330ml bottles',
            'unit_price': 1.80,
            'sku': 'CORONA001'
        }
    ]
    
    # Test pairing
    pairings = service.pair_line_items(invoice_lines, delivery_lines)
    
    assert len(pairings) == 2
    
    # Check first pairing (Heineken)
    heineken_pairing = next(p for p in pairings if p['invoice_line']['sku'] == 'HEINEKEN001')
    assert heineken_pairing['score'] > 0.7
    assert heineken_pairing['delivery_line']['id'] == 101
    
    # Check second pairing (Corona)
    corona_pairing = next(p for p in pairings if p['invoice_line']['sku'] == 'CORONA001')
    assert corona_pairing['score'] > 0.7
    assert corona_pairing['delivery_line']['id'] == 102
    
    print("✅ Line pairing test passed")

def test_partial_delivery():
    """Test partial delivery scenarios"""
    service = PairingService()
    
    # Invoice has more lines than delivery note
    invoice_lines = [
        {'id': 1, 'quantity': 24, 'description': 'Product A', 'unit_price': 1.0, 'sku': 'A001'},
        {'id': 2, 'quantity': 12, 'description': 'Product B', 'unit_price': 2.0, 'sku': 'B001'},
        {'id': 3, 'quantity': 6, 'description': 'Product C', 'unit_price': 3.0, 'sku': 'C001'}
    ]
    
    delivery_lines = [
        {'id': 101, 'quantity': 24, 'description': 'Product A', 'unit_price': 1.0, 'sku': 'A001'},
        {'id': 102, 'quantity': 12, 'description': 'Product B', 'unit_price': 2.0, 'sku': 'B001'}
    ]
    
    pairings = service.pair_line_items(invoice_lines, delivery_lines)
    
    assert len(pairings) == 2  # Only A and B should match
    assert all(p['invoice_line']['sku'] in ['A001', 'B001'] for p in pairings)
    
    print("✅ Partial delivery test passed")

def test_over_delivery():
    """Test over-delivery scenarios"""
    service = PairingService()
    
    # Delivery note has more lines than invoice
    invoice_lines = [
        {'id': 1, 'quantity': 24, 'description': 'Product A', 'unit_price': 1.0, 'sku': 'A001'}
    ]
    
    delivery_lines = [
        {'id': 101, 'quantity': 24, 'description': 'Product A', 'unit_price': 1.0, 'sku': 'A001'},
        {'id': 102, 'quantity': 12, 'description': 'Product B', 'unit_price': 2.0, 'sku': 'B001'}
    ]
    
    pairings = service.pair_line_items(invoice_lines, delivery_lines)
    
    assert len(pairings) == 1  # Only A should match
    assert pairings[0]['invoice_line']['sku'] == 'A001'
    
    print("✅ Over delivery test passed")

def test_multi_dn_scenario():
    """Test multiple delivery notes scenario"""
    service = PairingService()
    
    # One invoice line that could match multiple delivery notes
    invoice_lines = [
        {'id': 1, 'quantity': 24, 'description': 'Product A', 'unit_price': 1.0, 'sku': 'A001'}
    ]
    
    delivery_lines = [
        {'id': 101, 'quantity': 12, 'description': 'Product A', 'unit_price': 1.0, 'sku': 'A001'},
        {'id': 102, 'quantity': 12, 'description': 'Product A', 'unit_price': 1.0, 'sku': 'A001'}
    ]
    
    pairings = service.pair_line_items(invoice_lines, delivery_lines)
    
    assert len(pairings) == 1  # Should pick the best match
    assert pairings[0]['score'] > 0.7
    
    print("✅ Multi DN scenario test passed")

def test_persistence():
    """Test line pairing persistence"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize database
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        service = PairingService()
        service.db_manager = db_manager
        
        # Test data
        pairings = [
            {
                'invoice_line': {'id': 1, 'quantity': 24, 'description': 'Test'},
                'delivery_line': {'id': 101, 'quantity': 24, 'description': 'Test'},
                'score': 0.9,
                'reasons': ['Quantity match', 'Description similarity']
            }
        ]
        
        # Test persistence
        success = service.persist_line_pairing(1, pairings)
        assert success
        
        print("✅ Persistence test passed")
        
    finally:
        os.unlink(db_path)

if __name__ == "__main__":
    test_quantity_matching()
    test_description_matching()
    test_price_matching()
    test_sku_matching()
    test_line_pairing()
    test_partial_delivery()
    test_over_delivery()
    test_multi_dn_scenario()
    test_persistence()
    print("All line pairing tests passed!") 