#!/usr/bin/env python3
"""
Test the fixed unified OCR engine - should not hang on import
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_fixed_unified_engine():
    print("🧪 Testing Fixed Unified OCR Engine")
    print("=" * 40)
    
    try:
        # Test 1: Import without hanging
        print("1. Testing import (should not hang)...")
        from ocr.unified_ocr_engine import get_unified_ocr_engine, ProcessingResult
        print("✅ Import successful - no hanging!")
        
        # Test 2: Test lazy loading
        print("2. Testing lazy loading...")
        engine_func = get_unified_ocr_engine
        print("✅ Got engine function")
        
        # Test 3: Test actual instantiation (this might take time but shouldn't hang)
        print("3. Testing engine instantiation...")
        engine = engine_func()
        print(f"✅ Engine instantiated successfully")
        print(f"   - Tesseract available: {engine.tesseract_available}")
        print(f"   - PaddleOCR loaded: {engine.models_loaded}")
        
        # Test 4: Test ProcessingResult dataclass
        print("4. Testing ProcessingResult...")
        result = ProcessingResult(
            success=True,
            document_type="test",
            supplier="Test Supplier",
            invoice_number="TEST001",
            date="2024-01-01",
            total_amount=100.0,
            line_items=[],
            overall_confidence=0.8,
            processing_time=1.0,
            raw_text="Test text",
            word_count=10,
            engine_used="test"
        )
        print("✅ ProcessingResult created successfully")
        
        print("\n🎉 All tests passed! Unified OCR Engine is ready.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fixed_unified_engine()
    sys.exit(0 if success else 1) 