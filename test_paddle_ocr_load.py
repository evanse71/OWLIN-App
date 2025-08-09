#!/usr/bin/env python3
"""
Test script to check PaddleOCR load time and basic functionality.
"""

import sys
import os
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_paddle_ocr_load_time():
    """Test how long it takes to load PaddleOCR."""
    print("🧪 Testing PaddleOCR Load Time")
    
    try:
        print("🔄 Importing PaddleOCR...")
        from paddleocr import PaddleOCR
        
        print("🔄 Initializing PaddleOCR model...")
        start_time = time.time()
        
        # Initialize PaddleOCR
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        
        load_time = time.time() - start_time
        print(f"✅ PaddleOCR load time: {load_time:.2f} seconds")
        
        if load_time > 30:
            print("⚠️ WARNING: PaddleOCR took more than 30 seconds to load!")
            print("   This may cause timeout issues in production.")
        elif load_time > 10:
            print("⚠️ WARNING: PaddleOCR took more than 10 seconds to load.")
            print("   Consider implementing lazy loading or caching.")
        else:
            print("✅ PaddleOCR load time is acceptable.")
        
        return ocr, load_time
        
    except ImportError as e:
        print(f"❌ PaddleOCR not installed: {e}")
        return None, 0
    except Exception as e:
        print(f"❌ PaddleOCR initialization failed: {e}")
        return None, 0

def test_paddle_ocr_basic_functionality(ocr_model):
    """Test basic PaddleOCR functionality with a simple test."""
    print("\n🧪 Testing PaddleOCR Basic Functionality")
    
    if not ocr_model:
        print("❌ No PaddleOCR model available for testing")
        return False
    
    try:
        # Create a simple test image with text
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        
        print("🔄 Creating test image...")
        
        # Create a simple image with text
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a font, fallback to default if not available
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 10), "Test Invoice", fill='black', font=font)
        draw.text((10, 40), "Total: $100.00", fill='black', font=font)
        
        # Convert to numpy array
        img_array = np.array(img)
        
        print("🔄 Running PaddleOCR on test image...")
        start_time = time.time()
        
        result = ocr_model.ocr(img_array)
        
        process_time = time.time() - start_time
        print(f"✅ PaddleOCR processing time: {process_time:.2f} seconds")
        
        if result and len(result) > 0:
            print("✅ PaddleOCR returned results:")
            for line in result:
                if line and len(line) > 0:
                    for item in line:
                        if len(item) >= 2:
                            text = item[1]
                            confidence = item[2]
                            print(f"   Text: '{text}' (confidence: {confidence:.2f})")
        else:
            print("⚠️ PaddleOCR returned no results")
        
        if process_time > 10:
            print("⚠️ WARNING: PaddleOCR processing took more than 10 seconds!")
            print("   This may cause timeout issues in production.")
        else:
            print("✅ PaddleOCR processing time is acceptable.")
        
        return True
        
    except Exception as e:
        print(f"❌ PaddleOCR functionality test failed: {e}")
        return False

def test_system_info():
    """Test system information to help diagnose performance issues."""
    print("\n🧪 Testing System Information")
    
    import platform
    import psutil
    
    print(f"📊 System: {platform.system()} {platform.release()}")
    print(f"📊 Architecture: {platform.machine()}")
    print(f"📊 Python: {platform.python_version()}")
    
    # CPU info
    cpu_count = psutil.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"📊 CPU: {cpu_count} cores, {cpu_percent}% usage")
    
    # Memory info
    memory = psutil.virtual_memory()
    print(f"📊 Memory: {memory.total / (1024**3):.1f}GB total, {memory.percent}% used")
    
    # Check if we're on Mac with Intel vs Apple Silicon
    if platform.system() == "Darwin":
        import subprocess
        try:
            result = subprocess.run(['uname', '-m'], capture_output=True, text=True)
            arch = result.stdout.strip()
            if arch == "x86_64":
                print("⚠️ WARNING: Running on Intel Mac - PaddleOCR may be slower")
            elif arch == "arm64":
                print("✅ Running on Apple Silicon Mac - should be faster")
            else:
                print(f"📊 Architecture: {arch}")
        except:
            print("⚠️ Could not determine Mac architecture")
    
    return True

def test_file_processing_simulation():
    """Simulate file processing to check for potential issues."""
    print("\n🧪 Testing File Processing Simulation")
    
    try:
        # Test PDF to image conversion
        from pdf2image import convert_from_path
        
        print("🔄 Testing PDF to image conversion...")
        
        # Create a simple test PDF if available
        test_pdf = "test_invoice.pdf"
        if os.path.exists(test_pdf):
            print(f"📄 Found test PDF: {test_pdf}")
            
            start_time = time.time()
            images = convert_from_path(test_pdf, dpi=300)
            conversion_time = time.time() - start_time
            
            print(f"✅ PDF conversion time: {conversion_time:.2f} seconds for {len(images)} pages")
            
            if conversion_time > 5:
                print("⚠️ WARNING: PDF conversion took more than 5 seconds!")
            else:
                print("✅ PDF conversion time is acceptable.")
        else:
            print("ℹ️ No test PDF found - skipping PDF conversion test")
        
        return True
        
    except ImportError:
        print("⚠️ pdf2image not available - skipping PDF conversion test")
        return True
    except Exception as e:
        print(f"❌ File processing simulation failed: {e}")
        return False

def main():
    """Run all PaddleOCR diagnostic tests."""
    print("🚀 Starting PaddleOCR Diagnostic Tests")
    print("=" * 50)
    
    try:
        # Test system info
        test_system_info()
        
        # Test file processing
        test_file_processing_simulation()
        
        # Test PaddleOCR load time
        ocr_model, load_time = test_paddle_ocr_load_time()
        
        # Test basic functionality
        if ocr_model:
            test_paddle_ocr_basic_functionality(ocr_model)
        
        print("\n" + "=" * 50)
        print("✅ All diagnostic tests completed!")
        
        # Summary and recommendations
        print("\n📋 Summary and Recommendations:")
        
        if load_time > 30:
            print("❌ CRITICAL: PaddleOCR load time is too high!")
            print("   - Consider implementing lazy loading")
            print("   - Consider using a lighter OCR model")
            print("   - Check system resources")
        elif load_time > 10:
            print("⚠️ WARNING: PaddleOCR load time is high")
            print("   - Consider implementing caching")
            print("   - Monitor for timeout issues")
        else:
            print("✅ PaddleOCR load time is acceptable")
        
        print("\n🔧 Next Steps:")
        print("   1. Check the enhanced logging in ocr_engine.py")
        print("   2. Try uploading a simple PNG/JPG first")
        print("   3. Monitor the logs for where timeouts occur")
        print("   4. Consider implementing timeout handling")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Diagnostic tests failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 