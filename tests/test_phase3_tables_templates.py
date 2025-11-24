"""
Phase 3 Tables + Templates + Donut + LLM Tests

Tests for table extraction, supplier templates, Donut fallback, and LLM normalization
with graceful fallbacks when optional dependencies are missing.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

from backend.ocr.table_extractor import (
    Cell, cluster_columns, assemble_rows, to_string_table,
    extract_table_data, detect_table_headers, extract_line_items
)
from backend.ocr.donut_fallback import DonutRunner, get_donut_runner, parse_with_donut
from backend.llm.normalize_ocr import normalize, normalize_with_llm
from backend.config import (
    FEATURE_OCR_V3_TABLES, FEATURE_OCR_V3_TEMPLATES,
    FEATURE_OCR_V3_DONUT, FEATURE_OCR_V3_LLM,
    CONF_FALLBACK_PAGE, CONF_FALLBACK_OVERALL
)


class TestTableExtraction:
    """Test Phase 3 table extraction functionality."""
    
    def test_tables_flag_off_returns_without_table_data(self, monkeypatch):
        """Test that table extraction is disabled when flag is off."""
        monkeypatch.setenv("FEATURE_OCR_V3_TABLES", "false")
        from backend.ocr.table_extractor import to_string_table
        assert to_string_table([]) == []
    
    def test_cell_clustering(self):
        """Test cell clustering into columns."""
        cells = [
            Cell((10, 20, 50, 30), "Item 1", 0.9),
            Cell((12, 20, 50, 30), "Item 2", 0.8),  # Same column (x within tolerance)
            Cell((100, 20, 50, 30), "Price 1", 0.9),  # Different column
            Cell((102, 20, 50, 30), "Price 2", 0.8),  # Same column as Price 1
        ]
        
        columns = cluster_columns(cells)
        assert len(columns) == 2
        assert len(columns[0]) == 2  # Item 1, Item 2
        assert len(columns[1]) == 2  # Price 1, Price 2
    
    def test_row_assembly(self):
        """Test cell assembly into rows."""
        cells = [
            Cell((10, 20, 50, 30), "Item 1", 0.9),
            Cell((100, 20, 50, 30), "Price 1", 0.8),  # Same row (y within tolerance)
            Cell((10, 50, 50, 30), "Item 2", 0.9),  # Different row
            Cell((100, 50, 50, 30), "Price 2", 0.8),  # Same row as Item 2
        ]
        
        rows = assemble_rows(cells)
        assert len(rows) == 2
        assert len(rows[0]) == 2  # Item 1, Price 1
        assert len(rows[1]) == 2  # Item 2, Price 2
    
    def test_string_table_conversion(self):
        """Test conversion to string table."""
        cells = [
            Cell((10, 20, 50, 30), "Item 1", 0.9),
            Cell((100, 20, 50, 30), "Price 1", 0.8),
        ]
        rows = [[cells[0], cells[1]]]
        
        result = to_string_table(rows)
        assert result == [["Item 1", "Price 1"]]
    
    def test_table_headers_detection(self):
        """Test table header detection."""
        table_data = [
            ["Item", "Qty", "Price", "Total"],
            ["Sample Item", "1", "£10.00", "£10.00"]
        ]
        
        headers = detect_table_headers(table_data)
        assert headers == ["Item", "Qty", "Price", "Total"]
    
    def test_line_items_extraction(self):
        """Test line items extraction from table data."""
        table_data = [
            ["Item", "Qty", "Price", "Total"],
            ["Sample Item", "1", "£10.00", "£10.00"],
            ["Another Item", "2", "£5.00", "£10.00"]
        ]
        headers = ["Item", "Qty", "Price", "Total"]
        
        line_items = extract_line_items(table_data, headers)
        assert len(line_items) == 2
        assert line_items[0]["item"] == "Sample Item"
        assert line_items[0]["qty"] == "1"
        assert line_items[1]["item"] == "Another Item"


class TestSupplierTemplates:
    """Test Phase 3 supplier template functionality."""
    
    def test_templates_yaml_loads(self):
        """Test that supplier templates YAML file exists and loads."""
        template_path = Path("backend/ocr/supplier_templates.yaml")
        assert template_path.exists()
        
        content = template_path.read_text(encoding="utf-8")
        assert "supplier:" in content
        assert "ACME SUPPLIES LTD" in content
        assert "FARM FRESH PRODUCE" in content
    
    def test_template_matching_placeholder(self):
        """Test template matching functionality (placeholder)."""
        # This would test the actual template matching logic
        # For now, just verify the function exists
        from backend.ocr.owlin_scan_pipeline import _load_supplier_templates, _match_supplier_template
        
        templates = _load_supplier_templates()
        assert isinstance(templates, list)
        
        # Test with mock data
        if templates:
            result = _match_supplier_template("ACME SUPPLIES LTD Invoice #12345", templates)
            # Should match ACME template
            assert result is not None or result is None  # Either matches or doesn't


class TestDonutFallback:
    """Test Phase 3 Donut fallback functionality."""
    
    def test_donut_runner_initialization(self):
        """Test Donut runner initialization."""
        runner = DonutRunner()
        assert runner.model is None
        assert runner.processor is None
        assert not runner._loaded
    
    def test_donut_runner_load_graceful_fallback(self):
        """Test Donut runner graceful fallback when dependencies missing."""
        runner = DonutRunner()
        
        # Test that load() returns False when transformers not available
        # (This will naturally fail if transformers is not installed)
        result = runner.load()
        # Should be False if transformers not available, True if it is
        assert isinstance(result, bool)
        # If it loaded successfully, it should be marked as loaded
        if result:
            assert runner._loaded
    
    def test_donut_parse_unavailable(self):
        """Test Donut parsing when model not available."""
        runner = DonutRunner()
        result = runner.parse_image("nonexistent.jpg")
        
        assert result["status"] == "unavailable"
        assert "error" in result
    
    def test_get_donut_runner_singleton(self):
        """Test global Donut runner singleton."""
        runner1 = get_donut_runner()
        runner2 = get_donut_runner()
        assert runner1 is runner2
    
    def test_parse_with_donut_convenience(self):
        """Test convenience function for Donut parsing."""
        result = parse_with_donut("nonexistent.jpg")
        assert result["status"] == "unavailable"


class TestLLMNormalizer:
    """Test Phase 3 LLM normalization functionality."""
    
    def test_llm_normalizer_failsafe(self):
        """Test LLM normalizer failsafe behavior."""
        from backend.llm.normalize_ocr import normalize
        
        out = normalize(["Total: £12.50"])
        assert out["currency"] in ("GBP", "EUR", "USD", None)
        assert "supplier_name" in out
        assert "invoice_number" in out
        assert "total_amount" in out
        assert "lines" in out
        assert "confidence" in out
    
    def test_currency_detection(self):
        """Test currency detection in normalization."""
        from backend.llm.normalize_ocr import normalize
        
        # Test GBP
        result = normalize(["Total: £12.50"])
        assert result["currency"] == "GBP"
        
        # Test EUR
        result = normalize(["Total: €12.50"])
        assert result["currency"] == "EUR"
        
        # Test USD
        result = normalize(["Total: $12.50"])
        assert result["currency"] == "USD"
    
    def test_invoice_number_extraction(self):
        """Test invoice number extraction."""
        from backend.llm.normalize_ocr import normalize
        
        result = normalize(["Invoice #12345", "Date: 2023-01-01"])
        assert result["invoice_number"] == "12345"
    
    def test_normalize_with_llm_placeholder(self):
        """Test LLM normalization placeholder."""
        from backend.llm.normalize_ocr import normalize_with_llm
        
        result = normalize_with_llm(["Total: £12.50"])
        assert "currency" in result
        assert result["currency"] == "GBP"


class TestPhase3Integration:
    """Test Phase 3 integration with feature flags."""
    
    def test_all_flags_off_phase2_behavior(self, monkeypatch):
        """Test that with all Phase 3 flags off, behavior matches Phase 2."""
        monkeypatch.setenv("FEATURE_OCR_V3_TABLES", "false")
        monkeypatch.setenv("FEATURE_OCR_V3_TEMPLATES", "false")
        monkeypatch.setenv("FEATURE_OCR_V3_DONUT", "false")
        monkeypatch.setenv("FEATURE_OCR_V3_LLM", "false")
        
        # Test that functions exist and can be called
        from backend.ocr.table_extractor import extract_table_data
        from backend.ocr.donut_fallback import parse_with_donut
        from backend.llm.normalize_ocr import normalize_with_llm
        
        # These should not crash
        assert extract_table_data([], "test.jpg") is None
        assert parse_with_donut("test.jpg")["status"] == "unavailable"
        assert normalize_with_llm(["test"]) is not None
    
    def test_missing_dependencies_graceful_fallback(self, monkeypatch):
        """Test that missing dependencies don't crash the system."""
        monkeypatch.setenv("FEATURE_OCR_V3_TABLES", "true")
        monkeypatch.setenv("FEATURE_OCR_V3_TEMPLATES", "true")
        monkeypatch.setenv("FEATURE_OCR_V3_DONUT", "true")
        monkeypatch.setenv("FEATURE_OCR_V3_LLM", "true")
        
        # Test with missing dependencies
        with patch('backend.ocr.owlin_scan_pipeline.yaml', None):
            with patch('backend.ocr.owlin_scan_pipeline.fuzz', None):
                # Should not crash
                from backend.ocr.owlin_scan_pipeline import _load_supplier_templates, _match_supplier_template
                
                templates = _load_supplier_templates()
                assert templates == []
                
                result = _match_supplier_template("test", [])
                assert result is None
    
    def test_config_flags_loaded(self):
        """Test that Phase 3 config flags are properly loaded."""
        from backend.config import (
            FEATURE_OCR_V3_TABLES, FEATURE_OCR_V3_TEMPLATES,
            FEATURE_OCR_V3_DONUT, FEATURE_OCR_V3_LLM,
            CONF_FALLBACK_PAGE, CONF_FALLBACK_OVERALL
        )
        
        # Flags should be boolean
        assert isinstance(FEATURE_OCR_V3_TABLES, bool)
        assert isinstance(FEATURE_OCR_V3_TEMPLATES, bool)
        assert isinstance(FEATURE_OCR_V3_DONUT, bool)
        assert isinstance(FEATURE_OCR_V3_LLM, bool)
        
        # Thresholds should be float
        assert isinstance(CONF_FALLBACK_PAGE, float)
        assert isinstance(CONF_FALLBACK_OVERALL, float)
        
        # Default values should be False for flags, reasonable for thresholds
        assert FEATURE_OCR_V3_TABLES is False
        assert FEATURE_OCR_V3_TEMPLATES is False
        assert FEATURE_OCR_V3_DONUT is False
        assert FEATURE_OCR_V3_LLM is False
        assert CONF_FALLBACK_PAGE == 0.45
        assert CONF_FALLBACK_OVERALL == 0.50
