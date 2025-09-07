#!/usr/bin/env python3
"""
Test script for the Advanced OCR System
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_advanced_ocr_import():
    """Test if advanced OCR processor can be imported"""
    try:
        from backend.advanced_ocr_processor import advanced_ocr_processor
        print("✅ Advanced OCR processor imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import advanced OCR processor: {e}")
        return False

def test_dependencies():
    """Test if required dependencies are available"""
    dependencies = [
        ('fitz', 'PyMuPDF'),
        ('pytesseract', 'pytesseract'),
        ('cv2', 'opencv-python'),
        ('numpy', 'numpy'),
        ('easyocr', 'easyocr'),
        ('transformers', 'transformers'),
        ('torch', 'torch'),
        ('sentence_transformers', 'sentence-transformers'),
        ('spacy', 'spacy'),
        ('fuzzywuzzy', 'fuzzywuzzy'),
    ]
    
    missing_deps = []
    
    for module, package in dependencies:
        try:
            __import__(module)
            print(f"✅ {package} available")
        except ImportError:
            print(f"❌ {package} missing")
            missing_deps.append(package)
    
    if missing_deps:
        print(f"\n⚠️ Missing dependencies: {', '.join(missing_deps)}")
        print("Run: pip3 install -r requirements_advanced_ocr.txt")
        return False
    else:
        print("\n✅ All dependencies available")
        return True

def test_system_dependencies():
    """Test if system dependencies are available"""
    import subprocess
    
    system_deps = ['tesseract', 'pdftoppm']
    missing_sys_deps = []
    
    for dep in system_deps:
        try:
            result = subprocess.run([dep, '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {dep} available")
            else:
                print(f"❌ {dep} not working")
                missing_sys_deps.append(dep)
        except FileNotFoundError:
            print(f"❌ {dep} not found")
            missing_sys_deps.append(dep)
    
    if missing_sys_deps:
        print(f"\n⚠️ Missing system dependencies: {', '.join(missing_sys_deps)}")
        print("Install with: brew install tesseract poppler")
        return False
    else:
        print("\n✅ All system dependencies available")
        return True

def test_spacy_model():
    """Test if spaCy model is available"""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("✅ spaCy English model available")
        return True
    except OSError:
        print("❌ spaCy English model not found")
        print("Install with: python3 -m spacy download en_core_web_sm")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Advanced OCR System...\n")
    
    tests = [
        ("Dependencies", test_dependencies),
        ("System Dependencies", test_system_dependencies),
        ("spaCy Model", test_spacy_model),
        ("Advanced OCR Import", test_advanced_ocr_import),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"🔍 Testing {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Advanced OCR system is ready.")
        print("\n🚀 To start the advanced backend:")
        print("   ./start_advanced_backend.sh")
    else:
        print("⚠️ Some tests failed. Please install missing dependencies.")
        print("\n📦 To install dependencies:")
        print("   ./install_advanced_ocr.sh")

if __name__ == "__main__":
    main() 