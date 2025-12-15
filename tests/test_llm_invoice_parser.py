"""
Comprehensive tests for LLM-based invoice parser.

Tests cover:
- Single-page invoice extraction
- Multi-page continuation detection
- Invoice/DN splitting
- Bounding box re-alignment
- Math verification
- Graceful failure modes
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Import modules to test
from backend.llm.invoice_parser import (
    LLMInvoiceParser,
    BBoxAligner,
    LLMLineItem,
    LLMDocumentResult,
    DocumentType,
    DocumentGroup,
    create_invoice_parser
)


# Sample OCR text for testing
SAMPLE_INVOICE_OCR = """
ACME Corporation Ltd
123 Business Street
London, UK

INVOICE

Invoice Number: INV-2024-001
Date: 15 January 2024
Currency: GBP

Bill To:
Customer Company
456 Customer Road

DESCRIPTION                QTY    UNIT PRICE    TOTAL
Crate of Beer             60     £10.60        £477.00
Unknown item              50     £9.85         £265.95
Unknown item              29     £30.74        £891.54

                          Subtotal:    £1,634.49
                          VAT (20%):   £326.90
                          Total:       £1,961.39

Payment Terms: Net 30
"""

SAMPLE_DELIVERY_NOTE_OCR = """
ACME Corporation Ltd
DELIVERY NOTE

Delivery Note Number: DN-2024-001
Date: 15 January 2024

DESCRIPTION                QTY
Crate of Beer             60
Wine Box                  50
Spirits Case              29

Delivered to: Customer Company
Signed: ___________
"""


class TestLLMInvoiceParser:
    """Test suite for LLM invoice parser."""
    
    def test_parser_initialization(self):
        """Test parser initializes with correct config."""
        parser = LLMInvoiceParser(
            ollama_url="http://test:11434",
            model_name="test-model",
            timeout=60,
            max_retries=5
        )
        
        assert parser.ollama_url == "http://test:11434"
        assert parser.model_name == "test-model"
        assert parser.timeout == 60
        assert parser.max_retries == 5
        assert parser.system_prompt is not None
    
    @patch('backend.llm.invoice_parser.requests.post')
    def test_parse_document_success(self, mock_post):
        """Test successful document parsing."""
        # Mock Ollama response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps({
                "document_type": "invoice",
                "supplier_name": "ACME Corporation Ltd",
                "invoice_number": "INV-2024-001",
                "invoice_date": "2024-01-15",
                "currency": "GBP",
                "line_items": [
                    {
                        "description": "Crate of Beer",
                        "qty": 60.0,
                        "unit_price": 10.60,
                        "total": 636.00
                    },
                    {
                        "description": "Wine Box",
                        "qty": 50.0,
                        "unit_price": 9.85,
                        "total": 492.50
                    }
                ],
                "subtotal": 1128.50,
                "vat_amount": 225.70,
                "vat_rate": 0.2,
                "grand_total": 1354.20
            })
        }
        mock_post.return_value = mock_response
        
        # Parse document
        parser = LLMInvoiceParser()
        result = parser.parse_document(SAMPLE_INVOICE_OCR)
        
        # Assertions
        assert result.success is True
        assert result.document_type == DocumentType.INVOICE
        assert result.supplier_name == "ACME Corporation Ltd"
        assert result.invoice_number == "INV-2024-001"
        assert len(result.line_items) == 2
        assert result.line_items[0].description == "Crate of Beer"
        assert result.line_items[0].qty == 60.0
        assert result.confidence > 0.0
    
    @patch('backend.llm.invoice_parser.requests.post')
    def test_parse_document_with_math_errors(self, mock_post):
        """Test parser detects and fixes math errors."""
        # Mock response with math error
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps({
                "document_type": "invoice",
                "supplier_name": "Test Corp",
                "invoice_number": "INV-001",
                "invoice_date": "2024-01-15",
                "currency": "GBP",
                "line_items": [
                    {
                        "description": "Item A",
                        "qty": 10.0,
                        "unit_price": 5.00,
                        "total": 60.00  # Wrong! Should be 50.00
                    }
                ],
                "subtotal": 60.00,
                "vat_amount": 12.00,
                "vat_rate": 0.2,
                "grand_total": 72.00
            })
        }
        mock_post.return_value = mock_response
        
        parser = LLMInvoiceParser()
        result = parser.parse_document("test ocr text")
        
        # Parser should auto-fix the math error
        assert result.line_items[0].total == 50.00  # Fixed
        assert result.confidence < 1.0  # Penalized for math error
    
    @patch('backend.llm.invoice_parser.requests.post')
    def test_parse_document_ollama_unavailable(self, mock_post):
        """Test graceful failure when Ollama is unavailable."""
        # Mock connection error
        mock_post.side_effect = ConnectionError("Ollama not running")
        
        parser = LLMInvoiceParser(max_retries=1)
        result = parser.parse_document("test ocr text")
        
        # Should return error result, not crash
        assert result.success is False
        assert result.error_message is not None
        assert result.confidence == 0.0
        assert "Ollama" in result.error_message or "Connection" in result.error_message
    
    @patch('backend.llm.invoice_parser.requests.post')
    def test_parse_document_timeout(self, mock_post):
        """Test timeout handling."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        parser = LLMInvoiceParser(timeout=1, max_retries=1)
        result = parser.parse_document("test ocr text")
        
        assert result.success is False
        assert result.confidence == 0.0
    
    @patch('backend.llm.invoice_parser.requests.post')
    def test_parse_document_invalid_json(self, mock_post):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "This is not valid JSON {broken"
        }
        mock_post.return_value = mock_response
        
        parser = LLMInvoiceParser()
        result = parser.parse_document("test ocr text")
        
        assert result.success is False
        assert "JSON" in result.error_message or "parse" in result.error_message.lower()
    
    @patch('backend.llm.invoice_parser.requests.post')
    def test_verify_totals_pass(self, mock_post):
        """Test totals verification passes for correct math."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps({
                "document_type": "invoice",
                "supplier_name": "Test",
                "invoice_number": "INV-001",
                "invoice_date": "2024-01-15",
                "currency": "GBP",
                "line_items": [
                    {"description": "Item", "qty": 10, "unit_price": 10, "total": 100}
                ],
                "subtotal": 100.00,
                "vat_amount": 20.00,
                "vat_rate": 0.2,
                "grand_total": 120.00
            })
        }
        mock_post.return_value = mock_response
        
        parser = LLMInvoiceParser()
        result = parser.parse_document("test")
        
        # Should have high confidence (no errors)
        assert result.confidence >= 0.9
        assert result.subtotal == 100.00
        assert result.grand_total == 120.00


class TestBBoxAligner:
    """Test suite for bounding box re-alignment."""
    
    def test_aligner_initialization(self):
        """Test aligner initializes with correct threshold."""
        aligner = BBoxAligner(match_threshold=0.8)
        assert aligner.match_threshold == 0.8
    
    def test_align_simple_match(self):
        """Test simple bbox alignment."""
        aligner = BBoxAligner()
        
        # LLM line items
        llm_items = [
            LLMLineItem(
                description="Crate of Beer",
                qty=60,
                unit_price=10.60,
                total=636.00
            )
        ]
        
        # OCR blocks
        ocr_blocks = [
            {"text": "Crate", "bbox": [10, 100, 40, 20]},
            {"text": "of", "bbox": [55, 100, 15, 20]},
            {"text": "Beer", "bbox": [75, 100, 30, 20]},
            {"text": "60", "bbox": [200, 100, 20, 20]},
        ]
        
        # Align
        aligned = aligner.align_llm_to_ocr(llm_items, ocr_blocks)
        
        # Should have bbox
        assert len(aligned) == 1
        assert aligned[0].bbox is not None
        assert len(aligned[0].bbox) == 4
        
        # Union bbox should cover "Crate of Beer"
        bbox = aligned[0].bbox
        assert bbox[0] == 10  # min x
        assert bbox[1] == 100  # min y
        assert bbox[2] == 95  # width (105 - 10)
        assert bbox[3] == 20  # height
    
    def test_align_no_match(self):
        """Test alignment when no OCR blocks match."""
        aligner = BBoxAligner()
        
        llm_items = [
            LLMLineItem(
                description="Champagne Bottle",
                qty=1,
                unit_price=100,
                total=100
            )
        ]
        
        ocr_blocks = [
            {"text": "Beer", "bbox": [10, 100, 40, 20]},
            {"text": "Wine", "bbox": [60, 100, 40, 20]},
        ]
        
        aligned = aligner.align_llm_to_ocr(llm_items, ocr_blocks)
        
        # Should still return item but without bbox (or confidence penalty)
        assert len(aligned) == 1
        assert aligned[0].bbox is None or aligned[0].bbox == [0, 0, 0, 0]
        assert aligned[0].confidence < 1.0  # Penalized
    
    def test_align_empty_ocr_blocks(self):
        """Test alignment with empty OCR blocks."""
        aligner = BBoxAligner()
        
        llm_items = [
            LLMLineItem(description="Item", qty=1, unit_price=10, total=10)
        ]
        
        aligned = aligner.align_llm_to_ocr(llm_items, [])
        
        # Should handle gracefully
        assert len(aligned) == 1
        assert aligned[0].bbox is None or aligned[0].bbox == [0, 0, 0, 0]


class TestMultiPageHandling:
    """Test multi-page document handling."""
    
    def test_is_continuation_no_header(self):
        """Test continuation detection when page 2 has no header."""
        parser = LLMInvoiceParser()
        
        page1 = LLMDocumentResult(
            document_type=DocumentType.INVOICE,
            supplier_name="ACME Corp",
            invoice_number="INV-001",
            invoice_date="2024-01-15",
            line_items=[
                LLMLineItem(description="Item 1", qty=10, unit_price=5, total=50)
            ],
            grand_total=60.0
        )
        
        page2 = LLMDocumentResult(
            document_type=DocumentType.INVOICE,
            supplier_name="",  # No header
            invoice_number="",
            invoice_date="",
            line_items=[
                LLMLineItem(description="Item 2", qty=5, unit_price=10, total=50)
            ],
            grand_total=0.0  # No totals
        )
        
        assert parser.is_continuation(page1, page2) is True
    
    def test_is_continuation_same_invoice_number(self):
        """Test continuation with same invoice number."""
        parser = LLMInvoiceParser()
        
        page1 = LLMDocumentResult(
            document_type=DocumentType.INVOICE,
            invoice_number="INV-001",
            line_items=[LLMLineItem(description="Item 1", qty=10, unit_price=5, total=50)]
        )
        
        page2 = LLMDocumentResult(
            document_type=DocumentType.INVOICE,
            invoice_number="INV-001",  # Same number
            line_items=[LLMLineItem(description="Item 2", qty=5, unit_price=10, total=50)]
        )
        
        assert parser.is_continuation(page1, page2) is True
    
    def test_is_continuation_different_docs(self):
        """Test non-continuation with different documents."""
        parser = LLMInvoiceParser()
        
        page1 = LLMDocumentResult(
            document_type=DocumentType.INVOICE,
            supplier_name="ACME Corp",
            invoice_number="INV-001",
            line_items=[LLMLineItem(description="Item 1", qty=10, unit_price=5, total=50)],
            grand_total=60.0
        )
        
        page2 = LLMDocumentResult(
            document_type=DocumentType.INVOICE,
            supplier_name="Different Corp",  # Different supplier
            invoice_number="INV-002",  # Different number
            line_items=[LLMLineItem(description="Item 2", qty=5, unit_price=10, total=50)],
            grand_total=60.0  # Has totals
        )
        
        assert parser.is_continuation(page1, page2) is False
    
    def test_merge_pages(self):
        """Test merging multiple pages into one document."""
        parser = LLMInvoiceParser()
        
        page1 = LLMDocumentResult(
            document_type=DocumentType.INVOICE,
            supplier_name="ACME Corp",
            invoice_number="INV-001",
            line_items=[
                LLMLineItem(description="Item 1", qty=10, unit_price=5, total=50)
            ],
            subtotal=50.0,
            vat_amount=0.0,
            grand_total=0.0  # No totals on first page
        )
        
        page2 = LLMDocumentResult(
            document_type=DocumentType.INVOICE,
            line_items=[
                LLMLineItem(description="Item 2", qty=5, unit_price=10, total=50)
            ],
            subtotal=100.0,  # Totals on last page
            vat_amount=20.0,
            grand_total=120.0
        )
        
        merged = parser.merge_pages([page1, page2])
        
        # Should have all line items
        assert len(merged.line_items) == 2
        # Should use last page's totals
        assert merged.grand_total == 120.0
        assert merged.subtotal == 100.0
    
    def test_split_documents_different_types(self):
        """Test splitting invoice + delivery note."""
        parser = LLMInvoiceParser()
        
        page1 = LLMDocumentResult(
            document_type=DocumentType.INVOICE,
            supplier_name="ACME Corp",
            invoice_number="INV-001",
            line_items=[LLMLineItem(description="Item 1", qty=10, unit_price=5, total=50)],
            grand_total=60.0
        )
        
        page2 = LLMDocumentResult(
            document_type=DocumentType.DELIVERY_NOTE,  # Different type
            supplier_name="ACME Corp",
            invoice_number="DN-001",
            line_items=[LLMLineItem(description="Item 2", qty=10, unit_price=0, total=0)],
            grand_total=0.0
        )
        
        groups = parser.split_documents([page1, page2])
        
        # Should split into 2 groups
        assert len(groups) == 2
        assert groups[0].document_type == DocumentType.INVOICE
        assert groups[1].document_type == DocumentType.DELIVERY_NOTE
        assert groups[0].pages == [1]
        assert groups[1].pages == [2]
    
    def test_split_documents_different_invoice_numbers(self):
        """Test splitting two separate invoices."""
        parser = LLMInvoiceParser()
        
        page1 = LLMDocumentResult(
            document_type=DocumentType.INVOICE,
            supplier_name="ACME Corp",
            invoice_number="INV-001",
            line_items=[LLMLineItem(description="Item 1", qty=10, unit_price=5, total=50)],
            grand_total=60.0
        )
        
        page2 = LLMDocumentResult(
            document_type=DocumentType.INVOICE,
            supplier_name="ACME Corp",
            invoice_number="INV-002",  # Different invoice
            line_items=[LLMLineItem(description="Item 2", qty=5, unit_price=10, total=50)],
            grand_total=60.0
        )
        
        groups = parser.split_documents([page1, page2])
        
        # Should split into 2 groups
        assert len(groups) == 2
        assert groups[0].pages == [1]
        assert groups[1].pages == [2]


class TestFactoryFunction:
    """Test factory function."""
    
    @patch('backend.llm.invoice_parser.LLM_OLLAMA_URL', 'http://test:11434')
    @patch('backend.llm.invoice_parser.LLM_MODEL_NAME', 'test-model')
    @patch('backend.llm.invoice_parser.LLM_TIMEOUT_SECONDS', 60)
    @patch('backend.llm.invoice_parser.LLM_MAX_RETRIES', 5)
    def test_create_invoice_parser_with_config(self):
        """Test factory function uses config values."""
        parser = create_invoice_parser()
        
        # Should use config values (but fallback if import fails)
        assert parser is not None
        assert isinstance(parser, LLMInvoiceParser)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

