"""
Type definitions for the normalization module.

Provides type-safe data structures for normalized invoice data,
parsing results, and error handling.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal


class FieldErrorType(Enum):
    """Types of field parsing errors."""
    PARSE_ERROR = "parse_error"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"
    INVALID_FORMAT = "invalid_format"
    OUT_OF_RANGE = "out_of_range"


@dataclass
class FieldError:
    """Represents a field parsing error with context."""
    field_name: str
    error_type: FieldErrorType
    raw_value: str
    message: str
    confidence: float = 0.0
    suggestions: Optional[List[str]] = None


@dataclass
class ParsedDate:
    """Normalized date with confidence and metadata."""
    date: Optional[date]
    raw_value: str
    confidence: float
    format_detected: Optional[str]
    errors: List[FieldError]
    
    def is_valid(self) -> bool:
        """Check if the date is valid and confident."""
        return self.date is not None and self.confidence >= 0.7
    
    def to_iso_string(self) -> Optional[str]:
        """Return ISO date string (YYYY-MM-DD) or None."""
        return self.date.isoformat() if self.date else None


@dataclass
class ParsedCurrency:
    """Normalized currency with confidence and metadata."""
    currency_code: Optional[str]  # ISO 4217 code (USD, EUR, GBP, etc.)
    symbol: Optional[str]  # Original symbol (£, €, $, etc.)
    raw_value: str
    confidence: float
    errors: List[FieldError]
    
    def is_valid(self) -> bool:
        """Check if the currency is valid and confident."""
        return self.currency_code is not None and self.confidence >= 0.7


@dataclass
class ParsedPrice:
    """Normalized price with confidence and metadata."""
    amount: Optional[Decimal]
    currency_code: Optional[str]
    raw_value: str
    confidence: float
    errors: List[FieldError]
    
    def is_valid(self) -> bool:
        """Check if the price is valid and confident."""
        return self.amount is not None and self.confidence >= 0.7
    
    def to_float(self) -> Optional[float]:
        """Return amount as float or None."""
        return float(self.amount) if self.amount is not None else None


@dataclass
class ParsedVAT:
    """Normalized VAT/tax information."""
    rate: Optional[Decimal]  # Tax rate as decimal (0.20 for 20%)
    amount: Optional[Decimal]  # Tax amount
    raw_value: str
    confidence: float
    errors: List[FieldError]
    
    def is_valid(self) -> bool:
        """Check if the VAT is valid and confident."""
        return (self.rate is not None or self.amount is not None) and self.confidence >= 0.7


@dataclass
class ParsedSupplier:
    """Normalized supplier information."""
    name: Optional[str]
    aliases: List[str]  # Alternative names found
    raw_value: str
    confidence: float
    errors: List[FieldError]
    
    def is_valid(self) -> bool:
        """Check if the supplier is valid and confident."""
        return self.name is not None and self.confidence >= 0.7


@dataclass
class ParsedUnit:
    """Normalized unit of measure."""
    unit: Optional[str]  # Standardized unit (kg, pcs, hours, etc.)
    raw_value: str
    confidence: float
    errors: List[FieldError]
    
    def is_valid(self) -> bool:
        """Check if the unit is valid and confident."""
        return self.unit is not None and self.confidence >= 0.7


@dataclass
class NormalizedLineItem:
    """Normalized line item with all fields parsed."""
    description: str
    quantity: Optional[Decimal]
    unit: Optional[str]
    unit_price: Optional[Decimal]
    line_total: Optional[Decimal]
    vat_rate: Optional[Decimal]
    vat_amount: Optional[Decimal]
    raw_data: Dict[str, Any]
    confidence: float
    errors: List[FieldError]
    
    def is_valid(self) -> bool:
        """Check if the line item has sufficient valid data."""
        return (
            bool(self.description.strip()) and
            (self.quantity is not None or self.unit_price is not None or self.line_total is not None)
        )


@dataclass
class NormalizedInvoice:
    """Complete normalized invoice with all fields parsed."""
    supplier_name: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[date]
    currency: Optional[str]
    subtotal: Optional[Decimal]
    tax_amount: Optional[Decimal]
    total_amount: Optional[Decimal]
    line_items: List[NormalizedLineItem]
    raw_data: Dict[str, Any]
    overall_confidence: float
    errors: List[FieldError]
    
    def is_valid(self) -> bool:
        """Check if the invoice has sufficient valid data."""
        return (
            self.supplier_name is not None or
            self.invoice_number is not None or
            self.total_amount is not None or
            len(self.line_items) > 0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "supplier_name": self.supplier_name,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "currency": self.currency,
            "subtotal": float(self.subtotal) if self.subtotal else None,
            "tax_amount": float(self.tax_amount) if self.tax_amount else None,
            "total_amount": float(self.total_amount) if self.total_amount else None,
            "line_items": [
                {
                    "description": item.description,
                    "quantity": float(item.quantity) if item.quantity else None,
                    "unit": item.unit,
                    "unit_price": float(item.unit_price) if item.unit_price else None,
                    "line_total": float(item.line_total) if item.line_total else None,
                    "vat_rate": float(item.vat_rate) if item.vat_rate else None,
                    "vat_amount": float(item.vat_amount) if item.vat_amount else None,
                    "confidence": item.confidence,
                    "errors": [error.__dict__ for error in item.errors]
                }
                for item in self.line_items
            ],
            "overall_confidence": self.overall_confidence,
            "errors": [error.__dict__ for error in self.errors]
        }


@dataclass
class NormalizationResult:
    """Result of the normalization process."""
    normalized_invoice: NormalizedInvoice
    processing_time: float
    parser_used: str
    fallback_used: bool
    warnings: List[str]
    routing_result: Optional[Any] = None  # ConfidenceRoutingResult
    
    def is_successful(self) -> bool:
        """Check if normalization was successful."""
        return self.normalized_invoice.is_valid() and not self.fallback_used
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the normalization result."""
        return {
            "success": self.is_successful(),
            "confidence": self.normalized_invoice.overall_confidence,
            "fields_parsed": sum(1 for field in [
                self.normalized_invoice.supplier_name,
                self.normalized_invoice.invoice_number,
                self.normalized_invoice.invoice_date,
                self.normalized_invoice.currency,
                self.normalized_invoice.total_amount
            ] if field is not None),
            "line_items_count": len(self.normalized_invoice.line_items),
            "errors_count": len(self.normalized_invoice.errors),
            "processing_time": self.processing_time,
            "parser_used": self.parser_used,
            "fallback_used": self.fallback_used
        }
