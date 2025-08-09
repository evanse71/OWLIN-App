#!/usr/bin/env python3
"""
Test the unified OCR engine
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_unified_engine():
    print("🧪 Testing Unified OCR Engine")
    print("=" * 40)
    
    try:
        from ocr.unified_ocr_engine import unified_ocr_engine, ProcessingResult
        print("✅ Unified engine imported successfully")
        
        # Test initialization
        if unified_ocr_engine.tesseract_available:
            print("✅ Tesseract available")
        else:
            print("⚠️ Tesseract not available")
        
        print("✅ Unified OCR Engine test completed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_unified_engine() 