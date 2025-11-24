"""
Unit tests for normalization parsers.

Tests individual field parsers with diverse real-world examples,
edge cases, and error conditions.
"""

import pytest
from decimal import Decimal
from datetime import date

from backend.normalization.parsers import (
    DateParser, CurrencyParser, PriceParser, VATParser,
    SupplierParser, UnitParser, LineItemParser
)
from backend.normalization.types import FieldErrorType


class TestDateParser:
    """Test date parsing with various formats and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DateParser()
    
    def test_iso_date_format(self):
        """Test ISO date format (YYYY-MM-DD)."""
        result = self.parser.parse("2024-01-15")
        assert result.date == date(2024, 1, 15)
        assert result.confidence >= 0.9
        assert result.is_valid()
    
    def test_dd_mm_yyyy_format(self):
        """Test DD/MM/YYYY format."""
        result = self.parser.parse("15/01/2024")
        assert result.date == date(2024, 1, 15)
        assert result.confidence >= 0.8
        assert result.is_valid()
    
    def test_mm_dd_yyyy_format(self):
        """Test MM/DD/YYYY format."""
        result = self.parser.parse("01/15/2024")
        assert result.date == date(2024, 1, 15)
        assert result.confidence >= 0.8
        assert result.is_valid()
    
    def test_month_name_format(self):
        """Test month name format."""
        result = self.parser.parse("15 January 2024")
        assert result.date == date(2024, 1, 15)
        assert result.confidence >= 0.8
        assert result.is_valid()
    
    def test_two_digit_year(self):
        """Test two-digit year handling."""
        result = self.parser.parse("15/01/24")
        assert result.date == date(2024, 1, 15)
        assert result.is_valid()
    
    def test_ambiguous_date(self):
        """Test ambiguous date (01/02/2024 - could be Jan 2 or Feb 1)."""
        result = self.parser.parse("01/02/2024")
        # Should parse as DD/MM/YYYY (European format)
        assert result.date == date(2024, 2, 1)
        assert result.is_valid()
    
    def test_invalid_date(self):
        """Test invalid date format."""
        result = self.parser.parse("not a date")
        assert result.date is None
        assert not result.is_valid()
        assert len(result.errors) > 0
        assert result.errors[0].error_type == FieldErrorType.INVALID_FORMAT
    
    def test_empty_date(self):
        """Test empty date string."""
        result = self.parser.parse("")
        assert result.date is None
        assert not result.is_valid()
        assert result.errors[0].error_type == FieldErrorType.MISSING
    
    def test_context_confidence_adjustment(self):
        """Test confidence adjustment based on context."""
        context = {"region": "UK"}
        result = self.parser.parse("15/01/2024", context)
        assert result.confidence > 0.8  # Should be boosted for UK region
    
    def test_multiple_dates_in_text(self):
        """Test extracting date from text with multiple dates."""
        result = self.parser.parse("Invoice date: 15/01/2024, Due date: 30/01/2024")
        # Should find the first valid date
        assert result.date is not None
        assert result.is_valid()


class TestCurrencyParser:
    """Test currency parsing with various symbols and codes."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CurrencyParser()
    
    def test_currency_symbols(self):
        """Test currency symbol detection."""
        test_cases = [
            ("£", "GBP"),
            ("€", "EUR"),
            ("$", "USD"),
            ("¥", "JPY"),
        ]
        
        for symbol, expected_code in test_cases:
            result = self.parser.parse(symbol)
            assert result.currency_code == expected_code
            assert result.confidence >= 0.9
            assert result.is_valid()
    
    def test_iso_currency_codes(self):
        """Test ISO currency code detection."""
        test_cases = ["GBP", "EUR", "USD", "JPY", "INR"]
        
        for code in test_cases:
            result = self.parser.parse(code)
            assert result.currency_code == code
            assert result.confidence >= 0.9
            assert result.is_valid()
    
    def test_currency_names(self):
        """Test currency name detection."""
        test_cases = [
            ("Pound", "GBP"),
            ("Euro", "EUR"),
            ("Dollar", "USD"),
        ]
        
        for name, expected_code in test_cases:
            result = self.parser.parse(name)
            assert result.currency_code == expected_code
            assert result.is_valid()
    
    def test_ambiguous_currency(self):
        """Test ambiguous currency (Dollar could be USD, CAD, AUD, etc.)."""
        result = self.parser.parse("Dollar")
        assert result.currency_code == "USD"  # Default to USD
        assert result.is_valid()
    
    def test_invalid_currency(self):
        """Test invalid currency format."""
        result = self.parser.parse("XYZ")
        assert result.currency_code is None
        assert not result.is_valid()
        assert len(result.errors) > 0
    
    def test_empty_currency(self):
        """Test empty currency string."""
        result = self.parser.parse("")
        assert result.currency_code is None
        assert not result.is_valid()
        assert result.errors[0].error_type == FieldErrorType.MISSING
    
    def test_context_confidence_adjustment(self):
        """Test confidence adjustment based on context."""
        context = {"region": "UK"}
        result = self.parser.parse("£", context)
        assert result.confidence > 0.9  # Should be boosted for UK region


class TestPriceParser:
    """Test price parsing with various formats and currencies."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = PriceParser()
    
    def test_currency_symbol_amount(self):
        """Test currency symbol with amount."""
        test_cases = [
            ("£123.45", Decimal("123.45"), "GBP"),
            ("€99.99", Decimal("99.99"), "EUR"),
            ("$1,234.56", Decimal("1234.56"), "USD"),
        ]
        
        for price_str, expected_amount, expected_currency in test_cases:
            result = self.parser.parse(price_str)
            assert result.amount == expected_amount
            assert result.currency_code == expected_currency
            assert result.is_valid()
    
    def test_amount_currency_symbol(self):
        """Test amount with currency symbol."""
        result = self.parser.parse("123.45£")
        assert result.amount == Decimal("123.45")
        assert result.currency_code == "GBP"
        assert result.is_valid()
    
    def test_iso_code_amount(self):
        """Test ISO currency code with amount."""
        result = self.parser.parse("GBP 123.45")
        assert result.amount == Decimal("123.45")
        assert result.currency_code == "GBP"
        assert result.is_valid()
    
    def test_amount_iso_code(self):
        """Test amount with ISO currency code."""
        result = self.parser.parse("123.45 EUR")
        assert result.amount == Decimal("123.45")
        assert result.currency_code == "EUR"
        assert result.is_valid()
    
    def test_plain_amount(self):
        """Test plain amount without currency."""
        result = self.parser.parse("123.45")
        assert result.amount == Decimal("123.45")
        assert result.currency_code is None
        assert result.is_valid()
    
    def test_comma_separated_amount(self):
        """Test amount with comma separators."""
        result = self.parser.parse("1,234.56")
        assert result.amount == Decimal("1234.56")
        assert result.is_valid()
    
    def test_invalid_price(self):
        """Test invalid price format."""
        result = self.parser.parse("not a price")
        assert result.amount is None
        assert not result.is_valid()
        assert len(result.errors) > 0
    
    def test_empty_price(self):
        """Test empty price string."""
        result = self.parser.parse("")
        assert result.amount is None
        assert not result.is_valid()
        assert result.errors[0].error_type == FieldErrorType.MISSING
    
    def test_context_currency_inference(self):
        """Test currency inference from context."""
        context = {"default_currency": "GBP"}
        result = self.parser.parse("123.45", context)
        assert result.amount == Decimal("123.45")
        assert result.currency_code == "GBP"
        assert result.is_valid()


class TestVATParser:
    """Test VAT/tax parsing with various formats."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = VATParser()
    
    def test_vat_rate_percentage(self):
        """Test VAT rate as percentage."""
        result = self.parser.parse("VAT @ 20%")
        assert result.rate == Decimal("0.20")
        assert result.confidence >= 0.9
        assert result.is_valid()
    
    def test_tax_rate_percentage(self):
        """Test tax rate as percentage."""
        result = self.parser.parse("Tax @ 19%")
        assert result.rate == Decimal("0.19")
        assert result.is_valid()
    
    def test_vat_amount(self):
        """Test VAT amount."""
        result = self.parser.parse("VAT: £24.50")
        assert result.amount == Decimal("24.50")
        assert result.is_valid()
    
    def test_tax_amount(self):
        """Test tax amount."""
        result = self.parser.parse("Tax: €19.99")
        assert result.amount == Decimal("19.99")
        assert result.is_valid()
    
    def test_rate_without_symbol(self):
        """Test rate without @ symbol."""
        result = self.parser.parse("20% VAT")
        assert result.rate == Decimal("0.20")
        assert result.is_valid()
    
    def test_invalid_vat(self):
        """Test invalid VAT format."""
        result = self.parser.parse("not vat")
        assert result.rate is None
        assert result.amount is None
        assert not result.is_valid()
        assert len(result.errors) > 0
    
    def test_empty_vat(self):
        """Test empty VAT string."""
        result = self.parser.parse("")
        assert result.rate is None
        assert result.amount is None
        assert not result.is_valid()
        assert result.errors[0].error_type == FieldErrorType.MISSING
    
    def test_context_confidence_adjustment(self):
        """Test confidence adjustment for common tax rates."""
        result = self.parser.parse("20% VAT")
        assert result.confidence > 0.8  # Should be boosted for common rate


class TestSupplierParser:
    """Test supplier name parsing with normalization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SupplierParser()
    
    def test_supplier_prefix(self):
        """Test supplier with prefix."""
        result = self.parser.parse("Supplier: ABC Company Ltd")
        assert result.name == "ABC Company Ltd"
        assert result.confidence >= 0.9
        assert result.is_valid()
    
    def test_vendor_prefix(self):
        """Test vendor with prefix."""
        result = self.parser.parse("Vendor: XYZ Corporation")
        assert result.name == "XYZ Corporation"
        assert result.is_valid()
    
    def test_company_suffix_normalization(self):
        """Test company suffix normalization."""
        result = self.parser.parse("ABC Company Limited")
        assert result.name == "ABC Company Limited"
        assert result.is_valid()
    
    def test_trading_as_alias(self):
        """Test trading as alias extraction."""
        result = self.parser.parse("ABC Ltd trading as XYZ")
        assert result.name == "ABC Ltd"
        assert "XYZ" in result.aliases
        assert result.is_valid()
    
    def test_clean_supplier_name(self):
        """Test cleaning up supplier name."""
        result = self.parser.parse("Mr. John Smith Ltd")
        assert result.name == "John Smith Ltd"  # Should remove "Mr."
        assert result.is_valid()
    
    def test_invalid_supplier(self):
        """Test invalid supplier format."""
        result = self.parser.parse("")
        assert result.name is None
        assert not result.is_valid()
        assert result.errors[0].error_type == FieldErrorType.MISSING
    
    def test_context_confidence_adjustment(self):
        """Test confidence adjustment for known suppliers."""
        context = {"known_suppliers": ["ABC Company Ltd"]}
        result = self.parser.parse("ABC Company Ltd", context)
        assert result.confidence > 0.9  # Should be boosted for known supplier


class TestUnitParser:
    """Test unit of measure parsing with standardization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = UnitParser()
    
    def test_weight_units(self):
        """Test weight unit parsing."""
        test_cases = [
            ("kg", "kg"),
            ("kilogram", "kg"),
            ("kilograms", "kg"),
            ("g", "g"),
            ("gram", "g"),
            ("grams", "g"),
        ]
        
        for unit_str, expected_unit in test_cases:
            result = self.parser.parse(unit_str)
            assert result.unit == expected_unit
            assert result.is_valid()
    
    def test_volume_units(self):
        """Test volume unit parsing."""
        test_cases = [
            ("l", "l"),
            ("litre", "l"),
            ("litres", "l"),
            ("ml", "ml"),
            ("millilitre", "ml"),
        ]
        
        for unit_str, expected_unit in test_cases:
            result = self.parser.parse(unit_str)
            assert result.unit == expected_unit
            assert result.is_valid()
    
    def test_count_units(self):
        """Test count unit parsing."""
        test_cases = [
            ("pcs", "pcs"),
            ("pieces", "pcs"),
            ("piece", "pcs"),
            ("units", "pcs"),
            ("unit", "pcs"),
        ]
        
        for unit_str, expected_unit in test_cases:
            result = self.parser.parse(unit_str)
            assert result.unit == expected_unit
            assert result.is_valid()
    
    def test_time_units(self):
        """Test time unit parsing."""
        test_cases = [
            ("hr", "hr"),
            ("hour", "hr"),
            ("hours", "hr"),
            ("min", "min"),
            ("minute", "min"),
            ("minutes", "min"),
        ]
        
        for unit_str, expected_unit in test_cases:
            result = self.parser.parse(unit_str)
            assert result.unit == expected_unit
            assert result.is_valid()
    
    def test_invalid_unit(self):
        """Test invalid unit format."""
        result = self.parser.parse("xyz")
        assert result.unit is None
        assert not result.is_valid()
        assert len(result.errors) > 0
    
    def test_empty_unit(self):
        """Test empty unit string."""
        result = self.parser.parse("")
        assert result.unit is None
        assert not result.is_valid()
        assert result.errors[0].error_type == FieldErrorType.MISSING


class TestLineItemParser:
    """Test line item parsing with comprehensive field extraction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = LineItemParser()
    
    def test_complete_line_item(self):
        """Test parsing complete line item data."""
        raw_data = {
            "description": "Office Supplies",
            "quantity": "2",
            "unit": "pcs",
            "unit_price": "£15.50",
            "line_total": "£31.00",
            "vat_rate": "20%",
            "vat_amount": "£6.20"
        }
        
        result = self.parser.parse(raw_data)
        
        assert result.description == "Office Supplies"
        assert result.quantity == Decimal("2")
        assert result.unit == "pcs"
        assert result.unit_price == Decimal("15.50")
        assert result.line_total == Decimal("31.00")
        assert result.vat_rate == Decimal("0.20")
        assert result.vat_amount == Decimal("6.20")
        assert result.is_valid()
        assert result.confidence > 0.8
    
    def test_minimal_line_item(self):
        """Test parsing minimal line item data."""
        raw_data = {
            "description": "Consulting Services",
            "amount": "£500.00"
        }
        
        result = self.parser.parse(raw_data)
        
        assert result.description == "Consulting Services"
        assert result.line_total == Decimal("500.00")
        assert result.is_valid()
    
    def test_missing_fields(self):
        """Test parsing with missing fields."""
        raw_data = {
            "description": "Unknown Item"
        }
        
        result = self.parser.parse(raw_data)
        
        assert result.description == "Unknown Item"
        assert result.quantity is None
        assert result.unit_price is None
        assert result.line_total is None
        assert not result.is_valid()  # Should be invalid due to missing essential fields
    
    def test_numeric_quantity(self):
        """Test numeric quantity parsing."""
        raw_data = {
            "description": "Widgets",
            "qty": "10",
            "price": "£5.00"
        }
        
        result = self.parser.parse(raw_data)
        
        assert result.quantity == Decimal("10")
        assert result.unit_price == Decimal("5.00")
        assert result.is_valid()
    
    def test_confidence_calculation(self):
        """Test confidence calculation for line items."""
        # High confidence case
        high_conf_data = {
            "description": "Clear Item",
            "quantity": "5",
            "unit_price": "£10.00",
            "line_total": "£50.00"
        }
        
        high_result = self.parser.parse(high_conf_data)
        assert high_result.confidence > 0.8
        
        # Low confidence case
        low_conf_data = {
            "description": "Unclear"
        }
        
        low_result = self.parser.parse(low_conf_data)
        assert low_result.confidence < 0.5
    
    def test_context_usage(self):
        """Test using context for parsing."""
        context = {"default_currency": "GBP"}
        raw_data = {
            "description": "Item",
            "price": "15.50"  # No currency symbol
        }
        
        result = self.parser.parse(raw_data, context)
        assert result.unit_price == Decimal("15.50")
        assert result.is_valid()


if __name__ == "__main__":
    pytest.main([__file__])
