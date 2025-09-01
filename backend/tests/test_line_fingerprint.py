#!/usr/bin/env python3
"""
Test line fingerprint system
"""

import sys
import os
import tempfile
import sqlite3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.line_fingerprint import LineFingerprint
from db_manager_unified import DatabaseManager

def test_fingerprint_computation():
    """Test fingerprint computation"""
    fingerprint = LineFingerprint()
    
    # Test data
    line_data = {
        'sku_id': 'TEST_SKU_001',
        'qty': 2.0,
        'uom_key': 'volume_ml',
        'unit_price_raw': 1.50,
        'nett_price': 1.35,
        'nett_value': 2.70,
        'date': '2024-01-15',
        'supplier_id': 'TEST_SUPPLIER',
        'ruleset_id': 1
    }
    
    # Compute fingerprint
    fp1 = fingerprint.compute_fingerprint(line_data)
    assert fp1 is not None
    assert len(fp1) == 64  # SHA256 hex length
    assert fp1 != ""
    
    # Test stability
    fp2 = fingerprint.compute_fingerprint(line_data)
    assert fp1 == fp2
    
    print("✅ Fingerprint computation test passed")

def test_fingerprint_stability():
    """Test fingerprint stability across multiple computations"""
    fingerprint = LineFingerprint()
    
    line_data = {
        'sku_id': 'STABLE_TEST',
        'qty': 1.0,
        'uom_key': 'volume_ml',
        'unit_price_raw': 10.0,
        'nett_price': 10.0,
        'nett_value': 10.0,
        'date': '2024-01-01',
        'supplier_id': 'STABLE_SUPPLIER',
        'ruleset_id': 1
    }
    
    # Test stability validation
    is_stable = fingerprint.validate_fingerprint_stability(line_data)
    assert is_stable
    
    print("✅ Fingerprint stability test passed")

def test_fingerprint_persistence():
    """Test fingerprint persistence to database"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize database
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        fingerprint = LineFingerprint()
        fingerprint.db_manager = db_manager
        
        # Create test line data
        line_data = {
            'sku_id': 'PERSIST_TEST',
            'qty': 1.0,
            'uom_key': 'volume_ml',
            'unit_price_raw': 5.0,
            'nett_price': 5.0,
            'nett_value': 5.0,
            'date': '2024-01-01',
            'supplier_id': 'PERSIST_SUPPLIER',
            'ruleset_id': 1
        }
        
        # Compute and persist
        fp = fingerprint.compute_and_persist(1, 1, line_data)
        assert fp is not None
        
        # Retrieve fingerprint
        retrieved = fingerprint.get_fingerprint(1, 1)
        assert retrieved == fp
        
        print("✅ Fingerprint persistence test passed")
        
    finally:
        os.unlink(db_path)

def test_duplicate_detection():
    """Test duplicate fingerprint detection"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize database
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        fingerprint = LineFingerprint()
        fingerprint.db_manager = db_manager
        
        # Create identical line data
        line_data = {
            'sku_id': 'DUPLICATE_TEST',
            'qty': 1.0,
            'uom_key': 'volume_ml',
            'unit_price_raw': 3.0,
            'nett_price': 3.0,
            'nett_value': 3.0,
            'date': '2024-01-01',
            'supplier_id': 'DUPLICATE_SUPPLIER',
            'ruleset_id': 1
        }
        
        # Persist multiple times
        fp1 = fingerprint.compute_and_persist(1, 1, line_data)
        fp2 = fingerprint.compute_and_persist(2, 1, line_data)
        
        assert fp1 == fp2
        
        # Find duplicates
        duplicates = fingerprint.find_duplicate_fingerprints(fp1)
        assert len(duplicates) >= 2
        
        print("✅ Duplicate detection test passed")
        
    finally:
        os.unlink(db_path)

def test_fingerprint_uniqueness():
    """Test that different data produces different fingerprints"""
    fingerprint = LineFingerprint()
    
    # Base line data
    base_data = {
        'sku_id': 'UNIQUE_TEST',
        'qty': 1.0,
        'uom_key': 'volume_ml',
        'unit_price_raw': 10.0,
        'nett_price': 10.0,
        'nett_value': 10.0,
        'date': '2024-01-01',
        'supplier_id': 'UNIQUE_SUPPLIER',
        'ruleset_id': 1
    }
    
    base_fp = fingerprint.compute_fingerprint(base_data)
    
    # Test different quantities
    data2 = base_data.copy()
    data2['qty'] = 2.0
    fp2 = fingerprint.compute_fingerprint(data2)
    assert fp2 != base_fp
    
    # Test different prices
    data3 = base_data.copy()
    data3['unit_price_raw'] = 15.0
    fp3 = fingerprint.compute_fingerprint(data3)
    assert fp3 != base_fp
    
    # Test different SKUs
    data4 = base_data.copy()
    data4['sku_id'] = 'DIFFERENT_SKU'
    fp4 = fingerprint.compute_fingerprint(data4)
    assert fp4 != base_fp
    
    print("✅ Fingerprint uniqueness test passed")

def test_critical_fields():
    """Test that all critical fields are included in fingerprint"""
    fingerprint = LineFingerprint()
    
    # Test with missing fields
    incomplete_data = {
        'sku_id': 'INCOMPLETE_TEST',
        'qty': 1.0
        # Missing other critical fields
    }
    
    fp1 = fingerprint.compute_fingerprint(incomplete_data)
    assert fp1 != ""
    
    # Test with complete data
    complete_data = {
        'sku_id': 'COMPLETE_TEST',
        'qty': 1.0,
        'uom_key': 'volume_ml',
        'unit_price_raw': 10.0,
        'nett_price': 10.0,
        'nett_value': 10.0,
        'date': '2024-01-01',
        'supplier_id': 'COMPLETE_SUPPLIER',
        'ruleset_id': 1
    }
    
    fp2 = fingerprint.compute_fingerprint(complete_data)
    assert fp2 != ""
    assert fp1 != fp2  # Should be different due to missing fields
    
    print("✅ Critical fields test passed")

if __name__ == "__main__":
    test_fingerprint_computation()
    test_fingerprint_stability()
    test_fingerprint_persistence()
    test_duplicate_detection()
    test_fingerprint_uniqueness()
    test_critical_fields()
    print("All line fingerprint tests passed!") 