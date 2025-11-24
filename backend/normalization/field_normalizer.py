"""
Main field normalizer that orchestrates all parsing and normalization.

This module provides the main FieldNormalizer class that coordinates all
individual parsers to produce a complete normalized invoice.
"""

from __future__ import annotations
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from .parsers import (
    DateParser, CurrencyParser, PriceParser, VATParser,
    SupplierParser, UnitParser, LineItemParser
)
from .types import (
    NormalizedInvoice, NormalizedLineItem, NormalizationResult,
    FieldError, FieldErrorType
)
from .confidence_routing import ConfidenceRouter, ConfidenceRoutingResult

LOGGER = logging.getLogger("owlin.normalization.field_normalizer")


class FieldNormalizer:
    """
    Main field normalizer that orchestrates all parsing and normalization.
    
    This class coordinates all individual parsers to produce a complete
    normalized invoice with type-safe fields and comprehensive error handling.
    """
    
    def __init__(self, confidence_config: Optional[Dict[str, Any]] = None):
        """Initialize the field normalizer with all parsers."""
        self.date_parser = DateParser()
        self.currency_parser = CurrencyParser()
        self.price_parser = PriceParser()
        self.vat_parser = VATParser()
        self.supplier_parser = SupplierParser()
        self.unit_parser = UnitParser()
        self.line_item_parser = LineItemParser()
        
        # Initialize confidence router
        self.confidence_router = ConfidenceRouter(confidence_config)
        
        LOGGER.info("FieldNormalizer initialized with all parsers and confidence routing")
    
    def normalize_invoice(self, raw_data: Dict[str, Any], 
                         context: Optional[Dict[str, Any]] = None) -> NormalizationResult:
        """
        Normalize a complete invoice from raw OCR data.
        
        Args:
            raw_data: Raw invoice data from OCR pipeline
            context: Additional context (e.g., document region, language, known suppliers)
        
        Returns:
            NormalizationResult with complete normalized invoice
        """
        start_time = time.time()
        warnings = []
        
        try:
            LOGGER.info("Starting invoice normalization")
            
            # Extract context information
            if context is None:
                context = {}
            
            # Parse all fields
            supplier_name = self._parse_supplier_name(raw_data, context)
            invoice_number = self._parse_invoice_number(raw_data, context)
            invoice_date = self._parse_invoice_date(raw_data, context)
            currency = self._parse_currency(raw_data, context)
            subtotal = self._parse_subtotal(raw_data, context)
            tax_amount = self._parse_tax_amount(raw_data, context)
            total_amount = self._parse_total_amount(raw_data, context)
            line_items = self._parse_line_items(raw_data, context)
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(
                supplier_name, invoice_number, invoice_date, currency,
                subtotal, tax_amount, total_amount, line_items
            )
            
            # Collect all errors
            all_errors = []
            for field_result in [supplier_name, invoice_number, invoice_date, 
                               currency, subtotal, tax_amount, total_amount]:
                if hasattr(field_result, 'errors'):
                    all_errors.extend(field_result.errors)
            
            for line_item in line_items:
                all_errors.extend(line_item.errors)
            
            # Create normalized invoice
            normalized_invoice = NormalizedInvoice(
                supplier_name=supplier_name.name if supplier_name and supplier_name.is_valid() else None,
                invoice_number=invoice_number,
                invoice_date=invoice_date.date if invoice_date and invoice_date.is_valid() else None,
                currency=currency.currency_code if currency and currency.is_valid() else None,
                subtotal=subtotal.amount if subtotal and subtotal.is_valid() else None,
                tax_amount=tax_amount.amount if tax_amount and tax_amount.is_valid() else None,
                total_amount=total_amount.amount if total_amount and total_amount.is_valid() else None,
                line_items=line_items,
                raw_data=raw_data,
                overall_confidence=overall_confidence,
                errors=all_errors
            )
            
            processing_time = time.time() - start_time
            
            # Determine parser used and fallback status
            parser_used = "comprehensive_parsing"
            fallback_used = overall_confidence < 0.7
            
            if fallback_used:
                warnings.append("Low confidence normalization - fallback mechanisms used")
            
            LOGGER.info("Invoice normalization completed in %.3f seconds, confidence: %.3f", 
                       processing_time, overall_confidence)
            
            return NormalizationResult(
                normalized_invoice=normalized_invoice,
                processing_time=processing_time,
                parser_used=parser_used,
                fallback_used=fallback_used,
                warnings=warnings
            )
            
        except Exception as e:
            LOGGER.error("Invoice normalization failed: %s", e)
            
            # Create error result
            error_invoice = NormalizedInvoice(
                supplier_name=None,
                invoice_number=None,
                invoice_date=None,
                currency=None,
                subtotal=None,
                tax_amount=None,
                total_amount=None,
                line_items=[],
                raw_data=raw_data,
                overall_confidence=0.0,
                errors=[FieldError(
                    field_name="normalization",
                    error_type=FieldErrorType.PARSE_ERROR,
                    raw_value=str(raw_data),
                    message=f"Normalization failed: {e}"
                )]
            )
            
            return NormalizationResult(
                normalized_invoice=error_invoice,
                processing_time=time.time() - start_time,
                parser_used="error",
                fallback_used=True,
                warnings=[f"Normalization failed: {e}"]
            )
    
    def _parse_supplier_name(self, raw_data: Dict[str, Any], 
                            context: Optional[Dict[str, Any]]) -> Any:
        """Parse supplier name from raw data."""
        supplier_keys = ['supplier', 'vendor', 'from', 'company', 'business_name']
        
        for key in supplier_keys:
            if key in raw_data and raw_data[key]:
                return self.supplier_parser.parse(str(raw_data[key]), context)
        
        # Try to extract from document text
        if 'text' in raw_data:
            return self.supplier_parser.parse(str(raw_data['text']), context)
        
        return self.supplier_parser.parse("", context)
    
    def _parse_invoice_number(self, raw_data: Dict[str, Any], 
                             context: Optional[Dict[str, Any]]) -> Optional[str]:
        """Parse invoice number from raw data."""
        invoice_keys = ['invoice_number', 'invoice_no', 'invoice_id', 'reference', 'ref', 'number']
        
        for key in invoice_keys:
            if key in raw_data and raw_data[key]:
                return str(raw_data[key]).strip()
        
        return None
    
    def _parse_invoice_date(self, raw_data: Dict[str, Any], 
                           context: Optional[Dict[str, Any]]) -> Any:
        """Parse invoice date from raw data."""
        date_keys = ['invoice_date', 'date', 'issue_date', 'created_date', 'billing_date']
        
        for key in date_keys:
            if key in raw_data and raw_data[key]:
                return self.date_parser.parse(str(raw_data[key]), context)
        
        return self.date_parser.parse("", context)
    
    def _parse_currency(self, raw_data: Dict[str, Any], 
                     context: Optional[Dict[str, Any]]) -> Any:
        """Parse currency from raw data."""
        currency_keys = ['currency', 'currency_code', 'curr']
        
        for key in currency_keys:
            if key in raw_data and raw_data[key]:
                return self.currency_parser.parse(str(raw_data[key]), context)
        
        # Try to extract from price fields
        price_keys = ['total', 'subtotal', 'amount', 'price']
        for key in price_keys:
            if key in raw_data and raw_data[key]:
                price_result = self.price_parser.parse(str(raw_data[key]), context)
                if price_result.currency_code:
                    return price_result
        
        return self.currency_parser.parse("", context)
    
    def _parse_subtotal(self, raw_data: Dict[str, Any], 
                       context: Optional[Dict[str, Any]]) -> Any:
        """Parse subtotal from raw data."""
        subtotal_keys = ['subtotal', 'net_total', 'net', 'sub_total', 'before_tax']
        
        for key in subtotal_keys:
            if key in raw_data and raw_data[key]:
                return self.price_parser.parse(str(raw_data[key]), context)
        
        return self.price_parser.parse("", context)
    
    def _parse_tax_amount(self, raw_data: Dict[str, Any], 
                         context: Optional[Dict[str, Any]]) -> Any:
        """Parse tax amount from raw data."""
        tax_keys = ['tax_amount', 'vat_amount', 'tax', 'vat', 'tax_total', 'vat_total']
        
        for key in tax_keys:
            if key in raw_data and raw_data[key]:
                return self.vat_parser.parse(str(raw_data[key]), context)
        
        return self.vat_parser.parse("", context)
    
    def _parse_total_amount(self, raw_data: Dict[str, Any], 
                           context: Optional[Dict[str, Any]]) -> Any:
        """Parse total amount from raw data."""
        total_keys = ['total', 'total_amount', 'grand_total', 'amount_due', 'final_total']
        
        for key in total_keys:
            if key in raw_data and raw_data[key]:
                return self.price_parser.parse(str(raw_data[key]), context)
        
        return self.price_parser.parse("", context)
    
    def _parse_line_items(self, raw_data: Dict[str, Any], 
                         context: Optional[Dict[str, Any]]) -> List[NormalizedLineItem]:
        """Parse line items from raw data."""
        line_items = []
        
        # Try to get line items from table data
        if 'line_items' in raw_data and isinstance(raw_data['line_items'], list):
            for item_data in raw_data['line_items']:
                if isinstance(item_data, dict):
                    line_item = self.line_item_parser.parse(item_data, context)
                    line_items.append(line_item)
        
        # Try to get line items from table extraction results
        if 'table_data' in raw_data and isinstance(raw_data['table_data'], list):
            for item_data in raw_data['table_data']:
                if isinstance(item_data, dict):
                    line_item = self.line_item_parser.parse(item_data, context)
                    line_items.append(line_item)
        
        # Try to get line items from blocks
        if 'blocks' in raw_data and isinstance(raw_data['blocks'], list):
            for block in raw_data['blocks']:
                if isinstance(block, dict) and block.get('type') == 'table':
                    table_data = block.get('table_data')
                    if isinstance(table_data, list):
                        for item_data in table_data:
                            if isinstance(item_data, dict):
                                line_item = self.line_item_parser.parse(item_data, context)
                                line_items.append(line_item)
        
        return line_items
    
    def _calculate_overall_confidence(self, supplier_name, invoice_number, invoice_date,
                                    currency, subtotal, tax_amount, total_amount, 
                                    line_items: List[NormalizedLineItem]) -> float:
        """Calculate overall confidence for the normalized invoice."""
        confidence_factors = []
        
        # Field confidence factors
        if supplier_name and hasattr(supplier_name, 'confidence'):
            confidence_factors.append(supplier_name.confidence)
        else:
            confidence_factors.append(0.0)
        
        if invoice_date and hasattr(invoice_date, 'confidence'):
            confidence_factors.append(invoice_date.confidence)
        else:
            confidence_factors.append(0.0)
        
        if currency and hasattr(currency, 'confidence'):
            confidence_factors.append(currency.confidence)
        else:
            confidence_factors.append(0.0)
        
        if total_amount and hasattr(total_amount, 'confidence'):
            confidence_factors.append(total_amount.confidence)
        else:
            confidence_factors.append(0.0)
        
        # Line items confidence
        if line_items:
            line_item_confidences = [item.confidence for item in line_items if item.confidence > 0]
            if line_item_confidences:
                confidence_factors.append(sum(line_item_confidences) / len(line_item_confidences))
            else:
                confidence_factors.append(0.0)
        else:
            confidence_factors.append(0.0)
        
        # Calculate weighted average
        return sum(confidence_factors) / len(confidence_factors)
    
    def normalize_single_field(self, field_name: str, raw_value: str, 
                              context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Normalize a single field value.
        
        Args:
            field_name: Name of the field to normalize
            raw_value: Raw value to normalize
            context: Additional context
        
        Returns:
            Parsed result for the field
        """
        if field_name.lower() in ['date', 'invoice_date', 'issue_date']:
            return self.date_parser.parse(raw_value, context)
        elif field_name.lower() in ['currency', 'currency_code']:
            return self.currency_parser.parse(raw_value, context)
        elif field_name.lower() in ['price', 'amount', 'total', 'subtotal']:
            return self.price_parser.parse(raw_value, context)
        elif field_name.lower() in ['vat', 'tax', 'vat_rate', 'tax_rate']:
            return self.vat_parser.parse(raw_value, context)
        elif field_name.lower() in ['supplier', 'vendor', 'company']:
            return self.supplier_parser.parse(raw_value, context)
        elif field_name.lower() in ['unit', 'uom', 'measure']:
            return self.unit_parser.parse(raw_value, context)
        else:
            LOGGER.warning("Unknown field name for normalization: %s", field_name)
            return None
    
    def normalize_invoice_with_routing(self, raw_data: Dict[str, Any], 
                                    context: Optional[Dict[str, Any]] = None) -> Tuple[NormalizationResult, ConfidenceRoutingResult]:
        """
        Normalize an invoice with confidence routing and flagging.
        
        Args:
            raw_data: Raw invoice data from OCR pipeline
            context: Additional context (e.g., document region, language, known suppliers)
        
        Returns:
            Tuple of (NormalizationResult, ConfidenceRoutingResult)
        """
        # First, normalize the invoice
        normalization_result = self.normalize_invoice(raw_data, context)
        
        # Then, apply confidence routing
        routing_result = self.confidence_router.route_invoice(
            normalization_result.normalized_invoice, 
            context
        )
        
        # Add routing information to the normalization result
        normalization_result.routing_result = routing_result
        
        LOGGER.info(
            "Invoice normalization with routing completed: %d auto-accepted, %d review candidates",
            len(routing_result.auto_accepted_fields),
            len(routing_result.review_candidates)
        )
        
        return normalization_result, routing_result
