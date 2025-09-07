#!/usr/bin/env python3
"""
Pre-load OCR Models

This script pre-loads the OCR models so they're available immediately when needed.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def preload_paddle_ocr():
    """Pre-load PaddleOCR models"""
    print("🔄 Pre-loading PaddleOCR models...")
    try:
        from paddleocr import PaddleOCR
        
        # Initialize PaddleOCR with all models
        paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
        )
        
        print("✅ PaddleOCR models pre-loaded successfully")
        return True
    except Exception as e:
        print(f"❌ PaddleOCR pre-loading failed: {e}")
        return False

def preload_enhanced_ocr_engine():
    """Pre-load the enhanced OCR engine"""
    print("🔄 Pre-loading enhanced OCR engine...")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        
        # Create engine instance (this will trigger model loading)
        engine = EnhancedOCREngine()
        
        # Force load PaddleOCR models
        engine._ensure_paddle_ocr_loaded()
        
        print("✅ Enhanced OCR engine pre-loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Enhanced OCR engine pre-loading failed: {e}")
        return False

def test_ocr_after_preload():
    """Test OCR after pre-loading"""
    print("🔄 Testing OCR after pre-loading...")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        from PIL import Image
        
        engine = EnhancedOCREngine()
        test_image = Image.new('RGB', (100, 50), color='white')
        
        # Test Tesseract
        tesseract_results = engine._run_tesseract_raw(test_image, 1)
        print(f"✅ Tesseract test completed - {len(tesseract_results)} results")
        
        # Test PaddleOCR (if available)
        if engine.paddle_ocr is not None:
            paddle_results = engine._run_paddle_ocr_raw(test_image, 1)
            print(f"✅ PaddleOCR test completed - {len(paddle_results)} results")
        else:
            print("⚠️ PaddleOCR not available")
        
        return True
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        return False

def main():
    """Pre-load all OCR models"""
    print("🔬 Pre-loading OCR Models")
    print("=" * 30)
    
    # Step 1: Pre-load PaddleOCR
    if not preload_paddle_ocr():
        print("❌ PaddleOCR pre-loading failed")
        return
    
    # Step 2: Pre-load enhanced OCR engine
    if not preload_enhanced_ocr_engine():
        print("❌ Enhanced OCR engine pre-loading failed")
        return
    
    # Step 3: Test OCR after pre-loading
    if not test_ocr_after_preload():
        print("❌ OCR test failed")
        return
    
    print("\n✅ All OCR models pre-loaded successfully!")
    print("The OCR system should now work without hanging during processing.")

if __name__ == "__main__":
    main() 