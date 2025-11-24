"""
Individual field parsers for normalization.

Each parser handles a specific field type with comprehensive error handling,
fallback mechanisms, and confidence scoring.
"""

from __future__ import annotations
import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, Union

from .types import (
    FieldError, FieldErrorType, ParsedDate, ParsedCurrency, ParsedPrice,
    ParsedVAT, ParsedSupplier, ParsedUnit, NormalizedLineItem
)

LOGGER = logging.getLogger("owlin.normalization.parsers")


class DateParser:
    """Parser for date fields with comprehensive format detection."""
    
    # Common date patterns with confidence scores
    DATE_PATTERNS = [
        # ISO format (highest confidence)
        (r'\b(\d{4})-(\d{2})-(\d{2})\b', 0.95, '%Y-%m-%d'),
        # DD/MM/YYYY or MM/DD/YYYY
        (r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b', 0.85, None),
        # DD/MM/YY or MM/DD/YY
        (r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2})\b', 0.80, None),
        # DD Month YYYY
        (r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b', 0.90, None),
        # Month DD, YYYY
        (r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})\b', 0.90, None),
        # DD.MM.YYYY
        (r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b', 0.85, None),
    ]
    
    MONTH_NAMES = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    def parse(self, raw_value: str, context: Optional[Dict[str, Any]] = None) -> ParsedDate:
        """
        Parse a date string with comprehensive format detection.
        
        Args:
            raw_value: Raw date string from OCR
            context: Additional context (e.g., document language, region)
        
        Returns:
            ParsedDate with normalized date and metadata
        """
        if not raw_value or not raw_value.strip():
            return ParsedDate(
                date=None,
                raw_value=raw_value,
                confidence=0.0,
                format_detected=None,
                errors=[FieldError(
                    field_name="date",
                    error_type=FieldErrorType.MISSING,
                    raw_value=raw_value,
                    message="Empty date value"
                )]
            )
        
        raw_value = raw_value.strip()
        errors = []
        best_date = None
        best_confidence = 0.0
        best_format = None
        
        # Try each pattern
        for pattern, base_confidence, format_str in self.DATE_PATTERNS:
            matches = re.finditer(pattern, raw_value, re.IGNORECASE)
            for match in matches:
                try:
                    parsed_date = self._parse_match(match, format_str)
                    if parsed_date:
                        # Adjust confidence based on context
                        confidence = self._adjust_confidence(base_confidence, context)
                        if confidence > best_confidence:
                            best_date = parsed_date
                            best_confidence = confidence
                            best_format = format_str or pattern
                except Exception as e:
                    errors.append(FieldError(
                        field_name="date",
                        error_type=FieldErrorType.PARSE_ERROR,
                        raw_value=raw_value,
                        message=f"Failed to parse date with pattern {pattern}: {e}"
                    ))
        
        if best_date is None:
            errors.append(FieldError(
                field_name="date",
                error_type=FieldErrorType.INVALID_FORMAT,
                raw_value=raw_value,
                message="No valid date format detected"
            ))
        
        return ParsedDate(
            date=best_date,
            raw_value=raw_value,
            confidence=best_confidence,
            format_detected=best_format,
            errors=errors
        )
    
    def _parse_match(self, match, format_str: Optional[str]) -> Optional[date]:
        """Parse a regex match into a date object."""
        groups = match.groups()
        
        if format_str:
            # Direct format string
            date_str = match.group(0)
            return datetime.strptime(date_str, format_str).date()
        
        # Handle different group patterns
        if len(groups) == 3:
            if any(month in groups for month in self.MONTH_NAMES.keys()):
                # Month name format
                return self._parse_month_name_format(groups)
            else:
                # Numeric format - try both DD/MM/YYYY and MM/DD/YYYY
                return self._parse_numeric_format(groups)
        
        return None
    
    def _parse_month_name_format(self, groups: Tuple[str, ...]) -> Optional[date]:
        """Parse month name format (DD Month YYYY or Month DD, YYYY)."""
        try:
            if len(groups) == 3:
                # Try DD Month YYYY
                if groups[0].isdigit() and groups[1].lower() in self.MONTH_NAMES:
                    day = int(groups[0])
                    month = self.MONTH_NAMES[groups[1].lower()]
                    year = int(groups[2])
                    return date(year, month, day)
                # Try Month DD, YYYY
                elif groups[0].lower() in self.MONTH_NAMES and groups[1].isdigit():
                    month = self.MONTH_NAMES[groups[0].lower()]
                    day = int(groups[1])
                    year = int(groups[2])
                    return date(year, month, day)
        except (ValueError, KeyError):
            pass
        return None
    
    def _parse_numeric_format(self, groups: Tuple[str, ...]) -> Optional[date]:
        """Parse numeric format trying both DD/MM/YYYY and MM/DD/YYYY."""
        try:
            if len(groups) == 3:
                part1, part2, part3 = groups
                
                # Handle 2-digit years
                if len(part3) == 2:
                    year = 2000 + int(part3) if int(part3) < 50 else 1900 + int(part3)
                else:
                    year = int(part3)
                
                # Try DD/MM/YYYY first (more common in Europe)
                try:
                    day, month = int(part1), int(part2)
                    if 1 <= day <= 31 and 1 <= month <= 12:
                        return date(year, month, day)
                except ValueError:
                    pass
                
                # Try MM/DD/YYYY (US format)
                try:
                    month, day = int(part1), int(part2)
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        return date(year, month, day)
                except ValueError:
                    pass
        except (ValueError, TypeError):
            pass
        return None
    
    def _adjust_confidence(self, base_confidence: float, context: Optional[Dict[str, Any]]) -> float:
        """Adjust confidence based on context."""
        if not context:
            return base_confidence
        
        # Adjust based on document language/region
        region = context.get('region', '').lower()
        if region in ['uk', 'gb', 'europe']:
            # Higher confidence for DD/MM/YYYY patterns
            return base_confidence * 1.1
        elif region in ['us', 'usa']:
            # Higher confidence for MM/DD/YYYY patterns
            return base_confidence * 1.1
        
        return base_confidence


class CurrencyParser:
    """Parser for currency fields with symbol and code detection."""
    
    CURRENCY_MAP = {
        # Symbols to ISO codes
        '£': 'GBP',
        '€': 'EUR', 
        '$': 'USD',
        '¥': 'JPY',
        '₹': 'INR',
        '₽': 'RUB',
        '₩': 'KRW',
        '₪': 'ILS',
        '₨': 'PKR',
        '₦': 'NGN',
        '₡': 'CRC',
        '₱': 'PHP',
        '₫': 'VND',
        '₴': 'UAH',
        '₸': 'KZT',
        '₼': 'AZN',
        '₾': 'GEL',
        '₿': 'BTC',
    }
    
    CURRENCY_PATTERNS = [
        (r'[£€$¥₹₽₩₪₨₦₡₱₫₴₸₼₾₿]', 0.95),  # Currency symbols
        (r'\b(GBP|EUR|USD|JPY|INR|RUB|KRW|ILS|PKR|NGN|CRC|PHP|VND|UAH|KZT|AZN|GEL|BTC)\b', 0.90),  # ISO codes
        (r'\b(Pound|Pounds|Sterling)\b', 0.85),  # GBP
        (r'\b(Euro|Euros)\b', 0.85),  # EUR
        (r'\b(Dollar|Dollars)\b', 0.80),  # USD (ambiguous)
        (r'\b(Yen|Yuan)\b', 0.80),  # JPY/CNY (ambiguous)
    ]
    
    def parse(self, raw_value: str, context: Optional[Dict[str, Any]] = None) -> ParsedCurrency:
        """
        Parse a currency string with symbol and code detection.
        
        Args:
            raw_value: Raw currency string from OCR
            context: Additional context (e.g., document region, language)
        
        Returns:
            ParsedCurrency with normalized currency and metadata
        """
        if not raw_value or not raw_value.strip():
            return ParsedCurrency(
                currency_code=None,
                symbol=None,
                raw_value=raw_value,
                confidence=0.0,
                errors=[FieldError(
                    field_name="currency",
                    error_type=FieldErrorType.MISSING,
                    raw_value=raw_value,
                    message="Empty currency value"
                )]
            )
        
        raw_value = raw_value.strip()
        errors = []
        best_code = None
        best_symbol = None
        best_confidence = 0.0
        
        # Try symbol detection first (highest confidence)
        for symbol, code in self.CURRENCY_MAP.items():
            if symbol in raw_value:
                confidence = 0.95
                if confidence > best_confidence:
                    best_code = code
                    best_symbol = symbol
                    best_confidence = confidence
                break
        
        # Try pattern matching
        for pattern, base_confidence in self.CURRENCY_PATTERNS:
            matches = re.finditer(pattern, raw_value, re.IGNORECASE)
            for match in matches:
                matched_text = match.group(0).upper()
                confidence = self._adjust_confidence(base_confidence, context)
                
                # Map matched text to currency code
                code = self._map_text_to_code(matched_text)
                if code and confidence > best_confidence:
                    best_code = code
                    best_symbol = matched_text
                    best_confidence = confidence
        
        if best_code is None:
            errors.append(FieldError(
                field_name="currency",
                error_type=FieldErrorType.INVALID_FORMAT,
                raw_value=raw_value,
                message="No valid currency format detected"
            ))
        
        return ParsedCurrency(
            currency_code=best_code,
            symbol=best_symbol,
            raw_value=raw_value,
            confidence=best_confidence,
            errors=errors
        )
    
    def _map_text_to_code(self, text: str) -> Optional[str]:
        """Map text to currency code."""
        text_upper = text.upper()
        
        # Direct ISO code mapping
        if text_upper in ['GBP', 'EUR', 'USD', 'JPY', 'INR', 'RUB', 'KRW', 'ILS', 'PKR', 'NGN', 'CRC', 'PHP', 'VND', 'UAH', 'KZT', 'AZN', 'GEL', 'BTC']:
            return text_upper
        
        # Text to code mapping
        text_mapping = {
            'POUND': 'GBP', 'POUNDS': 'GBP', 'STERLING': 'GBP',
            'EURO': 'EUR', 'EUROS': 'EUR',
            'DOLLAR': 'USD', 'DOLLARS': 'USD',  # Default to USD, could be ambiguous
            'YEN': 'JPY', 'YUAN': 'CNY'
        }
        
        return text_mapping.get(text_upper)
    
    def _adjust_confidence(self, base_confidence: float, context: Optional[Dict[str, Any]]) -> float:
        """Adjust confidence based on context."""
        if not context:
            return base_confidence
        
        # Adjust based on document region
        region = context.get('region', '').lower()
        if region in ['uk', 'gb'] and base_confidence > 0.8:
            return base_confidence * 1.1  # Higher confidence for GBP in UK
        elif region in ['eu', 'europe'] and base_confidence > 0.8:
            return base_confidence * 1.1  # Higher confidence for EUR in Europe
        elif region in ['us', 'usa'] and base_confidence > 0.8:
            return base_confidence * 1.1  # Higher confidence for USD in US
        
        return base_confidence


class PriceParser:
    """Parser for price fields with currency and amount extraction."""
    
    PRICE_PATTERNS = [
        # Currency symbol + amount
        (r'[£€$¥₹₽₩₪₨₦₡₱₫₴₸₼₾₿]([\d,]+\.?\d*)', 0.95),
        # Amount + currency symbol
        (r'([\d,]+\.?\d*)[£€$¥₹₽₩₪₨₦₡₱₫₴₸₼₾₿]', 0.95),
        # ISO currency code + amount
        (r'\b(GBP|EUR|USD|JPY|INR|RUB|KRW|ILS|PKR|NGN|CRC|PHP|VND|UAH|KZT|AZN|GEL|BTC)\s*([\d,]+\.?\d*)', 0.90),
        # Amount + ISO currency code
        (r'([\d,]+\.?\d*)\s*(GBP|EUR|USD|JPY|INR|RUB|KRW|ILS|PKR|NGN|CRC|PHP|VND|UAH|KZT|AZN|GEL|BTC)', 0.90),
        # Plain amount (no currency)
        (r'\b([\d,]+\.?\d*)\b', 0.70),
    ]
    
    def parse(self, raw_value: str, context: Optional[Dict[str, Any]] = None) -> ParsedPrice:
        """
        Parse a price string with amount and currency extraction.
        
        Args:
            raw_value: Raw price string from OCR
            context: Additional context (e.g., document currency, region)
        
        Returns:
            ParsedPrice with normalized amount and currency
        """
        if not raw_value or not raw_value.strip():
            return ParsedPrice(
                amount=None,
                currency_code=None,
                raw_value=raw_value,
                confidence=0.0,
                errors=[FieldError(
                    field_name="price",
                    error_type=FieldErrorType.MISSING,
                    raw_value=raw_value,
                    message="Empty price value"
                )]
            )
        
        raw_value = raw_value.strip()
        errors = []
        best_amount = None
        best_currency = None
        best_confidence = 0.0
        
        # Try each pattern
        for pattern, base_confidence in self.PRICE_PATTERNS:
            matches = re.finditer(pattern, raw_value, re.IGNORECASE)
            for match in matches:
                try:
                    amount, currency = self._parse_match(match, pattern)
                    if amount is not None:
                        confidence = self._adjust_confidence(base_confidence, context, currency)
                        if confidence > best_confidence:
                            best_amount = amount
                            best_currency = currency
                            best_confidence = confidence
                except Exception as e:
                    errors.append(FieldError(
                        field_name="price",
                        error_type=FieldErrorType.PARSE_ERROR,
                        raw_value=raw_value,
                        message=f"Failed to parse price with pattern {pattern}: {e}"
                    ))
        
        # If no currency detected, try to infer from context
        if best_currency is None and context:
            best_currency = context.get('default_currency')
            if best_currency:
                best_confidence *= 0.8  # Reduce confidence for inferred currency
        
        if best_amount is None:
            errors.append(FieldError(
                field_name="price",
                error_type=FieldErrorType.INVALID_FORMAT,
                raw_value=raw_value,
                message="No valid price format detected"
            ))
        
        return ParsedPrice(
            amount=best_amount,
            currency_code=best_currency,
            raw_value=raw_value,
            confidence=best_confidence,
            errors=errors
        )
    
    def _parse_match(self, match, pattern: str) -> Tuple[Optional[Decimal], Optional[str]]:
        """Parse a regex match into amount and currency."""
        groups = match.groups()
        
        # Extract amount (always the numeric part)
        amount_str = None
        currency_str = None
        
        if len(groups) == 1:
            # Single group - could be amount or currency
            if groups[0].replace(',', '').replace('.', '').isdigit():
                amount_str = groups[0]
            else:
                currency_str = groups[0]
        elif len(groups) == 2:
            # Two groups - amount and currency
            if groups[0].replace(',', '').replace('.', '').isdigit():
                amount_str, currency_str = groups[0], groups[1]
            else:
                amount_str, currency_str = groups[1], groups[0]
        
        # Parse amount
        amount = None
        if amount_str:
            try:
                # Remove commas and convert to Decimal
                clean_amount = amount_str.replace(',', '')
                amount = Decimal(clean_amount)
            except (ValueError, InvalidOperation):
                pass
        
        # Parse currency
        currency = None
        if currency_str:
            currency = self._normalize_currency(currency_str)
        
        return amount, currency
    
    def _normalize_currency(self, currency_str: str) -> Optional[str]:
        """Normalize currency string to ISO code."""
        currency_str = currency_str.strip().upper()
        
        # Direct mapping
        currency_map = {
            '£': 'GBP', '€': 'EUR', '$': 'USD', '¥': 'JPY',
            'POUND': 'GBP', 'POUNDS': 'GBP', 'STERLING': 'GBP',
            'EURO': 'EUR', 'EUROS': 'EUR',
            'DOLLAR': 'USD', 'DOLLARS': 'USD',
            'YEN': 'JPY', 'YUAN': 'CNY'
        }
        
        return currency_map.get(currency_str, currency_str if len(currency_str) == 3 else None)
    
    def _adjust_confidence(self, base_confidence: float, context: Optional[Dict[str, Any]], currency: Optional[str]) -> float:
        """Adjust confidence based on context."""
        if not context:
            return base_confidence
        
        # Boost confidence if currency matches document context
        doc_currency = context.get('default_currency')
        if doc_currency and currency == doc_currency:
            return min(base_confidence * 1.2, 1.0)
        
        return base_confidence


class VATParser:
    """Parser for VAT/tax fields with rate and amount extraction."""
    
    VAT_PATTERNS = [
        # VAT rate patterns
        (r'VAT\s*@?\s*(\d+(?:\.\d+)?)%', 0.90),
        (r'Tax\s*@?\s*(\d+(?:\.\d+)?)%', 0.85),
        (r'(\d+(?:\.\d+)?)%\s*VAT', 0.90),
        (r'(\d+(?:\.\d+)?)%\s*Tax', 0.85),
        # VAT amount patterns
        (r'VAT:\s*[£€$]?([\d,]+\.?\d*)', 0.85),
        (r'Tax:\s*[£€$]?([\d,]+\.?\d*)', 0.80),
        (r'VAT\s*[£€$]?([\d,]+\.?\d*)', 0.85),
        (r'Tax\s*[£€$]?([\d,]+\.?\d*)', 0.80),
    ]
    
    def parse(self, raw_value: str, context: Optional[Dict[str, Any]] = None) -> ParsedVAT:
        """
        Parse a VAT/tax string with rate and amount extraction.
        
        Args:
            raw_value: Raw VAT string from OCR
            context: Additional context (e.g., document region, tax rates)
        
        Returns:
            ParsedVAT with normalized rate and amount
        """
        if not raw_value or not raw_value.strip():
            return ParsedVAT(
                rate=None,
                amount=None,
                raw_value=raw_value,
                confidence=0.0,
                errors=[FieldError(
                    field_name="vat",
                    error_type=FieldErrorType.MISSING,
                    raw_value=raw_value,
                    message="Empty VAT value"
                )]
            )
        
        raw_value = raw_value.strip()
        errors = []
        best_rate = None
        best_amount = None
        best_confidence = 0.0
        
        # Try each pattern
        for pattern, base_confidence in self.VAT_PATTERNS:
            matches = re.finditer(pattern, raw_value, re.IGNORECASE)
            for match in matches:
                try:
                    rate, amount = self._parse_match(match, pattern)
                    confidence = self._adjust_confidence(base_confidence, context, rate, amount)
                    if confidence > best_confidence:
                        best_rate = rate
                        best_amount = amount
                        best_confidence = confidence
                except Exception as e:
                    errors.append(FieldError(
                        field_name="vat",
                        error_type=FieldErrorType.PARSE_ERROR,
                        raw_value=raw_value,
                        message=f"Failed to parse VAT with pattern {pattern}: {e}"
                    ))
        
        if best_rate is None and best_amount is None:
            errors.append(FieldError(
                field_name="vat",
                error_type=FieldErrorType.INVALID_FORMAT,
                raw_value=raw_value,
                message="No valid VAT format detected"
            ))
        
        return ParsedVAT(
            rate=best_rate,
            amount=best_amount,
            raw_value=raw_value,
            confidence=best_confidence,
            errors=errors
        )
    
    def _parse_match(self, match, pattern: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """Parse a regex match into rate and amount."""
        groups = match.groups()
        
        rate = None
        amount = None
        
        if len(groups) == 1:
            value_str = groups[0]
            try:
                value = Decimal(value_str)
                
                # Determine if it's a rate or amount based on context
                if '%' in match.group(0) or value <= 100:  # Likely a rate
                    rate = value / 100  # Convert percentage to decimal
                else:  # Likely an amount
                    amount = value
            except (ValueError, InvalidOperation):
                pass
        
        return rate, amount
    
    def _adjust_confidence(self, base_confidence: float, context: Optional[Dict[str, Any]], 
                         rate: Optional[Decimal], amount: Optional[Decimal]) -> float:
        """Adjust confidence based on context."""
        if not context:
            return base_confidence
        
        # Boost confidence if rate matches common tax rates
        if rate is not None:
            common_rates = [Decimal('0.20'), Decimal('0.19'), Decimal('0.21'), Decimal('0.25')]  # 20%, 19%, 21%, 25%
            if rate in common_rates:
                return min(base_confidence * 1.1, 1.0)
        
        return base_confidence


class SupplierParser:
    """Parser for supplier name fields with normalization and aliases."""
    
    # Common supplier name patterns
    SUPPLIER_PATTERNS = [
        (r'Supplier:\s*(.+)', 0.90),
        (r'Vendor:\s*(.+)', 0.90),
        (r'From:\s*(.+)', 0.85),
        (r'Bill\s*To:\s*(.+)', 0.80),
        (r'Company:\s*(.+)', 0.85),
    ]
    
    # Common company suffixes
    COMPANY_SUFFIXES = [
        'LTD', 'LIMITED', 'INC', 'INCORPORATED', 'CORP', 'CORPORATION',
        'LLC', 'LLP', 'LP', 'CO', 'COMPANY', 'GROUP', 'HOLDINGS',
        'PLC', 'AG', 'GMBH', 'SA', 'SRL', 'SPA', 'BV', 'NV'
    ]
    
    def parse(self, raw_value: str, context: Optional[Dict[str, Any]] = None) -> ParsedSupplier:
        """
        Parse a supplier name with normalization and alias detection.
        
        Args:
            raw_value: Raw supplier string from OCR
            context: Additional context (e.g., known suppliers, region)
        
        Returns:
            ParsedSupplier with normalized name and aliases
        """
        if not raw_value or not raw_value.strip():
            return ParsedSupplier(
                name=None,
                aliases=[],
                raw_value=raw_value,
                confidence=0.0,
                errors=[FieldError(
                    field_name="supplier",
                    error_type=FieldErrorType.MISSING,
                    raw_value=raw_value,
                    message="Empty supplier value"
                )]
            )
        
        raw_value = raw_value.strip()
        errors = []
        
        # Extract supplier name using patterns
        supplier_name = None
        confidence = 0.0
        
        for pattern, base_confidence in self.SUPPLIER_PATTERNS:
            match = re.search(pattern, raw_value, re.IGNORECASE)
            if match:
                supplier_name = match.group(1).strip()
                confidence = base_confidence
                break
        
        # If no pattern matched, use the whole string
        if supplier_name is None:
            supplier_name = raw_value
            confidence = 0.5
        
        # Normalize the supplier name
        normalized_name, aliases = self._normalize_supplier_name(supplier_name)
        
        # Adjust confidence based on context
        confidence = self._adjust_confidence(confidence, context, normalized_name)
        
        return ParsedSupplier(
            name=normalized_name,
            aliases=aliases,
            raw_value=raw_value,
            confidence=confidence,
            errors=errors
        )
    
    def _normalize_supplier_name(self, name: str) -> Tuple[Optional[str], List[str]]:
        """Normalize supplier name and extract aliases."""
        if not name:
            return None, []
        
        # Clean up the name
        name = name.strip()
        
        # Remove common prefixes
        prefixes_to_remove = ['Mr.', 'Ms.', 'Mrs.', 'Dr.', 'Prof.']
        for prefix in prefixes_to_remove:
            if name.startswith(prefix):
                name = name[len(prefix):].strip()
        
        # Extract aliases (alternative names)
        aliases = []
        
        # Check for "trading as" or "d/b/a" patterns
        trading_as_patterns = [
            r'trading\s+as\s+(.+)',
            r'd/b/a\s+(.+)',
            r'doing\s+business\s+as\s+(.+)',
        ]
        
        for pattern in trading_as_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                aliases.append(match.group(1).strip())
                name = name[:match.start()].strip()
        
        # Normalize company suffixes
        normalized_name = name
        for suffix in self.COMPANY_SUFFIXES:
            if name.upper().endswith(' ' + suffix):
                # Keep the suffix but normalize it
                base_name = name[:-len(' ' + suffix)].strip()
                normalized_name = f"{base_name} {suffix}"
                break
        
        return normalized_name, aliases
    
    def _adjust_confidence(self, base_confidence: float, context: Optional[Dict[str, Any]], 
                          normalized_name: Optional[str]) -> float:
        """Adjust confidence based on context."""
        if not context or not normalized_name:
            return base_confidence
        
        # Boost confidence if supplier is in known suppliers list
        known_suppliers = context.get('known_suppliers', [])
        if normalized_name in known_suppliers:
            return min(base_confidence * 1.2, 1.0)
        
        # Boost confidence if name contains company indicators
        company_indicators = ['LTD', 'LIMITED', 'INC', 'CORP', 'LLC', 'COMPANY']
        if any(indicator in normalized_name.upper() for indicator in company_indicators):
            return min(base_confidence * 1.1, 1.0)
        
        return base_confidence


class UnitParser:
    """Parser for unit of measure fields with standardization."""
    
    # Unit mappings to standard units
    UNIT_MAPPINGS = {
        # Weight units
        'kg': ['kg', 'kilogram', 'kilograms', 'kilo', 'kilos'],
        'g': ['g', 'gram', 'grams', 'gm', 'gms'],
        'lb': ['lb', 'lbs', 'pound', 'pounds', 'lbs'],
        'oz': ['oz', 'ounce', 'ounces'],
        
        # Volume units
        'l': ['l', 'litre', 'litres', 'liter', 'liters', 'lt', 'ltr'],
        'ml': ['ml', 'millilitre', 'millilitres', 'milliliter', 'milliliters'],
        'gal': ['gal', 'gallon', 'gallons'],
        'pt': ['pt', 'pint', 'pints'],
        
        # Count units
        'pcs': ['pcs', 'pieces', 'piece', 'pcs', 'units', 'unit', 'items', 'item'],
        'box': ['box', 'boxes', 'case', 'cases', 'pack', 'packs'],
        'dozen': ['dozen', 'doz', 'dozens'],
        'gross': ['gross', 'gr'],
        
        # Length units
        'm': ['m', 'metre', 'metres', 'meter', 'meters'],
        'cm': ['cm', 'centimetre', 'centimetres', 'centimeter', 'centimeters'],
        'mm': ['mm', 'millimetre', 'millimetres', 'millimeter', 'millimeters'],
        'ft': ['ft', 'foot', 'feet'],
        'in': ['in', 'inch', 'inches'],
        
        # Time units
        'hr': ['hr', 'hour', 'hours', 'h'],
        'min': ['min', 'minute', 'minutes', 'mins'],
        'day': ['day', 'days', 'd'],
        'week': ['week', 'weeks', 'wk', 'wks'],
        'month': ['month', 'months', 'mo', 'mos'],
        'year': ['year', 'years', 'yr', 'yrs'],
        
        # Area units
        'm2': ['m2', 'm²', 'square metre', 'square metres', 'sqm'],
        'ft2': ['ft2', 'ft²', 'square foot', 'square feet', 'sqft'],
        
        # Other common units
        'each': ['each', 'ea', 'per', 'apiece'],
        'pair': ['pair', 'pairs', 'pr'],
        'set': ['set', 'sets'],
    }
    
    def parse(self, raw_value: str, context: Optional[Dict[str, Any]] = None) -> ParsedUnit:
        """
        Parse a unit of measure string with standardization.
        
        Args:
            raw_value: Raw unit string from OCR
            context: Additional context (e.g., product type, industry)
        
        Returns:
            ParsedUnit with normalized unit
        """
        if not raw_value or not raw_value.strip():
            return ParsedUnit(
                unit=None,
                raw_value=raw_value,
                confidence=0.0,
                errors=[FieldError(
                    field_name="unit",
                    error_type=FieldErrorType.MISSING,
                    raw_value=raw_value,
                    message="Empty unit value"
                )]
            )
        
        raw_value = raw_value.strip()
        errors = []
        
        # Find matching unit
        normalized_unit = None
        confidence = 0.0
        
        for standard_unit, variations in self.UNIT_MAPPINGS.items():
            for variation in variations:
                if variation.lower() == raw_value.lower():
                    normalized_unit = standard_unit
                    confidence = 0.95
                    break
            if normalized_unit:
                break
        
        # If no exact match, try partial matching
        if not normalized_unit:
            for standard_unit, variations in self.UNIT_MAPPINGS.items():
                for variation in variations:
                    if variation.lower() in raw_value.lower() or raw_value.lower() in variation.lower():
                        normalized_unit = standard_unit
                        confidence = 0.80
                        break
                if normalized_unit:
                    break
        
        if not normalized_unit:
            errors.append(FieldError(
                field_name="unit",
                error_type=FieldErrorType.INVALID_FORMAT,
                raw_value=raw_value,
                message="No valid unit format detected"
            ))
        
        return ParsedUnit(
            unit=normalized_unit,
            raw_value=raw_value,
            confidence=confidence,
            errors=errors
        )


class LineItemParser:
    """Parser for line item fields with comprehensive extraction."""
    
    def parse(self, raw_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> NormalizedLineItem:
        """
        Parse line item data with all field extraction.
        
        Args:
            raw_data: Raw line item data from OCR/table extraction
            context: Additional context (e.g., document currency, tax rates)
        
        Returns:
            NormalizedLineItem with all fields parsed
        """
        errors = []
        
        # Extract description
        description = self._extract_description(raw_data)
        
        # Extract quantity
        quantity = self._extract_quantity(raw_data, context)
        
        # Extract unit
        unit = self._extract_unit(raw_data, context)
        
        # Extract unit price
        unit_price = self._extract_unit_price(raw_data, context)
        
        # Extract line total
        line_total = self._extract_line_total(raw_data, context)
        
        # Extract VAT rate
        vat_rate = self._extract_vat_rate(raw_data, context)
        
        # Extract VAT amount
        vat_amount = self._extract_vat_amount(raw_data, context)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(raw_data, description, quantity, unit_price, line_total)
        
        return NormalizedLineItem(
            description=description,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            line_total=line_total,
            vat_rate=vat_rate,
            vat_amount=vat_amount,
            raw_data=raw_data,
            confidence=confidence,
            errors=errors
        )
    
    def _extract_description(self, raw_data: Dict[str, Any]) -> str:
        """Extract description from raw data."""
        # Try different possible keys for description
        description_keys = ['description', 'item', 'product', 'service', 'name', 'text']
        
        for key in description_keys:
            if key in raw_data and raw_data[key]:
                return str(raw_data[key]).strip()
        
        # If no specific key found, use the first non-numeric field
        for key, value in raw_data.items():
            if isinstance(value, str) and value.strip() and not value.replace('.', '').replace(',', '').isdigit():
                return value.strip()
        
        return ""
    
    def _extract_quantity(self, raw_data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Optional[Decimal]:
        """Extract quantity from raw data."""
        quantity_keys = ['quantity', 'qty', 'amount', 'count', 'number']
        
        for key in quantity_keys:
            if key in raw_data and raw_data[key]:
                try:
                    value = str(raw_data[key]).replace(',', '')
                    return Decimal(value)
                except (ValueError, InvalidOperation):
                    continue
        
        return None
    
    def _extract_unit(self, raw_data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Optional[str]:
        """Extract unit from raw data."""
        unit_keys = ['unit', 'uom', 'measure', 'measurement']
        
        for key in unit_keys:
            if key in raw_data and raw_data[key]:
                unit_parser = UnitParser()
                parsed_unit = unit_parser.parse(str(raw_data[key]), context)
                if parsed_unit.is_valid():
                    return parsed_unit.unit
        
        return None
    
    def _extract_unit_price(self, raw_data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Optional[Decimal]:
        """Extract unit price from raw data."""
        price_keys = ['unit_price', 'price', 'rate', 'cost', 'unit_cost']
        
        for key in price_keys:
            if key in raw_data and raw_data[key]:
                try:
                    price_parser = PriceParser()
                    parsed_price = price_parser.parse(str(raw_data[key]), context)
                    if parsed_price.is_valid():
                        return parsed_price.amount
                except Exception:
                    continue
        
        return None
    
    def _extract_line_total(self, raw_data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Optional[Decimal]:
        """Extract line total from raw data."""
        total_keys = ['total', 'line_total', 'amount', 'sum', 'subtotal']
        
        for key in total_keys:
            if key in raw_data and raw_data[key]:
                try:
                    price_parser = PriceParser()
                    parsed_price = price_parser.parse(str(raw_data[key]), context)
                    if parsed_price.is_valid():
                        return parsed_price.amount
                except Exception:
                    continue
        
        return None
    
    def _extract_vat_rate(self, raw_data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Optional[Decimal]:
        """Extract VAT rate from raw data."""
        vat_keys = ['vat_rate', 'tax_rate', 'rate', 'vat', 'tax']
        
        for key in vat_keys:
            if key in raw_data and raw_data[key]:
                try:
                    vat_parser = VATParser()
                    parsed_vat = vat_parser.parse(str(raw_data[key]), context)
                    if parsed_vat.is_valid() and parsed_vat.rate is not None:
                        return parsed_vat.rate
                except Exception:
                    continue
        
        return None
    
    def _extract_vat_amount(self, raw_data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Optional[Decimal]:
        """Extract VAT amount from raw data."""
        vat_amount_keys = ['vat_amount', 'tax_amount', 'vat', 'tax']
        
        for key in vat_amount_keys:
            if key in raw_data and raw_data[key]:
                try:
                    vat_parser = VATParser()
                    parsed_vat = vat_parser.parse(str(raw_data[key]), context)
                    if parsed_vat.is_valid() and parsed_vat.amount is not None:
                        return parsed_vat.amount
                except Exception:
                    continue
        
        return None
    
    def _calculate_confidence(self, raw_data: Dict[str, Any], description: str, 
                            quantity: Optional[Decimal], unit_price: Optional[Decimal], 
                            line_total: Optional[Decimal]) -> float:
        """Calculate overall confidence for the line item."""
        confidence_factors = []
        
        # Description confidence
        if description and len(description.strip()) > 3:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.2)
        
        # Quantity confidence
        if quantity is not None and quantity > 0:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.3)
        
        # Unit price confidence
        if unit_price is not None and unit_price > 0:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.3)
        
        # Line total confidence
        if line_total is not None and line_total > 0:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.3)
        
        # Calculate weighted average
        return sum(confidence_factors) / len(confidence_factors)
