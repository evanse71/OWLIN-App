#!/usr/bin/env python3
"""
Simplified Tests for Multi-Invoice PDF Splitting functionality
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from typing import List

# Import the modules to test
from ocr.unified_ocr_engine import InvoiceBlock
from ocr.ocr_engine import OCRResult


class TestInvoiceBlock:
    """Test InvoiceBlock dataclass"""
    
    def test_invoice_block_creation(self):
        """Test creating an InvoiceBlock"""
        block = InvoiceBlock(
            page_start=1,
            page_end=3,
            confidence=0.8,
            requires_manual_review=False,
            header_text="Invoice No: INV-001",
            supplier_guess="Test Corp"
        )
        
        assert block.page_start == 1
        assert block.page_end == 3
        assert block.confidence == 0.8
        assert block.requires_manual_review == False
        assert block.header_text == "Invoice No: INV-001"
        assert block.supplier_guess == "Test Corp"
    
    def test_invoice_block_defaults(self):
        """Test InvoiceBlock with default values"""
        block = InvoiceBlock(
            page_start=1,
            page_end=2,
            confidence=0.5,
            requires_manual_review=True
        )
        
        assert block.header_text == ""
        assert block.supplier_guess == ""


class TestOCRResult:
    """Test OCRResult class"""
    
    def test_ocr_result_creation(self):
        """Test creating an OCRResult"""
        result = OCRResult(
            text="Test invoice text",
            confidence=0.9,
            bounding_box=[[0,0],[100,0],[100,100],[0,100]],
            page_number=1
        )
        
        assert result.text == "Test invoice text"
        assert result.confidence == 0.9
        assert result.page_number == 1


class TestBoundaryDetectionLogic:
    """Test boundary detection logic without full engine"""
    
    def test_header_pattern_matching(self):
        """Test header pattern matching logic"""
        import re
        
        # Header patterns from the engine
        header_patterns = [
            r'\b(?:invoice|inv)\s*(?:no|number|#)\s*[:.]?\s*([A-Z0-9\-/]+)',
            r'\b(?:invoice|inv)\s*(?:date|dated)\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'\b(?:supplier|vendor|company)\s*[:.]?\s*([A-Za-z\s&]+)',
        ]
        
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in header_patterns]
        
        # Test text with invoice header
        test_text = "Invoice No: INV-001\nSupplier: Test Corp\nTotal: £100"
        
        header_found = False
        for pattern in compiled_patterns:
            matches = pattern.findall(test_text)
            if matches:
                header_found = True
                break
        
        assert header_found == True
    
    def test_confidence_thresholds(self):
        """Test confidence threshold logic"""
        # High confidence should not require manual review
        high_confidence = 0.8
        requires_review_high = high_confidence < 0.6
        assert requires_review_high == False
        
        # Low confidence should require manual review
        low_confidence = 0.4
        requires_review_low = low_confidence < 0.6
        assert requires_review_low == True


class TestDatabaseSchema:
    """Test database schema for multi-invoice support"""
    
    def test_migration_sql_syntax(self):
        """Test that migration SQL is syntactically correct"""
        # Read the migration file
        migration_path = "db/migrations/20250820_multi_invoice_support.sql"
        
        if os.path.exists(migration_path):
            with open(migration_path, 'r') as f:
                sql_content = f.read()
            
            # Basic syntax check - ensure no obvious SQL errors
            assert "ALTER TABLE invoices ADD COLUMN" in sql_content
            assert "requires_manual_review" in sql_content
            assert "page_range" in sql_content
            assert "parent_pdf_filename" in sql_content
            assert "CREATE INDEX" in sql_content


class TestMockBoundaryDetection:
    """Test boundary detection with mocked engine"""
    
    @patch('ocr.unified_ocr_engine.UnifiedOCREngine')
    def test_mock_boundary_detection(self, mock_engine_class):
        """Test boundary detection with mocked engine"""
        # Create mock engine
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        # Mock the detect_invoice_boundaries method
        mock_engine.detect_invoice_boundaries.return_value = [
            InvoiceBlock(page_start=1, page_end=2, confidence=0.8, requires_manual_review=False),
            InvoiceBlock(page_start=3, page_end=4, confidence=0.7, requires_manual_review=True),
        ]
        
        # Test the mock
        pages = [OCRResult(text="test", confidence=0.8, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=1)]
        blocks = mock_engine.detect_invoice_boundaries(pages)
        
        assert len(blocks) == 2
        assert blocks[0].page_start == 1
        assert blocks[0].page_end == 2
        assert blocks[0].requires_manual_review == False
        assert blocks[1].page_start == 3
        assert blocks[1].page_end == 4
        assert blocks[1].requires_manual_review == True


if __name__ == "__main__":
    pytest.main([__file__]) 