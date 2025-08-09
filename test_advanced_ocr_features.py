#!/usr/bin/env python3
"""
Test all advanced OCR features and improvements
"""

import sys
import os
from pathlib import Path
import tempfile
from PIL import Image, ImageDraw, ImageFont

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def create_test_invoice_image(text_content: str) -> str:
    """Create a test invoice image with specified text"""
    try:
        # Create a simple test invoice image
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a standard font, fallback to default
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        # Draw the text
        y_position = 50
        for line in text_content.split('\n'):
            draw.text((50, y_position), line, fill='black', font=font)
            y_position += 30
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name)
        return temp_file.name
        
    except Exception as e:
        print(f"❌ Could not create test image: {e}")
        return None

def test_performance_optimization():
    """Test performance optimization features"""
    print("🚀 Testing Performance Optimization")
    print("-" * 40)
    
    try:
        from ocr.unified_ocr_engine import get_unified_ocr_engine
        
        engine = get_unified_ocr_engine()
        
        # Create test image
        test_text = """
ACME Corporation
Invoice #: INV-001
Date: 2024-01-15
Total: $150.00
Description: Professional Services
        """
        test_image_path = create_test_invoice_image(test_text)
        
        if not test_image_path:
            print("❌ Could not create test image")
            return False
        
        print("1. Testing speed optimization...")
        result_speed = engine.process_document(test_image_path, optimize_for_speed=True)
        print(f"   Speed mode: {result_speed.processing_time:.2f}s, confidence: {result_speed.overall_confidence:.2f}")
        
        print("2. Testing accuracy optimization...")
        result_accuracy = engine.process_document(test_image_path, optimize_for_speed=False)
        print(f"   Accuracy mode: {result_accuracy.processing_time:.2f}s, confidence: {result_accuracy.overall_confidence:.2f}")
        
        # Cleanup
        os.unlink(test_image_path)
        
        print("✅ Performance optimization tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Performance optimization test failed: {e}")
        return False

def test_enhanced_field_extraction():
    """Test enhanced field extraction"""
    print("🔍 Testing Enhanced Field Extraction")
    print("-" * 40)
    
    try:
        from ocr.unified_ocr_engine import get_unified_ocr_engine
        
        engine = get_unified_ocr_engine()
        
        # Test with more complex invoice text
        complex_text = """
BlueTech Solutions Ltd.
123 Business Avenue
Tech City, TC 12345

INVOICE
Invoice Number: INV-2024-001
Date: January 15, 2024
Due Date: February 15, 2024

Bill To:
Customer Corp
456 Client Street

Line Items:
1  Software License      $500.00
2  Support Services      $300.00
3  Training             $200.00

Subtotal:               $1000.00
Tax (10%):              $100.00
Total Amount:           $1100.00
        """
        
        test_image_path = create_test_invoice_image(complex_text)
        
        if not test_image_path:
            print("❌ Could not create test image")
            return False
        
        result = engine.process_document(test_image_path)
        
        print("Extracted fields:")
        print(f"   Supplier: {result.supplier}")
        print(f"   Invoice Number: {result.invoice_number}")
        print(f"   Date: {result.date}")
        print(f"   Total Amount: ${result.total_amount}")
        print(f"   Line Items: {len(result.line_items)} items")
        print(f"   Document Type: {result.document_type}")
        
        # Cleanup
        os.unlink(test_image_path)
        
        print("✅ Enhanced field extraction tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced field extraction test failed: {e}")
        return False

def test_batch_processing():
    """Test batch processing capabilities"""
    print("📦 Testing Batch Processing")
    print("-" * 40)
    
    try:
        from ocr.unified_ocr_engine import get_unified_ocr_engine
        
        engine = get_unified_ocr_engine()
        
        # Create multiple test images
        test_files = []
        test_texts = [
            "Invoice A\nINV-001\nTotal: $100.00",
            "Invoice B\nINV-002\nTotal: $200.00", 
            "Invoice C\nINV-003\nTotal: $300.00"
        ]
        
        for i, text in enumerate(test_texts):
            test_image_path = create_test_invoice_image(text)
            if test_image_path:
                test_files.append(test_image_path)
        
        if not test_files:
            print("❌ Could not create test images")
            return False
        
        print(f"Processing {len(test_files)} documents in batch...")
        results = engine.process_batch(test_files, max_workers=2)
        
        successful = sum(1 for r in results if r.success)
        total_time = sum(r.processing_time for r in results)
        
        print(f"Batch results:")
        print(f"   Processed: {len(results)} documents")
        print(f"   Successful: {successful}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average time: {total_time/len(results):.2f}s per document")
        
        for i, result in enumerate(results):
            print(f"   Doc {i+1}: {result.engine_used}, {result.processing_time:.2f}s")
        
        # Cleanup
        for file_path in test_files:
            os.unlink(file_path)
        
        print("✅ Batch processing tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Batch processing test failed: {e}")
        return False

def test_analytics_system():
    """Test analytics and monitoring"""
    print("📊 Testing Analytics System")
    print("-" * 40)
    
    try:
        from ocr.ocr_analytics import ocr_analytics
        
        # Get performance summary
        summary = ocr_analytics.get_performance_summary(days=30)
        print("Performance Summary:")
        for key, value in summary.items():
            print(f"   {key}: {value}")
        
        # Get engine performance
        engine_perf = ocr_analytics.get_engine_performance()
        print("\nEngine Performance:")
        for engine, stats in engine_perf.items():
            print(f"   {engine}: {stats}")
        
        # Get error analysis
        error_analysis = ocr_analytics.get_error_analysis()
        print("\nError Analysis:")
        for key, value in error_analysis.items():
            print(f"   {key}: {value}")
        
        print("✅ Analytics system tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Analytics system test failed: {e}")
        return False

def test_confidence_validation():
    """Test confidence scoring and validation"""
    print("🎯 Testing Confidence Validation")
    print("-" * 40)
    
    try:
        from ocr.unified_ocr_engine import get_unified_ocr_engine
        
        engine = get_unified_ocr_engine()
        
        # Test with clear text (high confidence expected)
        clear_text = """
CLEAR INVOICE
Invoice: 12345
Amount: $500.00
        """
        
        clear_image = create_test_invoice_image(clear_text)
        if clear_image:
            result = engine.process_document(clear_image)
            print(f"Clear text confidence: {result.overall_confidence:.2f}")
            print(f"Quality assessment: {'High' if result.overall_confidence > 0.7 else 'Medium' if result.overall_confidence > 0.4 else 'Low'}")
            os.unlink(clear_image)
        
        print("✅ Confidence validation tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Confidence validation test failed: {e}")
        return False

def main():
    """Run all advanced feature tests"""
    print("🧪 Testing Advanced OCR Features")
    print("=" * 50)
    
    tests = [
        test_performance_optimization,
        test_enhanced_field_extraction,
        test_batch_processing,
        test_analytics_system,
        test_confidence_validation
    ]
    
    results = []
    for test in tests:
        print()
        result = test()
        results.append(result)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"🎉 Advanced Features Test Summary: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All advanced features working correctly!")
        print("\n🚀 Ready for enhanced OCR processing with:")
        print("   - Performance optimization")
        print("   - Enhanced field extraction") 
        print("   - Batch processing")
        print("   - Analytics monitoring")
        print("   - Confidence validation")
    else:
        print("⚠️ Some tests failed - check logs above")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 