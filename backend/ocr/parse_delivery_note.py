"""
Delivery Note Template Parser

This module provides comprehensive delivery note parsing functionality with structured output.
It uses heuristic parsing with regular expressions and pattern matching to extract
delivery note metadata including supplier, dates, and line items.

Key Features:
- Supplier name inference from top-of-page bounding boxes
- Date recognition with multiple format support
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

logger = logging.getLogger(__name__)

@dataclass
class DeliveryLineItem:
    """Individual line item from delivery note"""
    description: str
    quantity: Optional[float]
    unit: Optional[str] = None
    confidence: float = 0.0

@dataclass
class ParsedDeliveryNote:
    """Structured delivery note data with confidence scoring"""
    delivery_number: str
    date: str
    supplier: str
    line_items: List[DeliveryLineItem]
    confidence: float
    total_items: Optional[int] = None
    delivery_address: Optional[str] = None
    received_by: Optional[str] = None

def parse_delivery_note(text: str, overall_confidence: float = 0.0) -> ParsedDeliveryNote:
    """
    Parse delivery note text and extract structured data
    
    Args:
        text: Full OCR text from delivery note
        overall_confidence: Overall OCR confidence score
        
    Returns:
        ParsedDeliveryNote object with extracted data
    """
    try:
        logger.info("🔄 Starting delivery note parsing")
        
        # Split text into lines for analysis
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Extract basic fields
        delivery_number = extract_delivery_number(lines)
        date = extract_delivery_date(lines)
        supplier = extract_supplier_name(lines)
        
        # Extract line items
        line_items = extract_delivery_line_items(lines)
        
        # Extract additional fields
        delivery_address = extract_delivery_address(lines)
        received_by = extract_received_by(lines)
        total_items = len(line_items)
        
        # Calculate parsing confidence
        parsing_confidence = calculate_parsing_confidence(
            delivery_number, date, supplier, line_items
        )
        
        result = ParsedDeliveryNote(
            delivery_number=delivery_number,
            date=date,
            supplier=supplier,
            line_items=line_items,
            confidence=parsing_confidence,
            total_items=total_items,
            delivery_address=delivery_address,
            received_by=received_by
        )
        
        logger.info(f"✅ Delivery note parsing completed: {supplier}, {delivery_number}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Delivery note parsing failed: {e}")
        # Return default delivery note with error information
        return ParsedDeliveryNote(
            delivery_number="Unknown",
            date="Unknown",
            supplier="Unknown Supplier",
            line_items=[],
            confidence=0.0
        )

def extract_delivery_number(lines: List[str]) -> str:
    """
    Extract delivery note number using regex patterns
    
    Args:
        lines: List of text lines
        
    Returns:
        Extracted delivery number or "Unknown"
    """
    # Delivery number patterns
    patterns = [
        r'delivery\s*note\s*#?\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'delivery\s*number\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'dn\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'pod\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'reference\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'ref\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
        r'order\s*#?\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
    ]
    
    for line in lines:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                delivery_num = match.group(1).strip()
                if delivery_num and len(delivery_num) > 2:
                    logger.debug(f"📄 Found delivery number: {delivery_num}")
                    return delivery_num
    
    logger.warning("⚠️ No delivery number found")
    return "Unknown"

def extract_delivery_date(lines: List[str]) -> str:
    """
    Extract delivery date using multiple format patterns
    
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
        # Look for delivery date keywords
        if any(keyword in line.lower() for keyword in ['delivery date', 'date', 'delivered', 'received']):
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
                                logger.debug(f"📅 Found delivery date: {date_str}")
                                return date_str
                    except (ValueError, IndexError):
                        continue
    
    logger.warning("⚠️ No delivery date found")
    return "Unknown"

def extract_supplier_name(lines: List[str]) -> str:
    """
    Extract supplier name from top-of-page text
    
    Args:
        lines: List of text lines
        
    Returns:
        Extracted supplier name or "Unknown Supplier"
    """
    # Look for supplier in first few lines (top of page)
    top_lines = lines[:10]
    
    # Common supplier keywords
    supplier_keywords = ['ltd', 'limited', 'plc', 'company', 'co', 'corp', 'corporation']
    
    for line in top_lines:
        # Skip lines that are likely not supplier names
        if any(skip in line.lower() for skip in ['delivery note', 'pod', 'received', 'date', 'page']):
            continue
        
        # Check if line contains supplier keywords
        if any(keyword in line.lower() for keyword in supplier_keywords):
            # Clean up the line
            supplier = re.sub(r'[^\w\s\-&]', '', line).strip()
            if len(supplier) > 3:
                logger.debug(f"🏢 Found supplier: {supplier}")
                return supplier
        
        # Check for company-like patterns
        if re.search(r'[A-Z][a-z]+\s+(Ltd|Limited|PLC|Company|Corp)', line):
            supplier = re.sub(r'[^\w\s\-&]', '', line).strip()
            if len(supplier) > 3:
                logger.debug(f"🏢 Found supplier: {supplier}")
                return supplier
    
    # Fallback: look for any capitalized line that might be a company name
    for line in top_lines[:5]:
        if len(line) > 5 and line[0].isupper() and not any(skip in line.lower() for skip in ['delivery note', 'pod', 'received']):
            supplier = re.sub(r'[^\w\s\-&]', '', line).strip()
            if len(supplier) > 3:
                logger.debug(f"🏢 Found supplier (fallback): {supplier}")
                return supplier
    
    logger.warning("⚠️ No supplier name found")
    return "Unknown Supplier"

def extract_delivery_line_items(lines: List[str]) -> List[DeliveryLineItem]:
    """
    Extract line items from delivery note text
    
    Args:
        lines: List of text lines
        
    Returns:
        List of DeliveryLineItem objects
    """
    line_items = []
    
    # Look for line item patterns
    for i, line in enumerate(lines):
        # Skip header lines
        if i < 5:  # Skip first few lines (likely headers)
            continue
        
        # Look for line item patterns
        line_item = extract_single_delivery_line_item(line)
        if line_item:
            line_items.append(line_item)
    
    logger.debug(f"📋 Found {len(line_items)} delivery line items")
    return line_items

def extract_single_delivery_line_item(line: str) -> Optional[DeliveryLineItem]:
    """
    Extract a single line item from a text line
    
    Args:
        line: Text line to parse
        
    Returns:
        DeliveryLineItem object or None if not a line item
    """
    # Skip lines that are likely not line items
    if any(skip in line.lower() for skip in ['delivery note', 'pod', 'received', 'page', 'total']):
        return None
    
    # Look for quantity patterns
    quantity_patterns = [
        r'(\d+)\s*x\s*([A-Za-z\s]+)',  # "2 x Product Name"
        r'(\d+)\s*@\s*([A-Za-z\s]+)',  # "2 @ Product Name"
        r'qty\s*:\s*(\d+)',             # "Qty: 2"
        r'quantity\s*:\s*(\d+)',        # "Quantity: 2"
        r'(\d+)\s+([A-Za-z\s]+)',      # "2 Product Name"
    ]
    
    quantity = None
    description = ""
    
    # Try to extract quantity and description
    for pattern in quantity_patterns:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            try:
                quantity = float(match.group(1))
                if len(match.groups()) > 1:
                    description = match.group(2).strip()
                break
            except ValueError:
                continue
    
    # If no quantity pattern found, try to extract description only
    if not description:
        # Remove common delivery note keywords
        description = re.sub(r'\b(delivered|received|checked|verified)\b', '', line, flags=re.IGNORECASE)
        description = description.strip()
    
    # Only return if we have a meaningful description
    if description and len(description) > 3:
        return DeliveryLineItem(
            description=description,
            quantity=quantity,
            confidence=0.8  # Default confidence for line items
        )
    
    return None

def extract_delivery_address(lines: List[str]) -> Optional[str]:
    """
    Extract delivery address from delivery note
    
    Args:
        lines: List of text lines
        
    Returns:
        Extracted delivery address or None
    """
    address_keywords = ['delivery address', 'ship to', 'deliver to', 'address']
    
    for line in lines:
        if any(keyword in line.lower() for keyword in address_keywords):
            # Extract address after keyword
            for keyword in address_keywords:
                if keyword in line.lower():
                    address = line.lower().split(keyword)[-1].strip()
                    if address and len(address) > 10:
                        logger.debug(f"📍 Found delivery address: {address}")
                        return address
    
    return None

def extract_received_by(lines: List[str]) -> Optional[str]:
    """
    Extract received by information from delivery note
    
    Args:
        lines: List of text lines
        
    Returns:
        Extracted received by information or None
    """
    received_keywords = ['received by', 'signed by', 'delivered to', 'accepted by']
    
    for line in lines:
        if any(keyword in line.lower() for keyword in received_keywords):
            # Extract name after keyword
            for keyword in received_keywords:
                if keyword in line.lower():
                    name = line.lower().split(keyword)[-1].strip()
                    if name and len(name) > 2:
                        logger.debug(f"👤 Found received by: {name}")
                        return name
    
    return None

def calculate_parsing_confidence(delivery_number: str, date: str, supplier: str, 
                               line_items: List[DeliveryLineItem]) -> float:
    """
    Calculate confidence score for parsed delivery note data
    
    Args:
        delivery_number: Extracted delivery number
        date: Extracted date
        supplier: Extracted supplier name
        line_items: List of line items
        
    Returns:
        Confidence score (0.0 to 1.0)
    """
    confidence = 0.0
    total_fields = 0
    
    # Delivery number confidence
    if delivery_number != "Unknown":
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
    
    # Line items confidence
    if line_items:
        confidence += 0.4
    total_fields += 1
    
    # Normalize to 0-1 scale
    if total_fields > 0:
        confidence = confidence / total_fields
    
    return round(confidence, 3) 