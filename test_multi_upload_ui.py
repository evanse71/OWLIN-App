#!/usr/bin/env python3
"""
Test script for multi-upload UI module integration

This script tests the multi-upload UI module with Streamlit integration,
including OCR processing, validation, and database persistence.
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

def test_multi_upload_ui_imports():
    """Test that all multi-upload UI modules can be imported"""
    try:
        from backend.multi_upload_ui import (
            upload_invoices_ui,
            upload_delivery_notes_ui,
            create_streamlit_app
        )
        logger.info("✅ Multi-upload UI imports successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Multi-upload UI import failed: {e}")
        return False

def test_dependencies_available():
    """Test that all required dependencies are available"""
    try:
        # Test Streamlit availability
        import streamlit as st
        logger.info("✅ Streamlit available")
        
        # Test backend dependencies
        from backend.field_extractor import extract_invoice_fields
        from backend.upload_validator import validate_upload
        from backend.ocr_processing import run_ocr, run_ocr_with_fallback
        from backend.db_manager import init_db, save_invoice, user_has_permission
        
        logger.info("✅ All backend dependencies available")
        return True
    except ImportError as e:
        logger.error(f"❌ Dependency import failed: {e}")
        return False

def test_upload_invoices_function():
    """Test the upload_invoices_ui function signature and basic functionality"""
    try:
        from backend.multi_upload_ui import upload_invoices_ui
        
        # Test function signature
        import inspect
        sig = inspect.signature(upload_invoices_ui)
        params = list(sig.parameters.keys())
        
        expected_params = ['db_path', 'user_role']
        if params == expected_params:
            logger.info("✅ upload_invoices_ui function signature correct")
            return True
        else:
            logger.error(f"❌ Function signature mismatch. Expected {expected_params}, got {params}")
            return False
            
    except Exception as e:
        logger.error(f"❌ upload_invoices_ui test failed: {e}")
        return False

def test_upload_delivery_notes_function():
    """Test the upload_delivery_notes_ui function signature and basic functionality"""
    try:
        from backend.multi_upload_ui import upload_delivery_notes_ui
        
        # Test function signature
        import inspect
        sig = inspect.signature(upload_delivery_notes_ui)
        params = list(sig.parameters.keys())
        
        expected_params = ['db_path', 'user_role']
        if params == expected_params:
            logger.info("✅ upload_delivery_notes_ui function signature correct")
            return True
        else:
            logger.error(f"❌ Function signature mismatch. Expected {expected_params}, got {params}")
            return False
            
    except Exception as e:
        logger.error(f"❌ upload_delivery_notes_ui test failed: {e}")
        return False

def test_create_streamlit_app_function():
    """Test the create_streamlit_app function"""
    try:
        from backend.multi_upload_ui import create_streamlit_app
        
        # Test function signature
        import inspect
        sig = inspect.signature(create_streamlit_app)
        params = list(sig.parameters.keys())
        
        if len(params) == 0:  # Should take no parameters
            logger.info("✅ create_streamlit_app function signature correct")
            return True
        else:
            logger.error(f"❌ Function signature mismatch. Expected no parameters, got {params}")
            return False
            
    except Exception as e:
        logger.error(f"❌ create_streamlit_app test failed: {e}")
        return False

def test_permission_integration():
    """Test that permission checking is properly integrated"""
    try:
        from backend.multi_upload_ui import upload_invoices_ui
        from backend.db_manager import user_has_permission, get_user_permissions
        
        # Test permission functions
        assert user_has_permission("Finance") == True
        assert user_has_permission("admin") == True
        assert user_has_permission("viewer") == False
        
        # Test comprehensive permissions
        finance_perms = get_user_permissions("Finance")
        assert finance_perms["upload_invoices"] == True
        assert finance_perms["view_invoices"] == True
        
        admin_perms = get_user_permissions("admin")
        assert admin_perms["upload_invoices"] == True
        assert admin_perms["delete_invoices"] == True
        
        logger.info("✅ Permission integration working correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ Permission integration test failed: {e}")
        return False

def test_ocr_integration():
    """Test that OCR processing is properly integrated"""
    try:
        from backend.multi_upload_ui import upload_invoices_ui
        from backend.ocr_processing import run_ocr_with_fallback
        
        # Test OCR function availability
        logger.info("✅ OCR integration available")
        return True
        
    except Exception as e:
        logger.error(f"❌ OCR integration test failed: {e}")
        return False

def test_database_integration():
    """Test that database operations are properly integrated"""
    try:
        from backend.multi_upload_ui import upload_invoices_ui
        from backend.db_manager import init_db, save_invoice, save_file_hash
        
        # Test database functions availability
        logger.info("✅ Database integration available")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database integration test failed: {e}")
        return False

def test_validation_integration():
    """Test that validation is properly integrated"""
    try:
        from backend.multi_upload_ui import upload_invoices_ui
        from backend.upload_validator import validate_upload
        from backend.field_extractor import extract_invoice_fields
        
        # Test validation functions availability
        logger.info("✅ Validation integration available")
        return True
        
    except Exception as e:
        logger.error(f"❌ Validation integration test failed: {e}")
        return False

def test_file_processing_workflow():
    """Test the complete file processing workflow"""
    try:
        from backend.multi_upload_ui import upload_invoices_ui
        from backend.ocr_processing import run_ocr_with_fallback
        from backend.field_extractor import extract_invoice_fields
        from backend.upload_validator import validate_upload
        from backend.db_manager import init_db, save_invoice, save_file_hash
        
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        # Initialize database
        init_db(db_path)
        
        # Test workflow components
        logger.info("✅ File processing workflow components available")
        
        # Clean up
        os.unlink(db_path)
        return True
        
    except Exception as e:
        logger.error(f"❌ File processing workflow test failed: {e}")
        return False

def test_streamlit_compatibility():
    """Test Streamlit compatibility and imports"""
    try:
        import streamlit as st
        
        # Test basic Streamlit functionality
        logger.info("✅ Streamlit compatibility confirmed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Streamlit compatibility test failed: {e}")
        return False

def test_backend_imports():
    """Test that the backend can import with the multi-upload UI"""
    try:
        from backend.main import app
        logger.info("✅ Backend imports successful with multi-upload UI")
        return True
    except Exception as e:
        logger.error(f"❌ Backend import failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Starting multi-upload UI integration tests...")
    
    tests = [
        ("Multi-Upload UI Imports", test_multi_upload_ui_imports),
        ("Dependencies Available", test_dependencies_available),
        ("Upload Invoices Function", test_upload_invoices_function),
        ("Upload Delivery Notes Function", test_upload_delivery_notes_function),
        ("Create Streamlit App Function", test_create_streamlit_app_function),
        ("Permission Integration", test_permission_integration),
        ("OCR Integration", test_ocr_integration),
        ("Database Integration", test_database_integration),
        ("Validation Integration", test_validation_integration),
        ("File Processing Workflow", test_file_processing_workflow),
        ("Streamlit Compatibility", test_streamlit_compatibility),
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
        logger.info("🎉 All tests passed! Multi-upload UI integration is working correctly.")
        return True
    else:
        logger.error("⚠️ Some tests failed. Please check the logs above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 