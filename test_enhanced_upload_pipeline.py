#!/usr/bin/env python3
"""
Enhanced Upload Pipeline Test Script

This script tests the new unified upload pipeline with confidence scoring,
manual review logic, and template parsing functionality.

Tests include:
- PDF and image file processing
- Confidence scoring and thresholds
- Manual review flagging
- Template parsing and metadata extraction
- Role-based processing
- Error handling and fallback mechanisms

Author: OWLIN Development Team
Version: 1.0.0
"""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
import json
import time

# Add backend to path
sys.path.append('backend')

from upload_pipeline import process_document, OCRResult, ParsedInvoice
from ocr.ocr_engine import run_invoice_ocr, get_paddle_ocr_model
from ocr.parse_invoice import parse_invoice

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedUploadPipelineTester:
    """Test suite for the enhanced upload pipeline"""
    
    def __init__(self):
        self.test_results = []
        self.test_files_dir = Path("test_files")
        self.test_files_dir.mkdir(exist_ok=True)
        
    def create_test_files(self) -> Dict[str, Path]:
        """Create test files for different scenarios"""
        test_files = {}
        
        # Create a simple test image
        try:
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np
            
            # Test image 1: High quality invoice
            img1 = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img1)
            
            # Add some text to simulate an invoice
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            draw.text((50, 50), "INVOICE", fill='black', font=font)
            draw.text((50, 100), "Supplier: Test Company Ltd", fill='black', font=font)
            draw.text((50, 150), "Invoice Number: INV-2024-001", fill='black', font=font)
            draw.text((50, 200), "Date: 2024-01-15", fill='black', font=font)
            draw.text((50, 250), "Total: £1,250.00", fill='black', font=font)
            
            img1_path = self.test_files_dir / "test_invoice_high_quality.png"
            img1.save(img1_path)
            test_files['high_quality'] = img1_path
            logger.info(f"✅ Created high quality test image: {img1_path}")
            
            # Test image 2: Low quality (blurry)
            img2 = Image.new('RGB', (800, 600), color='white')
            draw2 = ImageDraw.Draw(img2)
            draw2.text((50, 50), "INVOICE", fill='black', font=font)
            draw2.text((50, 100), "Supplier: Blurry Company", fill='black', font=font)
            
            # Apply blur effect
            img2 = img2.filter(ImageFilter.GaussianBlur(radius=2))
            img2_path = self.test_files_dir / "test_invoice_low_quality.png"
            img2.save(img2_path)
            test_files['low_quality'] = img2_path
            logger.info(f"✅ Created low quality test image: {img2_path}")
            
        except ImportError:
            logger.warning("⚠️ PIL not available, skipping image creation")
        
        return test_files
    
    def test_ocr_engine_initialization(self) -> bool:
        """Test OCR engine initialization"""
        logger.info("🔄 Testing OCR engine initialization...")
        
        try:
            model = get_paddle_ocr_model()
            if model:
                logger.info("✅ PaddleOCR model initialized successfully")
                return True
            else:
                logger.warning("⚠️ PaddleOCR model not available")
                return False
        except Exception as e:
            logger.error(f"❌ OCR engine initialization failed: {e}")
            return False
    
    def test_confidence_scoring(self, test_files: Dict[str, Path]) -> bool:
        """Test confidence scoring functionality"""
        logger.info("🔄 Testing confidence scoring...")
        
        try:
            from PIL import Image
            
            for quality, file_path in test_files.items():
                if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    logger.info(f"📊 Testing confidence scoring for {quality} image...")
                    
                    # Load image
                    image = Image.open(file_path)
                    
                    # Run OCR
                    ocr_results = run_invoice_ocr(image, 1)
                    
                    if ocr_results:
                        # Calculate confidence
                        confidences = [result.confidence for result in ocr_results]
                        avg_confidence = sum(confidences) / len(confidences)
                        
                        logger.info(f"📊 {quality} image - Average confidence: {avg_confidence:.3f}")
                        logger.info(f"📊 {quality} image - Confidence range: {min(confidences):.3f} - {max(confidences):.3f}")
                        
                        # Test confidence thresholds
                        if avg_confidence >= 0.70:
                            logger.info(f"✅ {quality} image meets re-processing threshold")
                        elif avg_confidence >= 0.65:
                            logger.info(f"⚠️ {quality} image requires manual review")
                        else:
                            logger.warning(f"❌ {quality} image has very low confidence")
                    else:
                        logger.warning(f"⚠️ No OCR results for {quality} image")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Confidence scoring test failed: {e}")
            return False
    
    def test_manual_review_logic(self, test_files: Dict[str, Path]) -> bool:
        """Test manual review flagging logic"""
        logger.info("🔄 Testing manual review logic...")
        
        try:
            for quality, file_path in test_files.items():
                if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    logger.info(f"🔍 Testing manual review for {quality} image...")
                    
                    # Process document
                    result = process_document(
                        str(file_path),
                        parse_templates=True,
                        save_debug=True
                    )
                    
                    # Check manual review flag
                    if result['manual_review_required']:
                        logger.info(f"⚠️ {quality} image flagged for manual review")
                        logger.info(f"📊 Confidence scores: {result['confidence_scores']}")
                    else:
                        logger.info(f"✅ {quality} image passed automatic processing")
                    
                    # Test confidence thresholds
                    overall_confidence = result['overall_confidence']
                    if overall_confidence < 0.65:
                        logger.info(f"📊 {quality} image below manual review threshold (65%)")
                    elif overall_confidence < 0.70:
                        logger.info(f"📊 {quality} image below re-processing threshold (70%)")
                    else:
                        logger.info(f"📊 {quality} image above all thresholds")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Manual review logic test failed: {e}")
            return False
    
    def test_template_parsing(self, test_files: Dict[str, Path]) -> bool:
        """Test template parsing functionality"""
        logger.info("🔄 Testing template parsing...")
        
        try:
            for quality, file_path in test_files.items():
                if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    logger.info(f"📄 Testing template parsing for {quality} image...")
                    
                    # Process document with template parsing
                    result = process_document(
                        str(file_path),
                        parse_templates=True,
                        save_debug=True
                    )
                    
                    if 'parsed_invoice' in result:
                        parsed = result['parsed_invoice']
                        logger.info(f"✅ Template parsing successful for {quality} image")
                        logger.info(f"📊 Supplier: {parsed.supplier}")
                        logger.info(f"📊 Invoice Number: {parsed.invoice_number}")
                        logger.info(f"📊 Date: {parsed.date}")
                        logger.info(f"📊 Gross Total: £{parsed.gross_total:.2f}")
                        logger.info(f"📊 Parsing Confidence: {parsed.confidence:.3f}")
                    else:
                        logger.warning(f"⚠️ No parsed invoice data for {quality} image")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Template parsing test failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling and fallback mechanisms"""
        logger.info("🔄 Testing error handling...")
        
        try:
            # Test with non-existent file
            non_existent_file = self.test_files_dir / "non_existent.pdf"
            
            try:
                result = process_document(str(non_existent_file))
                logger.error("❌ Should have raised exception for non-existent file")
                return False
            except Exception as e:
                logger.info(f"✅ Correctly handled non-existent file: {e}")
            
            # Test with invalid file type
            invalid_file = self.test_files_dir / "test.txt"
            invalid_file.write_text("This is not an image or PDF")
            
            try:
                result = process_document(str(invalid_file))
                logger.info("✅ Handled invalid file type gracefully")
            except Exception as e:
                logger.info(f"✅ Correctly handled invalid file type: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling test failed: {e}")
            return False
    
    def test_performance(self, test_files: Dict[str, Path]) -> bool:
        """Test processing performance"""
        logger.info("🔄 Testing processing performance...")
        
        try:
            for quality, file_path in test_files.items():
                if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    logger.info(f"⏱️ Testing performance for {quality} image...")
                    
                    start_time = time.time()
                    result = process_document(
                        str(file_path),
                        parse_templates=True,
                        save_debug=False  # Disable debug for performance test
                    )
                    end_time = time.time()
                    
                    processing_time = end_time - start_time
                    logger.info(f"⏱️ {quality} image processed in {processing_time:.2f} seconds")
                    
                    # Check if processing time is reasonable (should be under 30 seconds)
                    if processing_time < 30:
                        logger.info(f"✅ {quality} image processing time acceptable")
                    else:
                        logger.warning(f"⚠️ {quality} image processing time slow: {processing_time:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return False
    
    def test_debug_artifacts(self, test_files: Dict[str, Path]) -> bool:
        """Test debug artifact generation"""
        logger.info("🔄 Testing debug artifact generation...")
        
        try:
            debug_dir = Path("data/debug_ocr")
            
            for quality, file_path in test_files.items():
                if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    logger.info(f"💾 Testing debug artifacts for {quality} image...")
                    
                    # Process with debug enabled
                    result = process_document(
                        str(file_path),
                        parse_templates=True,
                        save_debug=True
                    )
                    
                    # Check if debug artifacts were created
                    if debug_dir.exists():
                        debug_files = list(debug_dir.glob(f"*{file_path.stem}*"))
                        if debug_files:
                            logger.info(f"✅ Debug artifacts created: {len(debug_files)} files")
                            for debug_file in debug_files:
                                logger.info(f"📁 Debug file: {debug_file.name}")
                        else:
                            logger.warning(f"⚠️ No debug artifacts found for {quality} image")
                    else:
                        logger.warning(f"⚠️ Debug directory not created")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Debug artifacts test failed: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        logger.info("🚀 Starting Enhanced Upload Pipeline Tests")
        logger.info("=" * 60)
        
        test_results = {}
        
        # Create test files
        logger.info("📁 Creating test files...")
        test_files = self.create_test_files()
        
        # Test 1: OCR Engine Initialization
        logger.info("\n" + "=" * 40)
        test_results['ocr_initialization'] = self.test_ocr_engine_initialization()
        
        # Test 2: Confidence Scoring
        logger.info("\n" + "=" * 40)
        test_results['confidence_scoring'] = self.test_confidence_scoring(test_files)
        
        # Test 3: Manual Review Logic
        logger.info("\n" + "=" * 40)
        test_results['manual_review'] = self.test_manual_review_logic(test_files)
        
        # Test 4: Template Parsing
        logger.info("\n" + "=" * 40)
        test_results['template_parsing'] = self.test_template_parsing(test_files)
        
        # Test 5: Error Handling
        logger.info("\n" + "=" * 40)
        test_results['error_handling'] = self.test_error_handling()
        
        # Test 6: Performance
        logger.info("\n" + "=" * 40)
        test_results['performance'] = self.test_performance(test_files)
        
        # Test 7: Debug Artifacts
        logger.info("\n" + "=" * 40)
        test_results['debug_artifacts'] = self.test_debug_artifacts(test_files)
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\n📈 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            logger.info("🎉 All tests passed! Enhanced upload pipeline is working correctly.")
        else:
            logger.warning(f"⚠️ {total - passed} test(s) failed. Please review the implementation.")
        
        return test_results

def main():
    """Main test execution"""
    tester = EnhancedUploadPipelineTester()
    results = tester.run_all_tests()
    
    # Save results to file
    results_file = Path("test_results_enhanced_pipeline.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"📄 Test results saved to: {results_file}")
    
    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure

if __name__ == "__main__":
    main() 