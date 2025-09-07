#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all critical imports"""
    print("🔍 Testing imports...")
    
    try:
        print("Testing routes imports...")
        from routes import upload_enhanced, matching, upload_validation
        print("✅ Routes imports successful")
    except ImportError as e:
        print(f"❌ Routes import failed: {e}")
        return False
    
    try:
        print("Testing upload imports...")
        from upload import adaptive_processor, multi_page_processor
        print("✅ Upload imports successful")
    except ImportError as e:
        print(f"❌ Upload import failed: {e}")
        return False
    
    try:
        print("Testing OCR imports...")
        from ocr import enhanced_ocr_engine, enhanced_line_item_extractor
        print("✅ OCR imports successful")
    except ImportError as e:
        print(f"❌ OCR import failed: {e}")
        return False
    
    try:
        print("Testing agent imports...")
        from agent import get_agent_info
        print("✅ Agent imports successful")
    except ImportError as e:
        print(f"❌ Agent import failed: {e}")
        return False
    
    try:
        print("Testing upload_pipeline import...")
        from upload_pipeline import process_document_enhanced
        print("✅ Upload pipeline import successful")
    except ImportError as e:
        print(f"❌ Upload pipeline import failed: {e}")
        return False
    
    print("🎉 All imports successful!")
    return True

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("✅ Backend imports are ready!")
    else:
        print("❌ Some imports failed - check the errors above") 