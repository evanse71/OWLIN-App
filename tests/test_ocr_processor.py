# -*- coding: utf-8 -*-
"""
Comprehensive test suite for OCR processor functionality.

Tests PaddleOCR integration, Tesseract fallback, and per-block OCR processing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
import cv2

from backend.ocr.ocr_processor import (
    OCRProcessor, OCRResult, PageOCRResult, process_document_ocr
)


class TestOCRProcessor:
    """Test the OCRProcessor class functionality."""
    
    def test_ocr_processor_initialization(self):
        """Test OCRProcessor initializes correctly."""
        processor = OCRProcessor()
        assert processor._paddle_ocr is None
        assert processor._confidence_threshold == 0.7
        assert "header" in processor._block_type_configs
        assert "table" in processor._block_type_configs
        assert "footer" in processor._block_type_configs
    
    def test_block_type_configurations(self):
        """Test block type configurations for different regions."""
        processor = OCRProcessor()
        
        # Test header configuration
        header_config = processor._block_type_configs["header"]
        assert header_config["lang"] == "en"
        assert header_config["use_angle_cls"] is True
        
        # Test table configuration
        table_config = processor._block_type_configs["table"]
        assert table_config["lang"] == "en"
        assert table_config["use_angle_cls"] is True
        assert table_config.get("structure") is True
        
        # Test handwriting configuration
        handwriting_config = processor._block_type_configs["handwriting"]
        assert handwriting_config["use_angle_cls"] is False
    
    def test_extract_block_image(self, tmp_path):
        """Test block image extraction from full image."""
        processor = OCRProcessor()
        
        # Create test image
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        cv2.rectangle(img, (50, 50), (150, 100), (0, 0, 0), 2)
        cv2.putText(img, "TEST TEXT", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        
        # Extract block
        bbox = (50, 50, 100, 50)
        block_img = processor._extract_block_image(img, bbox)
        
        assert block_img.shape == (50, 100, 3)
        assert block_img.size > 0
    
    def test_preprocess_block_image(self, tmp_path):
        """Test block image preprocessing for different types."""
        processor = OCRProcessor()
        
        # Create test image
        img = np.ones((100, 200, 3), dtype=np.uint8) * 255
        cv2.putText(img, "TEST", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # Test different block types
        for block_type in ["header", "table", "footer", "body", "handwriting"]:
            processed = processor._preprocess_block_image(img, block_type)
            assert processed is not None
            assert processed.shape[:2] == img.shape[:2]  # Same dimensions
    
    def test_analyze_text_structure(self):
        """Test text structure analysis."""
        processor = OCRProcessor()
        
        # Test empty text
        field_count, line_count = processor._analyze_text_structure("")
        assert field_count == 0
        assert line_count == 0
        
        # Test simple text
        text = "Line 1\nLine 2\nLine 3"
        field_count, line_count = processor._analyze_text_structure(text)
        assert line_count == 3
        assert field_count > 0
        
        # Test invoice-like text
        invoice_text = "Item 1: $10.00\nItem 2: $20.00\nTotal: $30.00"
        field_count, line_count = processor._analyze_text_structure(invoice_text)
        assert line_count == 3
        assert field_count > 0
    
    def test_process_block_with_mock_ocr(self, tmp_path):
        """Test block processing with mocked OCR."""
        processor = OCRProcessor()
        
        # Create test image
        img = np.ones((100, 200, 3), dtype=np.uint8) * 255
        cv2.putText(img, "TEST TEXT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        
        block_info = {
            "type": "header",
            "bbox": [50, 50, 100, 50]
        }
        
        # Mock PaddleOCR
        with patch.object(processor, '_ocr_with_paddle') as mock_paddle:
            mock_paddle.return_value = ("TEST TEXT", 0.9, 0.1)
            
            result = processor.process_block(img, block_info)
            
            assert result.type == "header"
            assert result.ocr_text == "TEST TEXT"
            assert result.confidence == 0.9
            assert result.method_used == "paddleocr"
            assert result.processing_time > 0
    
    def test_process_block_fallback_to_tesseract(self, tmp_path):
        """Test block processing fallback to Tesseract."""
        processor = OCRProcessor()
        
        # Create test image
        img = np.ones((100, 200, 3), dtype=np.uint8) * 255
        cv2.putText(img, "TEST TEXT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        
        block_info = {
            "type": "header",
            "bbox": [50, 50, 100, 50]
        }
        
        # Mock PaddleOCR failure and Tesseract success
        with patch.object(processor, '_ocr_with_paddle') as mock_paddle:
            with patch.object(processor, '_ocr_with_tesseract') as mock_tesseract:
                mock_paddle.return_value = ("", 0.1, 0.1)  # Low confidence
                mock_tesseract.return_value = ("TEST TEXT", 0.8, 0.1)
                
                result = processor.process_block(img, block_info)
                
                assert result.ocr_text == "TEST TEXT"
                assert result.confidence == 0.8
                assert result.method_used == "tesseract"
    
    def test_process_page_comprehensive(self, tmp_path):
        """Test comprehensive page processing."""
        processor = OCRProcessor()
        
        # Create test image
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        cv2.putText(img, "HEADER", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(img, "TABLE CONTENT", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        cv2.putText(img, "FOOTER", (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        test_img_path = tmp_path / "test_page.png"
        cv2.imwrite(str(test_img_path), img)
        
        # Define layout blocks
        layout_blocks = [
            {"type": "header", "bbox": [0, 0, 300, 100]},
            {"type": "table", "bbox": [0, 100, 300, 200]},
            {"type": "footer", "bbox": [0, 300, 300, 100]}
        ]
        
        # Mock OCR methods
        with patch.object(processor, '_ocr_with_paddle') as mock_paddle:
            mock_paddle.return_value = ("MOCKED TEXT", 0.8, 0.1)
            
            result = processor.process_page(test_img_path, layout_blocks, page_num=1)
            
            assert result.page_num == 1
            assert len(result.blocks) == 3
            assert result.processing_time > 0
            assert result.confidence_avg > 0
    
    def test_error_handling_missing_image(self, tmp_path):
        """Test error handling with missing image."""
        processor = OCRProcessor()
        missing_path = tmp_path / "missing.png"
        
        layout_blocks = [{"type": "header", "bbox": [0, 0, 100, 50]}]
        
        result = processor.process_page(missing_path, layout_blocks, page_num=1)
        
        assert result.page_num == 1
        assert len(result.blocks) == 0
        assert result.method_used == "error"
        assert result.confidence_avg == 0.0
    
    def test_confidence_threshold_logging(self, tmp_path):
        """Test low confidence logging."""
        processor = OCRProcessor()
        
        # Create test image
        img = np.ones((100, 200, 3), dtype=np.uint8) * 255
        
        block_info = {
            "type": "header",
            "bbox": [50, 50, 100, 50]
        }
        
        # Mock low confidence result
        with patch.object(processor, '_ocr_with_paddle') as mock_paddle:
            mock_paddle.return_value = ("LOW CONFIDENCE TEXT", 0.5, 0.1)
            
            with patch('backend.ocr.ocr_processor.LOGGER') as mock_logger:
                result = processor.process_block(img, block_info)
                
                # Should log warning for low confidence
                mock_logger.warning.assert_called()
                assert "Low confidence OCR" in str(mock_logger.warning.call_args)


class TestOCRProcessorIntegration:
    """Test OCR processor integration with the main pipeline."""
    
    def test_process_document_ocr_function(self, tmp_path):
        """Test the main process_document_ocr function."""
        # Create test image
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        cv2.putText(img, "TEST INVOICE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(img, "Item 1: $10.00", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        cv2.putText(img, "Total: $10.00", (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        test_img_path = tmp_path / "test_invoice.png"
        cv2.imwrite(str(test_img_path), img)
        
        layout_blocks = [
            {"type": "header", "bbox": [0, 0, 300, 100]},
            {"type": "table", "bbox": [0, 100, 300, 200]},
            {"type": "footer", "bbox": [0, 300, 300, 100]}
        ]
        
        # Test with mocked OCR
        with patch('backend.ocr.ocr_processor.OCRProcessor.process_block') as mock_process:
            mock_result = OCRResult(
                type="header",
                bbox=(0, 0, 300, 100),
                ocr_text="TEST INVOICE",
                confidence=0.9,
                method_used="paddleocr",
                processing_time=0.1
            )
            mock_process.return_value = mock_result
            
            result = process_document_ocr(test_img_path, layout_blocks, page_num=1, 
                                         save_artifacts=True, artifact_dir=tmp_path)
            
            assert result.page_num == 1
            assert len(result.blocks) == 3
            assert result.processing_time > 0
    
    def test_artifact_saving(self, tmp_path):
        """Test JSON artifact saving functionality."""
        processor = OCRProcessor()
        
        # Create test result
        blocks = [
            OCRResult(type="header", bbox=(0, 0, 100, 50), ocr_text="HEADER", 
                     confidence=0.9, method_used="paddleocr", processing_time=0.1),
            OCRResult(type="table", bbox=(0, 50, 100, 100), ocr_text="TABLE", 
                     confidence=0.8, method_used="paddleocr", processing_time=0.1)
        ]
        
        result = PageOCRResult(
            page_num=1,
            blocks=blocks,
            processing_time=0.2,
            method_used="paddleocr",
            confidence_avg=0.85
        )
        
        # Save artifacts
        json_path = processor.save_ocr_artifacts(result, tmp_path)
        
        # Verify file was created
        assert json_path.exists()
        assert json_path.name == "ocr_page_001.json"
        
        # Verify JSON content
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        assert data["page_num"] == 1
        assert len(data["blocks"]) == 2
        assert data["method_used"] == "paddleocr"
        assert data["confidence_avg"] == 0.85


class TestOCRProcessorPerformance:
    """Test OCR processor performance and robustness."""
    
    def test_processing_performance(self, tmp_path):
        """Test that OCR processing completes within reasonable time."""
        import time
        
        processor = OCRProcessor()
        
        # Create test image
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        cv2.putText(img, "PERFORMANCE TEST", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        test_img_path = tmp_path / "performance_test.png"
        cv2.imwrite(str(test_img_path), img)
        
        layout_blocks = [
            {"type": "header", "bbox": [0, 0, 300, 100]},
            {"type": "body", "bbox": [0, 100, 300, 200]}
        ]
        
        start_time = time.time()
        result = processor.process_page(test_img_path, layout_blocks, page_num=1)
        end_time = time.time()
        
        # Should complete within 30 seconds (allowing for model loading)
        assert (end_time - start_time) < 30.0
        assert result.processing_time < 30.0
    
    def test_multiple_blocks_processing(self, tmp_path):
        """Test processing multiple blocks efficiently."""
        processor = OCRProcessor()
        
        # Create test image
        img = np.ones((600, 400, 3), dtype=np.uint8) * 255
        
        # Add multiple text regions
        for i in range(5):
            y = 50 + i * 100
            cv2.putText(img, f"Block {i+1}", (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        
        test_img_path = tmp_path / "multi_block_test.png"
        cv2.imwrite(str(test_img_path), img)
        
        # Define multiple blocks
        layout_blocks = []
        for i in range(5):
            layout_blocks.append({
                "type": "body",
                "bbox": [0, i * 100, 400, 100]
            })
        
        result = processor.process_page(test_img_path, layout_blocks, page_num=1)
        
        assert len(result.blocks) == 5
        assert result.processing_time > 0
        
        # All blocks should be processed
        for block in result.blocks:
            assert block.type == "body"
            assert block.processing_time > 0
    
    def test_error_recovery(self, tmp_path):
        """Test error recovery and graceful degradation."""
        processor = OCRProcessor()
        
        # Create test image
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        test_img_path = tmp_path / "error_test.png"
        cv2.imwrite(str(test_img_path), img)
        
        layout_blocks = [
            {"type": "header", "bbox": [0, 0, 300, 100]},
            {"type": "table", "bbox": [0, 100, 300, 200]},
            {"type": "footer", "bbox": [0, 300, 300, 100]}
        ]
        
        # Mock OCR failures
        with patch.object(processor, '_ocr_with_paddle') as mock_paddle:
            with patch.object(processor, '_ocr_with_tesseract') as mock_tesseract:
                # First block fails completely
                mock_paddle.side_effect = [Exception("OCR failed"), ("TEXT2", 0.8, 0.1), ("TEXT3", 0.8, 0.1)]
                mock_tesseract.side_effect = [Exception("Tesseract failed"), ("TEXT2", 0.7, 0.1), ("TEXT3", 0.7, 0.1)]
                
                result = processor.process_page(test_img_path, layout_blocks, page_num=1)
                
                # Should handle errors gracefully
                assert len(result.blocks) == 3
                assert result.blocks[0].ocr_text == ""  # Failed block
                assert result.blocks[0].confidence == 0.0
                assert result.blocks[0].method_used == "error"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
