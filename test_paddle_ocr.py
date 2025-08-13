#!/usr/bin/env python3
"""
Test script for PaddleOCR functionality.
This script tests PaddleOCR independently of the main application.
"""

import sys
import os
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def create_test_invoice_image():
    """Create a test invoice image for OCR testing."""
    # Create a white image
    img = Image.new('RGB', (600, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a system font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Add invoice text
    text_lines = [
        "INVOICE",
        "Invoice Number: INV-2025-001",
        "Date: 2025-01-15",
        "Supplier: Test Company Ltd",
        "Customer: Sample Customer",
        "",
        "Item Description          Qty    Price    Total",
        "--------------------------------------------",
        "Office Supplies           5      £10.50   £52.50",
        "Paper A4                  2      £15.00   £30.00",
        "Pens Blue                 10     £2.50    £25.00",
        "",
        "Subtotal:                                    £107.50",
        "VAT (20%):                                   £21.50",
        "Total:                                        £129.00"
    ]
    
    y_position = 20
    for line in text_lines:
        draw.text((20, y_position), line, fill='black', font=font)
        y_position += 25
    
    return img

def test_paddle_ocr_basic():
    """Test basic PaddleOCR functionality."""
    print("🧪 Testing basic PaddleOCR functionality...")
    
    try:
        from paddleocr import PaddleOCR
        
        # Initialize PaddleOCR
        start_time = time.time()
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        load_time = time.time() - start_time
        print(f"✅ PaddleOCR initialized in {load_time:.2f}s")
        
        # Create test image
        test_img = create_test_invoice_image()
        print("✅ Test invoice image created")
        
        # Run OCR
        start_time = time.time()
        result = ocr.ocr(np.array(test_img))
        ocr_time = time.time() - start_time
        print(f"✅ OCR completed in {ocr_time:.2f}s")
        
        # Analyze results
        if result and len(result) > 0:
            print(f"📊 Found {len(result)} text lines")
            total_confidence = 0.0
            line_count = 0
            extracted_text = []
            
            for line in result:
                if line and len(line) > 0:
                    for item in line:
                        if len(item) >= 2:
                            text = item[1]
                            confidence = item[2]
                            
                            # Handle both string and float confidence values
                            if isinstance(confidence, str):
                                try:
                                    confidence = float(confidence)
                                except ValueError:
                                    confidence = 0.0
                            elif not isinstance(confidence, (int, float)):
                                confidence = 0.0
                            
                            total_confidence += confidence
                            line_count += 1
                            extracted_text.append(text)
                            print(f"   Text: '{text}' (confidence: {confidence:.2f})")
            
            if line_count > 0:
                avg_confidence = total_confidence / line_count
                print(f"📊 Average confidence: {avg_confidence:.2f}")
                print(f"📊 Total lines detected: {line_count}")
                print(f"📊 Total text extracted: {' '.join(extracted_text)}")
                return True
            else:
                print("❌ No text detected")
                return False
        else:
            print("❌ No OCR results")
            return False
            
    except Exception as e:
        print(f"❌ PaddleOCR test failed: {str(e)}")
        return False

def test_paddle_ocr_with_pdf():
    """Test PaddleOCR with a PDF file if available."""
    print("\n🧪 Testing PaddleOCR with PDF file...")
    
    # Check if we have a test PDF
    test_pdf_path = "data/uploads/invoice_73318.pdf"
    if not os.path.exists(test_pdf_path):
        print(f"⚠️ Test PDF not found at {test_pdf_path}")
        return False
    
    try:
        from paddleocr import PaddleOCR
        from pdf2image import convert_from_path
        
        # Initialize PaddleOCR
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        print("✅ PaddleOCR initialized for PDF test")
        
        # Convert PDF to images
        print(f"🔄 Converting PDF: {test_pdf_path}")
        images = convert_from_path(test_pdf_path, dpi=300)
        print(f"✅ PDF converted to {len(images)} images at 300 DPI")
        
        if images:
            print(f"🔍 First image shape: {images[0].size}")
        
        # Process each page
        total_words = 0
        total_confidence = 0.0
        
        for i, image in enumerate(images):
            print(f"🔄 Processing page {i+1}...")
            
            # Run OCR
            result = ocr.ocr(np.array(image))
            
            if result and len(result) > 0:
                page_words = 0
                page_confidence = 0.0
                word_count = 0
                
                for line in result:
                    if line and len(line) > 0:
                        for item in line:
                            if len(item) >= 2:
                                text = item[1]
                                confidence = item[2]
                                
                                # Handle confidence values
                                if isinstance(confidence, str):
                                    try:
                                        confidence = float(confidence)
                                    except ValueError:
                                        confidence = 0.0
                                elif not isinstance(confidence, (int, float)):
                                    confidence = 0.0
                                
                                page_confidence += confidence
                                word_count += 1
                                page_words += len(text.split())
                
                avg_page_confidence = page_confidence / word_count if word_count > 0 else 0.0
                total_words += page_words
                total_confidence += avg_page_confidence
                
                print(f"📄 OCR page {i+1}: found {page_words} words, confidence ~{avg_page_confidence:.2f}%")
                
                # Log first few text blocks
                for line in result[:3]:
                    if line and len(line) > 0:
                        for item in line[:2]:  # First 2 items
                            if len(item) >= 2:
                                print(f"   → '{item[1]}' at {item[0]}")
            else:
                print(f"⚠️ No OCR results for page {i+1}")
        
        if total_words > 0:
            overall_confidence = total_confidence / len(images)
            print(f"✅ PDF OCR completed: {total_words} total words, avg confidence: {overall_confidence:.2f}%")
            return True
        else:
            print("❌ No text extracted from PDF")
            return False
            
    except Exception as e:
        print(f"❌ PDF OCR test failed: {str(e)}")
        return False

def main():
    """Run all PaddleOCR tests."""
    print("🚀 Starting PaddleOCR tests...\n")
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Basic PaddleOCR
    if test_paddle_ocr_basic():
        tests_passed += 1
    
    # Test 2: PDF OCR
    if test_paddle_ocr_with_pdf():
        tests_passed += 1
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✅ All PaddleOCR tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main()) 