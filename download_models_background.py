#!/usr/bin/env python3
"""
Background Model Download

This script downloads OCR models in the background with progress tracking.
"""

import sys
import os
import time
import threading
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def download_with_progress():
    """Download models with progress tracking"""
    print("🔄 Starting background model download...")
    print("⏳ This will take 2-5 minutes on first run...")
    
    try:
        from paddleocr import PaddleOCR
        
        print("📦 Step 1: Initializing PaddleOCR...")
        start_time = time.time()
        
        # Initialize PaddleOCR
        paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
        )
        
        download_time = time.time() - start_time
        print(f"✅ Models downloaded in {download_time:.1f} seconds")
        
        # Test the models
        print("🧪 Testing models...")
        from PIL import Image
        test_image = Image.new('RGB', (100, 50), color='white')
        results = paddle_ocr.ocr(test_image)
        
        print(f"✅ Model test successful")
        return True
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def run_download_with_timeout(timeout_minutes=10):
    """Run download with timeout"""
    print(f"⏰ Setting timeout to {timeout_minutes} minutes...")
    
    # Create a thread for the download
    download_thread = threading.Thread(target=download_with_progress)
    download_thread.daemon = True
    download_thread.start()
    
    # Wait for completion or timeout
    download_thread.join(timeout=timeout_minutes * 60)
    
    if download_thread.is_alive():
        print(f"⏰ Download timed out after {timeout_minutes} minutes")
        return False
    else:
        print("✅ Download completed successfully")
        return True

def create_cache_file():
    """Create a cache file to track downloaded models"""
    try:
        cache_file = Path("data/ocr_models_cache.txt")
        cache_file.parent.mkdir(exist_ok=True)
        
        with open(cache_file, 'w') as f:
            f.write(f"Models downloaded at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("PaddleOCR models are ready for use\n")
        
        print("✅ Cache file created")
        return True
    except Exception as e:
        print(f"❌ Cache creation failed: {e}")
        return False

def test_quick_ocr():
    """Quick test of OCR after download"""
    print("🔄 Quick OCR test...")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        from PIL import Image
        
        engine = EnhancedOCREngine()
        test_image = Image.new('RGB', (100, 50), color='white')
        
        # Quick Tesseract test
        results = engine._run_tesseract_raw(test_image, 1)
        print(f"✅ Quick test successful - {len(results)} results")
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False

def main():
    """Main download process"""
    print("🔬 Background Model Download")
    print("=" * 30)
    
    # Step 1: Download models with timeout
    if not run_download_with_timeout(10):  # 10 minute timeout
        print("❌ Model download failed or timed out")
        print("💡 You can try again or use Tesseract-only mode")
        return
    
    # Step 2: Create cache
    if not create_cache_file():
        print("❌ Cache creation failed")
        return
    
    # Step 3: Quick test
    if not test_quick_ocr():
        print("❌ Quick test failed")
        return
    
    print("\n🎉 Model download completed!")
    print("The OCR system should now work without hanging.")

if __name__ == "__main__":
    main() 