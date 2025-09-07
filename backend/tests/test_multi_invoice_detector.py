#!/usr/bin/env python3
"""
Comprehensive Test Suite for Multi-Invoice Detection System

This module provides extensive testing for the new unified multi-invoice detection
system, including unit tests, integration tests, and performance tests.
"""

import unittest
import tempfile
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Import the new detection system
try:
    from ocr.multi_invoice_detector import (
        MultiInvoiceDetector, DetectionConfig, DetectionResult,
        DocumentContext, get_multi_invoice_detector
    )
    from ocr.performance_monitor import PerformanceMonitor, get_performance_monitor
    from plugins.multi_invoice import BrewingIndustryPlugin
    UNIFIED_DETECTION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Unified detection not available: {e}")
    UNIFIED_DETECTION_AVAILABLE = False

class TestMultiInvoiceDetector(unittest.TestCase):
    """Test cases for the unified multi-invoice detection system"""
    
    def setUp(self):
        """Set up test environment"""
        if not UNIFIED_DETECTION_AVAILABLE:
            self.skipTest("Unified detection system not available")
        
        self.config = DetectionConfig(
            confidence_threshold=0.7,
            cache_ttl_seconds=300,
            max_workers=2,
            enable_caching=False  # Disable caching for tests
        )
        
        self.detector = MultiInvoiceDetector(self.config)
        
        # Test data
        self.single_invoice_text = """
        INVOICE #12345
        WILD HORSE BREWING CO LTD
        Date: 2024-01-15
        Total: £150.00
        """
        
        self.multi_invoice_text = """
        INVOICE #12345
        WILD HORSE BREWING CO LTD
        Date: 2024-01-15
        Total: £150.00
        
        --- PAGE 2 ---
        
        INVOICE #67890
        RED DRAGON DISPENSE LIMITED
        Date: 2024-01-16
        Total: £200.00
        """
        
        self.complex_multi_invoice_text = """
        INVOICE #BREW-2024-001
        WILD HORSE BREWING CO LTD
        Date: 2024-01-15
        Total: £150.00
        
        --- PAGE 2 ---
        
        INVOICE #DISP-2024-002
        RED DRAGON DISPENSE LIMITED
        Date: 2024-01-16
        Total: £200.00
        
        --- PAGE 3 ---
        
        INVOICE #HOSP-2024-003
        SNOWDONIA HOSPITALITY
        Date: 2024-01-17
        Total: £300.00
        """
    
    def test_single_invoice_detection(self):
        """Test detection of single invoice"""
        result = self.detector.detect(self.single_invoice_text)
        
        self.assertIsInstance(result, DetectionResult)
        self.assertFalse(result.is_multi_invoice)
        self.assertGreater(result.confidence, 0.0)
        self.assertEqual(len(result.detected_invoices), 0)
        self.assertEqual(len(result.error_messages), 0)
    
    def test_multi_invoice_detection(self):
        """Test detection of multi-invoice document"""
        result = self.detector.detect(self.multi_invoice_text)
        
        self.assertIsInstance(result, DetectionResult)
        self.assertTrue(result.is_multi_invoice)
        self.assertGreater(result.confidence, 0.0)
        self.assertGreater(len(result.detected_invoices), 0)
        self.assertEqual(len(result.error_messages), 0)
    
    def test_complex_multi_invoice_detection(self):
        """Test detection of complex multi-invoice document"""
        result = self.detector.detect(self.complex_multi_invoice_text)
        
        self.assertIsInstance(result, DetectionResult)
        self.assertTrue(result.is_multi_invoice)
        self.assertGreater(result.confidence, 0.0)
        self.assertGreaterEqual(len(result.detected_invoices), 2)
        self.assertEqual(len(result.error_messages), 0)
    
    def test_context_analysis(self):
        """Test context analysis functionality"""
        result = self.detector.detect(self.single_invoice_text)
        
        self.assertIsInstance(result.context_analysis, DocumentContext)
        self.assertGreater(result.context_analysis.word_count, 0)
        self.assertGreaterEqual(result.context_analysis.structure_score, 0.0)
        self.assertGreaterEqual(result.context_analysis.confidence_score, 0.0)
    
    def test_performance_monitoring(self):
        """Test performance monitoring integration"""
        monitor = get_performance_monitor()
        
        # Start monitoring
        operation_id = monitor.start_operation("test_detection")
        
        # Perform detection
        result = self.detector.detect(self.single_invoice_text)
        
        # End monitoring
        monitor.end_operation(operation_id, success=True)
        
        # Check metrics
        system_metrics = monitor.get_system_metrics()
        self.assertGreater(system_metrics.total_operations, 0)
        self.assertGreater(system_metrics.successful_operations, 0)
    
    def test_caching_functionality(self):
        """Test caching functionality"""
        # Create detector with caching enabled
        config_with_cache = DetectionConfig(
            enable_caching=True,
            cache_ttl_seconds=300
        )
        detector_with_cache = MultiInvoiceDetector(config_with_cache)
        
        # First detection (should cache)
        result1 = detector_with_cache.detect(self.single_invoice_text)
        
        # Second detection (should use cache)
        result2 = detector_with_cache.detect(self.single_invoice_text)
        
        # Results should be identical
        self.assertEqual(result1.is_multi_invoice, result2.is_multi_invoice)
        self.assertEqual(result1.confidence, result2.confidence)
    
    def test_error_handling(self):
        """Test error handling with invalid input"""
        # Test with empty text
        result = self.detector.detect("")
        
        self.assertIsInstance(result, DetectionResult)
        self.assertFalse(result.is_multi_invoice)
        self.assertEqual(result.confidence, 0.0)
        
        # Test with None text
        result = self.detector.detect(None)
        
        self.assertIsInstance(result, DetectionResult)
        self.assertFalse(result.is_multi_invoice)
        self.assertEqual(len(result.error_messages), 0)
    
    def test_batch_processing(self):
        """Test batch processing functionality"""
        texts = [
            self.single_invoice_text,
            self.multi_invoice_text,
            self.complex_multi_invoice_text
        ]
        
        results = self.detector.batch_detect(texts)
        
        self.assertEqual(len(results), 3)
        self.assertIsInstance(results[0], DetectionResult)
        self.assertIsInstance(results[1], DetectionResult)
        self.assertIsInstance(results[2], DetectionResult)
    
    def test_plugin_integration(self):
        """Test plugin system integration"""
        # Create and register a test plugin
        plugin = BrewingIndustryPlugin()
        
        # Test plugin detection
        result = plugin.detect(self.single_invoice_text, {})
        
        self.assertIsInstance(result, dict)
        self.assertIn("is_brewing_industry", result)
        self.assertIn("suppliers_detected", result)
        self.assertIn("brewing_keywords", result)
    
    def test_configuration_loading(self):
        """Test configuration loading and validation"""
        config = DetectionConfig(
            confidence_threshold=0.8,
            cache_ttl_seconds=600,
            max_workers=4
        )
        
        self.assertEqual(config.confidence_threshold, 0.8)
        self.assertEqual(config.cache_ttl_seconds, 600)
        self.assertEqual(config.max_workers, 4)
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        start_time = time.time()
        
        # Perform multiple detections
        for _ in range(10):
            result = self.detector.detect(self.single_invoice_text)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance should be reasonable (less than 1 second for 10 operations)
        self.assertLess(total_time, 1.0)
        
        # Average time per operation should be less than 100ms
        avg_time_per_operation = total_time / 10
        self.assertLess(avg_time_per_operation, 0.1)

class TestPerformanceMonitor(unittest.TestCase):
    """Test cases for performance monitoring system"""
    
    def setUp(self):
        """Set up test environment"""
        self.monitor = PerformanceMonitor()
    
    def test_operation_timing(self):
        """Test operation timing functionality"""
        operation_id = self.monitor.start_operation("test_operation")
        
        # Simulate some work
        time.sleep(0.1)
        
        self.monitor.end_operation(operation_id, success=True)
        
        # Check metrics
        system_metrics = self.monitor.get_system_metrics()
        self.assertEqual(system_metrics.total_operations, 1)
        self.assertEqual(system_metrics.successful_operations, 1)
        self.assertEqual(system_metrics.failed_operations, 0)
    
    def test_error_tracking(self):
        """Test error tracking functionality"""
        operation_id = self.monitor.start_operation("test_error_operation")
        
        self.monitor.end_operation(operation_id, success=False, error_message="Test error")
        
        # Check metrics
        system_metrics = self.monitor.get_system_metrics()
        self.assertEqual(system_metrics.total_operations, 1)
        self.assertEqual(system_metrics.successful_operations, 0)
        self.assertEqual(system_metrics.failed_operations, 1)
        self.assertEqual(system_metrics.error_rate, 1.0)
    
    def test_performance_report(self):
        """Test performance report generation"""
        # Add some test metrics
        for i in range(5):
            operation_id = self.monitor.start_operation(f"test_operation_{i}")
            time.sleep(0.01)
            self.monitor.end_operation(operation_id, success=True)
        
        report = self.monitor.get_performance_report()
        
        self.assertIn("system_metrics", report)
        self.assertIn("recent_performance", report)
        self.assertIn("insights", report)
        
        system_metrics = report["system_metrics"]
        self.assertEqual(system_metrics["total_operations"], 5)
        self.assertEqual(system_metrics["successful_operations"], 5)
        self.assertEqual(system_metrics["failed_operations"], 0)
    
    def test_metrics_persistence(self):
        """Test metrics persistence to file"""
        # Add some test metrics
        operation_id = self.monitor.start_operation("test_persistence")
        self.monitor.end_operation(operation_id, success=True)
        
        # Save metrics
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            self.monitor.save_metrics(temp_file)
            
            # Verify file was created and contains valid JSON
            with open(temp_file, 'r') as f:
                data = json.load(f)
            
            self.assertIn("metrics", data)
            self.assertIn("system_metrics", data)
            self.assertIn("exported_at", data)
        finally:
            # Clean up
            Path(temp_file).unlink(missing_ok=True)

class TestPluginSystem(unittest.TestCase):
    """Test cases for plugin system"""
    
    def setUp(self):
        """Set up test environment"""
        self.plugin = BrewingIndustryPlugin()
    
    def test_plugin_detection(self):
        """Test plugin detection functionality"""
        text = """
        INVOICE #BREW-2024-001
        WILD HORSE BREWING CO LTD
        Date: 2024-01-15
        Total: £150.00
        """
        
        result = self.plugin.detect(text, {})
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["is_brewing_industry"])
        self.assertIn("WILD HORSE BREWING CO LTD", result["suppliers_detected"])
    
    def test_plugin_confidence(self):
        """Test plugin confidence calculation"""
        text = """
        INVOICE #BREW-2024-001
        WILD HORSE BREWING CO LTD
        Date: 2024-01-15
        Total: £150.00
        """
        
        confidence = self.plugin.get_confidence(text, {})
        
        self.assertIsInstance(confidence, float)
        self.assertGreater(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
    
    def test_plugin_validation(self):
        """Test plugin validation"""
        # Valid text
        valid_text = "WILD HORSE BREWING CO LTD invoice"
        self.assertTrue(self.plugin.validate(valid_text))
        
        # Invalid text
        invalid_text = "Some random text without brewing content"
        self.assertFalse(self.plugin.validate(invalid_text))

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2) 