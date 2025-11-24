# -*- coding: utf-8 -*-
"""
Comprehensive test suite for table extraction functionality.

Tests structure-aware table extraction, cell detection, line-item parsing,
and fallback heuristics for various invoice and receipt formats.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
import cv2

from backend.ocr.table_extractor import (
    TableExtractor, LineItem, TableResult, extract_table_from_block
)


class TestTableExtractor:
    """Test the TableExtractor class functionality."""
    
    def test_table_extractor_initialization(self):
        """Test TableExtractor initializes correctly."""
        extractor = TableExtractor()
        assert extractor._confidence_threshold == 0.7
        assert extractor._min_cell_size == (20, 20)
        assert extractor._line_threshold == 50
        assert len(extractor._price_patterns) > 0
        assert len(extractor._quantity_patterns) > 0
    
    def test_detect_table_structure(self, tmp_path):
        """Test table structure detection with OpenCV."""
        extractor = TableExtractor()
        
        # Create a test image with table structure
        img = np.ones((400, 600, 3), dtype=np.uint8) * 255
        
        # Draw table lines
        # Horizontal lines
        for y in [50, 100, 150, 200, 250]:
            cv2.line(img, (50, y), (550, y), (0, 0, 0), 2)
        
        # Vertical lines
        for x in [50, 150, 300, 450, 550]:
            cv2.line(img, (x, 50), (x, 250), (0, 0, 0), 2)
        
        # Add some text in cells
        cv2.putText(img, "Item", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(img, "Qty", (160, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(img, "Price", (310, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        cells, detected = extractor._detect_table_structure(img)
        
        assert detected is True
        assert len(cells) > 0
        # Should detect multiple cells
        assert len(cells) >= 4
    
    def test_extract_cell_text(self, tmp_path):
        """Test cell text extraction."""
        extractor = TableExtractor()
        
        # Create a test cell image
        cell_img = np.ones((50, 100, 3), dtype=np.uint8) * 255
        cv2.putText(cell_img, "Test Item", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        cell_bbox = (0, 0, 100, 50)
        
        # Mock OCR methods
        with patch.object(extractor, '_load_paddle_ocr') as mock_load:
            mock_ocr = MagicMock()
            mock_ocr.ocr.return_value = [[[None, ("Test Item", 0.9)]]]
            mock_load.return_value = mock_ocr
            
            text, confidence = extractor._extract_cell_text(cell_img, cell_bbox)
            
            assert text == "Test Item"
            assert confidence == 0.9
    
    def test_group_cells_into_rows(self):
        """Test cell grouping into table rows."""
        extractor = TableExtractor()
        
        # Create mock cells with different y-coordinates
        cells = [
            (0, 0, 100, 50),    # Row 1
            (100, 0, 100, 50),  # Row 1
            (200, 0, 100, 50),  # Row 1
            (0, 60, 100, 50),   # Row 2
            (100, 60, 100, 50), # Row 2
            (200, 60, 100, 50), # Row 2
        ]
        
        cell_texts = ["Item1", "Qty1", "Price1", "Item2", "Qty2", "Price2"]
        
        rows = extractor._group_cells_into_rows(cells, cell_texts)
        
        assert len(rows) == 2  # Two rows
        assert len(rows[0]) == 3  # Three cells in first row
        assert len(rows[1]) == 3  # Three cells in second row
        
        # Check that cells are sorted left to right within rows
        assert rows[0][0][0] == 0   # First cell x-coordinate
        assert rows[0][1][0] == 100 # Second cell x-coordinate
        assert rows[0][2][0] == 200 # Third cell x-coordinate
    
    def test_parse_line_item(self):
        """Test line item parsing from cell data."""
        extractor = TableExtractor()
        
        # Create mock row cells
        row_cells = [
            (0, 0, 100, 50, "Widget A"),      # Description
            (100, 0, 50, 50, "5"),           # Quantity
            (150, 0, 80, 50, "$10.00"),      # Unit price
            (230, 0, 80, 50, "$50.00"),      # Total price
            (310, 0, 60, 50, "$5.00"),       # VAT
        ]
        
        line_item = extractor._parse_line_item(row_cells, 0)
        
        assert line_item.description == "Widget A"
        assert line_item.quantity == "5"
        assert line_item.unit_price == "$10.00"
        assert line_item.total_price == "$50.00"
        assert line_item.vat == "$5.00"
        assert line_item.row_index == 0
        assert line_item.confidence > 0.0
    
    def test_fallback_line_grouping(self):
        """Test fallback line grouping when structure detection fails."""
        extractor = TableExtractor()
        
        # Create mock OCR text
        ocr_text = """
        Item Description Quantity Price Total
        Widget A 5 $10.00 $50.00
        Widget B 3 $15.00 $45.00
        Widget C 2 $20.00 $40.00
        """
        
        line_items = extractor._fallback_line_grouping(np.ones((100, 100, 3), dtype=np.uint8), ocr_text)
        
        assert len(line_items) >= 3  # Should extract at least 3 line items
        
        # Check first line item
        first_item = line_items[0]
        assert "Widget A" in first_item.description
        assert first_item.quantity == "5"
        assert "$10.00" in first_item.unit_price
        assert "$50.00" in first_item.total_price
    
    def test_extract_table_structure_aware(self, tmp_path):
        """Test complete table extraction with structure detection."""
        extractor = TableExtractor()
        
        # Create a test table image
        img = np.ones((300, 500, 3), dtype=np.uint8) * 255
        
        # Draw table structure
        # Horizontal lines
        for y in [50, 100, 150, 200]:
            cv2.line(img, (50, y), (450, y), (0, 0, 0), 2)
        
        # Vertical lines
        for x in [50, 150, 250, 350, 450]:
            cv2.line(img, (x, 50), (x, 200), (0, 0, 0), 2)
        
        # Add text content
        cv2.putText(img, "Item", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(img, "Qty", (160, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(img, "Price", (260, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(img, "Total", (360, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        cv2.putText(img, "Widget A", (60, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(img, "5", (160, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(img, "$10.00", (260, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(img, "$50.00", (360, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        
        bbox = (0, 0, 500, 300)
        
        # Mock cell text extraction
        with patch.object(extractor, '_extract_cell_text') as mock_extract:
            mock_extract.return_value = ("Mock Text", 0.8)
            
            result = extractor.extract_table(img, bbox)
            
            assert result.type == "table"
            assert result.method_used in ["structure_aware", "fallback_line_grouping"]
            assert result.processing_time > 0
            assert result.cell_count >= 0
            assert result.row_count >= 0
    
    def test_extract_table_fallback(self, tmp_path):
        """Test table extraction with fallback when structure detection fails."""
        extractor = TableExtractor()
        
        # Create a test image without clear table structure
        img = np.ones((200, 400, 3), dtype=np.uint8) * 255
        cv2.putText(img, "Item Widget A Qty 5 Price $10.00 Total $50.00", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        bbox = (0, 0, 400, 200)
        ocr_text = "Item Widget A Qty 5 Price $10.00 Total $50.00"
        
        # Mock structure detection to fail
        with patch.object(extractor, '_detect_table_structure') as mock_detect:
            mock_detect.return_value = ([], False)
            
            result = extractor.extract_table(img, bbox, ocr_text)
            
            assert result.type == "table"
            assert result.method_used == "fallback_line_grouping"
            assert result.fallback_used is True
            assert len(result.line_items) > 0
    
    def test_error_handling(self, tmp_path):
        """Test error handling in table extraction."""
        extractor = TableExtractor()
        
        # Test with empty image
        empty_img = np.array([])
        bbox = (0, 0, 0, 0)
        
        result = extractor.extract_table(empty_img, bbox)
        
        assert result.type == "table"
        assert result.method_used == "error"
        assert result.confidence == 0.0
        assert len(result.line_items) == 0
    
    def test_save_table_artifacts(self, tmp_path):
        """Test saving table extraction artifacts."""
        extractor = TableExtractor()
        
        # Create test result
        line_item = LineItem(
            description="Test Item",
            quantity="5",
            unit_price="$10.00",
            total_price="$50.00",
            vat="$5.00",
            confidence=0.9,
            row_index=0,
            cell_data={"cell_0": "Test Item"}
        )
        
        result = TableResult(
            type="table",
            bbox=(0, 0, 400, 200),
            line_items=[line_item],
            confidence=0.9,
            method_used="structure_aware",
            processing_time=0.1,
            fallback_used=False,
            cell_count=4,
            row_count=1
        )
        
        # Save artifacts
        json_path = extractor.save_table_artifacts(result, tmp_path)
        
        # Verify file was created
        assert json_path.exists()
        assert json_path.name.startswith("table_extraction_")
        
        # Verify JSON content
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        assert data["type"] == "table"
        assert len(data["line_items"]) == 1
        assert data["method_used"] == "structure_aware"
        assert data["confidence"] == 0.9


class TestTableExtractorIntegration:
    """Test table extractor integration with the main pipeline."""
    
    def test_extract_table_from_block_function(self, tmp_path):
        """Test the main extract_table_from_block function."""
        # Create test image
        img = np.ones((300, 500, 3), dtype=np.uint8) * 255
        
        # Draw simple table
        cv2.line(img, (50, 50), (450, 50), (0, 0, 0), 2)
        cv2.line(img, (50, 100), (450, 100), (0, 0, 0), 2)
        cv2.line(img, (50, 50), (50, 100), (0, 0, 0), 2)
        cv2.line(img, (250, 50), (250, 100), (0, 0, 0), 2)
        cv2.line(img, (450, 50), (450, 100), (0, 0, 0), 2)
        
        cv2.putText(img, "Item", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(img, "Price", (260, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        block_info = {
            "type": "table",
            "bbox": [0, 0, 500, 300]
        }
        
        # Mock cell text extraction
        with patch('backend.ocr.table_extractor.TableExtractor._extract_cell_text') as mock_extract:
            mock_extract.return_value = ("Mock Text", 0.8)
            
            result = extract_table_from_block(img, block_info)
            
            assert result.type == "table"
            assert result.method_used in ["structure_aware", "fallback_line_grouping"]
            assert result.processing_time > 0
    
    def test_non_table_block(self, tmp_path):
        """Test handling of non-table blocks."""
        img = np.ones((200, 300, 3), dtype=np.uint8) * 255
        
        block_info = {
            "type": "header",
            "bbox": [0, 0, 300, 200]
        }
        
        result = extract_table_from_block(img, block_info)
        
        assert result.type == "header"
        assert result.method_used == "not_table"
        assert len(result.line_items) == 0


class TestTableExtractorPerformance:
    """Test table extractor performance and robustness."""
    
    def test_processing_performance(self, tmp_path):
        """Test that table extraction completes within reasonable time."""
        import time
        
        extractor = TableExtractor()
        
        # Create test table image
        img = np.ones((400, 600, 3), dtype=np.uint8) * 255
        
        # Draw table structure
        for y in range(50, 400, 50):
            cv2.line(img, (50, y), (550, y), (0, 0, 0), 1)
        for x in range(50, 600, 100):
            cv2.line(img, (x, 50), (x, 350), (0, 0, 0), 1)
        
        bbox = (0, 0, 600, 400)
        
        start_time = time.time()
        result = extractor.extract_table(img, bbox)
        end_time = time.time()
        
        # Should complete within 10 seconds
        assert (end_time - start_time) < 10.0
        assert result.processing_time < 10.0
    
    def test_large_table_processing(self, tmp_path):
        """Test processing of large tables with many cells."""
        extractor = TableExtractor()
        
        # Create large table image
        img = np.ones((800, 1200, 3), dtype=np.uint8) * 255
        
        # Draw many table cells
        for y in range(50, 800, 30):
            cv2.line(img, (50, y), (1150, y), (0, 0, 0), 1)
        for x in range(50, 1200, 100):
            cv2.line(img, (x, 50), (x, 750), (0, 0, 0), 1)
        
        bbox = (0, 0, 1200, 800)
        
        # Mock cell text extraction for performance
        with patch.object(extractor, '_extract_cell_text') as mock_extract:
            mock_extract.return_value = ("Cell Text", 0.8)
            
            result = extractor.extract_table(img, bbox)
            
            assert result.processing_time > 0
            assert result.cell_count > 0
            assert result.row_count > 0
    
    def test_memory_efficiency(self, tmp_path):
        """Test memory efficiency with large images."""
        extractor = TableExtractor()
        
        # Create large image
        img = np.ones((2000, 3000, 3), dtype=np.uint8) * 255
        
        # Add some table structure
        cv2.line(img, (100, 100), (2900, 100), (0, 0, 0), 2)
        cv2.line(img, (100, 200), (2900, 200), (0, 0, 0), 2)
        cv2.line(img, (100, 100), (100, 200), (0, 0, 0), 2)
        cv2.line(img, (1500, 100), (1500, 200), (0, 0, 0), 2)
        cv2.line(img, (2900, 100), (2900, 200), (0, 0, 0), 2)
        
        bbox = (100, 100, 2800, 100)
        
        # Should handle large images without memory issues
        result = extractor.extract_table(img, bbox)
        
        assert result.processing_time > 0
        assert result.type == "table"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
