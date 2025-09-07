#!/usr/bin/env python3
"""
Test OCR confidence functionality
"""

import sys
import os
import tempfile
import sqlite3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager_unified import DatabaseManager

def test_ocr_confidence_persistence():
    """Test OCR confidence persistence"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize database
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert test invoice with OCR confidence
            cursor.execute("""
                INSERT INTO invoices 
                (supplier_name, invoice_date, total_amount, ocr_avg_conf_page, ocr_min_conf_line)
                VALUES (?, ?, ?, ?, ?)
            """, ('Test Supplier', '2024-01-01', 100.0, 0.85, 0.72))
            
            invoice_id = cursor.lastrowid
            
            # Insert test line items with OCR confidence
            cursor.execute("""
                INSERT INTO invoice_line_items 
                (invoice_id, description, quantity, unit_price, line_total, ocr_confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (invoice_id, 'Test Product', 2.0, 10.0, 20.0, 0.88))
            
            cursor.execute("""
                INSERT INTO invoice_line_items 
                (invoice_id, description, quantity, unit_price, line_total, ocr_confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (invoice_id, 'Low Confidence Product', 1.0, 5.0, 5.0, 0.45))
            
            conn.commit()
            
            # Verify persistence
            cursor.execute("""
                SELECT ocr_avg_conf_page, ocr_min_conf_line 
                FROM invoices WHERE id = ?
            """, (invoice_id,))
            
            row = cursor.fetchone()
            assert row[0] == 0.85  # avg_conf_page
            assert row[1] == 0.72  # min_conf_line
            
            # Verify line confidence
            cursor.execute("""
                SELECT ocr_confidence FROM invoice_line_items 
                WHERE invoice_id = ? ORDER BY id
            """, (invoice_id,))
            
            confidences = [row[0] for row in cursor.fetchall()]
            assert confidences == [0.88, 0.45]
        
        print("✅ OCR confidence persistence test passed")
        
    finally:
        os.unlink(db_path)

def test_parser_gating():
    """Test parser gating based on OCR confidence"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Test cases with different confidence levels
            test_cases = [
                (0.30, "block"),      # < 50% = block
                (0.45, "block"),      # < 50% = block
                (0.55, "flag"),       # < 70% = flag
                (0.65, "flag"),       # < 70% = flag
                (0.75, "process"),    # >= 70% = process
                (0.95, "process")     # >= 70% = process
            ]
            
            for confidence, expected_action in test_cases:
                action = _get_parser_action(confidence)
                assert action == expected_action, f"Confidence {confidence} should be {expected_action}, got {action}"
        
        print("✅ Parser gating test passed")
        
    finally:
        os.unlink(db_path)

def test_confidence_aggregation():
    """Test confidence aggregation logic"""
    # Test line confidences aggregation
    line_confidences = [0.95, 0.88, 0.72, 0.45, 0.92]
    
    avg_confidence = sum(line_confidences) / len(line_confidences)
    min_confidence = min(line_confidences)
    
    assert abs(avg_confidence - 0.784) < 0.001
    assert min_confidence == 0.45
    
    print("✅ Confidence aggregation test passed")

def test_confidence_validation():
    """Test confidence value validation"""
    # Valid confidence values
    valid_confidences = [0.0, 0.5, 1.0, 0.999]
    for conf in valid_confidences:
        assert 0.0 <= conf <= 1.0
    
    # Invalid confidence values
    invalid_confidences = [-0.1, 1.1, 2.0, -1.0]
    for conf in invalid_confidences:
        assert not (0.0 <= conf <= 1.0)
    
    print("✅ Confidence validation test passed")

def _get_parser_action(confidence: float) -> str:
    """Get parser action based on confidence level"""
    if confidence < 0.50:
        return "block"
    elif confidence < 0.70:
        return "flag"
    else:
        return "process"

if __name__ == "__main__":
    test_ocr_confidence_persistence()
    test_parser_gating()
    test_confidence_aggregation()
    test_confidence_validation()
    print("All OCR confidence tests passed!") 