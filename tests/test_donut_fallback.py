# tests/test_donut_fallback.py
"""
Unit tests for Donut fallback module.

This module tests the Donut fallback functionality including model wrapper,
output mapping, and pipeline integration.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from backend.fallbacks.donut_fallback import DonutFallback, DonutResult, get_donut_fallback
from backend.fallbacks.mapper import map_donut_to_invoice_card, merge_invoice_cards, validate_invoice_card


class TestDonutFallback(unittest.TestCase):
    """Test Donut fallback processor."""
    
    def test_donut_fallback_initialization_disabled(self):
        """Test Donut fallback initialization when disabled."""
        fallback = DonutFallback(enabled=False)
        
        self.assertFalse(fallback.enabled)
        self.assertFalse(fallback.is_available())
        self.assertFalse(fallback._model_loaded)
    
    def test_donut_fallback_initialization_enabled(self):
        """Test Donut fallback initialization when enabled."""
        with patch('backend.fallbacks.donut_fallback.DonutFallback._load_donut_model'):
            fallback = DonutFallback(enabled=True)
            
            self.assertTrue(fallback.enabled)
            # Model loading is mocked, so availability depends on mock
    
    def test_is_available_disabled(self):
        """Test is_available when disabled."""
        fallback = DonutFallback(enabled=False)
        self.assertFalse(fallback.is_available())
    
    def test_is_available_no_model(self):
        """Test is_available when model not loaded."""
        fallback = DonutFallback(enabled=True)
        fallback._model_loaded = False
        fallback._model = None
        
        self.assertFalse(fallback.is_available())
    
    def test_is_available_with_model(self):
        """Test is_available when model is loaded."""
        fallback = DonutFallback(enabled=True)
        fallback._model_loaded = True
        fallback._model = Mock()
        
        self.assertTrue(fallback.is_available())
    
    def test_process_document_unavailable(self):
        """Test process_document when model is unavailable."""
        fallback = DonutFallback(enabled=True)
        fallback._model_loaded = False
        
        result = fallback.process_document("/path/to/image.png")
        
        self.assertFalse(result.ok)
        self.assertEqual(result.meta["reason"], "unavailable")
    
    @patch('backend.fallbacks.donut_fallback.Path.exists')
    @patch('backend.fallbacks.donut_fallback.Image.open')
    def test_process_document_success(self, mock_image_open, mock_path_exists):
        """Test successful document processing."""
        # Setup mocks
        mock_path_exists.return_value = True
        mock_image = Mock()
        mock_image.mode = "RGB"
        mock_image_open.return_value = mock_image
        
        # Create fallback with mock model
        fallback = DonutFallback(enabled=True)
        fallback._model_loaded = True
        fallback._model = Mock()
        fallback.processor = Mock()
        
        # Mock the processing methods
        with patch.object(fallback, '_process_with_donut') as mock_process:
            mock_process.return_value = {
                "parsed": {"company": "Test Company", "total": "100.00"},
                "confidence": 0.8,
                "meta": {"model": "test"}
            }
            
            result = fallback.process_document("/path/to/image.png")
            
            self.assertTrue(result.ok)
            self.assertEqual(result.confidence, 0.8)
            self.assertIn("company", result.parsed)
    
    def test_get_model_info(self):
        """Test get_model_info method."""
        fallback = DonutFallback(enabled=True, model_path="/path/to/model")
        fallback._model_loaded = True
        fallback._model = Mock()
        fallback._model.name = "test_model"
        
        info = fallback.get_model_info()
        
        self.assertTrue(info["enabled"])
        self.assertTrue(info["available"])
        self.assertTrue(info["model_loaded"])
        self.assertEqual(info["model_path"], "/path/to/model")
        self.assertEqual(info["model_name"], "test_model")


class TestDonutResult(unittest.TestCase):
    """Test DonutResult data class."""
    
    def test_donut_result_creation(self):
        """Test DonutResult creation."""
        result = DonutResult(
            ok=True,
            parsed={"company": "Test Company"},
            confidence=0.8,
            took_s=1.5,
            meta={"model": "test"}
        )
        
        self.assertTrue(result.ok)
        self.assertEqual(result.parsed["company"], "Test Company")
        self.assertEqual(result.confidence, 0.8)
        self.assertEqual(result.took_s, 1.5)
    
    def test_donut_result_to_dict(self):
        """Test DonutResult to_dict method."""
        result = DonutResult(
            ok=True,
            parsed={"company": "Test Company"},
            confidence=0.8,
            took_s=1.5
        )
        
        result_dict = result.to_dict()
        
        self.assertIn("ok", result_dict)
        self.assertIn("parsed", result_dict)
        self.assertIn("confidence", result_dict)
        self.assertIn("took_s", result_dict)
        self.assertIn("meta", result_dict)


class TestDonutMapper(unittest.TestCase):
    """Test Donut output mapping functionality."""
    
    def test_map_donut_to_invoice_card_basic(self):
        """Test basic Donut output mapping."""
        donut_output = {
            "company": "Test Company",
            "date": "2024-01-01",
            "total": "100.00",
            "vat_total": "20.00"
        }
        
        invoice_card = map_donut_to_invoice_card(donut_output)
        
        self.assertEqual(invoice_card["supplier"], "Test Company")
        self.assertEqual(invoice_card["date"], "2024-01-01")
        self.assertEqual(invoice_card["total"], 100.0)
        self.assertEqual(invoice_card["vat_total"], 20.0)
        self.assertIn("mapping_metadata", invoice_card)
    
    def test_map_donut_to_invoice_card_with_line_items(self):
        """Test mapping with line items."""
        donut_output = {
            "company": "Test Company",
            "line_items": [
                {"description": "Item 1", "quantity": "2", "unit_price": "10.00"},
                {"description": "Item 2", "quantity": "1", "unit_price": "20.00"}
            ]
        }
        
        invoice_card = map_donut_to_invoice_card(donut_output)
        
        self.assertEqual(len(invoice_card["line_items"]), 2)
        self.assertEqual(invoice_card["line_items"][0]["description"], "Item 1")
        self.assertEqual(invoice_card["line_items"][0]["quantity"], 2.0)
    
    def test_map_donut_to_invoice_card_empty(self):
        """Test mapping with empty output."""
        donut_output = {}
        
        invoice_card = map_donut_to_invoice_card(donut_output)
        
        self.assertIsNone(invoice_card["supplier"])
        self.assertIsNone(invoice_card["date"])
        self.assertIsNone(invoice_card["total"])
        self.assertEqual(len(invoice_card["line_items"]), 0)
    
    def test_map_donut_to_invoice_card_malformed(self):
        """Test mapping with malformed output."""
        donut_output = "not a dict"
        
        invoice_card = map_donut_to_invoice_card(donut_output)
        
        # Should handle gracefully
        self.assertIsNone(invoice_card["supplier"])
        self.assertIn("mapping_error", invoice_card)


class TestInvoiceCardMerger(unittest.TestCase):
    """Test invoice card merging functionality."""
    
    def test_merge_invoice_cards_basic(self):
        """Test basic invoice card merging."""
        base_card = {
            "supplier": "Base Company",
            "date": "2024-01-01",
            "total": 100.0
        }
        
        donut_card = {
            "supplier": "Donut Company",
            "date": "2024-01-02",
            "total": 200.0,
            "vat_total": 40.0
        }
        
        merged = merge_invoice_cards(base_card, donut_card)
        
        # Should keep base values for existing fields
        self.assertEqual(merged["supplier"], "Base Company")
        self.assertEqual(merged["date"], "2024-01-01")
        self.assertEqual(merged["total"], 100.0)
        
        # Should add new fields from Donut
        self.assertEqual(merged["vat_total"], 40.0)
        self.assertTrue(merged["donut_merged"])
    
    def test_merge_invoice_cards_fill_missing(self):
        """Test merging when base card has missing fields."""
        base_card = {
            "supplier": "Base Company"
        }
        
        donut_card = {
            "supplier": "Donut Company",
            "date": "2024-01-02",
            "total": 200.0
        }
        
        merged = merge_invoice_cards(base_card, donut_card)
        
        # Should keep existing base values
        self.assertEqual(merged["supplier"], "Base Company")
        
        # Should fill missing fields from Donut
        self.assertEqual(merged["date"], "2024-01-02")
        self.assertEqual(merged["total"], 200.0)
    
    def test_merge_invoice_cards_line_items(self):
        """Test merging line items."""
        base_card = {
            "supplier": "Base Company",
            "line_items": []
        }
        
        donut_card = {
            "line_items": [
                {"description": "Item 1", "quantity": 1}
            ]
        }
        
        merged = merge_invoice_cards(base_card, donut_card)
        
        # Should add line items when base is empty
        self.assertEqual(len(merged["line_items"]), 1)
        self.assertEqual(merged["line_items"][0]["description"], "Item 1")


class TestInvoiceCardValidator(unittest.TestCase):
    """Test invoice card validation functionality."""
    
    def test_validate_invoice_card_basic(self):
        """Test basic invoice card validation."""
        card = {
            "supplier": "Test Company",
            "date": "2024-01-01",
            "total": 100.0,
            "line_items": [
                {"description": "Item 1", "quantity": 1}
            ]
        }
        
        validated = validate_invoice_card(card)
        
        self.assertEqual(validated["supplier"], "Test Company")
        self.assertEqual(validated["date"], "2024-01-01")
        self.assertEqual(validated["total"], 100.0)
        self.assertEqual(len(validated["line_items"]), 1)
        self.assertIn("validation_metadata", validated)
    
    def test_validate_invoice_card_malformed(self):
        """Test validation with malformed card."""
        card = {
            "supplier": "Test Company",
            "line_items": "not a list"  # Invalid line items
        }
        
        validated = validate_invoice_card(card)
        
        # Should handle gracefully
        self.assertEqual(validated["supplier"], "Test Company")
        self.assertNotIn("line_items", validated)


class TestDonutGlobalFunctions(unittest.TestCase):
    """Test global Donut functions."""
    
    def test_get_donut_fallback(self):
        """Test getting global Donut fallback instance."""
        fallback = get_donut_fallback(enabled=True)
        
        self.assertIsNotNone(fallback)
        self.assertTrue(fallback.enabled)
        
        # Should return same instance
        fallback2 = get_donut_fallback()
        self.assertIs(fallback, fallback2)
    
    @patch('backend.fallbacks.donut_fallback.DonutFallback')
    def test_initialize_donut_fallback(self, mock_fallback_class):
        """Test Donut fallback initialization."""
        mock_fallback = Mock()
        mock_fallback.is_available.return_value = True
        mock_fallback_class.return_value = mock_fallback
        
        result = initialize_donut_fallback(enabled=True)
        
        self.assertTrue(result)
        mock_fallback_class.assert_called_once_with(enabled=True, model_path=None)


if __name__ == '__main__':
    unittest.main()
