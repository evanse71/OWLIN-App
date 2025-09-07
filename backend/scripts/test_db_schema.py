#!/usr/bin/env python3
"""
Database Schema Test Script

Tests the new Phase-C OCR fields and JSON serialization
"""

import sqlite3
import json
import sys
from pathlib import Path

def test_db_schema():
    """Test database schema and JSON serialization"""
    
    # Connect to database
    db_path = Path(__file__).parent.parent / "owlin.db"
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("🧪 Testing database schema...")
    
    # Test 1: Check if new columns exist
    cursor.execute("PRAGMA table_info(invoices)")
    invoice_columns = [col[1] for col in cursor.fetchall()]
    
    required_columns = [
        'doc_type', 'doc_type_score', 'policy_action', 
        'reasons_json', 'validation_json'
    ]
    
    missing_columns = []
    for col in required_columns:
        if col not in invoice_columns:
            missing_columns.append(col)
    
    if missing_columns:
        print(f"❌ Missing columns in invoices table: {missing_columns}")
        return False
    else:
        print("✅ All required columns exist in invoices table")
    
    # Test 2: Check line_items columns
    cursor.execute("PRAGMA table_info(line_items)")
    line_columns = [col[1] for col in cursor.fetchall()]
    
    required_line_columns = [
        'line_confidence', 'row_reasons_json', 'computed_total', 'unit_original'
    ]
    
    missing_line_columns = []
    for col in required_line_columns:
        if col not in line_columns:
            missing_line_columns.append(col)
    
    if missing_line_columns:
        print(f"❌ Missing columns in line_items table: {missing_line_columns}")
        return False
    else:
        print("✅ All required columns exist in line_items table")
    
    # Test 3: Check audit_log table
    cursor.execute("PRAGMA table_info(audit_log)")
    audit_columns = [col[1] for col in cursor.fetchall()]
    
    if not audit_columns:
        print("❌ audit_log table does not exist")
        return False
    else:
        print("✅ audit_log table exists")
    
    # Test 4: Test JSON serialization
    print("\n🧪 Testing JSON serialization...")
    
    test_data = {
        "doc_type": "invoice",
        "doc_type_score": 0.85,
        "policy_action": "ACCEPT",
        "reasons": ["Contains invoice keywords", "Has business structure"],
        "validation": {
            "arithmetic_ok": True,
            "currency_ok": True,
            "vat_ok": True,
            "date_ok": True,
            "issues": []
        },
        "line_items": [
            {
                "description": "Test Item",
                "quantity": 1,
                "unit": "ea",
                "unit_price": 10.00,
                "line_total": 10.00,
                "line_confidence": 95.0,
                "row_reasons": ["COLUMN_DETECTION"],
                "computed_total": False,
                "unit_original": "each"
            }
        ]
    }
    
    try:
        # Test insert with JSON
        cursor.execute("""
            INSERT INTO invoices (
                supplier_name, invoice_number, total_amount, 
                doc_type, doc_type_score, policy_action, 
                reasons_json, validation_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Test Supplier",
            "TEST-001",
            10.00,
            test_data["doc_type"],
            test_data["doc_type_score"],
            test_data["policy_action"],
            json.dumps(test_data["reasons"]),
            json.dumps(test_data["validation"])
        ))
        
        invoice_id = cursor.lastrowid
        
        # Test line items insert
        cursor.execute("""
            INSERT INTO line_items (
                invoice_id, description, quantity, unit, 
                unit_price, line_total, line_confidence, 
                row_reasons_json, computed_total, unit_original
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_id,
            test_data["line_items"][0]["description"],
            test_data["line_items"][0]["quantity"],
            test_data["line_items"][0]["unit"],
            test_data["line_items"][0]["unit_price"],
            test_data["line_items"][0]["line_total"],
            test_data["line_items"][0]["line_confidence"],
            json.dumps(test_data["line_items"][0]["row_reasons"]),
            test_data["line_items"][0]["computed_total"],
            test_data["line_items"][0]["unit_original"]
        ))
        
        # Test select and JSON deserialization
        cursor.execute("""
            SELECT doc_type, doc_type_score, policy_action, 
                   reasons_json, validation_json
            FROM invoices WHERE id = ?
        """, (invoice_id,))
        
        row = cursor.fetchone()
        if row:
            doc_type, doc_type_score, policy_action, reasons_json, validation_json = row
            
            # Test JSON deserialization
            reasons = json.loads(reasons_json)
            validation = json.loads(validation_json)
            
            print("✅ JSON serialization/deserialization works")
            print(f"   doc_type: {doc_type}")
            print(f"   doc_type_score: {doc_type_score}")
            print(f"   policy_action: {policy_action}")
            print(f"   reasons: {reasons}")
            print(f"   validation: {validation}")
        
        # Test audit log insert
        cursor.execute("""
            INSERT INTO audit_log (
                user_id, session_id, action, document_id,
                policy_action, reasons_json, confidence, processing_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "test_user",
            "test_session",
            "OCR_PROCESS",
            invoice_id,
            test_data["policy_action"],
            json.dumps(test_data["reasons"]),
            95.0,
            1500
        ))
        
        print("✅ Audit log insert works")
        
        # Clean up test data
        cursor.execute("DELETE FROM line_items WHERE invoice_id = ?", (invoice_id,))
        cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        cursor.execute("DELETE FROM audit_log WHERE document_id = ?", (invoice_id,))
        
        conn.commit()
        
    except Exception as e:
        print(f"❌ JSON serialization test failed: {e}")
        conn.rollback()
        return False
    
    conn.close()
    print("\n✅ All database schema tests passed!")
    return True

if __name__ == "__main__":
    success = test_db_schema()
    sys.exit(0 if success else 1) 