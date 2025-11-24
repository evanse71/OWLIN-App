"""
Real-world document tests for normalization module.

Tests with actual invoice and receipt examples from various regions,
formats, and industries to ensure robust parsing.
"""

import pytest
from decimal import Decimal
from datetime import date

from backend.normalization.field_normalizer import FieldNormalizer


class TestRealWorldDocuments:
    """Test normalization with real-world document examples."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = FieldNormalizer()
    
    def test_uk_restaurant_receipt(self):
        """Test UK restaurant receipt with VAT."""
        raw_data = {
            "supplier": "The Red Lion Restaurant",
            "invoice_number": "RCP-2024-001",
            "invoice_date": "15/01/2024",
            "currency": "GBP",
            "subtotal": "£45.00",
            "vat_rate": "20%",
            "vat_amount": "£9.00",
            "total": "£54.00",
            "line_items": [
                {
                    "description": "Fish & Chips",
                    "quantity": "2",
                    "unit_price": "£12.50",
                    "line_total": "£25.00"
                },
                {
                    "description": "Beer (Pint)",
                    "quantity": "4",
                    "unit_price": "£5.00",
                    "line_total": "£20.00"
                }
            ]
        }
        
        context = {"region": "UK", "industry": "restaurant"}
        result = self.normalizer.normalize_invoice(raw_data, context)
        
        assert result.is_successful()
        assert result.normalized_invoice.supplier_name == "The Red Lion Restaurant"
        assert result.normalized_invoice.total_amount == Decimal("54.00")
        assert result.normalized_invoice.tax_amount == Decimal("9.00")
        assert len(result.normalized_invoice.line_items) == 2
        assert result.normalized_invoice.line_items[0].description == "Fish & Chips"
        assert result.normalized_invoice.line_items[0].quantity == Decimal("2")
    
    def test_us_consulting_invoice(self):
        """Test US consulting invoice with hourly rates."""
        raw_data = {
            "supplier": "Tech Solutions Inc",
            "invoice_number": "TS-2024-001",
            "invoice_date": "01/15/2024",
            "currency": "USD",
            "subtotal": "$2,000.00",
            "tax_rate": "8.5%",
            "tax_amount": "$170.00",
            "total": "$2,170.00",
            "line_items": [
                {
                    "description": "Software Development",
                    "quantity": "20",
                    "unit": "hours",
                    "unit_price": "$100.00",
                    "line_total": "$2,000.00"
                }
            ]
        }
        
        context = {"region": "US", "industry": "consulting"}
        result = self.normalizer.normalize_invoice(raw_data, context)
        
        assert result.is_successful()
        assert result.normalized_invoice.supplier_name == "Tech Solutions Inc"
        assert result.normalized_invoice.total_amount == Decimal("2170.00")
        assert result.normalized_invoice.line_items[0].unit == "hr"
        assert result.normalized_invoice.line_items[0].quantity == Decimal("20")
    
    def test_eu_retail_invoice(self):
        """Test EU retail invoice with multiple currencies."""
        raw_data = {
            "supplier": "Euro Retail GmbH",
            "invoice_number": "ER-2024-001",
            "invoice_date": "15.01.2024",
            "currency": "EUR",
            "subtotal": "€150.00",
            "vat_rate": "19%",
            "vat_amount": "€28.50",
            "total": "€178.50",
            "line_items": [
                {
                    "description": "Electronics",
                    "quantity": "1",
                    "unit_price": "€100.00",
                    "line_total": "€100.00"
                },
                {
                    "description": "Accessories",
                    "quantity": "2",
                    "unit_price": "€25.00",
                    "line_total": "€50.00"
                }
            ]
        }
        
        context = {"region": "EU", "industry": "retail"}
        result = self.normalizer.normalize_invoice(raw_data, context)
        
        assert result.is_successful()
        assert result.normalized_invoice.currency == "EUR"
        assert result.normalized_invoice.total_amount == Decimal("178.50")
        assert result.normalized_invoice.tax_amount == Decimal("28.50")
    
    def test_construction_invoice(self):
        """Test construction invoice with materials and labor."""
        raw_data = {
            "supplier": "BuildCorp Construction Ltd",
            "invoice_number": "BC-2024-001",
            "invoice_date": "15/01/2024",
            "currency": "GBP",
            "subtotal": "£5,000.00",
            "vat_rate": "20%",
            "vat_amount": "£1,000.00",
            "total": "£6,000.00",
            "line_items": [
                {
                    "description": "Concrete (10 cubic meters)",
                    "quantity": "10",
                    "unit": "m3",
                    "unit_price": "£200.00",
                    "line_total": "£2,000.00"
                },
                {
                    "description": "Labor (40 hours)",
                    "quantity": "40",
                    "unit": "hr",
                    "unit_price": "£75.00",
                    "line_total": "£3,000.00"
                }
            ]
        }
        
        context = {"region": "UK", "industry": "construction"}
        result = self.normalizer.normalize_invoice(raw_data, context)
        
        assert result.is_successful()
        assert result.normalized_invoice.supplier_name == "BuildCorp Construction Ltd"
        assert result.normalized_invoice.total_amount == Decimal("6000.00")
        assert len(result.normalized_invoice.line_items) == 2
        assert result.normalized_invoice.line_items[0].unit == "m3"
        assert result.normalized_invoice.line_items[1].unit == "hr"
    
    def test_medical_invoice(self):
        """Test medical invoice with services and supplies."""
        raw_data = {
            "supplier": "MedCare Services Ltd",
            "invoice_number": "MED-2024-001",
            "invoice_date": "15/01/2024",
            "currency": "GBP",
            "subtotal": "£300.00",
            "vat_rate": "0%",  # Medical services often VAT exempt
            "vat_amount": "£0.00",
            "total": "£300.00",
            "line_items": [
                {
                    "description": "Consultation",
                    "quantity": "1",
                    "unit_price": "£150.00",
                    "line_total": "£150.00"
                },
                {
                    "description": "Medical Supplies",
                    "quantity": "5",
                    "unit_price": "£30.00",
                    "line_total": "£150.00"
                }
            ]
        }
        
        context = {"region": "UK", "industry": "medical"}
        result = self.normalizer.normalize_invoice(raw_data, context)
        
        assert result.is_successful()
        assert result.normalized_invoice.supplier_name == "MedCare Services Ltd"
        assert result.normalized_invoice.total_amount == Decimal("300.00")
        assert result.normalized_invoice.tax_amount == Decimal("0.00")
    
    def test_ambiguous_date_formats(self):
        """Test handling of ambiguous date formats."""
        # US format (MM/DD/YYYY)
        us_data = {
            "supplier": "US Company Inc",
            "date": "01/15/2024",  # January 15, 2024
            "total": "$100.00"
        }
        
        us_context = {"region": "US"}
        us_result = self.normalizer.normalize_invoice(us_data, us_context)
        assert us_result.normalized_invoice.invoice_date == date(2024, 1, 15)
        
        # UK format (DD/MM/YYYY)
        uk_data = {
            "supplier": "UK Company Ltd",
            "date": "15/01/2024",  # 15 January 2024
            "total": "£100.00"
        }
        
        uk_context = {"region": "UK"}
        uk_result = self.normalizer.normalize_invoice(uk_data, uk_context)
        assert uk_result.normalized_invoice.invoice_date == date(2024, 1, 15)
    
    def test_multiple_currencies_in_document(self):
        """Test document with multiple currency references."""
        raw_data = {
            "supplier": "MultiCorp Ltd",
            "invoice_number": "MC-2024-001",
            "date": "15/01/2024",
            "currency": "GBP",
            "subtotal": "£100.00",
            "total": "£120.00",
            "notes": "Payment in USD: $150.00, EUR: €110.00"
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        # Should use the primary currency (GBP)
        assert result.normalized_invoice.currency == "GBP"
        assert result.normalized_invoice.total_amount == Decimal("120.00")
    
    def test_ocr_errors_and_corrections(self):
        """Test handling of OCR errors and corrections."""
        # Simulate OCR errors
        raw_data = {
            "supplier": "ABC C0mpany Ltd",  # OCR error: 0 instead of o
            "invoice_number": "INV-2O24-001",  # OCR error: O instead of 0
            "date": "15/01/2O24",  # OCR error: O instead of 0
            "currency": "GBP",
            "total": "£1OO.OO"  # OCR error: O instead of 0
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        # Should still extract some information
        assert result.normalized_invoice.supplier_name is not None
        assert result.normalized_invoice.currency == "GBP"
        # Note: The amount might not parse correctly due to OCR errors
    
    def test_partial_invoice_data(self):
        """Test normalization with partial invoice data."""
        raw_data = {
            "text": "Invoice from XYZ Ltd for £250.00 dated 15/01/2024",
            "blocks": [
                {
                    "type": "text",
                    "text": "Office Supplies £100.00"
                },
                {
                    "type": "text", 
                    "text": "Consulting £150.00"
                }
            ]
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        # Should extract information from text
        assert result.normalized_invoice.supplier_name is not None
        assert result.normalized_invoice.total_amount == Decimal("250.00")
        assert result.normalized_invoice.currency == "GBP"
        assert result.normalized_invoice.invoice_date == date(2024, 1, 15)
    
    def test_high_volume_line_items(self):
        """Test invoice with many line items."""
        line_items = []
        for i in range(20):  # 20 line items
            line_items.append({
                "description": f"Item {i+1}",
                "quantity": "1",
                "unit_price": "£10.00",
                "line_total": "£10.00"
            })
        
        raw_data = {
            "supplier": "Bulk Supplier Ltd",
            "invoice_number": "BULK-2024-001",
            "date": "15/01/2024",
            "currency": "GBP",
            "subtotal": "£200.00",
            "total": "£240.00",
            "line_items": line_items
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        assert result.is_successful()
        assert len(result.normalized_invoice.line_items) == 20
        assert result.normalized_invoice.total_amount == Decimal("240.00")
    
    def test_credit_note_normalization(self):
        """Test credit note normalization."""
        raw_data = {
            "supplier": "ABC Company Ltd",
            "document_type": "Credit Note",
            "credit_note_number": "CN-2024-001",
            "date": "15/01/2024",
            "currency": "GBP",
            "total": "-£100.00",  # Negative amount for credit
            "line_items": [
                {
                    "description": "Returned Goods",
                    "quantity": "1",
                    "unit_price": "-£100.00",
                    "line_total": "-£100.00"
                }
            ]
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        # Should handle negative amounts
        assert result.normalized_invoice.total_amount == Decimal("-100.00")
        assert result.normalized_invoice.line_items[0].line_total == Decimal("-100.00")
    
    def test_international_invoice(self):
        """Test international invoice with different formats."""
        raw_data = {
            "supplier": "Global Corp S.A.",
            "invoice_number": "GC-2024-001",
            "date": "15 janvier 2024",  # French date format
            "currency": "EUR",
            "total": "€500,00",  # European number format
            "line_items": [
                {
                    "description": "Services internationaux",
                    "quantity": "1",
                    "unit_price": "€500,00",
                    "line_total": "€500,00"
                }
            ]
        }
        
        result = self.normalizer.normalize_invoice(raw_data)
        
        assert result.normalized_invoice.supplier_name == "Global Corp S.A."
        assert result.normalized_invoice.currency == "EUR"
        assert result.normalized_invoice.total_amount == Decimal("500.00")


if __name__ == "__main__":
    pytest.main([__file__])
