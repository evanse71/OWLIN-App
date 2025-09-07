#!/usr/bin/env python3
"""
Test current state and provide recommendations for PaddleOCR timeout issues.
"""

import sys
import os
import platform

def check_current_state():
    """Check the current state and provide recommendations."""
    print("🔍 Checking Current State")
    print("=" * 50)
    
    # Check system
    print(f"📊 System: {platform.system()} {platform.release()}")
    print(f"📊 Architecture: {platform.machine()}")
    
    # Check if PaddleOCR is installed
    try:
        from paddleocr import PaddleOCR
        print("✅ PaddleOCR is installed")
        paddle_installed = True
    except ImportError:
        print("❌ PaddleOCR is NOT installed")
        paddle_installed = False
    
    # Check if enhanced logging is working
    try:
        sys.path.append('backend')
        from ocr.ocr_engine import run_paddle_ocr, PADDLEOCR_AVAILABLE
        print(f"✅ Enhanced logging available: {PADDLEOCR_AVAILABLE}")
        logging_working = True
    except Exception as e:
        print(f"❌ Enhanced logging not working: {e}")
        logging_working = False
    
    # Check if servers are running
    import requests
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend server is running")
            backend_running = True
        else:
            print("❌ Backend server not responding")
            backend_running = False
    except:
        print("❌ Backend server not running")
        backend_running = False
    
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend server is running")
            frontend_running = True
        else:
            print("❌ Frontend server not responding")
            frontend_running = False
    except:
        print("❌ Frontend server not running")
        frontend_running = False
    
    return {
        "paddle_installed": paddle_installed,
        "logging_working": logging_working,
        "backend_running": backend_running,
        "frontend_running": frontend_running,
        "is_intel_mac": platform.machine() == "x86_64" and platform.system() == "Darwin"
    }

def provide_recommendations(state):
    """Provide specific recommendations based on current state."""
    print("\n📋 Recommendations")
    print("=" * 50)
    
    if not state["paddle_installed"]:
        print("❌ CRITICAL: PaddleOCR is not installed!")
        print("   This is why you're getting timeouts - the system is falling back to empty results.")
        print("\n🔧 Solution:")
        print("   1. Install PaddleOCR:")
        print("      pip install paddleocr paddlepaddle")
        print("   2. Or use the requirements file:")
        print("      pip install -r requirements_paddleocr.txt")
        print("   3. Restart the backend server after installation")
    
    if state["is_intel_mac"]:
        print("⚠️ WARNING: You're on an Intel Mac")
        print("   PaddleOCR may be slower on Intel Macs compared to Apple Silicon.")
        print("   Consider increasing timeout values or using lighter models.")
    
    if not state["backend_running"]:
        print("❌ Backend server is not running!")
        print("   Start it with: python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    
    if not state["frontend_running"]:
        print("❌ Frontend server is not running!")
        print("   Start it with: npm run dev")
    
    if state["paddle_installed"] and state["backend_running"]:
        print("✅ Good news: PaddleOCR is installed and backend is running")
        print("   The timeout issue might be due to:")
        print("   1. Large PDF files taking too long to process")
        print("   2. Intel Mac performance limitations")
        print("   3. First-time model loading (should be faster after first use)")
        
        print("\n🔧 Try these solutions:")
        print("   1. Upload a simple PNG/JPG instead of PDF")
        print("   2. Try a smaller file first")
        print("   3. Check the enhanced logs for where it's hanging")
        print("   4. Consider increasing timeout in upload_fixed.py")
    
    print("\n🔍 Next Steps:")
    print("   1. Install PaddleOCR if not installed")
    print("   2. Try uploading a simple image (PNG/JPG) first")
    print("   3. Monitor the enhanced logs to see where timeouts occur")
    print("   4. Check if the issue is PDF conversion or PaddleOCR processing")

def main():
    """Main function to check state and provide recommendations."""
    print("🚀 PaddleOCR Timeout Diagnosis")
    print("=" * 50)
    
    state = check_current_state()
    provide_recommendations(state)
    
    print("\n" + "=" * 50)
    print("✅ Diagnosis complete!")
    
    if not state["paddle_installed"]:
        print("\n❌ PRIMARY ISSUE: PaddleOCR not installed")
        print("   This is causing the timeout issues.")
    else:
        print("\n✅ PaddleOCR is installed - check logs for specific timeout location")

if __name__ == "__main__":
    main() 