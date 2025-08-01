#!/usr/bin/env python3
"""
Test script to verify OCR functionality is working properly.
This script tests both Tesseract and PaddleOCR with sample files.
"""

import sys
import os
import tempfile
from pathlib import Path
import logging

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ocr_dependencies():
    """Test that all OCR dependencies are available."""
    print("🧪 Testing OCR Dependencies")
    
    try:
        import pytesseract
        print("✅ pytesseract imported successfully")
        version = pytesseract.get_tesseract_version()
        print(f"   Tesseract version: {version}")
    except Exception as e:
        print(f"❌ pytesseract import failed: {e}")
        return False
    
    try:
        from PIL import Image
        print("✅ Pillow imported successfully")
    except Exception as e:
        print(f"❌ Pillow import failed: {e}")
        return False
    
    try:
        import pdf2image
        print("✅ pdf2image imported successfully")
    except Exception as e:
        print(f"❌ pdf2image import failed: {e}")
        return False
    
    try:
        import subprocess
        result = subprocess.run(['pdftoppm', '-h'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ poppler-utils (pdftoppm) available")
        else:
            print("❌ poppler-utils not available")
            return False
    except Exception as e:
        print(f"❌ poppler-utils check failed: {e}")
        return False
    
    return True

def test_tesseract_ocr():
    """Test Tesseract OCR with a simple text image."""
    print("\n🧪 Testing Tesseract OCR")
    
    try:
        from backend.ocr.ocr_processing import run_ocr
        
        # Create a simple test image with text
        from PIL import Image, ImageDraw, ImageFont
        import tempfile
        
        # Create a test image with text
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a system font, fallback to default
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 10), "INVOICE #12345", fill='black', font=font)
        draw.text((10, 40), "Supplier: Test Company", fill='black', font=font)
        draw.text((10, 70), "Total: $100.00", fill='black', font=font)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            img.save(tmp_file.name)
            test_file = tmp_file.name
        
        print(f"   Created test image: {test_file}")
        
        # Run OCR
        results = run_ocr(test_file)
        
        # Clean up
        os.unlink(test_file)
        
        if results:
            print(f"✅ Tesseract OCR successful: {len(results)} text blocks")
            for i, result in enumerate(results[:3]):  # Show first 3 results
                print(f"   {i+1}. '{result['text']}' (conf: {result['confidence']:.1f}%)")
            return True
        else:
            print("❌ Tesseract OCR returned no results")
            return False
            
    except Exception as e:
        print(f"❌ Tesseract OCR test failed: {e}")
        return False

def test_paddle_ocr():
    """Test PaddleOCR functionality."""
    print("\n🧪 Testing PaddleOCR")
    
    try:
        from backend.ocr.ocr_processing import run_ocr_with_fallback
        
        # Create a simple test image with text
        from PIL import Image, ImageDraw, ImageFont
        import tempfile
        
        # Create a test image with text
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a system font, fallback to default
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 10), "INVOICE #67890", fill='black', font=font)
        draw.text((10, 40), "Supplier: Paddle Test", fill='black', font=font)
        draw.text((10, 70), "Total: $250.00", fill='black', font=font)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            img.save(tmp_file.name)
            test_file = tmp_file.name
        
        print(f"   Created test image: {test_file}")
        
        # Run OCR with PaddleOCR fallback
        results = run_ocr_with_fallback(test_file, use_paddle_first=True)
        
        # Clean up
        os.unlink(test_file)
        
        if results:
            print(f"✅ PaddleOCR successful: {len(results)} text blocks")
            for i, result in enumerate(results[:3]):  # Show first 3 results
                print(f"   {i+1}. '{result['text']}' (conf: {result['confidence']:.1f}%)")
            return True
        else:
            print("❌ PaddleOCR returned no results")
            return False
            
    except Exception as e:
        print(f"❌ PaddleOCR test failed: {e}")
        return False

def test_field_extraction():
    """Test field extraction with OCR results."""
    print("\n🧪 Testing Field Extraction")
    
    try:
        from backend.ocr.field_extractor import extract_invoice_fields
        
        # Create mock OCR results
        mock_ocr_results = [
            {
                "text": "INVOICE #12345",
                "bbox": [10, 10, 200, 30],
                "confidence": 95.0,
                "page_num": 1
            },
            {
                "text": "Supplier: Test Company Ltd",
                "bbox": [10, 40, 300, 60],
                "confidence": 90.0,
                "page_num": 1
            },
            {
                "text": "Date: 2024-01-15",
                "bbox": [10, 70, 200, 90],
                "confidence": 85.0,
                "page_num": 1
            },
            {
                "text": "Total: $1,250.00",
                "bbox": [300, 70, 400, 90],
                "confidence": 92.0,
                "page_num": 1
            }
        ]
        
        # Extract fields
        extracted_fields = extract_invoice_fields(mock_ocr_results)
        
        print("✅ Field extraction successful")
        print(f"   Supplier: {extracted_fields.get('supplier_name', 'Unknown')}")
        print(f"   Invoice Number: {extracted_fields.get('invoice_number', 'Unknown')}")
        print(f"   Date: {extracted_fields.get('invoice_date', 'Unknown')}")
        print(f"   Total: {extracted_fields.get('total_amount', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Field extraction test failed: {e}")
        return False

def test_upload_pipeline():
    """Test the complete upload pipeline with OCR."""
    print("\n🧪 Testing Upload Pipeline")
    
    try:
        from backend.upload_pipeline import process_document
        
        # Create a simple test image
        from PIL import Image, ImageDraw, ImageFont
        import tempfile
        
        # Create a test invoice image
        img = Image.new('RGB', (600, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a system font, fallback to default
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Draw invoice content
        draw.text((20, 20), "INVOICE", fill='black', font=font)
        draw.text((20, 50), "Invoice #: INV-2024-001", fill='black', font=font)
        draw.text((20, 80), "Supplier: ABC Company Ltd", fill='black', font=font)
        draw.text((20, 110), "Date: 2024-01-15", fill='black', font=font)
        draw.text((20, 140), "Subtotal: $500.00", fill='black', font=font)
        draw.text((20, 170), "VAT (20%): $100.00", fill='black', font=font)
        draw.text((400, 170), "TOTAL: $600.00", fill='black', font=font)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            img.save(tmp_file.name)
            test_file = tmp_file.name
        
        print(f"   Created test invoice: {test_file}")
        
        # Process the document
        result = process_document(test_file, validate_upload=False)
        
        # Clean up
        os.unlink(test_file)
        
        if result and 'parsed_invoice' in result:
            invoice = result['parsed_invoice']
            print("✅ Upload pipeline successful")
            print(f"   Supplier: {invoice.supplier}")
            print(f"   Invoice Number: {invoice.invoice_number}")
            print(f"   Date: {invoice.date}")
            print(f"   Total: {invoice.gross_total}")
            return True
        else:
            print("❌ Upload pipeline failed or no invoice parsed")
            return False
            
    except Exception as e:
        print(f"❌ Upload pipeline test failed: {e}")
        return False

def main():
    """Run all OCR functionality tests."""
    print("🚀 Starting OCR Functionality Tests")
    print("=" * 50)
    
    tests = [
        ("OCR Dependencies", test_ocr_dependencies),
        ("Tesseract OCR", test_tesseract_ocr),
        ("PaddleOCR", test_paddle_ocr),
        ("Field Extraction", test_field_extraction),
        ("Upload Pipeline", test_upload_pipeline)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All OCR functionality tests passed!")
        print("✅ OCR is properly configured and working")
    else:
        print("⚠️ Some tests failed - OCR may not be fully functional")
        print("💡 Check the error messages above for specific issues")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 