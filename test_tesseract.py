#!/usr/bin/env python3
"""
Test script to verify bundled Tesseract installation
"""

import os
import sys
import platform
import subprocess

def test_bundled_tesseract():
    print("🧪 Testing bundled Tesseract installation...")
    
    # Determine platform
    if platform.system() == "Windows":
        tess_path = os.path.join("tesseract_bin", "win", "tesseract.exe")
    elif platform.system() == "Darwin":
        tess_path = os.path.join("tesseract_bin", "mac", "tesseract")
    else:
        tess_path = os.path.join("tesseract_bin", "linux", "tesseract")
    
    # Check if binary exists
    if not os.path.exists(tess_path):
        print(f"❌ Tesseract binary not found at: {tess_path}")
        return False
    
    # Test if binary is executable
    try:
        result = subprocess.run([tess_path, "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Tesseract binary is working: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Tesseract binary failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing Tesseract binary: {e}")
        return False

if __name__ == "__main__":
    success = test_bundled_tesseract()
    sys.exit(0 if success else 1)
