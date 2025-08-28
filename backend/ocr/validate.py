#!/usr/bin/env python3
"""
Document Validation Suite - Production-Ready Validation System

This module provides comprehensive validation of extracted document data including:
- Arithmetic validation (line totals vs document totals)
- Currency consistency checks
- Date sanity validation
- VAT calculation verification
- Supplier name validation

Author: OWLIN Development Team
Version: 1.0.0
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
import zoneinfo

from .config import get_ocr_config

logger = logging.getLogger(__name__)

@dataclass
class ValidationIssue:
    """Individual validation issue"""
    issue_type: str
    severity: str  # 'error', 'warning', 'info'
    message: str
    details: Dict[str, Any]
    field: Optional[str] = None

@dataclass
class ValidationResult:
    """Result of document validation"""
    arithmetic_ok: bool
    currency_ok: bool
    date_ok: bool
    vat_ok: bool
    supplier_ok: bool
    overall_ok: bool
    issues: List[ValidationIssue]
    confidence: float  # 0.0 to 1.0

# Ignore receipt meta rows in arithmetic
IGNORE_ROWS_RX = re.compile(r"\b(change|rounding|cash|card|tip)\b", re.I)

def _norm_money(s: str) -> Optional[Decimal]:
    """Normalize currency values"""
    if s is None: 
        return None
    ss = s.replace(" ", "").replace("€","").replace("£","").replace("$","")
    ss = ss.replace(",", ".") if ss.count(",") > ss.count(".") else ss
    try: 
        return Decimal(ss)
    except: 
        return None

def _effective_line_total(row: Dict[str, Any]) -> Optional[Decimal]:
    """Calculate effective line total from quantity and unit price if line_total is missing"""
    if row.get('line_total') is not None:
        return _norm_money(str(row['line_total']))
    if row.get('quantity') is not None and row.get('unit_price') is not None:
        try: 
            qty = _norm_money(str(row['quantity']))
            price = _norm_money(str(row['unit_price']))
            if qty is not None and price is not None:
                return qty * price
        except: 
            pass
    return None

class DocumentValidator:
    """
    Production-ready document validator with comprehensive business rule checking
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._get_default_config()
        self._init_patterns()
        
    def _get_default_config(self) -> Dict:
        """Get default validation configuration"""
        return {
            'arithmetic': {
                'tolerance_amount': 0.50,  # £0.50 absolute tolerance
                'tolerance_percent': 0.005,  # 0.5% relative tolerance
                'min_total': 0.01,  # Minimum total to validate
            },
            'currency': {
                'allowed_currencies': ['GBP', 'USD', 'EUR'],
                'currency_symbols': ['£', '$', '€'],
                'require_consistency': True,
            },
            'date': {
                'max_future_days': 3,
                'max_past_years': 5,
                'require_valid_format': True,
            },
            'vat': {
                'uk_vat_rate': 0.20,  # 20% UK VAT
                'tolerance_percent': 0.01,  # 1% VAT tolerance
                'validate_vat_numbers': True,
            },
            'supplier': {
                'min_name_length': 3,
                'max_name_length': 100,
                'require_business_indicators': True,
            }
        }
    
    def _init_patterns(self):
        """Initialize regex patterns for validation"""
        
        # Currency patterns
        self.currency_patterns = {
            'GBP': [r'£', r'gbp', r'pound'],
            'USD': [r'\$', r'usd', r'dollar'],
            'EUR': [r'€', r'eur', r'euro'],
        }
        
        # VAT number patterns
        self.vat_patterns = {
            'UK': r'^GB\d{9}$|^GB\d{12}$|^GBGD\d{3}$|^GBHA\d{3}$',
            'EU': r'^[A-Z]{2}\d{9,12}$',
        }
        
        # Date patterns
        self.date_patterns = [
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',  # DD/MM/YYYY
            r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',  # YYYY/MM/DD
            r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{2,4})\b',  # DD MMM YYYY
        ]
        
    def validate_document(self, data: Dict[str, Any], ocr_text: str = "") -> ValidationResult:
        """Validate document data"""
        issues = []
        
        # Get document type
        doc_type = data.get('document_type', 'unknown')
        
        # For "other" document types, validation should fail
        if doc_type == 'other':
            issues.append(ValidationIssue(
                issue_type='DOC_UNKNOWN',
                severity='error',
                message='Document type is not a valid business document',
                details={
                    'expected': 'invoice|delivery_note|receipt|utility',
                    'actual': doc_type
                },
                field='document_type'
            ))
            return ValidationResult(
                arithmetic_ok=False,
                currency_ok=False,
                vat_ok=False,
                date_ok=False,
                supplier_ok=False,
                overall_ok=False,
                issues=issues,
                confidence=0.0
            )
        
        # Validate arithmetic
        arithmetic_ok, arithmetic_issues = self._validate_arithmetic(data)
        issues.extend(arithmetic_issues)
        
        # Validate currency
        currency_ok, currency_issues = self._validate_currency(data, ocr_text)
        issues.extend(currency_issues)
        
        # Validate VAT
        vat_ok, vat_issues = self._validate_vat(data)
        issues.extend(vat_issues)
        
        # Validate dates
        date_ok, date_issues = self._validate_dates(data)
        issues.extend(date_issues)
        
        # Validate supplier
        supplier_ok, supplier_issues = self._validate_supplier(data)
        issues.extend(supplier_issues)
        
        # Calculate overall validation result
        overall_ok = arithmetic_ok and currency_ok and vat_ok and date_ok and supplier_ok
        
        # Calculate confidence based on validation results
        confidence = sum([arithmetic_ok, currency_ok, vat_ok, date_ok, supplier_ok]) / 5.0
        
        return ValidationResult(
            arithmetic_ok=arithmetic_ok,
            currency_ok=currency_ok,
            vat_ok=vat_ok,
            date_ok=date_ok,
            supplier_ok=supplier_ok,
            overall_ok=overall_ok,
            issues=issues,
            confidence=confidence
        )
    
    def _validate_arithmetic(self, data: Dict[str, Any]) -> Tuple[bool, List[ValidationIssue]]:
        """Validate arithmetic consistency"""
        issues = []
        
        if not data.get('line_items'):
            return True, issues
        
        # Calculate line sum
        line_sum = 0.0
        for item in data['line_items']:
            # Skip meta rows (change, cash, card, void, refund, etc.)
            if self._is_meta_row(item):
                continue
            
            lt = self._effective_line_total_float(item)
            if lt is not None:
                line_sum += lt
        
        # Get total amount
        total_amount = data.get('total_amount', 0.0)
        if not isinstance(total_amount, (int, float)):
            total_amount = 0.0
        
        # Calculate tolerance
        config = get_ocr_config()
        tolerance = config.calculate_arithmetic_tolerance(total_amount)
        
        # Check if difference is within tolerance
        difference = abs(line_sum - total_amount)
        if difference > tolerance:
            issues.append(ValidationIssue(
                issue_type='ARITHMETIC_MISMATCH',
                severity='error',
                message=f'Line sum ({line_sum:.2f}) does not match total ({total_amount:.2f}). Difference: {difference:.2f}',
                details={
                    'line_sum': line_sum,
                    'total_amount': total_amount,
                    'difference': difference,
                    'tolerance': tolerance
                },
                field='total_amount'
            ))
            return False, issues
        
        return True, issues
    
    def _is_meta_row(self, item: Dict[str, Any]) -> bool:
        """Check if a line item is a meta row (change, cash, card, void, refund, etc.)"""
        description = str(item.get('description', '')).lower()
        
        # Get ignore patterns from config
        config = get_ocr_config()
        ignore_patterns = config.get_validation("ignore_receipt_meta_rows")
        
        for pattern in ignore_patterns:
            if pattern.lower() in description:
                return True
        
        return False
    
    def _effective_line_total_float(self, row: Dict[str, Any]) -> Optional[float]:
        """Calculate effective line total from quantity and unit price if line_total is missing (float version)"""
        if row.get('line_total') is not None:
            return self._extract_amount(row['line_total'])
        if row.get('quantity') is not None and row.get('unit_price') is not None:
            try: 
                qty = self._extract_amount(row['quantity'])
                price = self._extract_amount(row['unit_price'])
                if qty > 0 and price > 0:
                    return qty * price
            except: 
                pass
        return None
    
    def _extract_amount(self, value: Any) -> float:
        """Extract numeric amount from various formats"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[£$€,\s]', '', value)
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        return 0.0
    
    def _validate_currency(self, data: Dict[str, Any], ocr_text: str) -> Tuple[bool, List[ValidationIssue]]:
        """Validate currency consistency across the document"""
        issues = []
        
        try:
            # Extract currency information
            document_currency = data.get('currency', '').upper()
            line_items = data.get('line_items', [])
            
            # Check for currency symbols in OCR text
            detected_currencies = self._detect_currencies_in_text(ocr_text)
            
            # Validate document currency
            if document_currency and document_currency not in self.config['currency']['allowed_currencies']:
                issues.append(ValidationIssue(
                    issue_type='INVALID_CURRENCY',
                    severity='error',
                    message=f"Invalid currency code: {document_currency}",
                    details={
                        'detected_currency': document_currency,
                        'allowed_currencies': self.config['currency']['allowed_currencies']
                    },
                    field='currency'
                ))
            
            # Check currency consistency in line items
            if self.config['currency']['require_consistency']:
                line_currencies = set()
                for item in line_items:
                    item_currency = item.get('currency', '').upper()
                    if item_currency:
                        line_currencies.add(item_currency)
                
                if len(line_currencies) > 1:
                    issues.append(ValidationIssue(
                        issue_type='CURRENCY_INCONSISTENCY',
                        severity='error',
                        message="Multiple currencies detected in line items",
                        details={
                            'line_currencies': list(line_currencies),
                            'document_currency': document_currency
                        },
                        field='currency'
                    ))
                
                # Check if line item currencies match document currency
                if document_currency and line_currencies:
                    for line_currency in line_currencies:
                        if line_currency != document_currency:
                            issues.append(ValidationIssue(
                                issue_type='CURRENCY_MISMATCH',
                                severity='warning',
                                message=f"Line item currency ({line_currency}) doesn't match document currency ({document_currency})",
                                details={
                                    'line_currency': line_currency,
                                    'document_currency': document_currency
                                },
                                field='currency'
                            ))
            
            # Check for currency symbol consistency
            if detected_currencies and document_currency:
                expected_symbols = self.currency_patterns.get(document_currency, [])
                if detected_currencies and not any(symbol in detected_currencies for symbol in expected_symbols):
                    issues.append(ValidationIssue(
                        issue_type='CURRENCY_SYMBOL_MISMATCH',
                        severity='warning',
                        message=f"Currency symbols in text don't match declared currency ({document_currency})",
                        details={
                            'detected_symbols': detected_currencies,
                            'expected_symbols': expected_symbols,
                            'document_currency': document_currency
                        },
                        field='currency'
                    ))
                    
        except Exception as e:
            logger.error(f"Currency validation error: {e}")
            issues.append(ValidationIssue(
                issue_type='CURRENCY_VALIDATION_ERROR',
                severity='error',
                message=f"Currency validation failed: {str(e)}",
                details={'error': str(e)},
                field='currency'
            ))
        
        return len([i for i in issues if i.severity == 'error']) == 0, issues
    
    def _validate_dates(self, data: Dict[str, Any]) -> Tuple[bool, List[ValidationIssue]]:
        """Validate dates in the document"""
        issues = []
        
        # Get date from data
        invoice_date = data.get('date', '')
        if not invoice_date:
            return True, issues  # No date to validate
        
        try:
            # Parse date using UK format (DMY)
            parsed_date = self._parse_date_uk(invoice_date)
            if not parsed_date:
                issues.append(ValidationIssue(
                    issue_type='INVALID_DATE_FORMAT',
                    severity='warning',
                    message=f'Could not parse date: {invoice_date}',
                    details={
                        'expected': 'DD/MM/YYYY format',
                        'actual': invoice_date
                    },
                    field='date'
                ))
                return False, issues
            
            # Convert to date object for comparison
            parsed_date = parsed_date.date()
            
            # Get current date in UK timezone
            tz = zoneinfo.ZoneInfo("Europe/London")
            today = datetime.now(tz).date()
            
            # Check if date is in the future
            max_future_days = 3  # Default value
            try:
                config = get_ocr_config()
                max_future_days = config.get_threshold("future_date_days")
            except:
                pass  # Use default if config fails
            
            days_diff = (parsed_date - today).days
            
            if days_diff > max_future_days:
                issues.append(ValidationIssue(
                    issue_type='FUTURE_DATE',
                    severity='error',
                    message=f'Date {invoice_date} is {days_diff} days in the future (max allowed: {max_future_days})',
                    details={
                        'expected': f'Date not more than {max_future_days} days in future',
                        'actual': invoice_date,
                        'days_diff': days_diff
                    },
                    field='date'
                ))
                return False, issues
            
            # Check if date is too far in the past (optional)
            max_past_days = 365 * 2  # 2 years
            if days_diff < -max_past_days:
                issues.append(ValidationIssue(
                    issue_type='PAST_DATE',
                    severity='warning',
                    message=f'Date {invoice_date} is {abs(days_diff)} days in the past',
                    details={
                        'invoice_date': invoice_date,
                        'days_diff': days_diff,
                        'max_past_days': max_past_days
                    },
                    field='date'
                ))
            
            return True, issues
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_type='DATE_PARSE_ERROR',
                severity='error',
                message=f'Error parsing date {invoice_date}: {str(e)}',
                details={
                    'invoice_date': invoice_date,
                    'error': str(e)
                },
                field='date'
            ))
            return False, issues
    
    def _validate_vat(self, data: Dict[str, Any]) -> Tuple[bool, List[ValidationIssue]]:
        """Validate VAT calculations and VAT numbers"""
        issues = []
        
        try:
            # Check VAT rate consistency
            vat_rate = data.get('vat_rate')
            vat_amount = self._extract_amount(data.get('vat_amount', 0))
            subtotal = self._extract_amount(data.get('subtotal', 0))
            
            if vat_rate is not None and subtotal > 0:
                expected_vat = subtotal * float(vat_rate)
                vat_diff = abs(vat_amount - expected_vat)
                vat_tolerance = self.config['vat']['tolerance_percent']
                
                if vat_amount > 0 and vat_diff / max(vat_amount, 0.01) > vat_tolerance:
                    issues.append(ValidationIssue(
                        issue_type='VAT_RATE_MISMATCH',
                        severity='warning',
                        message=f"VAT amount doesn't match VAT rate calculation",
                        details={
                            'vat_rate': vat_rate,
                            'subtotal': subtotal,
                            'extracted_vat': vat_amount,
                            'expected_vat': expected_vat,
                            'difference': vat_diff,
                            'tolerance': vat_tolerance
                        },
                        field='vat_amount'
                    ))
            
            # Validate VAT numbers if present
            if self.config['vat']['validate_vat_numbers']:
                vat_number = data.get('vat_number', '')
                if vat_number:
                    if not self._validate_vat_number(vat_number):
                        issues.append(ValidationIssue(
                            issue_type='INVALID_VAT_NUMBER',
                            severity='warning',
                            message=f"Invalid VAT number format: {vat_number}",
                            details={'vat_number': vat_number},
                            field='vat_number'
                        ))
                        
        except Exception as e:
            logger.error(f"VAT validation error: {e}")
            issues.append(ValidationIssue(
                issue_type='VAT_VALIDATION_ERROR',
                severity='error',
                message=f"VAT validation failed: {str(e)}",
                details={'error': str(e)},
                field='vat_amount'
            ))
        
        return len([i for i in issues if i.severity == 'error']) == 0, issues
    
    def _validate_supplier(self, data: Dict[str, Any]) -> Tuple[bool, List[ValidationIssue]]:
        """Validate supplier information"""
        issues = []
        
        supplier_name = data.get('supplier', '')
        
        # Basic validation - just check if supplier name exists and has reasonable length
        if not supplier_name or len(supplier_name.strip()) < 3:
            issues.append(ValidationIssue(
                issue_type='MISSING_SUPPLIER',
                severity='warning',
                message='Supplier name is missing or too short',
                details={
                    'supplier_name': supplier_name,
                    'min_length': 3
                },
                field='supplier'
            ))
            return False, issues
        
        return True, issues
    
    def _detect_currencies_in_text(self, text: str) -> List[str]:
        """Detect currency symbols in text"""
        detected = []
        for currency, patterns in self.currency_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detected.append(pattern)
        return detected
    
    def _parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse date string into datetime object"""
        for pattern in self.date_patterns:
            match = re.search(pattern, date_string, re.IGNORECASE)
            if match:
                try:
                    if 'Jan|Feb|Mar' in pattern:
                        # DD MMM YYYY format
                        day, month, year = match.groups()
                        month_map = {
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }
                        month_num = month_map[month.lower()]
                        year = int(year) if len(year) == 4 else 2000 + int(year)
                        return datetime(int(year), month_num, int(day))
                    else:
                        # DD/MM/YYYY or YYYY/MM/DD format
                        groups = match.groups()
                        if len(groups[0]) == 4:  # YYYY/MM/DD
                            return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                        else:  # DD/MM/YYYY
                            year = int(groups[2]) if len(groups[2]) == 4 else 2000 + int(groups[2])
                            return datetime(year, int(groups[1]), int(groups[0]))
                except (ValueError, IndexError):
                    continue
        return None
    
    def _parse_date_uk(self, date_string: str) -> Optional[datetime]:
        """Parse date string with UK day-first format"""
        for pattern in self.date_patterns:
            match = re.search(pattern, date_string, re.IGNORECASE)
            if match:
                try:
                    if 'Jan|Feb|Mar' in pattern:
                        # DD MMM YYYY format
                        day, month, year = match.groups()
                        month_map = {
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }
                        month_num = month_map[month.lower()]
                        year = int(year) if len(year) == 4 else 2000 + int(year)
                        return datetime(int(year), month_num, int(day))
                    else:
                        # DD/MM/YYYY or YYYY/MM/DD format
                        groups = match.groups()
                        if len(groups[0]) == 4:  # YYYY/MM/DD
                            return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                        else:  # DD/MM/YYYY (UK format)
                            year = int(groups[2]) if len(groups[2]) == 4 else 2000 + int(groups[2])
                            return datetime(year, int(groups[1]), int(groups[0]))
                except (ValueError, IndexError):
                    continue
        return None
    
    def _validate_vat_number(self, vat_number: str) -> bool:
        """Validate VAT number format"""
        # Remove spaces and convert to uppercase
        vat_number = re.sub(r'\s', '', vat_number.upper())
        
        # Check UK VAT number format
        if re.match(self.vat_patterns['UK'], vat_number):
            return True
        
        # Check EU VAT number format
        if re.match(self.vat_patterns['EU'], vat_number):
            return True
        
        return False
    
    def _calculate_validation_confidence(self, issues: List[ValidationIssue]) -> float:
        """Calculate confidence based on validation issues"""
        if not issues:
            return 1.0
        
        # Count issues by severity
        error_count = len([i for i in issues if i.severity == 'error'])
        warning_count = len([i for i in issues if i.severity == 'warning'])
        info_count = len([i for i in issues if i.severity == 'info'])
        
        # Calculate confidence (errors have highest penalty)
        confidence = 1.0
        confidence -= error_count * 0.3
        confidence -= warning_count * 0.1
        confidence -= info_count * 0.05
        
        return max(0.0, min(1.0, confidence))

# Global validator instance
_validator = None

def get_document_validator(config: Optional[Dict] = None) -> DocumentValidator:
    """Get or create global document validator instance"""
    global _validator
    if _validator is None:
        _validator = DocumentValidator(config)
    return _validator

def validate_document(extracted_data: Dict[str, Any], ocr_text: str = "", config: Optional[Dict] = None) -> ValidationResult:
    """Convenience function to validate a document"""
    validator = get_document_validator(config)
    return validator.validate_document(extracted_data, ocr_text) 