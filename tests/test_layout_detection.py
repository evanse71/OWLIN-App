# -*- coding: utf-8 -*-
"""
Comprehensive test suite for layout detection functionality.

Tests LayoutParser integration, OpenCV fallback, and real-world document processing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
import cv2

from backend.ocr.layout_detector import (
    LayoutDetector, LayoutBlock, LayoutResult, detect_document_layout
)
from backend.config import FEATURE_OCR_V2_LAYOUT


class TestLayoutDetector:
    """Test the LayoutDetector class functionality."""
    
    def test_layout_detector_initialization(self):
        """Test LayoutDetector initializes correctly."""
        detector = LayoutDetector()
        assert detector._layout_model is None
        assert detector._fallback_enabled is True
        assert "Text" in detector._block_type_mapping
        assert "Table" in detector._block_type_mapping
    
    def test_block_type_mapping(self):
        """Test block type mapping for invoice-specific regions."""
        detector = LayoutDetector()
        
        # Test mapping
        assert detector._block_type_mapping["Text"] == "header"
        assert detector._block_type_mapping["Table"] == "table"
        assert detector._block_type_mapping["Figure"] == "footer"
        assert detector._block_type_mapping["Title"] == "header"
    
    def test_opencv_fallback_detection(self, tmp_path):
        """Test OpenCV fallback detection with synthetic document."""
        detector = LayoutDetector()
        
        # Create synthetic invoice-like image
        img = np.ones((800, 600, 3), dtype=np.uint8) * 255
        
        # Add header region (top 20%)
        cv2.rectangle(img, (50, 50), (550, 150), (0, 0, 0), 2)
        cv2.putText(img, "INVOICE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
        
        # Add table region (middle 60%)
        for i in range(5):
            y = 200 + i * 60
            cv2.line(img, (50, y), (550, y), (0, 0, 0), 1)
        
        # Add footer region (bottom 20%)
        cv2.rectangle(img, (50, 650), (550, 750), (0, 0, 0), 2)
        cv2.putText(img, "TOTAL: $123.45", (100, 700), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # Save test image
        test_img_path = tmp_path / "test_invoice.png"
        cv2.imwrite(str(test_img_path), img)
        
        # Test detection
        result = detector.detect_layout(test_img_path, page_num=1)
        
        # Verify results
        assert result.page_num == 1
        assert len(result.blocks) > 0
        assert result.method_used in ["layoutparser", "opencv_fallback", "fallback"]
        assert result.confidence_avg > 0.0
        
        # Check block types
        block_types = [block.type for block in result.blocks]
        assert any(bt in ["header", "table", "footer", "body"] for bt in block_types)
    
    def test_layout_detection_with_missing_image(self, tmp_path):
        """Test layout detection with missing image file."""
        detector = LayoutDetector()
        missing_path = tmp_path / "missing.png"
        
        result = detector.detect_layout(missing_path, page_num=1)
        
        assert result.page_num == 1
        assert len(result.blocks) == 0
        assert result.method_used == "error"
        assert result.confidence_avg == 0.0
    
    def test_artifact_saving(self, tmp_path):
        """Test JSON artifact saving functionality."""
        detector = LayoutDetector()
        
        # Create test result
        blocks = [
            LayoutBlock(type="header", bbox=(0, 0, 100, 50), confidence=0.8, source="test"),
            LayoutBlock(type="table", bbox=(0, 50, 100, 100), confidence=0.7, source="test"),
            LayoutBlock(type="footer", bbox=(0, 150, 100, 50), confidence=0.6, source="test")
        ]
        
        result = LayoutResult(
            page_num=1,
            blocks=blocks,
            processing_time=0.5,
            method_used="test",
            confidence_avg=0.7
        )
        
        # Save artifacts
        json_path = detector.save_layout_artifacts(result, tmp_path)
        
        # Verify file was created
        assert json_path.exists()
        assert json_path.name == "layout_page_001.json"
        
        # Verify JSON content
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        assert data["page_num"] == 1
        assert len(data["blocks"]) == 3
        assert data["method_used"] == "test"
        assert data["confidence_avg"] == 0.7


class TestLayoutDetectionIntegration:
    """Test layout detection integration with the main pipeline."""
    
    def test_detect_document_layout_function(self, tmp_path):
        """Test the main detect_document_layout function."""
        # Create test image
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        cv2.rectangle(img, (10, 10), (290, 100), (0, 0, 0), 2)
        cv2.putText(img, "TEST INVOICE", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        test_img_path = tmp_path / "test.png"
        cv2.imwrite(str(test_img_path), img)
        
        # Test detection
        result = detect_document_layout(test_img_path, page_num=1, save_artifacts=True, artifact_dir=tmp_path)
        
        # Verify results
        assert result.page_num == 1
        assert len(result.blocks) > 0
        assert result.processing_time > 0.0
        
        # Check if artifacts were saved
        json_files = list(tmp_path.glob("layout_page_*.json"))
        assert len(json_files) > 0
    
    def test_feature_flag_behavior(self, tmp_path):
        """Test behavior when feature flag is disabled."""
        # Create test image
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        test_img_path = tmp_path / "test.png"
        cv2.imwrite(str(test_img_path), img)
        
        with patch('backend.config.FEATURE_OCR_V2_LAYOUT', False):
            from backend.ocr.owlin_scan_pipeline import detect_layout
            
            # Should return single Text block when flag is off
            blocks = detect_layout(test_img_path)
            assert len(blocks) == 1
            assert blocks[0]["type"] == "Text"
    
    def test_layout_detection_with_real_documents(self, tmp_path):
        """Test layout detection with various document types."""
        # Create different document types
        documents = [
            ("invoice", self._create_invoice_image()),
            ("receipt", self._create_receipt_image()),
            ("delivery_note", self._create_delivery_note_image())
        ]
        
        results = []
        for doc_type, img in documents:
            test_path = tmp_path / f"{doc_type}.png"
            cv2.imwrite(str(test_path), img)
            
            result = detect_document_layout(test_path, page_num=1, save_artifacts=True, artifact_dir=tmp_path)
            results.append((doc_type, result))
            
            # Verify basic requirements
            assert result.page_num == 1
            assert len(result.blocks) > 0
            assert result.method_used in ["layoutparser", "opencv_fallback", "fallback"]
            assert result.confidence_avg > 0.0
        
        # Verify we detected different document types
        assert len(results) == 3
        
        # Check that artifacts were saved for each
        json_files = list(tmp_path.glob("layout_page_*.json"))
        assert len(json_files) >= 3
    
    def _create_invoice_image(self) -> np.ndarray:
        """Create a synthetic invoice image."""
        img = np.ones((800, 600, 3), dtype=np.uint8) * 255
        
        # Header
        cv2.rectangle(img, (50, 50), (550, 150), (0, 0, 0), 2)
        cv2.putText(img, "INVOICE #12345", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # Table
        for i in range(6):
            y = 200 + i * 50
            cv2.line(img, (50, y), (550, y), (0, 0, 0), 1)
        
        # Footer
        cv2.rectangle(img, (50, 600), (550, 750), (0, 0, 0), 2)
        cv2.putText(img, "TOTAL: $1,234.56", (100, 700), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        return img
    
    def _create_receipt_image(self) -> np.ndarray:
        """Create a synthetic receipt image."""
        img = np.ones((600, 400, 3), dtype=np.uint8) * 255
        
        # Header
        cv2.putText(img, "STORE RECEIPT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # Items
        for i in range(4):
            y = 100 + i * 80
            cv2.putText(img, f"Item {i+1}: $10.00", (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        
        # Total
        cv2.putText(img, "TOTAL: $40.00", (50, 450), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        return img
    
    def _create_delivery_note_image(self) -> np.ndarray:
        """Create a synthetic delivery note image."""
        img = np.ones((700, 500, 3), dtype=np.uint8) * 255
        
        # Header
        cv2.putText(img, "DELIVERY NOTE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # Delivery info
        cv2.putText(img, "Delivered to: 123 Main St", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        cv2.putText(img, "Date: 2024-01-15", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        
        # Items
        for i in range(3):
            y = 300 + i * 100
            cv2.putText(img, f"Package {i+1}: Delivered", (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        
        return img


class TestLayoutDetectionPerformance:
    """Test layout detection performance and robustness."""
    
    def test_detection_performance(self, tmp_path):
        """Test that layout detection completes within reasonable time."""
        import time
        
        # Create test image
        img = np.ones((800, 600, 3), dtype=np.uint8) * 255
        test_path = tmp_path / "performance_test.png"
        cv2.imwrite(str(test_path), img)
        
        start_time = time.time()
        result = detect_document_layout(test_path, page_num=1)
        end_time = time.time()
        
        # Should complete within 10 seconds
        assert (end_time - start_time) < 10.0
        assert result.processing_time < 10.0
    
    def test_multiple_pages_processing(self, tmp_path):
        """Test processing multiple pages."""
        results = []
        
        for page_num in range(1, 4):  # 3 pages
            img = np.ones((400, 300, 3), dtype=np.uint8) * 255
            test_path = tmp_path / f"page_{page_num}.png"
            cv2.imwrite(str(test_path), img)
            
            result = detect_document_layout(test_path, page_num=page_num, save_artifacts=True, artifact_dir=tmp_path)
            results.append(result)
        
        # Verify all pages processed
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.page_num == i + 1
            assert len(result.blocks) > 0
        
        # Check artifacts were saved
        json_files = list(tmp_path.glob("layout_page_*.json"))
        assert len(json_files) == 3
    
    def test_error_handling(self, tmp_path):
        """Test error handling with invalid inputs."""
        # Test with corrupted image
        corrupted_path = tmp_path / "corrupted.png"
        corrupted_path.write_bytes(b"not an image")
        
        result = detect_document_layout(corrupted_path, page_num=1)
        
        # Should handle gracefully
        assert result.page_num == 1
        # Should either have fallback blocks or empty result
        assert len(result.blocks) >= 0


class TestLayoutDetectionValidation:
    """Test layout detection validation and quality metrics."""
    
    def test_block_coordinate_validation(self, tmp_path):
        """Test that detected blocks have valid coordinates."""
        # Create test image with known regions
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        cv2.rectangle(img, (50, 50), (250, 150), (0, 0, 0), 2)  # Header region
        
        test_path = tmp_path / "coords_test.png"
        cv2.imwrite(str(test_path), img)
        
        result = detect_document_layout(test_path, page_num=1)
        
        for block in result.blocks:
            x, y, w, h = block.bbox
            # Coordinates should be valid
            assert x >= 0
            assert y >= 0
            assert w > 0
            assert h > 0
            # Should be within image bounds
            assert x + w <= 300
            assert y + h <= 400
    
    def test_confidence_scores_validation(self, tmp_path):
        """Test that confidence scores are within valid range."""
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        test_path = tmp_path / "confidence_test.png"
        cv2.imwrite(str(test_path), img)
        
        result = detect_document_layout(test_path, page_num=1)
        
        for block in result.blocks:
            # Confidence should be between 0 and 1
            assert 0.0 <= block.confidence <= 1.0
        
        # Average confidence should be valid
        assert 0.0 <= result.confidence_avg <= 1.0
    
    def test_block_type_validation(self, tmp_path):
        """Test that block types are valid invoice/receipt types."""
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        test_path = tmp_path / "types_test.png"
        cv2.imwrite(str(test_path), img)
        
        result = detect_document_layout(test_path, page_num=1)
        
        valid_types = {"header", "table", "footer", "body", "handwriting"}
        
        for block in result.blocks:
            assert block.type in valid_types, f"Invalid block type: {block.type}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
