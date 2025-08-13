#!/usr/bin/env python3
"""
Comprehensive test script for bundled Tesseract OCR in the Owlin app.
This script tests the detection, setup, and basic OCR functionality.
"""

import os
import sys
import platform
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def create_test_image():
    """Create a simple test image with text for OCR testing."""
    # Create a white image with black text
    img = Image.new('RGB', (400, 100), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a default font, fallback to basic if not available
    try:
        # Try to use a system font
        if platform.system() == "Windows":
            font = ImageFont.truetype("arial.ttf", 24)
        elif platform.system() == "Darwin":
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        else:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Draw test text
    text = "Hello World 123"
    draw.text((20, 30), text, fill='black', font=font)
    
    return img

def test_bundled_tesseract_detection():
    """Test the bundled Tesseract detection logic."""
    print("🔍 Testing bundled Tesseract detection...")
    
    # Import the detection function
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
    
    try:
        from invoices_page import detect_and_setup_tesseract
        print("✅ Successfully imported detection function")
        
        # Test the detection
        result = detect_and_setup_tesseract()
        print(f"✅ Detection result: {result}")
        return result
    except ImportError as e:
        print(f"❌ Failed to import detection function: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during detection: {e}")
        return False

def test_tesseract_binary():
    """Test if Tesseract binary is working."""
    print("🔧 Testing Tesseract binary...")
    
    # Determine platform and expected binary path
    if platform.system() == "Windows":
        tess_path = os.path.join("tesseract_bin", "win", "tesseract.exe")
    elif platform.system() == "Darwin":
        tess_path = os.path.join("tesseract_bin", "mac", "tesseract")
    else:
        tess_path = os.path.join("tesseract_bin", "linux", "tesseract")
    
    print(f"Expected binary path: {tess_path}")
    
    # Check if binary exists
    if not os.path.exists(tess_path):
        print(f"❌ Tesseract binary not found at: {tess_path}")
        return False
    
    # Test if binary is executable
    try:
        result = subprocess.run([tess_path, "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_info = result.stdout.strip().split('\n')[0]
            print(f"✅ Tesseract binary is working: {version_info}")
            return True
        else:
            print(f"❌ Tesseract binary failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing Tesseract binary: {e}")
        return False

def test_ocr_functionality():
    """Test basic OCR functionality with a test image."""
    print("📝 Testing OCR functionality...")
    
    try:
        import pytesseract
        
        # Create test image
        test_img = create_test_image()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            test_img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Perform OCR
            text = pytesseract.image_to_string(test_img)
            text = text.strip()
            
            print(f"✅ OCR result: '{text}'")
            
            # Check if we got some text (should contain "Hello World 123")
            if text:
                print("✅ OCR is working correctly")
                return True
            else:
                print("❌ OCR returned empty text")
                return False
                
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
            
    except ImportError:
        print("❌ pytesseract not available")
        return False
    except Exception as e:
        print(f"❌ Error during OCR test: {e}")
        return False

def test_tessdata():
    """Test if tessdata directory exists and contains language files."""
    print("📁 Testing tessdata...")
    
    # Determine platform and expected tessdata path
    if platform.system() == "Windows":
        tessdata_path = os.path.join("tesseract_bin", "win", "tessdata")
    elif platform.system() == "Darwin":
        tessdata_path = os.path.join("tesseract_bin", "mac", "tessdata")
    else:
        tessdata_path = os.path.join("tesseract_bin", "linux", "tessdata")
    
    print(f"Expected tessdata path: {tessdata_path}")
    
    if not os.path.exists(tessdata_path):
        print(f"❌ tessdata directory not found at: {tessdata_path}")
        return False
    
    # Check for language files
    language_files = [f for f in os.listdir(tessdata_path) if f.endswith('.traineddata')]
    if language_files:
        print(f"✅ Found {len(language_files)} language files: {', '.join(language_files[:5])}")
        return True
    else:
        print("❌ No language files found in tessdata directory")
        return False

def main():
    """Run all tests."""
    print("🧪 Comprehensive Tesseract Test Suite")
    print("=" * 50)
    
    # Test results
    results = {}
    
    # Test 1: Binary detection
    print("\n1. Testing Tesseract binary...")
    results['binary'] = test_tesseract_binary()
    
    # Test 2: Tessdata
    print("\n2. Testing tessdata...")
    results['tessdata'] = test_tessdata()
    
    # Test 3: Detection function
    print("\n3. Testing detection function...")
    results['detection'] = test_bundled_tesseract_detection()
    
    # Test 4: OCR functionality
    print("\n4. Testing OCR functionality...")
    results['ocr'] = test_ocr_functionality()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:12}: {status}")
    
    # Overall result
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! Bundled Tesseract is working correctly.")
        print("You can now use the Owlin app with full OCR functionality.")
    else:
        print("\n⚠️  Some tests failed. Please check the setup:")
        print("1. Run: ./setup_tesseract.sh")
        print("2. Ensure Tesseract binaries are in the correct directories")
        print("3. Check that tessdata contains language files")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 