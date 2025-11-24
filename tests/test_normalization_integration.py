"""
Integration tests for the normalization module.

Tests complete invoice normalization with real-world document examples,
end-to-end processing, and error handling.
"""

import pytest
from decimal import Decimal
from datetime import date

from backend.normalization.field_normalizer import FieldNormalizer
from backend.normalization.types import NormalizationResult


class TestInvoiceNormalization:
    """Test complete invoice normalization with real-world examples."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = FieldNormalizer()
    
    def test_uk_invoice_normalization(self):
        """Test normalization of UK invoice with GBP currency."""
        raw_data = {
            "supplier": "ABC Company Ltd",
            "invoice_number": "INV-2024-001",
            "invoice_date": "15/01/2024",
            "currency": "GBP",
            "subtotal": "£100.00",
            "vat_amount": "£20.00",
            "total": "£120.00",
            "line_items": [
                {
                    "description": "Office Supplies",
                    "quantity": "2",
                    "unit_price": "£25.00",
                    "line_total": "£50.00"
                },
                {
                    "description": "Consulting Services",
                    "quantity": "5",
                    "unit_price": "£10.00",
                    "line_total": "£50.00"
                }
            ]
        }
        
        context = {"region": "UK", "default_currency": "GBP"}
        result = self.normalizer.normalize_invoice(raw_data, context)
        
        assert isinstance(result, NormalizationResult)
        assert result.is_successful()
        assert result.normalized_invoice.supplier_name == "ABC Company Ltd"
        assert result.normalized_invoice.invoice_number == "INV-2024-001"
        assert result.normalized_invoice.invoice_date == date(2024, 1, 15)
        assert result.normalized_invoice.currency == "GBP"
        assert result.normalized_invoice.subtotal == Decimal("100.00")
        assert result.normalized_invoice.tax_amount == Decimal("20.00")
        assert result.normalized_invoice.total_amount == Decimal("120.00")
        assert len(result.normalized_invoice.line_items) == 2
        assert result.normalized_invoice.overall_confidence > 0.8
    
    def test_eu_invoice_normalization(self):
        """Test normalization of EU invoice with EUR currency."""
        raw_data = {
            "vendor": "XYZ GmbH",
            "invoice_no": "2024-001",
            "date": "15.01.2024",
            "curr": "EUR",
            "net_total": "€200.00",
            "vat": "€42.00",
            "grand_total": "€242.00",
            "line_items": [
                {
                    "item": "Software License",
                    "qty": "1",
                    "rate": "€200.00",
                    "total": "€200.00"
                }
            ]
        }
        
        context = {"region": "EU", "default_currency": "EUR"}
        result = self.normalizer.normalize_invoice(raw_data, context)
        
        assert result.is_successful()
        assert result.normalized_invoice.supplier_name == "XYZ GmbH"
        assert result.normalized_invoice.currency == "EUR"
        assert result.normalized_invoice.total_amount == Decimal("242.00")
        assert len(result.normalized_invoice.line_items) == 1
    
    def test_us_invoice_normalization(self):
        """Test normalization of US invoice with USD currency."""
        raw_data = {
            "company": "American Corp Inc",
            "reference": "US-2024-001",
            "issue_date": "01/15/2024",
            "currency_code": "USD",
            "sub_total": "$500.00",
            "tax": "$50.00",
            "amount_due": "$550.00",
            "line_items": [
                {
                    "description": "Professional Services",
                    "quantity": "10",
                    "unit_price": "$50.00",
                    "line_total": "$500.00"
                }
            ]
        }
        
        context = {"region": "US", "default_currency": "USD"}
        result = self.normalizer.normalize_invoice(raw_data, context)
        
        assert result.is_successful()
        assert result.normalized_invoice.supplier_name == "American Corp Inc"
        assert result.normalized_invoice.currency == "USD"
        assert result.normalized_invoice.total_amount == Decimal("550.00")
    
    def test_minimal_invoice_normalization(self):
        """Test normalization with minimal data."""
        raw_data = {
            "text": "Invoice from ABC Ltd for £100.00 dated 15/01/2024"
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        # Should still extract some information
        assert result.normalized_invoice.supplier_name is not None
        assert result.normalized_invoice.total_amount == Decimal("100.00")
        assert result.normalized_invoice.currency == "GBP"
        assert result.normalized_invoice.invoice_date == date(2024, 1, 15)
    
    def test_table_extraction_integration(self):
        """Test integration with table extraction results."""
        raw_data = {
            "supplier": "Table Corp Ltd",
            "invoice_number": "TBL-001",
            "date": "15/01/2024",
            "currency": "GBP",
            "total": "£150.00",
            "table_data": [
                {
                    "description": "Item 1",
                    "quantity": "2",
                    "unit_price": "£25.00",
                    "total": "£50.00"
                },
                {
                    "description": "Item 2",
                    "quantity": "1",
                    "unit_price": "£100.00",
                    "total": "£100.00"
                }
            ]
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        assert result.is_successful()
        assert len(result.normalized_invoice.line_items) == 2
        assert result.normalized_invoice.line_items[0].description == "Item 1"
        assert result.normalized_invoice.line_items[0].quantity == Decimal("2")
        assert result.normalized_invoice.line_items[0].unit_price == Decimal("25.00")
    
    def test_blocks_integration(self):
        """Test integration with OCR blocks."""
        raw_data = {
            "blocks": [
                {
                    "type": "header",
                    "text": "ABC Company Ltd Invoice INV-001"
                },
                {
                    "type": "table",
                    "table_data": [
                        {
                            "description": "Services",
                            "amount": "£100.00"
                        }
                    ]
                }
            ]
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        # Should extract from blocks
        assert result.normalized_invoice.supplier_name is not None
        assert len(result.normalized_invoice.line_items) >= 1
    
    def test_error_handling(self):
        """Test error handling with invalid data."""
        raw_data = {
            "supplier": "",  # Empty supplier
            "invoice_date": "invalid date",
            "currency": "XYZ",  # Invalid currency
            "total": "not a number"
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        # Should handle errors gracefully
        assert not result.is_successful()
        assert len(result.normalized_invoice.errors) > 0
        assert result.fallback_used
    
    def test_confidence_calculation(self):
        """Test confidence calculation across different scenarios."""
        # High confidence case
        high_conf_data = {
            "supplier": "Clear Company Ltd",
            "invoice_number": "INV-001",
            "invoice_date": "15/01/2024",
            "currency": "GBP",
            "total": "£100.00"
        }
        
        high_result = self.normalizer.normalize_invoice(high_conf_data)
        assert high_result.normalized_invoice.overall_confidence > 0.8
        
        # Low confidence case
        low_conf_data = {
            "text": "unclear invoice data"
        }
        
        low_result = self.normalizer.normalize_invoice(low_conf_data)
        assert low_result.normalized_invoice.overall_confidence < 0.5
    
    def test_context_usage(self):
        """Test using context for better parsing."""
        raw_data = {
            "supplier": "Local Company",
            "total": "100.00"  # No currency symbol
        }
        
        context = {
            "region": "UK",
            "default_currency": "GBP",
            "known_suppliers": ["Local Company"]
        }
        
        result = self.normalizer.normalize_invoice(raw_data, context)
        
        assert result.normalized_invoice.currency == "GBP"
        assert result.normalized_invoice.total_amount == Decimal("100.00")
        assert result.normalized_invoice.supplier_name == "Local Company"
    
    def test_processing_time(self):
        """Test processing time measurement."""
        raw_data = {
            "supplier": "Test Company Ltd",
            "invoice_number": "TEST-001",
            "date": "15/01/2024",
            "currency": "GBP",
            "total": "£100.00"
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        assert result.processing_time > 0
        assert result.processing_time < 1.0  # Should be fast
    
    def test_warnings_generation(self):
        """Test warning generation for low confidence."""
        raw_data = {
            "text": "unclear invoice with low confidence data"
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        assert result.fallback_used
        assert len(result.warnings) > 0
        assert "Low confidence" in result.warnings[0] or "fallback" in result.warnings[0]
    
    def test_json_serialization(self):
        """Test JSON serialization of results."""
        raw_data = {
            "supplier": "JSON Test Ltd",
            "invoice_number": "JSON-001",
            "date": "15/01/2024",
            "currency": "GBP",
            "total": "£100.00"
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        # Test to_dict method
        invoice_dict = result.normalized_invoice.to_dict()
        assert isinstance(invoice_dict, dict)
        assert "supplier_name" in invoice_dict
        assert "invoice_number" in invoice_dict
        assert "invoice_date" in invoice_dict
        assert "currency" in invoice_dict
        assert "total_amount" in invoice_dict
        
        # Test summary method
        summary = result.get_summary()
        assert isinstance(summary, dict)
        assert "success" in summary
        assert "confidence" in summary
        assert "fields_parsed" in summary
        assert "processing_time" in summary


class TestSingleFieldNormalization:
    """Test single field normalization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = FieldNormalizer()
    
    def test_date_field_normalization(self):
        """Test single date field normalization."""
        result = self.normalizer.normalize_single_field("date", "15/01/2024")
        assert result.date == date(2024, 1, 15)
        assert result.is_valid()
    
    def test_currency_field_normalization(self):
        """Test single currency field normalization."""
        result = self.normalizer.normalize_single_field("currency", "£")
        assert result.currency_code == "GBP"
        assert result.is_valid()
    
    def test_price_field_normalization(self):
        """Test single price field normalization."""
        result = self.normalizer.normalize_single_field("price", "£123.45")
        assert result.amount == Decimal("123.45")
        assert result.currency_code == "GBP"
        assert result.is_valid()
    
    def test_vat_field_normalization(self):
        """Test single VAT field normalization."""
        result = self.normalizer.normalize_single_field("vat", "20%")
        assert result.rate == Decimal("0.20")
        assert result.is_valid()
    
    def test_supplier_field_normalization(self):
        """Test single supplier field normalization."""
        result = self.normalizer.normalize_single_field("supplier", "ABC Company Ltd")
        assert result.name == "ABC Company Ltd"
        assert result.is_valid()
    
    def test_unit_field_normalization(self):
        """Test single unit field normalization."""
        result = self.normalizer.normalize_single_field("unit", "kg")
        assert result.unit == "kg"
        assert result.is_valid()
    
    def test_unknown_field_normalization(self):
        """Test unknown field normalization."""
        result = self.normalizer.normalize_single_field("unknown_field", "value")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__])
