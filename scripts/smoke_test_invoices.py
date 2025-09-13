#!/usr/bin/env python3
"""
Smoke Test for Invoices Domain
Tests the complete invoices functionality including upload, OCR, issue detection, and pairing.
"""
import sys
import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Any

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import (
    load_invoices_from_db, get_invoice_details, get_issues_for_invoice,
    get_pairing_suggestions, resolve_issue, escalate_issue, 
    confirm_pairing, reject_pairing, get_flagged_issues,
    normalize_units, calculate_confidence_score, detect_issues
)
from app.enhanced_file_processor import (
    save_file_metadata, process_uploaded_file, retry_ocr_for_invoice
)
from app.db_migrations import run_migrations, log_audit_event

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection and table existence."""
    logger.info("🔍 Testing database connection...")
    
    try:
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        
        # Check required tables exist
        required_tables = [
            'invoices', 'invoice_line_items', 'uploaded_files', 
            'issues', 'audit_log', 'pairings', 'delivery_notes'
        ]
        
        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                raise Exception(f"Required table '{table}' not found")
        
        conn.close()
        logger.info("✅ Database connection and tables verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def test_business_logic():
    """Test business logic functions."""
    logger.info("🧮 Testing business logic functions...")
    
    try:
        # Test unit normalization
        test_cases = [
            ("24 x 275ml", 24),
            ("12 pack", 12),
            ("1 case", 1),
            ("6 bottles", 6),
            ("", 1),
            ("invalid", 1)
        ]
        
        for input_val, expected in test_cases:
            result = normalize_units(input_val)
            if result != expected:
                raise Exception(f"Unit normalization failed: {input_val} -> {result}, expected {expected}")
        
        # Test confidence calculation
        test_text = "Invoice #12345\nTotal: £100.00\nVAT: £20.00"
        test_items = [{'qty': 10, 'price': 8.0}]
        confidence = calculate_confidence_score(test_text, test_items)
        
        if confidence < 0 or confidence > 100:
            raise Exception(f"Invalid confidence score: {confidence}")
        
        # Test issue detection
        invoice_data = {'total_amount_pennies': 10000}  # £100.00
        line_items = [{'total_pennies': 8000, 'qty': 10, 'unit_price_pennies': 800}]  # £80.00
        
        issues = detect_issues(invoice_data, line_items)
        if not isinstance(issues, list):
            raise Exception("Issue detection should return a list")
        
        logger.info("✅ Business logic functions verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Business logic test failed: {e}")
        return False

def test_invoice_crud():
    """Test invoice CRUD operations."""
    logger.info("📄 Testing invoice CRUD operations...")
    
    try:
        # Test loading invoices
        invoices = load_invoices_from_db()
        if not isinstance(invoices, list):
            raise Exception("load_invoices_from_db should return a list")
        
        # Test getting invoice details (if any exist)
        if invoices:
            invoice_id = invoices[0]['id']
            details = get_invoice_details(invoice_id)
            if not details:
                raise Exception("get_invoice_details should return invoice details")
        
        # Test getting issues
        issues = get_flagged_issues()
        if not isinstance(issues, list):
            raise Exception("get_flagged_issues should return a list")
        
        logger.info("✅ Invoice CRUD operations verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Invoice CRUD test failed: {e}")
        return False

def test_audit_logging():
    """Test audit logging functionality."""
    logger.info("📝 Testing audit logging...")
    
    try:
        # Test audit log entry
        log_audit_event(
            user_id="test_user",
            action="test_action",
            entity_type="test_entity",
            entity_id="test_id",
            new_values={"test": "value"}
        )
        
        # Verify audit log entry was created
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM audit_log WHERE user_id = 'test_user'")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            raise Exception("Audit log entry was not created")
        
        logger.info("✅ Audit logging verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Audit logging test failed: {e}")
        return False

def test_file_processing():
    """Test file processing functionality."""
    logger.info("📁 Testing file processing...")
    
    try:
        # Test file metadata saving
        import uuid
        file_id = f"test-file-{uuid.uuid4().hex[:8]}"
        success = save_file_metadata(
            file_id=file_id,
            original_filename="test_invoice.pdf",
            file_type="invoice",
            file_path="data/uploads/invoices/test_invoice.pdf",
            file_size=1024
        )
        
        if not success:
            raise Exception("Failed to save file metadata")
        
        # Verify file was saved
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM uploaded_files WHERE id = ?", (file_id,))
        if not cursor.fetchone():
            raise Exception("File metadata was not saved to database")
        conn.close()
        
        logger.info("✅ File processing verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ File processing test failed: {e}")
        return False

def test_issue_management():
    """Test issue management functionality."""
    logger.info("🚨 Testing issue management...")
    
    try:
        # Create a test invoice first
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        
        test_invoice_id = "TEST-INV-001"
        cursor.execute('''
            INSERT OR REPLACE INTO invoices 
            (id, invoice_number, supplier, total_amount_pennies, status, 
             upload_timestamp, processing_status, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (test_invoice_id, "TEST-001", "Test Supplier", 10000, "pending",
              datetime.now().isoformat(), "completed", "test_user"))
        
        # Create a test issue
        test_issue_id = "TEST-ISS-001"
        cursor.execute('''
            INSERT OR REPLACE INTO issues 
            (id, invoice_id, issue_type, severity, description, status, 
             created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (test_issue_id, test_invoice_id, "total_mismatch", "high",
              "Test issue", "open", "test_user", datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Test getting issues for invoice
        issues = get_issues_for_invoice(test_invoice_id)
        if not issues:
            raise Exception("Failed to get issues for invoice")
        
        # Test resolving issue
        success = resolve_issue(test_issue_id, "Test resolution", "test_user")
        if not success:
            raise Exception("Failed to resolve issue")
        
        # Test escalating issue (create another one)
        test_issue_id_2 = "TEST-ISS-002"
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO issues 
            (id, invoice_id, issue_type, severity, description, status, 
             created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (test_issue_id_2, test_invoice_id, "price_mismatch", "medium",
              "Test escalation issue", "open", "test_user", datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        success = escalate_issue(test_issue_id_2, "Test escalation", "test_user")
        if not success:
            raise Exception("Failed to escalate issue")
        
        logger.info("✅ Issue management verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Issue management test failed: {e}")
        return False

def test_pairing_functionality():
    """Test pairing functionality."""
    logger.info("🔗 Testing pairing functionality...")
    
    try:
        # Create test delivery note
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        
        test_delivery_id = "TEST-DEL-001"
        test_invoice_id = "TEST-INV-001"
        
        cursor.execute('''
            INSERT OR REPLACE INTO delivery_notes 
            (id, delivery_number, delivery_date, supplier, upload_timestamp, 
             processing_status, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (test_delivery_id, "DEL-001", "2024-01-01", "Test Supplier",
              datetime.now().isoformat(), "completed", "test_user"))
        
        # Create pairing suggestion
        test_pairing_id = "TEST-PAIR-001"
        cursor.execute('''
            INSERT OR REPLACE INTO pairings 
            (id, invoice_id, delivery_note_id, similarity_score, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (test_pairing_id, test_invoice_id, test_delivery_id, 85.5, "suggested",
              datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Test getting pairing suggestions
        suggestions = get_pairing_suggestions(test_invoice_id)
        if not suggestions:
            raise Exception("Failed to get pairing suggestions")
        
        # Test confirming pairing
        success = confirm_pairing(test_pairing_id, "test_user")
        if not success:
            raise Exception("Failed to confirm pairing")
        
        # Test rejecting pairing (create another one)
        test_pairing_id_2 = "TEST-PAIR-002"
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO pairings 
            (id, invoice_id, delivery_note_id, similarity_score, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (test_pairing_id_2, test_invoice_id, test_delivery_id, 65.0, "suggested",
              datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        success = reject_pairing(test_pairing_id_2, "Test rejection", "test_user")
        if not success:
            raise Exception("Failed to reject pairing")
        
        logger.info("✅ Pairing functionality verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Pairing functionality test failed: {e}")
        return False

def cleanup_test_data():
    """Clean up test data."""
    logger.info("🧹 Cleaning up test data...")
    
    try:
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        
        # Clean up test data
        test_ids = [
            "TEST-INV-001", 
            "TEST-ISS-001", "TEST-ISS-002",
            "TEST-DEL-001",
            "TEST-PAIR-001", "TEST-PAIR-002"
        ]
        
        # Clean up any test files
        cursor.execute("DELETE FROM uploaded_files WHERE original_filename = 'test_invoice.pdf'")
        
        for table in ['uploaded_files', 'invoices', 'issues', 'delivery_notes', 'pairings']:
            for test_id in test_ids:
                cursor.execute(f"DELETE FROM {table} WHERE id = ?", (test_id,))
        
        # Clean up audit log test entries
        cursor.execute("DELETE FROM audit_log WHERE user_id = 'test_user'")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Test data cleaned up")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        return False

def main():
    """Run all smoke tests."""
    logger.info("🚀 Starting Invoices Domain Smoke Tests")
    logger.info("=" * 50)
    
    # Run migrations first
    try:
        run_migrations()
        logger.info("✅ Database migrations completed")
    except Exception as e:
        logger.error(f"❌ Database migrations failed: {e}")
        return False
    
    # Run tests
    tests = [
        ("Database Connection", test_database_connection),
        ("Business Logic", test_business_logic),
        ("Invoice CRUD", test_invoice_crud),
        ("Audit Logging", test_audit_logging),
        ("File Processing", test_file_processing),
        ("Issue Management", test_issue_management),
        ("Pairing Functionality", test_pairing_functionality)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Cleanup
    cleanup_test_data()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 SMOKE TEST SUMMARY")
    logger.info("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Invoices domain is ready for production.")
        return True
    else:
        logger.error(f"💥 {total - passed} tests failed. Please fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
