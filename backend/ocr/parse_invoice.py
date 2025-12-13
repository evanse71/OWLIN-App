"""
Invoice Template Parser

This module provides comprehensive invoice parsing functionality with structured output.
It uses heuristic parsing with regular expressions and pattern matching to extract
invoice metadata including supplier, dates, totals, and line items.

Key Features:
- Supplier name inference from top-of-page bounding boxes
- Date recognition with multiple format support
- Net/VAT/Gross total detection
- Line item detection and parsing
- Confidence scoring for extracted data
- Structured output with dataclasses

Author: OWLIN Development Team
Version: 1.0.0
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .field_extractor import extract_invoice_fields

logger = logging.getLogger(__name__)

@dataclass
class LineItem:
    """Individual line item from invoice"""
    description: str
    quantity: float
    unit_price: float
    total_price: float
    confidence: float = 0.0

@dataclass
class ParsedInvoice:
    """Structured invoice data with confidence scoring"""
    invoice_number: str
    date: str
    supplier: str
    net_total: float
    vat_total: float
    gross_total: float
    line_items: List[LineItem]
    confidence: float
    currency: str = "GBP"
    vat_rate: Optional[float] = None

def parse_invoice(text: str, overall_confidence: float = 0.0, ocr_results: Optional[List[Dict[str, Any]]] = None) -> ParsedInvoice:
    """
    Parse invoice text and extract structured data
    
    Args:
        text: Full OCR text from invoice
        overall_confidence: Overall OCR confidence score
        ocr_results: Optional OCR results with bounding boxes for enhanced field extraction
        
    Returns:
        ParsedInvoice object with extracted data
    """
    try:
        logger.info("🔄 Starting invoice parsing")
        
        # Split text into lines for analysis
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Extract basic fields using traditional parsing
        invoice_number = extract_invoice_number(lines)
        date = extract_invoice_date(lines)
        supplier = extract_supplier_name(lines)
        
        # Extract totals
        net_total, vat_total, gross_total = extract_totals(lines)
        
        # Extract line items
        line_items = extract_line_items(lines)

        # Totals reconciliation: if close, adjust to sum of lines
        try:
            sum_lines = sum(float(li.total_price if hasattr(li, 'total_price') else li.get('line_total', 0.0)) for li in line_items)
            if gross_total and sum_lines:
                diff = abs(sum_lines - gross_total)
                if (diff / max(1.0, gross_total)) < 0.015:
                    gross_total = sum_lines
        except Exception:
            pass
        
        # Determine currency
        currency = extract_currency(lines)
        
        # Calculate VAT rate if possible
        vat_rate = calculate_vat_rate(net_total, vat_total)
        
        # Enhanced field extraction using field_extractor if OCR results are available
        if ocr_results:
            logger.info("🔍 Using enhanced field extraction with OCR results")
            try:
                field_extraction_result = extract_invoice_fields(ocr_results)
                
                # Use field extractor results to validate and improve our parsing
                field_supplier = field_extraction_result.get('supplier_name', 'Unknown')
                field_invoice_number = field_extraction_result.get('invoice_number', 'Unknown')
                field_date = field_extraction_result.get('invoice_date', 'Unknown')
                field_net = field_extraction_result.get('net_amount', 'Unknown')
                field_vat = field_extraction_result.get('vat_amount', 'Unknown')
                field_total = field_extraction_result.get('total_amount', 'Unknown')
                field_currency = field_extraction_result.get('currency', 'Unknown')
                
                # Confidence scores from field extractor
                confidence_scores = field_extraction_result.get('confidence_scores', {})
                
                # Use field extractor results if they have higher confidence or our parsing failed
                if field_supplier != 'Unknown' and supplier == 'Unknown Supplier':
                    supplier = field_supplier
                    logger.info(f"✅ Enhanced supplier extraction: {supplier}")
                
                if field_invoice_number != 'Unknown' and invoice_number == 'Unknown':
                    invoice_number = field_invoice_number
                    logger.info(f"✅ Enhanced invoice number extraction: {invoice_number}")
                
                if field_date != 'Unknown' and date == 'Unknown':
                    date = field_date
                    logger.info(f"✅ Enhanced date extraction: {date}")
                
                # Use field extractor monetary values if they're valid numbers
                if isinstance(field_net, (int, float)) and net_total == 0.0:
                    net_total = float(field_net)
                    logger.info(f"✅ Enhanced net total extraction: £{net_total:.2f}")
                
                if isinstance(field_vat, (int, float)) and vat_total == 0.0:
                    vat_total = float(field_vat)
                    logger.info(f"✅ Enhanced VAT total extraction: £{vat_total:.2f}")
                
                if isinstance(field_total, (int, float)) and gross_total == 0.0:
                    gross_total = float(field_total)
                    logger.info(f"✅ Enhanced gross total extraction: £{gross_total:.2f}")
                
                if field_currency != 'Unknown' and currency == 'GBP':
                    currency = field_currency
                    logger.info(f"✅ Enhanced currency extraction: {currency}")
                
                # Check for warnings from field extractor
                warnings = field_extraction_result.get('warnings', [])
                if warnings:
                    logger.warning(f"⚠️ Field extraction warnings: {warnings}")
                
            except Exception as e:
                logger.warning(f"⚠️ Enhanced field extraction failed: {e}, using traditional parsing")
        
        # Calculate parsing confidence
        parsing_confidence = calculate_parsing_confidence(
            invoice_number, date, supplier, net_total, gross_total, line_items
        )
        
        result = ParsedInvoice(
            invoice_number=invoice_number,
            date=date,
            supplier=supplier,
            net_total=net_total,
            vat_total=vat_total,
            gross_total=gross_total,
            line_items=line_items,
            confidence=parsing_confidence,
            currency=currency,
            vat_rate=vat_rate
        )
        
        logger.info(f"✅ Invoice parsing completed: {supplier}, {invoice_number}, £{gross_total:.2f}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Invoice parsing failed: {e}")
        # Return default invoice with error information
        return ParsedInvoice(
            invoice_number="Unknown",
            date="Unknown",
            supplier="Unknown Supplier",
            net_total=0.0,
            vat_total=0.0,
            gross_total=0.0,
            line_items=[],
            confidence=0.0
        )

def extract_invoice_number(lines: List[str]) -> str:
    """
    Extract invoice number using regex patterns
    
    Args:
        lines: List of text lines
        
    Returns:
        Extracted invoice number or "Unknown"
    """
    # Invoice number patterns
    patterns = [
        r'invoice\s*#?\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'invoice\s*number\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'inv\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'bill\s*#?\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'reference\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'ref\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'order\s*#?\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
    ]
    
    for line in lines:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                invoice_num = match.group(1).strip()
                if invoice_num and len(invoice_num) > 2:
                    logger.debug(f"📄 Found invoice number: {invoice_num}")
                    return invoice_num
    
    logger.warning("⚠️ No invoice number found")
    return "Unknown"

def extract_invoice_date(lines: List[str]) -> str:
    """
    Extract invoice date using multiple format patterns
    
    Args:
        lines: List of text lines
        
    Returns:
        Extracted date in YYYY-MM-DD format or "Unknown"
    """
    # Date patterns
    date_patterns = [
        # DD/MM/YYYY or DD-MM-YYYY
        r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
        # MM/DD/YYYY or MM-DD-YYYY
        r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
        # YYYY-MM-DD
        r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})',
        # DD Month YYYY
        r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{4})',
        # Month DD, YYYY
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{1,2}),?\s+(\d{4})',
    ]
    
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    for line in lines:
        # Look for date keywords
        if any(keyword in line.lower() for keyword in ['date', 'issued', 'created', 'invoice date']):
            for pattern in date_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        groups = match.groups()
                        if len(groups) == 3:
                            if groups[0].isdigit() and len(groups[0]) == 4:
                                # YYYY-MM-DD format
                                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                            elif groups[2].isdigit() and len(groups[2]) == 4:
                                # DD/MM/YYYY or MM/DD/YYYY format
                                if int(groups[0]) > 12:
                                    # DD/MM/YYYY
                                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                                else:
                                    # MM/DD/YYYY
                                    month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                            else:
                                # Month DD, YYYY format
                                month_name, day, year = groups[0], int(groups[1]), int(groups[2])
                                month = month_map.get(month_name.lower()[:3], 1)
                            
                            # Validate date
                            if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                                logger.debug(f"📅 Found invoice date: {date_str}")
                                return date_str
                    except (ValueError, IndexError):
                        continue
    
    logger.warning("⚠️ No invoice date found")
    return "Unknown"

def extract_supplier_name(lines: List[str]) -> str:
    """
    Extract supplier name from top-of-page text with supplier lexicon boost.
    """
    top_lines = lines[:10]
    supplier_keywords = ['ltd', 'limited', 'plc', 'company', 'co', 'corp', 'corporation']

    # Load supplier lexicons
    aliases: Dict[str, List[str]] = {}
    try:
        import json, os
        with open(os.path.join('data', 'config', 'supplier_lexicons.json'), 'r') as f:
            aliases = json.load(f)
    except Exception:
        aliases = {}

    def canonicalize(name: str) -> Optional[str]:
        n = name.lower().strip()
        # Direct match
        for canon, alist in aliases.items():
            if n == canon:
                return canon
            for a in alist:
                if n == a.lower():
                    return canon
        # Token contain match
        for canon, alist in aliases.items():
            if any(a.lower() in n for a in alist):
                return canon
        return None

    # Heuristic search
    for line in top_lines:
        if any(skip in line.lower() for skip in ['invoice', 'bill', 'total', 'amount', 'date', 'page']):
            continue
        candidate = None
        if any(keyword in line.lower() for keyword in supplier_keywords):
            candidate = re.sub(r'[^\w\s\-&]', '', line).strip()
        elif re.search(r'[A-Z][a-z]+\s+(Ltd|Limited|PLC|Company|Corp)', line):
            candidate = re.sub(r'[^\w\s\-&]', '', line).strip()
        if candidate and len(candidate) > 3:
            canon = canonicalize(candidate) or candidate
            logger.debug(f"🏢 Found supplier: {canon}")
            return canon

    for line in top_lines[:5]:
        if len(line) > 5 and line[0].isupper() and not any(skip in line.lower() for skip in ['invoice', 'bill', 'total']):
            candidate = re.sub(r'[^\w\s\-&]', '', line).strip()
            canon = canonicalize(candidate) or candidate
            if len(canon) > 3:
                logger.debug(f"🏢 Found supplier (fallback): {canon}")
                return canon

    logger.warning("⚠️ No supplier name found")
    return "Unknown Supplier"

def extract_totals(lines: List[str]) -> Tuple[float, float, float]:
    """
    Extract net, VAT, and gross totals from invoice
    
    Args:
        lines: List of text lines
        
    Returns:
        Tuple of (net_total, vat_total, gross_total)
    """
    net_total = 0.0
    vat_total = 0.0
    gross_total = 0.0
    
    # Find all monetary values
    money_values = []
    for line in lines:
        # Look for currency amounts
        amounts = re.findall(r'[£$€]?\s*(\d+[,\d]*\.?\d*)', line)
        for amount in amounts:
            try:
                # Clean up amount string
                clean_amount = amount.replace(',', '')
                value = float(clean_amount)
                money_values.append((value, line.lower()))
            except ValueError:
                continue
    
    if not money_values:
        return net_total, vat_total, gross_total
    
    # Sort by value (largest first)
    money_values.sort(key=lambda x: x[0], reverse=True)
    
    # Extract totals based on context
    for value, line in money_values:
        line_lower = line.lower()
        
        # Gross total (usually the largest amount)
        if any(keyword in line_lower for keyword in ['total', 'amount due', 'grand total', 'sum']):
            if gross_total == 0.0:
                gross_total = value
                logger.debug(f"💰 Found gross total: £{value:.2f}")
        
        # VAT total
        elif any(keyword in line_lower for keyword in ['vat', 'tax', 'gst']):
            if vat_total == 0.0:
                vat_total = value
                logger.debug(f"💰 Found VAT total: £{value:.2f}")
        
        # Net total
        elif any(keyword in line_lower for keyword in ['net', 'subtotal', 'amount']):
            if net_total == 0.0:
                net_total = value
                logger.debug(f"💰 Found net total: £{value:.2f}")
    
    # If we found gross but not net, estimate net
    if gross_total > 0 and net_total == 0:
        net_total = gross_total - vat_total
    
    # If we found net but not gross, estimate gross
    if net_total > 0 and gross_total == 0:
        gross_total = net_total + vat_total
    
    # If we only found one total, use it as gross
    if gross_total == 0 and net_total == 0 and vat_total == 0 and money_values:
        gross_total = money_values[0][0]
        logger.debug(f"💰 Using largest amount as gross total: £{gross_total:.2f}")
    
    return net_total, vat_total, gross_total

def extract_line_items(lines: List[str]) -> List[LineItem]:
    """
    Extract line items from invoice text
    
    Args:
        lines: List of text lines
        
    Returns:
        List of LineItem objects
    """
    line_items = []
    
    # Look for line item patterns
    for i, line in enumerate(lines):
        # Skip header lines
        if i < 5:  # Skip first few lines (likely headers)
            continue
        
        # Look for line item patterns
        line_item = extract_single_line_item(line)
        if line_item:
            line_items.append(line_item)
    
    logger.debug(f"📋 Found {len(line_items)} line items")
    return line_items

def extract_single_line_item(line: str) -> Optional[LineItem]:
    """
    Extract a single line item from a text line
    
    Args:
        line: Text line to parse
        
    Returns:
        LineItem object or None if not a line item
    """
    # Skip lines that are likely not line items
    if any(skip in line.lower() for skip in ['total', 'subtotal', 'vat', 'tax', 'invoice', 'page']):
        return None
    
    # Look for quantity patterns
    quantity_patterns = [
        r'(\d+)\s*x\s*[£$€]?\s*(\d+\.?\d*)',  # "2 x £10.50"
        r'(\d+)\s*@\s*[£$€]?\s*(\d+\.?\d*)',  # "2 @ £10.50"
        r'qty\s*:\s*(\d+)',                     # "Qty: 2"
        r'quantity\s*:\s*(\d+)',                # "Quantity: 2"
    ]
    
    quantity = 1.0
    unit_price = 0.0
    total_price = 0.0
    description = ""
    
    # Try to extract quantity and unit price
    for pattern in quantity_patterns:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            try:
                quantity = float(match.group(1))
                if len(match.groups()) > 1:
                    unit_price = float(match.group(2))
                break
            except ValueError:
                continue
    
    # Look for total price
    price_match = re.search(r'[£$€]?\s*(\d+\.?\d*)', line)
    if price_match:
        try:
            total_price = float(price_match.group(1))
        except ValueError:
            pass
    
    # Extract description (everything except quantities and prices)
    description = re.sub(r'\d+\s*x\s*[£$€]?\s*\d+\.?\d*', '', line)
    description = re.sub(r'\d+\s*@\s*[£$€]?\s*\d+\.?\d*', '', description)
    description = re.sub(r'qty\s*:\s*\d+', '', description)
    description = re.sub(r'quantity\s*:\s*\d+', '', description)
    description = re.sub(r'[£$€]?\s*\d+\.?\d*', '', description)
    description = description.strip()
    
    # Only return if we have a meaningful description
    if description and len(description) > 3:
        # Calculate unit price if not found
        if unit_price == 0.0 and total_price > 0 and quantity > 0:
            unit_price = total_price / quantity
        
        # Calculate total price if not found
        if total_price == 0.0 and unit_price > 0 and quantity > 0:
            total_price = unit_price * quantity
        
        return LineItem(
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            confidence=0.8  # Default confidence for line items
        )
    
    return None

def extract_currency(lines: List[str]) -> str:
    """
    Extract currency from invoice text
    
    Args:
        lines: List of text lines
        
    Returns:
        Currency code (GBP, USD, EUR, etc.)
    """
    for line in lines:
        if '£' in line:
            return "GBP"
        elif '$' in line:
            return "USD"
        elif '€' in line:
            return "EUR"
    
    return "GBP"  # Default to GBP

def calculate_vat_rate(net_total: float, vat_total: float) -> Optional[float]:
    """
    Calculate VAT rate from net and VAT totals
    
    Args:
        net_total: Net total amount
        vat_total: VAT total amount
        
    Returns:
        VAT rate as percentage or None if cannot calculate
    """
    if net_total > 0 and vat_total > 0:
        try:
            vat_rate = (vat_total / net_total) * 100
            # Round to common VAT rates
            common_rates = [0, 5, 20, 21, 22, 23]
            closest_rate = min(common_rates, key=lambda x: abs(x - vat_rate))
            if abs(closest_rate - vat_rate) < 2:  # Within 2% tolerance
                return closest_rate
        except (ZeroDivisionError, ValueError):
            pass
    
    return None

def calculate_parsing_confidence(invoice_number: str, date: str, supplier: str, 
                               net_total: float, gross_total: float, 
                               line_items: List[LineItem]) -> float:
    """
    Calculate confidence score for parsed invoice data
    
    Args:
        invoice_number: Extracted invoice number
        date: Extracted date
        supplier: Extracted supplier name
        net_total: Net total amount
        gross_total: Gross total amount
        line_items: List of line items
        
    Returns:
        Confidence score (0.0 to 1.0)
    """
    confidence = 0.0
    total_fields = 0
    
    # Invoice number confidence
    if invoice_number != "Unknown":
        confidence += 0.2
    total_fields += 1
    
    # Date confidence
    if date != "Unknown":
        confidence += 0.2
    total_fields += 1
    
    # Supplier confidence
    if supplier != "Unknown Supplier":
        confidence += 0.2
    total_fields += 1
    
    # Totals confidence
    if gross_total > 0:
        confidence += 0.2
    total_fields += 1
    
    # Line items confidence
    if line_items:
        confidence += 0.2
    total_fields += 1
    
    # Normalize to 0-1 scale
    if total_fields > 0:
        confidence = confidence / total_fields
    
    return round(confidence, 3) 