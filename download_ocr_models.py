#!/usr/bin/env python3
"""
Download and Cache OCR Models

This script downloads PaddleOCR models once and caches them for future use.
"""

import sys
import os
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def download_paddle_ocr_models():
    """Download PaddleOCR models with progress tracking"""
    print("🔄 Downloading PaddleOCR models...")
    print("⏳ This may take a few minutes on first run...")
    
    try:
        from paddleocr import PaddleOCR
        
        print("📦 Initializing PaddleOCR...")
        start_time = time.time()
        
        # Initialize PaddleOCR - this will download models
        paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
        )
        
        download_time = time.time() - start_time
        print(f"✅ PaddleOCR models downloaded successfully in {download_time:.1f} seconds")
        
        # Test the models
        print("🧪 Testing downloaded models...")
        from PIL import Image
        test_image = Image.new('RGB', (100, 50), color='white')
        
        # Test OCR
        results = paddle_ocr.ocr(test_image)
        print(f"✅ Model test successful - {len(results[0]) if results and results[0] else 0} results")
        
        return True
        
    except Exception as e:
        print(f"❌ PaddleOCR model download failed: {e}")
        return False

def create_model_cache():
    """Create a model cache file to track downloaded models"""
    print("📁 Creating model cache...")
    try:
        cache_file = Path("data/ocr_models_cache.txt")
        cache_file.parent.mkdir(exist_ok=True)
        
        with open(cache_file, 'w') as f:
            f.write(f"Models downloaded at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("PaddleOCR models are ready for use\n")
        
        print("✅ Model cache created")
        return True
        
    except Exception as e:
        print(f"❌ Cache creation failed: {e}")
        return False

def test_enhanced_ocr_after_download():
    """Test the enhanced OCR engine after model download"""
    print("🔄 Testing enhanced OCR engine...")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        from PIL import Image
        
        engine = EnhancedOCREngine()
        test_image = Image.new('RGB', (100, 50), color='white')
        
        print("🧪 Testing Tesseract...")
        tesseract_results = engine._run_tesseract_raw(test_image, 1)
        print(f"✅ Tesseract: {len(tesseract_results)} results")
        
        print("🧪 Testing PaddleOCR...")
        if engine.paddle_ocr is not None:
            paddle_results = engine._run_paddle_ocr_raw(test_image, 1)
            print(f"✅ PaddleOCR: {len(paddle_results)} results")
        else:
            print("⚠️ PaddleOCR not available")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced OCR test failed: {e}")
        return False

def test_full_processing():
    """Test full document processing after model download"""
    print("🔄 Testing full document processing...")
    try:
        from backend.upload.adaptive_processor import AdaptiveProcessor
        
        processor = AdaptiveProcessor()
        test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
        
        if not test_file.exists():
            print("❌ Test file not found")
            return False
        
        print("📄 Processing test document...")
        start_time = time.time()
        result = processor.process_with_recovery(str(test_file))
        processing_time = time.time() - start_time
        
        print(f"✅ Full processing completed in {processing_time:.1f} seconds!")
        print(f"   Document Type: {result.document_type}")
        print(f"   Confidence: {result.overall_confidence}")
        print(f"   Line Items: {len(result.line_items)}")
        print(f"   Pages Processed: {result.pages_processed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Full processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Download models and test the system"""
    print("🔬 Download and Cache OCR Models")
    print("=" * 40)
    
    # Step 1: Download PaddleOCR models
    if not download_paddle_ocr_models():
        print("❌ Model download failed")
        return
    
    # Step 2: Create model cache
    if not create_model_cache():
        print("❌ Cache creation failed")
        return
    
    # Step 3: Test enhanced OCR engine
    if not test_enhanced_ocr_after_download():
        print("❌ Enhanced OCR test failed")
        return
    
    # Step 4: Test full processing
    if not test_full_processing():
        print("❌ Full processing test failed")
        return
    
    print("\n🎉 All OCR models downloaded and tested successfully!")
    print("The upload flow should now work without hanging or 0% confidence issues.")

if __name__ == "__main__":
    main() 