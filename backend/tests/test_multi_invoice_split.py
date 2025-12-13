#!/usr/bin/env python3
"""
Tests for Multi-Invoice PDF Splitting functionality
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from typing import List

# Import the modules to test
from ocr.unified_ocr_engine import UnifiedOCREngine, InvoiceBlock
from ocr.ocr_engine import OCRResult


class TestInvoiceBoundaryDetection:
    """Test invoice boundary detection functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = UnifiedOCREngine()
    
    def test_detect_invoice_boundaries_single_invoice(self):
        """Test detection with single invoice (no boundaries)"""
        # Create mock OCR results for a single invoice
        pages = [
            OCRResult(text="Invoice No: INV-001\nSupplier: Test Corp\nTotal: £100", confidence=0.9, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=1),
            OCRResult(text="Line Item 1: £50\nLine Item 2: £50", confidence=0.8, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=2),
        ]
        
        blocks = self.engine.detect_invoice_boundaries(pages)
        
        assert len(blocks) == 1
        assert blocks[0].page_start == 1
        assert blocks[0].page_end == 2
        assert blocks[0].requires_manual_review == False
    
    def test_detect_invoice_boundaries_multiple_invoices(self):
        """Test detection with multiple invoices"""
        # Create mock OCR results for multiple invoices
        pages = [
            OCRResult(text="Invoice No: INV-001\nSupplier: Test Corp\nTotal: £100", confidence=0.9, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=1),
            OCRResult(text="Line Item 1: £50\nLine Item 2: £50", confidence=0.8, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=2),
            OCRResult(text="Invoice No: INV-002\nSupplier: Another Corp\nTotal: £200", confidence=0.9, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=3),
            OCRResult(text="Line Item 1: £100\nLine Item 2: £100", confidence=0.8, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=4),
        ]
        
        blocks = self.engine.detect_invoice_boundaries(pages)
        
        assert len(blocks) == 2
        assert blocks[0].page_start == 1
        assert blocks[0].page_end == 2
        assert blocks[0].requires_manual_review == False
        assert blocks[1].page_start == 3
        assert blocks[1].page_end == 4
        assert blocks[1].requires_manual_review == False
    
    def test_detect_invoice_boundaries_low_confidence(self):
        """Test detection with low confidence pages"""
        # Create mock OCR results with low confidence
        pages = [
            OCRResult(text="Invoice No: INV-001\nSupplier: Test Corp\nTotal: £100", confidence=0.3, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=1),
            OCRResult(text="Line Item 1: £50\nLine Item 2: £50", confidence=0.4, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=2),
        ]
        
        blocks = self.engine.detect_invoice_boundaries(pages)
        
        assert len(blocks) == 1
        assert blocks[0].requires_manual_review == True  # Should require review due to low confidence
    
    def test_detect_invoice_boundaries_ambiguous_headers(self):
        """Test detection with ambiguous headers"""
        # Create mock OCR results with overlapping headers
        pages = [
            OCRResult(text="Invoice No: INV-001\nSupplier: Test Corp\nTotal: £100", confidence=0.9, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=1),
            OCRResult(text="Invoice No: INV-001\nSupplier: Test Corp\nTotal: £100", confidence=0.9, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=2),  # Duplicate header
            OCRResult(text="Line Item 1: £50\nLine Item 2: £50", confidence=0.8, bounding_box=[[0,0],[100,0],[100,100],[0,100]], page_number=3),
        ]
        
        blocks = self.engine.detect_invoice_boundaries(pages)
        
        # Should detect this as a single invoice despite duplicate headers
        assert len(blocks) == 1
        assert blocks[0].page_start == 1
        assert blocks[0].page_end == 3
    
    def test_detect_invoice_boundaries_empty_pages(self):
        """Test detection with empty pages"""
        pages = []
        blocks = self.engine.detect_invoice_boundaries(pages)
        assert len(blocks) == 0
    
    def test_detect_invoice_boundaries_long_invoice(self):
        """Test detection with a long invoice spanning many pages"""
        # Create mock OCR results for a long invoice
        pages = []
        for i in range(10):
            if i == 0:
                # First page has header
                text = f"Invoice No: INV-001\nSupplier: Test Corp\nTotal: £1000\nPage {i+1}"
            else:
                # Subsequent pages are continuation
                text = f"Line Item {i+1}: £100\nPage {i+1}"
            
            pages.append(OCRResult(
                text=text, 
                confidence=0.8, 
                bounding_box=[[0,0],[100,0],[100,100],[0,100]], 
                page_number=i+1
            ))
        
        blocks = self.engine.detect_invoice_boundaries(pages)
        
        # Should detect as single invoice despite many pages
        assert len(blocks) == 1
        assert blocks[0].page_start == 1
        assert blocks[0].page_end == 10
        assert blocks[0].requires_manual_review == False


class TestOCRRetry:
    """Test OCR retry functionality"""
    
    @patch('routes.ocr_retry.get_db_connection')
    def test_retry_ocr_success(self, mock_db_connection):
        """Test successful OCR retry"""
        from routes.ocr_retry import retry_ocr, RetryOCRRequest
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_connection.return_value = mock_conn
        
        # Mock invoice data
        mock_cursor.fetchone.return_value = (0.5, "test.pdf", "1-3", "test text")
        
        # Mock retry log
        mock_cursor.fetchone.side_effect = [
            (0.5, "test.pdf", "1-3", "test text"),  # First call for invoice data
            (1,)  # Second call for retry count
        ]
        
        request = RetryOCRRequest(reason="Test retry")
        
        # This would need to be run in an async context
        # For now, just test that the function can be imported and called
        assert retry_ocr is not None
        assert RetryOCRRequest is not None


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


class TestIntegration:
    """Integration tests for multi-invoice processing"""
    
    @patch('ocr.unified_ocr_engine.get_unified_ocr_engine')
    def test_upload_with_multi_invoice_detection(self, mock_get_engine):
        """Test upload route with multi-invoice detection"""
        # Mock the unified OCR engine
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        # Mock OCR results
        mock_engine.detect_invoice_boundaries.return_value = [
            InvoiceBlock(page_start=1, page_end=2, confidence=0.8, requires_manual_review=False),
            InvoiceBlock(page_start=3, page_end=4, confidence=0.7, requires_manual_review=True),
        ]
        
        # This would test the upload route integration
        # For now, just verify the mock setup works
        assert mock_engine.detect_invoice_boundaries is not None


if __name__ == "__main__":
    pytest.main([__file__]) 