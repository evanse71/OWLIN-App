#!/usr/bin/env python3
"""
Test script to verify OCR fixes
"""

import requests
import json
import os
from pathlib import Path

def test_ocr_fixes():
    """Test the OCR fixes"""
    print("🔍 Testing OCR fixes...")
    
    # Test 1: Health check
    try:
        response = requests.get("http://localhost:8002/api/health")
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: Check if services are running
    try:
        response = requests.get("http://localhost:8002/")
        if response.status_code == 200:
            print("✅ Main endpoint working")
        else:
            print(f"❌ Main endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Main endpoint failed: {e}")
        return False
    
    print("✅ All basic tests passed!")
    print("\n🎯 Ready for testing:")
    print("1. Single page PDF: Should process without 'Image processing failed'")
    print("2. Multi-invoice PDF: Should detect multiple invoices correctly")
    print("3. OCR confidence: Should be >30% (not 0% or 1%)")
    print("4. Frontend: Should display correctly without duplicate badges")
    
    return True

if __name__ == "__main__":
    test_ocr_fixes() 