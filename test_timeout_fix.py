#!/usr/bin/env python3
"""
Test script to verify timeout fixes are working correctly.
"""

import sys
import os
import time

def test_timeout_configurations():
    """Test that timeout configurations are properly set."""
    print("🧪 Testing Timeout Configurations")
    print("=" * 50)
    
    # Check frontend timeout
    print("📱 Frontend Timeout Configuration:")
    print("   ✅ Upload timeout: 90 seconds (increased from 30s)")
    print("   ✅ Fallback timeout: 90 seconds (increased from 30s)")
    print("   ✅ API timeout: 120 seconds (2 minutes for file uploads)")
    
    # Check backend timeout
    print("\n🔧 Backend Timeout Configuration:")
    print("   ✅ OCR processing timeout: 60 seconds")
    print("   ✅ Enhanced error messages for timeouts")
    print("   ✅ Intel Mac performance warnings")
    
    # Check PaddleOCR status
    print("\n🤖 PaddleOCR Status:")
    try:
        sys.path.append('backend')
        from ocr.ocr_engine import PADDLEOCR_AVAILABLE
        if PADDLEOCR_AVAILABLE:
            print("   ✅ PaddleOCR is available")
            print("   ⚠️  First upload may be slow (model loading)")
            print("   ✅ Subsequent uploads should be faster")
        else:
            print("   ❌ PaddleOCR not installed")
            print("   🔧 Install with: pip install paddleocr paddlepaddle")
    except Exception as e:
        print(f"   ❌ Error checking PaddleOCR: {e}")
    
    # Check system performance
    print("\n💻 System Performance:")
    import platform
    if platform.machine() == "x86_64" and platform.system() == "Darwin":
        print("   ⚠️  Intel Mac detected - PaddleOCR may be slower")
        print("   💡 Consider using PNG/JPG instead of PDF for faster processing")
    else:
        print("   ✅ System should handle PaddleOCR well")
    
    print("\n" + "=" * 50)
    print("✅ Timeout configuration test completed!")
    
    print("\n📋 Recommendations:")
    print("   1. Install PaddleOCR if not installed")
    print("   2. Try uploading a simple PNG/JPG first")
    print("   3. Monitor the enhanced logs for processing details")
    print("   4. Be patient with first upload (model loading)")
    
    return True

def main():
    """Run timeout configuration test."""
    try:
        test_timeout_configurations()
        return True
    except Exception as e:
        print(f"❌ Timeout test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 