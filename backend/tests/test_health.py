#!/usr/bin/env python3
"""
Test health metrics functionality
"""

import sys
import os
import tempfile
import sqlite3
import json
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.health import _get_flags_24h, _get_avg_line_flags_per_invoice_24h, _get_pairing_suggestion_rate_24h
from routes.health import _determine_health_status, _get_health_violations
from db_manager_unified import DatabaseManager

def test_flags_24h():
    """Test 24h flag counting"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize database
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert test invoices with flags
            cursor.execute("""
                INSERT INTO invoices 
                (supplier_name, invoice_date, total_amount, validation_flags, uploaded_at)
                VALUES (?, ?, ?, ?, ?)
            """, ('Test Supplier', '2024-01-01', 100.0, 
                  json.dumps({"PRICE_INCOHERENT": 1}), 
                  datetime.now().isoformat()))
            
            cursor.execute("""
                INSERT INTO invoices 
                (supplier_name, invoice_date, total_amount, validation_flags, uploaded_at)
                VALUES (?, ?, ?, ?, ?)
            """, ('Test Supplier 2', '2024-01-01', 200.0, 
                  json.dumps({"VAT_MISMATCH": 1}), 
                  datetime.now().isoformat()))
            
            conn.commit()
        
        # Test flag counting
        flags = _get_flags_24h(db_manager)
        
        assert flags["PRICE_INCOHERENT"] == 1
        assert flags["VAT_MISMATCH"] == 1
        assert flags["PACK_MISMATCH"] == 0
        assert flags["OCR_LOW_CONF"] == 0
        assert flags["OFF_CONTRACT_DISCOUNT"] == 0
        
        print("✅ Flags 24h test passed")
        
    finally:
        os.unlink(db_path)

def test_avg_line_flags():
    """Test average line flags per invoice"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert test invoice
            cursor.execute("""
                INSERT INTO invoices 
                (supplier_name, invoice_date, total_amount, uploaded_at)
                VALUES (?, ?, ?, ?)
            """, ('Test Supplier', '2024-01-01', 100.0, datetime.now().isoformat()))
            
            invoice_id = cursor.lastrowid
            
            # Insert line items with flags
            cursor.execute("""
                INSERT INTO invoice_line_items 
                (invoice_id, description, quantity, unit_price, line_total, line_flags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (invoice_id, 'Product 1', 2.0, 10.0, 20.0, 
                  json.dumps(["PRICE_INCOHERENT"])))
            
            cursor.execute("""
                INSERT INTO invoice_line_items 
                (invoice_id, description, quantity, unit_price, line_total, line_flags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (invoice_id, 'Product 2', 1.0, 5.0, 5.0, 
                  json.dumps(["OCR_LOW_CONF"])))
            
            conn.commit()
        
        # Test average calculation
        avg_flags = _get_avg_line_flags_per_invoice_24h(db_manager)
        assert avg_flags == 2.0  # 2 flagged lines / 1 invoice
        
        print("✅ Average line flags test passed")
        
    finally:
        os.unlink(db_path)

def test_pairing_suggestion_rate():
    """Test pairing suggestion rate"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert delivery notes
            cursor.execute("""
                INSERT INTO delivery_notes 
                (supplier_name, delivery_date, total_items, uploaded_at)
                VALUES (?, ?, ?, ?)
            """, ('Test Supplier', '2024-01-01', 10, datetime.now().isoformat()))
            
            cursor.execute("""
                INSERT INTO delivery_notes 
                (supplier_name, delivery_date, total_items, uploaded_at)
                VALUES (?, ?, ?, ?)
            """, ('Test Supplier 2', '2024-01-01', 5, datetime.now().isoformat()))
            
            # Insert pairing suggestions
            cursor.execute("""
                INSERT INTO pairing_suggestions 
                (delivery_note_id, invoice_id, score, status, reasons, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (1, 1, 85, 'pending', json.dumps(['supplier_match']), 
                  datetime.now().isoformat()))
            
            conn.commit()
        
        # Test suggestion rate
        rate = _get_pairing_suggestion_rate_24h(db_manager)
        assert rate == 0.5  # 1 suggestion / 2 delivery notes
        
        print("✅ Pairing suggestion rate test passed")
        
    finally:
        os.unlink(db_path)

def test_health_status():
    """Test health status determination"""
    # Test healthy status
    flags_healthy = {
        "PRICE_INCOHERENT": 0,
        "VAT_MISMATCH": 0,
        "PACK_MISMATCH": 0,
        "OCR_LOW_CONF": 0,
        "OFF_CONTRACT_DISCOUNT": 0
    }
    status = _determine_health_status(flags_healthy, 0.5)
    assert status == "healthy"
    
    # Test degraded status
    flags_degraded = {
        "PRICE_INCOHERENT": 0,
        "VAT_MISMATCH": 0,
        "PACK_MISMATCH": 5,
        "OCR_LOW_CONF": 8,
        "OFF_CONTRACT_DISCOUNT": 2
    }
    status = _determine_health_status(flags_degraded, 3.0)
    assert status == "degraded"
    
    # Test critical status
    flags_critical = {
        "PRICE_INCOHERENT": 1,
        "VAT_MISMATCH": 0,
        "PACK_MISMATCH": 0,
        "OCR_LOW_CONF": 0,
        "OFF_CONTRACT_DISCOUNT": 0
    }
    status = _determine_health_status(flags_critical, 0.5)
    assert status == "critical"
    
    print("✅ Health status test passed")

def test_health_violations():
    """Test health violations detection"""
    # Test no violations
    flags_clean = {
        "PRICE_INCOHERENT": 0,
        "VAT_MISMATCH": 0,
        "PACK_MISMATCH": 0,
        "OCR_LOW_CONF": 0,
        "OFF_CONTRACT_DISCOUNT": 0
    }
    violations = _get_health_violations(flags_clean, 0.5)
    assert len(violations) == 0
    
    # Test critical violations
    flags_critical = {
        "PRICE_INCOHERENT": 2,
        "VAT_MISMATCH": 1,
        "PACK_MISMATCH": 0,
        "OCR_LOW_CONF": 0,
        "OFF_CONTRACT_DISCOUNT": 0
    }
    violations = _get_health_violations(flags_critical, 0.5)
    assert len(violations) == 2
    assert any("Price incoherent" in v for v in violations)
    assert any("VAT mismatch" in v for v in violations)
    
    # Test high flag rate
    flags_high = {
        "PRICE_INCOHERENT": 0,
        "VAT_MISMATCH": 0,
        "PACK_MISMATCH": 15,
        "OCR_LOW_CONF": 0,
        "OFF_CONTRACT_DISCOUNT": 0
    }
    violations = _get_health_violations(flags_high, 3.5)
    assert len(violations) == 2
    assert any("High flag rate" in v for v in violations)
    assert any("High line flag rate" in v for v in violations)
    
    print("✅ Health violations test passed")

def test_empty_database():
    """Test health metrics with empty database"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        # Test with empty database
        flags = _get_flags_24h(db_manager)
        assert all(count == 0 for count in flags.values())
        
        avg_flags = _get_avg_line_flags_per_invoice_24h(db_manager)
        assert avg_flags == 0.0
        
        suggestion_rate = _get_pairing_suggestion_rate_24h(db_manager)
        assert suggestion_rate == 0.0
        
        print("✅ Empty database test passed")
        
    finally:
        os.unlink(db_path)

def test_old_data_exclusion():
    """Test that old data is excluded from 24h metrics"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert old invoice (2 days ago)
            old_date = (datetime.now() - timedelta(days=2)).isoformat()
            cursor.execute("""
                INSERT INTO invoices 
                (supplier_name, invoice_date, total_amount, validation_flags, uploaded_at)
                VALUES (?, ?, ?, ?, ?)
            """, ('Old Supplier', '2024-01-01', 100.0, 
                  json.dumps({"PRICE_INCOHERENT": 1}), old_date))
            
            # Insert recent invoice
            cursor.execute("""
                INSERT INTO invoices 
                (supplier_name, invoice_date, total_amount, validation_flags, uploaded_at)
                VALUES (?, ?, ?, ?, ?)
            """, ('Recent Supplier', '2024-01-01', 200.0, 
                  json.dumps({"VAT_MISMATCH": 1}), datetime.now().isoformat()))
            
            conn.commit()
        
        # Test that only recent data is counted
        flags = _get_flags_24h(db_manager)
        assert flags["PRICE_INCOHERENT"] == 0  # Old data excluded
        assert flags["VAT_MISMATCH"] == 1      # Recent data included
        
        print("✅ Old data exclusion test passed")
        
    finally:
        os.unlink(db_path)

if __name__ == "__main__":
    test_flags_24h()
    test_avg_line_flags()
    test_pairing_suggestion_rate()
    test_health_status()
    test_health_violations()
    test_empty_database()
    test_old_data_exclusion()
    print("All health tests passed!") 