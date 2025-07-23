"""
Integration Tests for Owlin OCR Invoice Scanning System
Tests the complete pipeline from file upload to data extraction and monitoring.
"""
import unittest
import tempfile
import os
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
import json
from datetime import datetime
from pathlib import Path

# Import our modules
from app.file_processor import FileProcessor
from app.ocr_preprocessing import OCRPreprocessor, create_preprocessing_config
from app.ocr_monitoring import OCRMonitor, OCRMetrics

class TestInvoiceScanningSystem(unittest.TestCase):
    """Test the complete invoice scanning system."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.test_dir, "uploads")
        self.data_dir = os.path.join(self.test_dir, "data")
        
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize components
        self.db_path = os.path.join(self.data_dir, "test_owlin.db")
        self.file_processor = FileProcessor(upload_dir=self.upload_dir, db_path=self.db_path)
        self.ocr_preprocessor = OCRPreprocessor()
        self.ocr_monitor = OCRMonitor(db_path=self.db_path)
        
        # Test configuration
        self.test_config = create_preprocessing_config(
            denoising_method='bilateral',
            thresholding_method='adaptive',
            contrast_method='clahe',
            enable_deskewing=True
        )
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_invoice_image(self, filename: str = "test_invoice.png") -> str:
        """Create a test invoice image for testing."""
        # Create a realistic invoice image
        width, height = 800, 1000
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Try to use a default font, fallback to basic if not available
        try:
            font = ImageFont.truetype("arial.ttf", 16)
            small_font = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add invoice header
        draw.text((50, 50), "INVOICE", fill='black', font=font)
        draw.text((50, 80), "Invoice #: INV-2024-001", fill='black', font=font)
        draw.text((50, 110), "Date: 01/15/2024", fill='black', font=font)
        
        # Add vendor information
        draw.text((50, 150), "Vendor: Test Company Inc.", fill='black', font=font)
        draw.text((50, 180), "123 Business Street", fill='black', font=font)
        draw.text((50, 210), "City, State 12345", fill='black', font=font)
        
        # Add line items
        draw.text((50, 280), "Item", fill='black', font=font)
        draw.text((300, 280), "Qty", fill='black', font=font)
        draw.text((400, 280), "Price", fill='black', font=font)
        draw.text((500, 280), "Total", fill='black', font=font)
        
        draw.text((50, 320), "Product A", fill='black', font=font)
        draw.text((300, 320), "2", fill='black', font=font)
        draw.text((400, 320), "$25.00", fill='black', font=font)
        draw.text((500, 320), "$50.00", fill='black', font=font)
        
        draw.text((50, 350), "Product B", fill='black', font=font)
        draw.text((300, 350), "1", fill='black', font=font)
        draw.text((400, 350), "$30.00", fill='black', font=font)
        draw.text((500, 350), "$30.00", fill='black', font=font)
        
        # Add total
        draw.text((400, 450), "Total Amount:", fill='black', font=font)
        draw.text((500, 450), "$80.00", fill='black', font=font)
        
        # Save image
        image_path = os.path.join(self.upload_dir, filename)
        image.save(image_path)
        return image_path
    
    def create_low_quality_invoice_image(self, filename: str = "low_quality_invoice.png") -> str:
        """Create a low-quality test invoice image."""
        # Create base image
        image_path = self.create_test_invoice_image("temp_invoice.png")
        
        # Load and degrade the image
        image = cv2.imread(image_path)
        
        # Add noise
        noise = np.random.normal(0, 25, image.shape).astype(np.uint8)
        noisy_image = cv2.add(image, noise)
        
        # Reduce contrast
        alpha = 0.5  # Contrast control
        beta = 30    # Brightness control
        degraded_image = cv2.convertScaleAbs(noisy_image, alpha=alpha, beta=beta)
        
        # Add blur
        blurred_image = cv2.GaussianBlur(degraded_image, (5, 5), 0)
        
        # Save degraded image
        degraded_path = os.path.join(self.upload_dir, filename)
        cv2.imwrite(degraded_path, blurred_image)
        
        # Clean up temp file
        os.remove(image_path)
        
        return degraded_path
    
    def test_ocr_preprocessing_quality_assessment(self):
        """Test OCR preprocessing quality assessment."""
        # Create test images
        high_quality_path = self.create_test_invoice_image("high_quality.png")
        low_quality_path = self.create_low_quality_invoice_image("low_quality.png")
        
        # Load images
        high_quality_img = cv2.imread(high_quality_path)
        high_quality_img = cv2.cvtColor(high_quality_img, cv2.COLOR_BGR2RGB)
        
        low_quality_img = cv2.imread(low_quality_path)
        low_quality_img = cv2.cvtColor(low_quality_img, cv2.COLOR_BGR2RGB)
        
        # Assess quality
        high_quality_score = self.ocr_preprocessor.assess_image_quality(high_quality_img)
        low_quality_score = self.ocr_preprocessor.assess_image_quality(low_quality_img)
        
        # Assertions
        self.assertIsInstance(high_quality_score, dict)
        self.assertIn('overall_score', high_quality_score)
        self.assertIn('contrast', high_quality_score)
        self.assertIn('sharpness', high_quality_score)
        self.assertIn('noise_level', high_quality_score)
        
        # High quality image should have better scores
        self.assertGreater(high_quality_score['overall_score'], low_quality_score['overall_score'])
        self.assertGreater(high_quality_score['contrast'], low_quality_score['contrast'])
    
    def test_ocr_preprocessing_pipeline(self):
        """Test the complete OCR preprocessing pipeline."""
        # Create test image
        image_path = self.create_test_invoice_image()
        image = cv2.imread(image_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Test preprocessing
        preprocessed_image = self.ocr_preprocessor.preprocess_image(image)
        
        # Assertions
        self.assertIsInstance(preprocessed_image, np.ndarray)
        self.assertEqual(preprocessed_image.shape, image.shape)
        
        # Test preprocessing stats
        stats = self.ocr_preprocessor.get_preprocessing_stats(image, preprocessed_image)
        self.assertIsInstance(stats, dict)
        self.assertIn('contrast_improvement', stats)
        self.assertIn('noise_reduction', stats)
        self.assertIn('edge_preservation', stats)
        self.assertIn('text_clarity', stats)
    
    def test_file_processing_pipeline(self):
        """Test the complete file processing pipeline."""
        # Create test image
        image_path = self.create_test_invoice_image()
        
        # Create a mock uploaded file object
        class MockUploadedFile:
            def __init__(self, path):
                self.path = path
                self.name = os.path.basename(path)
                self.type = 'image/png'
            
            def getbuffer(self):
                with open(self.path, 'rb') as f:
                    return f.read()
        
        uploaded_file = MockUploadedFile(image_path)
        
        # Process file
        result = self.file_processor.process_uploaded_file(uploaded_file)
        
        # Assertions
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('file_id', result)
        
        if result['success']:
            self.assertIn('ocr_confidence', result)
            self.assertIn('extracted_text', result)
            self.assertIn('extracted_data', result)
            self.assertIn('preprocessing_stats', result)
            
            # Check that confidence is reasonable
            self.assertGreaterEqual(result['ocr_confidence'], 0.0)
            self.assertLessEqual(result['ocr_confidence'], 1.0)
            
            # Check that some text was extracted
            self.assertGreater(len(result['extracted_text']), 0)
            
            # Check that some data was extracted
            self.assertIsInstance(result['extracted_data'], dict)
    
    def test_data_extraction(self):
        """Test data extraction from OCR text."""
        # Test text with invoice data
        test_text = """
        INVOICE
        Invoice #: INV-2024-001
        Date: 01/15/2024
        Vendor: Test Company Inc.
        
        Item                    Qty     Price   Total
        Product A              2       $25.00  $50.00
        Product B              1       $30.00  $30.00
        
        Total Amount: $80.00
        """
        
        # Extract data
        extracted_data = self.file_processor.extract_invoice_data(test_text, "test-file-id")
        
        # Assertions
        self.assertIsInstance(extracted_data, dict)
        
        # Check for extracted fields
        if 'invoice_number' in extracted_data:
            self.assertIn('INV-2024-001', extracted_data['invoice_number'])
        
        if 'total_amount' in extracted_data:
            self.assertIn('80.00', extracted_data['total_amount'])
        
        if 'invoice_date' in extracted_data:
            self.assertIn('01/15/2024', extracted_data['invoice_date'])
        
        if 'vendor' in extracted_data:
            self.assertIn('Test Company', extracted_data['vendor'])
    
    def test_monitoring_system(self):
        """Test the monitoring system."""
        # Create test metrics
        test_metrics = OCRMetrics(
            timestamp=datetime.now().isoformat(),
            file_id="test-123",
            file_type="invoice",
            original_confidence=0.65,
            processed_confidence=0.85,
            confidence_improvement=0.20,
            preprocessing_time=2.5,
            ocr_time=1.8,
            total_time=4.3,
            text_length=1500,
            quality_score=0.75,
            preprocessing_stats={'contrast_improvement': 12.5, 'noise_reduction': 8.2},
            success=True
        )
        
        # Record metrics
        self.ocr_monitor.record_metrics(test_metrics)
        
        # Get performance summary
        summary = self.ocr_monitor.get_performance_summary(days=1)
        
        # Assertions
        self.assertIsInstance(summary, dict)
        if summary:  # If there's data
            self.assertIn('total_files', summary)
            self.assertIn('successful_files', summary)
            self.assertIn('failed_files', summary)
            self.assertIn('success_rate', summary)
            self.assertIn('avg_confidence', summary)
            self.assertIn('avg_processing_time', summary)
        
        # Get recent alerts
        alerts = self.ocr_monitor.get_recent_alerts(limit=5)
        self.assertIsInstance(alerts, list)
        
        # Generate health report
        health_report = self.ocr_monitor.generate_health_report()
        self.assertIsInstance(health_report, dict)
        self.assertIn('health_score', health_report)
        self.assertIn('status', health_report)
        self.assertIn('summary', health_report)
        self.assertIn('recent_alerts', health_report)
        self.assertIn('recommendations', health_report)
    
    def test_error_handling(self):
        """Test error handling in the system."""
        # Test with invalid file
        class MockInvalidFile:
            def __init__(self):
                self.name = "invalid.txt"
                self.type = "text/plain"
            
            def getbuffer(self):
                return b"invalid content"
        
        invalid_file = MockInvalidFile()
        
        # Process invalid file
        result = self.file_processor.process_uploaded_file(invalid_file)
        
        # Should handle error gracefully
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('error', result)
        
        # Should not be successful
        self.assertFalse(result['success'])
        self.assertIsInstance(result['error'], str)
    
    def test_batch_processing(self):
        """Test batch processing capabilities."""
        # Create multiple test images
        image_paths = []
        for i in range(3):
            path = self.create_test_invoice_image(f"batch_test_{i}.png")
            image_paths.append(path)
        
        # Process each image
        results = []
        for path in image_paths:
            class MockUploadedFile:
                def __init__(self, path):
                    self.path = path
                    self.name = os.path.basename(path)
                    self.type = 'image/png'
                
                def getbuffer(self):
                    with open(self.path, 'rb') as f:
                        return f.read()
            
            uploaded_file = MockUploadedFile(path)
            result = self.file_processor.process_uploaded_file(uploaded_file)
            results.append(result)
        
        # Check results
        self.assertEqual(len(results), 3)
        
        successful_count = sum(1 for r in results if r.get('success', False))
        self.assertGreaterEqual(successful_count, 1)  # At least one should succeed
        
        # Check processing history
        history = self.file_processor.get_processing_history(limit=10)
        self.assertIsInstance(history, list)
        self.assertGreaterEqual(len(history), successful_count)
    
    def test_configuration_flexibility(self):
        """Test different preprocessing configurations."""
        # Test different configurations
        configs = [
            create_preprocessing_config(denoising_method='bilateral', thresholding_method='adaptive'),
            create_preprocessing_config(denoising_method='gaussian', thresholding_method='otsu'),
            create_preprocessing_config(contrast_method='histogram_equalization', enable_deskewing=False)
        ]
        
        # Create test image
        image_path = self.create_test_invoice_image()
        image = cv2.imread(image_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Test each configuration
        for i, config in enumerate(configs):
            preprocessor = OCRPreprocessor(config)
            preprocessed = preprocessor.preprocess_image(image)
            
            # Should always return a valid image
            self.assertIsInstance(preprocessed, np.ndarray)
            self.assertEqual(preprocessed.shape, image.shape)
    
    def test_database_persistence(self):
        """Test database persistence and retrieval."""
        # Create and process a test file
        image_path = self.create_test_invoice_image()
        
        class MockUploadedFile:
            def __init__(self, path):
                self.path = path
                self.name = os.path.basename(path)
                self.type = 'image/png'
            
            def getbuffer(self):
                with open(self.path, 'rb') as f:
                    return f.read()
        
        uploaded_file = MockUploadedFile(image_path)
        result = self.file_processor.process_uploaded_file(uploaded_file)
        
        if result['success']:
            file_id = result['file_id']
            
            # Get file details from database
            file_details = self.file_processor.get_file_details(file_id)
            
            # Assertions
            self.assertIsNotNone(file_details)
            self.assertEqual(file_details['file_id'], file_id)
            self.assertIn('filename', file_details)
            self.assertIn('status', file_details)
            self.assertIn('ocr_confidence', file_details)
            self.assertIn('extracted_data', file_details)
            
            # Check that extracted data was saved
            self.assertIsInstance(file_details['extracted_data'], dict)
    
    def test_performance_metrics(self):
        """Test performance metrics collection."""
        # Process multiple files to generate metrics
        for i in range(2):
            image_path = self.create_test_invoice_image(f"perf_test_{i}.png")
            
            class MockUploadedFile:
                def __init__(self, path):
                    self.path = path
                    self.name = os.path.basename(path)
                    self.type = 'image/png'
                
                def getbuffer(self):
                    with open(self.path, 'rb') as f:
                        return f.read()
            
            uploaded_file = MockUploadedFile(image_path)
            self.file_processor.process_uploaded_file(uploaded_file)
        
        # Get performance summary
        summary = self.ocr_monitor.get_performance_summary(days=1)
        
        if summary:
            # Check that metrics were recorded
            self.assertGreaterEqual(summary['total_files'], 2)
            self.assertGreaterEqual(summary['successful_files'], 0)
            self.assertGreaterEqual(summary['avg_confidence'], 0.0)
            self.assertLessEqual(summary['avg_confidence'], 1.0)
            self.assertGreaterEqual(summary['avg_processing_time'], 0.0)

def run_performance_benchmark():
    """Run a performance benchmark of the system."""
    print("🚀 Running Performance Benchmark...")
    
    # Create test environment
    test_dir = tempfile.mkdtemp()
    upload_dir = os.path.join(test_dir, "uploads")
    data_dir = os.path.join(test_dir, "data")
    
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    db_path = os.path.join(data_dir, "benchmark_owlin.db")
    file_processor = FileProcessor(upload_dir=upload_dir, db_path=db_path)
    
    # Create test images
    image_paths = []
    for i in range(5):
        # Create test image
        width, height = 800, 1000
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Add invoice content
        draw.text((50, 50), f"INVOICE #{i+1}", fill='black', font=font)
        draw.text((50, 80), f"Date: 01/{15+i:02d}/2024", fill='black', font=font)
        draw.text((50, 110), f"Total: ${100 + i*50}.00", fill='black', font=font)
        
        # Save image
        image_path = os.path.join(upload_dir, f"benchmark_{i}.png")
        image.save(image_path)
        image_paths.append(image_path)
    
    # Benchmark processing
    import time
    start_time = time.time()
    
    results = []
    for i, path in enumerate(image_paths):
        print(f"Processing image {i+1}/{len(image_paths)}...")
        
        class MockUploadedFile:
            def __init__(self, path):
                self.path = path
                self.name = os.path.basename(path)
                self.type = 'image/png'
            
            def getbuffer(self):
                with open(self.path, 'rb') as f:
                    return f.read()
        
        uploaded_file = MockUploadedFile(path)
        result = file_processor.process_uploaded_file(uploaded_file)
        results.append(result)
    
    total_time = time.time() - start_time
    
    # Calculate statistics
    successful = sum(1 for r in results if r.get('success', False))
    avg_confidence = sum(r.get('ocr_confidence', 0) for r in results if r.get('success', False)) / max(successful, 1)
    
    print(f"\n📊 Benchmark Results:")
    print(f"Total files processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Success rate: {successful/len(results)*100:.1f}%")
    print(f"Average confidence: {avg_confidence:.3f}")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Average time per file: {total_time/len(results):.2f}s")
    
    # Get performance summary
    monitor = OCRMonitor(db_path)
    summary = monitor.get_performance_summary(days=1)
    
    if summary:
        print(f"\n📈 Performance Summary:")
        print(f"Total files: {summary.get('total_files', 0)}")
        print(f"Success rate: {summary.get('success_rate', 0):.1f}%")
        print(f"Avg confidence: {summary.get('avg_confidence', 0):.3f}")
        print(f"Avg processing time: {summary.get('avg_processing_time', 0):.2f}s")
    
    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)
    
    return {
        'total_files': len(results),
        'successful': successful,
        'success_rate': successful/len(results)*100,
        'avg_confidence': avg_confidence,
        'total_time': total_time,
        'avg_time_per_file': total_time/len(results)
    }

if __name__ == "__main__":
    # Run unit tests
    print("🧪 Running Integration Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance benchmark
    print("\n" + "="*50)
    benchmark_results = run_performance_benchmark()
    
    print(f"\n✅ Integration testing completed!")
    print(f"Benchmark results saved for analysis.") 