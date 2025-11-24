# tests/test_htr_module.py
"""
Unit tests for HTR (Handwriting Recognition) module.

This module tests the core HTR functionality including base classes,
Kraken driver, integration, and dataset management.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from backend.htr.base import HTRBlock, HTRResult, HTRConfig, HTRStatus, HTRModelType, HTRSample
from backend.htr.kraken_driver import KrakenDriver
from backend.htr.integration import HTRProcessor, get_htr_processor
from backend.htr.dataset import HTRSampleStorage


class TestHTRBase(unittest.TestCase):
    """Test HTR base classes and data structures."""
    
    def test_htr_block_creation(self):
        """Test HTRBlock creation and methods."""
        block = HTRBlock(
            block_id="test_block",
            bbox=(10, 20, 100, 50),
            text="test handwriting",
            confidence=0.85,
            model_used=HTRModelType.KRAKEN,
            processing_time=1.5,
            source_image_path="/path/to/image.png"
        )
        
        self.assertEqual(block.block_id, "test_block")
        self.assertEqual(block.text, "test handwriting")
        self.assertEqual(block.confidence, 0.85)
        self.assertTrue(block.is_high_confidence(0.8))
        self.assertFalse(block.needs_review(0.8))
        
        # Test dictionary conversion
        block_dict = block.to_dict()
        self.assertIn("block_id", block_dict)
        self.assertIn("text", block_dict)
        self.assertIn("confidence", block_dict)
    
    def test_htr_result_creation(self):
        """Test HTRResult creation and methods."""
        blocks = [
            HTRBlock("block1", (0, 0, 100, 50), "text1", 0.9, HTRModelType.KRAKEN, 1.0, "/path1"),
            HTRBlock("block2", (0, 50, 100, 50), "text2", 0.7, HTRModelType.KRAKEN, 1.0, "/path2")
        ]
        
        result = HTRResult(
            document_id="test_doc",
            page_num=1,
            blocks=blocks,
            status=HTRStatus.SUCCESS,
            processing_time=2.5,
            model_used=HTRModelType.KRAKEN,
            total_blocks=2,
            high_confidence_blocks=1
        )
        
        self.assertEqual(result.document_id, "test_doc")
        self.assertEqual(len(result.blocks), 2)
        self.assertEqual(result.status, HTRStatus.SUCCESS)
        
        # Test confidence stats
        stats = result.get_confidence_stats()
        self.assertEqual(stats["min"], 0.7)
        self.assertEqual(stats["max"], 0.9)
        self.assertEqual(stats["avg"], 0.8)
    
    def test_htr_config_creation(self):
        """Test HTRConfig creation and methods."""
        config = HTRConfig(
            enabled=True,
            confidence_threshold=0.8,
            model_type=HTRModelType.KRAKEN,
            save_samples=True
        )
        
        self.assertTrue(config.enabled)
        self.assertEqual(config.confidence_threshold, 0.8)
        self.assertEqual(config.model_type, HTRModelType.KRAKEN)
        
        # Test dictionary conversion
        config_dict = config.to_dict()
        self.assertIn("enabled", config_dict)
        self.assertIn("confidence_threshold", config_dict)
        
        # Test from_dict
        config2 = HTRConfig.from_dict(config_dict)
        self.assertEqual(config2.enabled, config.enabled)
        self.assertEqual(config2.confidence_threshold, config.confidence_threshold)


class TestKrakenDriver(unittest.TestCase):
    """Test Kraken driver functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = HTRConfig(enabled=True, confidence_threshold=0.8)
        self.driver = KrakenDriver(self.config)
    
    def test_driver_initialization(self):
        """Test driver initialization."""
        self.assertIsNotNone(self.driver)
        self.assertEqual(self.driver.config, self.config)
    
    @patch('backend.htr.kraken_driver.importlib.import_module')
    def test_is_available_with_kraken(self, mock_import):
        """Test is_available when Kraken is available."""
        mock_import.return_value = Mock()
        self.assertTrue(self.driver.is_available())
    
    @patch('backend.htr.kraken_driver.importlib.import_module')
    def test_is_available_without_kraken(self, mock_import):
        """Test is_available when Kraken is not available."""
        mock_import.side_effect = ImportError("No module named 'kraken'")
        self.assertFalse(self.driver.is_available())
    
    def test_process_blocks_disabled(self):
        """Test process_blocks when HTR is disabled."""
        self.config.enabled = False
        driver = KrakenDriver(self.config)
        
        result = driver.process_blocks("/path/to/image.png", [])
        self.assertEqual(result.status, HTRStatus.SKIPPED)
    
    def test_process_blocks_no_blocks(self):
        """Test process_blocks with no handwriting blocks."""
        result = driver.process_blocks("/path/to/image.png", [])
        self.assertEqual(result.status, HTRStatus.SKIPPED)
    
    @patch('backend.htr.kraken_driver.Path.exists')
    @patch('backend.htr.kraken_driver.cv2.imread')
    def test_process_blocks_success(self, mock_imread, mock_exists):
        """Test successful process_blocks."""
        mock_exists.return_value = True
        mock_imread.return_value = Mock()
        
        # Mock the driver's internal methods
        with patch.object(self.driver, '_load_model', return_value=True):
            with patch.object(self.driver, '_crop_block', return_value=Mock()):
                with patch.object(self.driver, '_process_with_kraken', return_value=("test text", 0.9)):
                    result = self.driver.process_blocks("/path/to/image.png", [{"bbox": [0, 0, 100, 50]}])
                    
                    self.assertEqual(result.status, HTRStatus.SUCCESS)
                    self.assertEqual(len(result.blocks), 1)
                    self.assertEqual(result.blocks[0].text, "test text")


class TestHTRIntegration(unittest.TestCase):
    """Test HTR integration functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = HTRConfig(enabled=True, confidence_threshold=0.8)
        self.processor = HTRProcessor(self.config)
    
    def test_processor_initialization(self):
        """Test processor initialization."""
        self.assertIsNotNone(self.processor)
        self.assertEqual(self.processor.config, self.config)
    
    def test_is_available_disabled(self):
        """Test is_available when HTR is disabled."""
        self.config.enabled = False
        processor = HTRProcessor(self.config)
        self.assertFalse(processor.is_available())
    
    @patch('backend.htr.integration.KrakenDriver')
    def test_is_available_enabled(self, mock_driver_class):
        """Test is_available when HTR is enabled."""
        mock_driver = Mock()
        mock_driver.is_available.return_value = True
        mock_driver_class.return_value = mock_driver
        
        processor = HTRProcessor(self.config)
        self.assertTrue(processor.is_available())
    
    def test_filter_handwriting_blocks(self):
        """Test filtering of handwriting blocks."""
        layout_blocks = [
            {"type": "text", "bbox": [0, 0, 100, 50]},
            {"type": "handwriting", "bbox": [0, 50, 100, 50]},
            {"type": "table", "bbox": [0, 100, 100, 50]},
            {"type": "script", "bbox": [0, 150, 100, 50]}
        ]
        
        handwriting_blocks = self.processor._filter_handwriting_blocks(layout_blocks)
        
        # Should find handwriting and script blocks
        self.assertEqual(len(handwriting_blocks), 2)
        self.assertEqual(handwriting_blocks[0]["type"], "handwriting")
        self.assertEqual(handwriting_blocks[1]["type"], "script")
    
    def test_get_review_candidates(self):
        """Test getting review candidates."""
        # Create a mock result with review candidates
        block = HTRBlock("block1", (0, 0, 100, 50), "text", 0.7, HTRModelType.KRAKEN, 1.0, "/path")
        result = HTRResult("doc1", 1, [block], HTRStatus.SUCCESS, 1.0, HTRModelType.KRAKEN, 1, 0, [block])
        
        candidates = self.processor.get_review_candidates(result)
        
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["type"], "htr_block")
        self.assertEqual(candidates[0]["block_id"], "block1")


class TestHTRDataset(unittest.TestCase):
    """Test HTR dataset functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.storage = HTRSampleStorage(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        Path(self.temp_db.name).unlink(missing_ok=True)
    
    def test_sample_creation(self):
        """Test HTR sample creation."""
        sample = self.storage.create_sample(
            image_path="/path/to/image.png",
            ground_truth="test text",
            confidence=0.85,
            model_used=HTRModelType.KRAKEN,
            metadata={"test": "value"}
        )
        
        self.assertIsNotNone(sample)
        self.assertEqual(sample.image_path, "/path/to/image.png")
        self.assertEqual(sample.ground_truth, "test text")
        self.assertEqual(sample.confidence, 0.85)
        self.assertEqual(sample.model_used, HTRModelType.KRAKEN)
    
    def test_sample_storage(self):
        """Test saving and retrieving samples."""
        sample = self.storage.create_sample(
            image_path="/path/to/image.png",
            ground_truth="test text",
            confidence=0.85,
            model_used=HTRModelType.KRAKEN
        )
        
        # Save sample
        self.assertTrue(self.storage.save_sample(sample))
        
        # Retrieve samples
        samples = self.storage.get_samples()
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].ground_truth, "test text")
    
    def test_prediction_storage(self):
        """Test saving and retrieving predictions."""
        success = self.storage.save_prediction(
            document_id="doc1",
            page_num=1,
            block_id="block1",
            text="predicted text",
            confidence=0.8,
            model_used=HTRModelType.KRAKEN,
            bbox=[0, 0, 100, 50],
            processing_time=1.5
        )
        
        self.assertTrue(success)
        
        predictions = self.storage.get_predictions()
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]["text"], "predicted text")
    
    def test_statistics(self):
        """Test getting storage statistics."""
        # Add some test data
        sample = self.storage.create_sample("/path1", "text1", 0.8, HTRModelType.KRAKEN)
        self.storage.save_sample(sample)
        
        self.storage.save_prediction("doc1", 1, "block1", "text", 0.9, HTRModelType.KRAKEN, [0, 0, 100, 50], 1.0)
        
        stats = self.storage.get_statistics()
        self.assertEqual(stats["total_samples"], 1)
        self.assertEqual(stats["total_predictions"], 1)


class TestHTRGlobalFunctions(unittest.TestCase):
    """Test global HTR functions."""
    
    def test_get_htr_processor(self):
        """Test getting global HTR processor."""
        processor = get_htr_processor()
        self.assertIsNotNone(processor)
        
        # Should return same instance
        processor2 = get_htr_processor()
        self.assertIs(processor, processor2)
    
    @patch('backend.htr.integration.HTRProcessor')
    def test_initialize_htr(self, mock_processor_class):
        """Test HTR initialization."""
        mock_processor = Mock()
        mock_processor.is_available.return_value = True
        mock_processor_class.return_value = mock_processor
        
        result = initialize_htr()
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
