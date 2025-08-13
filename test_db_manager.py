#!/usr/bin/env python3
"""
Test script for database manager integration

This script tests the database manager module integration with the upload pipeline,
including database initialization, data persistence, and role-based access control.
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_manager_imports():
    """Test that all database manager modules can be imported"""
    try:
        from backend.db_manager import (
            init_db, save_invoice, save_delivery_note, save_file_hash,
            check_duplicate_invoice, check_duplicate_file_hash,
            get_all_invoices, get_all_delivery_notes, get_database_stats,
            user_has_permission, get_user_permissions, log_processing_result
        )
        logger.info("✅ Database manager imports successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Database manager import failed: {e}")
        return False

def test_database_initialization():
    """Test database initialization"""
    try:
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        # Initialize database
        from backend.db_manager import init_db
        init_db(db_path)
        
        # Check if database file exists
        if os.path.exists(db_path):
            logger.info("✅ Database initialization successful")
            os.unlink(db_path)  # Clean up
            return True
        else:
            logger.error("❌ Database file not created")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

def test_invoice_operations():
    """Test invoice save and retrieve operations"""
    try:
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        from backend.db_manager import init_db, save_invoice, get_all_invoices, check_duplicate_invoice
        
        # Initialize database
        init_db(db_path)
        
        # Test data
        test_invoice = {
            'supplier_name': 'Test Supplier Ltd',
            'invoice_number': 'INV-2024-001',
            'invoice_date': '2024-01-15',
            'net_amount': 1000.00,
            'vat_amount': 200.00,
            'total_amount': 1200.00,
            'currency': 'GBP',
            'file_path': '/test/path/invoice.pdf',
            'file_hash': 'abc123def456',
            'ocr_confidence': 85.5
        }
        
        # Save invoice
        success = save_invoice(test_invoice, db_path)
        if not success:
            logger.error("❌ Failed to save invoice")
            return False
        
        # Check for duplicate
        is_duplicate = check_duplicate_invoice('INV-2024-001', db_path)
        if not is_duplicate:
            logger.error("❌ Duplicate check failed")
            return False
        
        # Retrieve all invoices
        invoices = get_all_invoices(db_path)
        if len(invoices) != 1:
            logger.error(f"❌ Expected 1 invoice, got {len(invoices)}")
            return False
        
        # Verify invoice data
        invoice = invoices[0]
        if invoice['invoice_number'] != 'INV-2024-001':
            logger.error("❌ Invoice number mismatch")
            return False
        
        logger.info("✅ Invoice operations successful")
        os.unlink(db_path)  # Clean up
        return True
        
    except Exception as e:
        logger.error(f"❌ Invoice operations failed: {e}")
        return False

def test_delivery_note_operations():
    """Test delivery note save and retrieve operations"""
    try:
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        from backend.db_manager import init_db, save_delivery_note, get_all_delivery_notes
        
        # Initialize database
        init_db(db_path)
        
        # Test data
        test_delivery = {
            'supplier_name': 'Test Supplier Ltd',
            'delivery_number': 'DN-2024-001',
            'delivery_date': '2024-01-15',
            'total_items': 5,
            'file_path': '/test/path/delivery.pdf',
            'file_hash': 'def456ghi789',
            'ocr_confidence': 90.0
        }
        
        # Save delivery note
        success = save_delivery_note(test_delivery, db_path)
        if not success:
            logger.error("❌ Failed to save delivery note")
            return False
        
        # Retrieve all delivery notes
        delivery_notes = get_all_delivery_notes(db_path)
        if len(delivery_notes) != 1:
            logger.error(f"❌ Expected 1 delivery note, got {len(delivery_notes)}")
            return False
        
        # Verify delivery note data
        delivery = delivery_notes[0]
        if delivery['delivery_number'] != 'DN-2024-001':
            logger.error("❌ Delivery number mismatch")
            return False
        
        logger.info("✅ Delivery note operations successful")
        os.unlink(db_path)  # Clean up
        return True
        
    except Exception as e:
        logger.error(f"❌ Delivery note operations failed: {e}")
        return False

def test_file_hash_operations():
    """Test file hash operations for duplicate detection"""
    try:
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        from backend.db_manager import init_db, save_file_hash, check_duplicate_file_hash
        
        # Initialize database
        init_db(db_path)
        
        # Test file hash
        test_hash = "abc123def456ghi789"
        file_path = "/test/path/file.pdf"
        file_size = 1024
        mime_type = "application/pdf"
        
        # Save file hash
        success = save_file_hash(test_hash, file_path, file_size, mime_type, db_path)
        if not success:
            logger.error("❌ Failed to save file hash")
            return False
        
        # Check for duplicate
        is_duplicate = check_duplicate_file_hash(test_hash, db_path)
        if not is_duplicate:
            logger.error("❌ Duplicate file hash check failed")
            return False
        
        logger.info("✅ File hash operations successful")
        os.unlink(db_path)  # Clean up
        return True
        
    except Exception as e:
        logger.error(f"❌ File hash operations failed: {e}")
        return False

def test_user_permissions():
    """Test user permission functions"""
    try:
        from backend.db_manager import user_has_permission, get_user_permissions
        
        # Test user_has_permission
        assert user_has_permission("Finance") == True
        assert user_has_permission("admin") == True
        assert user_has_permission("GM") == True
        assert user_has_permission("viewer") == False
        assert user_has_permission(None) == False
        
        # Test get_user_permissions
        finance_perms = get_user_permissions("Finance")
        assert finance_perms["upload_invoices"] == True
        assert finance_perms["view_invoices"] == True
        assert finance_perms["delete_invoices"] == False
        
        admin_perms = get_user_permissions("admin")
        assert admin_perms["upload_invoices"] == True
        assert admin_perms["delete_invoices"] == True
        assert admin_perms["manage_users"] == True
        
        viewer_perms = get_user_permissions("viewer")
        assert viewer_perms["upload_invoices"] == False
        assert viewer_perms["view_invoices"] == True
        
        logger.info("✅ User permissions successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ User permissions failed: {e}")
        return False

def test_database_stats():
    """Test database statistics function"""
    try:
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        from backend.db_manager import init_db, get_database_stats
        
        # Initialize database
        init_db(db_path)
        
        # Get stats
        stats = get_database_stats(db_path)
        
        # Verify stats structure
        required_keys = ['invoice_count', 'delivery_count', 'file_hash_count', 'total_amount', 'recent_uploads']
        for key in required_keys:
            if key not in stats:
                logger.error(f"❌ Missing key in stats: {key}")
                return False
        
        # Verify initial values
        assert stats['invoice_count'] == 0
        assert stats['delivery_count'] == 0
        assert stats['file_hash_count'] == 0
        
        logger.info("✅ Database stats successful")
        os.unlink(db_path)  # Clean up
        return True
        
    except Exception as e:
        logger.error(f"❌ Database stats failed: {e}")
        return False

def test_upload_pipeline_integration():
    """Test that the upload pipeline can use the database manager"""
    try:
        from backend.upload_pipeline import process_document
        
        logger.info("✅ Upload pipeline integration successful")
        return True
    except Exception as e:
        logger.error(f"❌ Upload pipeline integration failed: {e}")
        return False

def test_backend_imports():
    """Test that the backend can import with the database manager"""
    try:
        from backend.main import app
        logger.info("✅ Backend imports successful with database manager")
        return True
    except Exception as e:
        logger.error(f"❌ Backend import failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Starting database manager integration tests...")
    
    tests = [
        ("Database Manager Imports", test_database_manager_imports),
        ("Database Initialization", test_database_initialization),
        ("Invoice Operations", test_invoice_operations),
        ("Delivery Note Operations", test_delivery_note_operations),
        ("File Hash Operations", test_file_hash_operations),
        ("User Permissions", test_user_permissions),
        ("Database Stats", test_database_stats),
        ("Upload Pipeline Integration", test_upload_pipeline_integration),
        ("Backend Imports", test_backend_imports)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running test: {test_name}")
        try:
            if test_func():
                logger.info(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
    
    logger.info(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Database manager integration is working correctly.")
        return True
    else:
        logger.error("⚠️ Some tests failed. Please check the logs above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 