import re
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def extract_invoice_metadata(text: str) -> Dict[str, Any]:
    """
    Extract invoice metadata from OCR text.
    
    Args:
        text: OCR text to parse
        
    Returns:
        Dictionary with invoice metadata
    """
    # Invoice number patterns
    invoice_patterns = [
        r'invoice\s*#?\s*:?\s*([A-Z0-9\-_/]+)',
        r'invoice\s*number\s*:?\s*([A-Z0-9\-_/]+)',
        r'inv\s*#?\s*:?\s*([A-Z0-9\-_/]+)',
        r'bill\s*#?\s*:?\s*([A-Z0-9\-_/]+)',
        r'order\s*#?\s*:?\s*([A-Z0-9\-_/]+)',
        r'reference\s*:?\s*([A-Z0-9\-_/]+)',
        r'ref\s*:?\s*([A-Z0-9\-_/]+)'
    ]
    
    # Date patterns
    date_patterns = [
        r'date\s*:?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})'
    ]
    
    # Supplier patterns
    supplier_patterns = [
        r'from\s*:?\s*([A-Za-z\s&.,]+)',
        r'supplier\s*:?\s*([A-Za-z\s&.,]+)',
        r'vendor\s*:?\s*([A-Za-z\s&.,]+)',
        r'company\s*:?\s*([A-Za-z\s&.,]+)',
        r'business\s*:?\s*([A-Za-z\s&.,]+)'
    ]
    
    # Amount patterns
    amount_patterns = [
        r'total\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'amount\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'grand\s*total\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'balance\s*due\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'[£$€]\s*([\d,]+\.?\d*)\s*$'
    ]
    
    # VAT patterns
    vat_patterns = [
        r'vat\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'tax\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'gst\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)'
    ]
    
    # Subtotal patterns
    subtotal_patterns = [
        r'subtotal\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'sub\s*total\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'net\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)'
    ]
    
    # VAT rate patterns
    vat_rate_patterns = [
        r'vat\s*rate\s*:?\s*(\d+(?:\.\d+)?)\s*%',
        r'(\d+(?:\.\d+)?)\s*%\s*vat',
        r'vat\s*(\d+(?:\.\d+)?)\s*%'
    ]
    
    # Extract invoice number
    invoice_number = "Unknown"
    for pattern in invoice_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            invoice_number = match.group(1).strip()
            break
    
    # Extract date
    invoice_date = datetime.now().strftime("%Y-%m-%d")
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                date_str = match.group(1).strip()
                # Try to parse the date
                if '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        if len(parts[2]) == 2:
                            parts[2] = '20' + parts[2]
                        invoice_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                elif '-' in date_str:
                    parts = date_str.split('-')
                    if len(parts) == 3:
                        if len(parts[0]) == 4:  # YYYY-MM-DD
                            invoice_date = date_str
                        else:  # DD-MM-YYYY
                            if len(parts[2]) == 2:
                                parts[2] = '20' + parts[2]
                            invoice_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                break
            except:
                continue
    
    # Extract supplier
    supplier_name = "Unknown"
    for pattern in supplier_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            supplier_name = match.group(1).strip()
            # Clean up supplier name
            supplier_name = re.sub(r'\s+', ' ', supplier_name)
            break
    
    # Extract amounts
    total_amount = 0.0
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                total_amount = float(match.group(1).replace(',', ''))
                break
            except:
                continue
    
    # Extract VAT
    vat_amount = 0.0
    for pattern in vat_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                vat_amount = float(match.group(1).replace(',', ''))
                break
            except:
                continue
    
    # Extract subtotal
    subtotal = 0.0
    for pattern in subtotal_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                subtotal = float(match.group(1).replace(',', ''))
                break
            except:
                continue
    
    # Extract VAT rate
    vat_rate = 0.2  # Default 20%
    for pattern in vat_rate_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                vat_rate = float(match.group(1)) / 100.0
                break
            except:
                continue
    
    # Calculate missing values
    if subtotal and vat_amount and total_amount:
        calculated_total = subtotal + vat_amount
        if abs(calculated_total - total_amount) < 0.01:
            # Values are consistent
            pass
        else:
            # Use calculated total
            total_amount = calculated_total
    elif subtotal and vat_amount and not total_amount:
        total_amount = subtotal + vat_amount
    elif subtotal and not vat_amount and total_amount:
        vat_amount = total_amount - subtotal
        vat_rate = vat_amount / subtotal if subtotal > 0 else 0.2
    elif not subtotal and vat_amount and total_amount:
        subtotal = total_amount - vat_amount
    elif subtotal and not vat_amount and not total_amount:
        vat_amount = subtotal * vat_rate
        total_amount = subtotal + vat_amount
    elif not subtotal and not vat_amount and total_amount:
        subtotal = total_amount / (1 + vat_rate)
        vat_amount = total_amount - subtotal
    
    return {
        "invoice_number": invoice_number,
        "supplier_name": supplier_name,
        "invoice_date": invoice_date,
        "total_amount": round(total_amount, 2),
        "subtotal": round(subtotal, 2),
        "vat": round(vat_amount, 2),
        "vat_rate": round(vat_rate, 3),
        "total_incl_vat": round(total_amount, 2)
    }

def extract_line_items(table_data: List[List[str]]) -> List[Dict[str, Any]]:
    """
    Extract line items from table data.
    
    Args:
        table_data: Table data as list of rows
        
    Returns:
        List of line item dictionaries
    """
    line_items = []
    
    if not table_data or len(table_data) < 2:
        return line_items
    
    # Find header row
    header_row = None
    for i, row in enumerate(table_data):
        row_text = ' '.join(row).lower()
        if any(keyword in row_text for keyword in ['qty', 'quantity', 'desc', 'description', 'price', 'unit', 'total', 'amount']):
            header_row = i
            break
    
    if header_row is None:
        return line_items
    
    # Parse line items
    for i in range(header_row + 1, len(table_data)):
        row = table_data[i]
        if len(row) < 2:
            continue
        
        # Skip total/subtotal rows
        row_text = ' '.join(row).lower()
        if any(keyword in row_text for keyword in ['total', 'subtotal', 'balance', 'due']):
            continue
        
        # Try to extract line item data
        line_item = parse_line_item_row(row)
        if line_item and line_item.get('item'):
            line_items.append(line_item)
    
    return line_items

def parse_line_item_row(row: List[str]) -> Dict[str, Any]:
    """
    Parse a single row as a line item.
    
    Args:
        row: List of cell strings
        
    Returns:
        Line item dictionary or None if invalid
    """
    if len(row) < 2:
        return None
    
    # Try different parsing strategies
    strategies = [
        parse_tabular_line_item,
        parse_space_separated_line_item,
        parse_pattern_based_line_item
    ]
    
    for strategy in strategies:
        try:
            result = strategy(row)
            if result and result.get('item'):
                return result
        except Exception as e:
            logger.debug(f"Strategy {strategy.__name__} failed: {str(e)}")
            continue
    
    return None

def parse_tabular_line_item(row: List[str]) -> Dict[str, Any]:
    """
    Parse line item from tabular format.
    
    Args:
        row: List of cell strings
        
    Returns:
        Line item dictionary
    """
    # Look for quantity, description, unit price, total
    qty = 1.0
    description = ""
    unit_price = 0.0
    line_total = 0.0
    
    for i, cell in enumerate(row):
        cell = cell.strip()
        if not cell:
            continue
        
        # Try to identify quantity
        qty_match = re.search(r'^(\d+(?:\.\d+)?)$', cell)
        if qty_match and qty == 1.0:
            qty = float(qty_match.group(1))
            continue
        
        # Try to identify prices
        price_match = re.search(r'[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)', cell)
        if price_match:
            price_val = float(price_match.group(1).replace(',', ''))
            
            # If we have a unit price, this might be line total
            if unit_price > 0 and line_total == 0:
                line_total = price_val
            elif unit_price == 0:
                unit_price = price_val
            continue
        
        # If not quantity or price, it's description
        if not description:
            description = cell
        else:
            description += " " + cell
    
    # Calculate missing values
    if unit_price > 0 and line_total == 0:
        line_total = unit_price * qty
    elif line_total > 0 and unit_price == 0 and qty > 0:
        unit_price = line_total / qty
    
    if not description:
        description = "Unknown Item"
    
    return create_line_item_dict(
        item=description,
        quantity=qty,
        unit_price_excl_vat=unit_price,
        line_total_excl_vat=line_total,
        vat_rate=0.2
    )

def parse_space_separated_line_item(row: List[str]) -> Dict[str, Any]:
    """
    Parse line item from space-separated format.
    
    Args:
        row: List of cell strings
        
    Returns:
        Line item dictionary
    """
    # Join all cells and split by spaces
    text = ' '.join(row)
    parts = text.split()
    
    qty = 1.0
    description = ""
    unit_price = 0.0
    line_total = 0.0
    
    i = 0
    while i < len(parts):
        part = parts[i]
        
        # Check for quantity (e.g., "5 x")
        if part.isdigit() and i + 1 < len(parts) and parts[i + 1].lower() in ['x', 'of', 'units']:
            qty = float(part)
            i += 2
            continue
        
        # Check for prices
        price_match = re.search(r'[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)', part)
        if price_match:
            price_val = float(price_match.group(1).replace(',', ''))
            
            if unit_price > 0 and line_total == 0:
                line_total = price_val
            elif unit_price == 0:
                unit_price = price_val
            i += 1
            continue
        
        # Add to description
        if not description:
            description = part
        else:
            description += " " + part
        i += 1
    
    # Calculate missing values
    if unit_price > 0 and line_total == 0:
        line_total = unit_price * qty
    elif line_total > 0 and unit_price == 0 and qty > 0:
        unit_price = line_total / qty
    
    if not description:
        description = "Unknown Item"
    
    return create_line_item_dict(
        item=description,
        quantity=qty,
        unit_price_excl_vat=unit_price,
        line_total_excl_vat=line_total,
        vat_rate=0.2
    )

def parse_pattern_based_line_item(row: List[str]) -> Dict[str, Any]:
    """
    Parse line item using pattern matching.
    
    Args:
        row: List of cell strings
        
    Returns:
        Line item dictionary
    """
    text = ' '.join(row)
    
    # Pattern: "Item Name X x £Y.YY £Z.ZZ"
    pattern1 = r'^(.+?)\s+(\d+(?:\.\d+)?)\s*x\s*[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)\s*[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)'
    match = re.search(pattern1, text)
    if match:
        description = match.group(1).strip()
        qty = float(match.group(2))
        unit_price = float(match.group(3).replace(',', ''))
        line_total = float(match.group(4).replace(',', ''))
        
        return create_line_item_dict(
            item=description,
            quantity=qty,
            unit_price_excl_vat=unit_price,
            line_total_excl_vat=line_total,
            vat_rate=0.2
        )
    
    # Pattern: "Item Name £Y.YY each X units £Z.ZZ"
    pattern2 = r'^(.+?)\s+[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)\s+each\s+(\d+(?:\.\d+)?)\s+units\s+[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)'
    match = re.search(pattern2, text)
    if match:
        description = match.group(1).strip()
        unit_price = float(match.group(2).replace(',', ''))
        qty = float(match.group(3))
        line_total = float(match.group(4).replace(',', ''))
        
        return create_line_item_dict(
            item=description,
            quantity=qty,
            unit_price_excl_vat=unit_price,
            line_total_excl_vat=line_total,
            vat_rate=0.2
        )
    
    return None

def create_line_item_dict(item: str, quantity: float, unit_price_excl_vat: float, 
                         line_total_excl_vat: float, vat_rate: float) -> Dict[str, Any]:
    """
    Create a standardized line item dictionary.
    
    Args:
        item: Item description
        quantity: Quantity
        unit_price_excl_vat: Unit price excluding VAT
        line_total_excl_vat: Line total excluding VAT
        vat_rate: VAT rate
        
    Returns:
        Line item dictionary
    """
    # Calculate VAT-inclusive values
    unit_price_incl_vat = unit_price_excl_vat * (1 + vat_rate)
    line_total_incl_vat = line_total_excl_vat * (1 + vat_rate)
    
    # Calculate price per unit (VAT-inclusive)
    price_per_unit = unit_price_incl_vat
    
    return {
        "item": item,
        "description": item,  # Backward compatibility
        "quantity": quantity,
        "unit_price": unit_price_excl_vat,  # Backward compatibility
        "total_price": line_total_excl_vat,  # Backward compatibility
        "unit_price_excl_vat": round(unit_price_excl_vat, 2),
        "unit_price_incl_vat": round(unit_price_incl_vat, 2),
        "line_total_excl_vat": round(line_total_excl_vat, 2),
        "line_total_incl_vat": round(line_total_incl_vat, 2),
        "price_excl_vat": round(unit_price_excl_vat, 2),
        "price_incl_vat": round(unit_price_incl_vat, 2),
        "price_per_unit": round(price_per_unit, 2),
        "vat_rate": round(vat_rate, 3),
        "line_position": 0,
        "flagged": False
    }

def calculate_confidence(parsed: Dict) -> float:
    """
    Calculate confidence score for parsed invoice data.
    
    Args:
        parsed: Parsed invoice dictionary
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    confidence = 0.0
    
    # Base confidence from metadata completeness
    metadata_fields = ['invoice_number', 'supplier_name', 'invoice_date', 'total_amount']
    metadata_score = sum(1 for field in metadata_fields if parsed.get(field) and parsed[field] != "Unknown" and parsed[field] != 0.0)
    metadata_confidence = metadata_score / len(metadata_fields) * 0.4
    
    # Line items confidence
    line_items = parsed.get('line_items', [])
    if line_items:
        line_item_confidence = min(len(line_items) * 0.1, 0.3)  # Max 0.3 for line items
    else:
        line_item_confidence = 0.0
    
    # VAT calculation consistency
    vat_confidence = 0.0
    if parsed.get('subtotal') and parsed.get('vat') and parsed.get('total_amount'):
        calculated_total = parsed['subtotal'] + parsed['vat']
        if abs(calculated_total - parsed['total_amount']) < 0.01:
            vat_confidence = 0.2
        else:
            vat_confidence = 0.1
    elif parsed.get('total_amount') and parsed.get('vat_rate'):
        vat_confidence = 0.1
    
    # OCR text quality (if available)
    ocr_confidence = 0.0
    ocr_text = parsed.get('ocr_text', '')
    if ocr_text:
        word_count = len(ocr_text.split())
        if word_count > 100:
            ocr_confidence = 0.1
        elif word_count > 50:
            ocr_confidence = 0.05
    
    confidence = metadata_confidence + line_item_confidence + vat_confidence + ocr_confidence
    
    # Penalize for missing critical data
    if not line_items:
        confidence *= 0.7  # 30% penalty for no line items
    
    if parsed.get('invoice_number') == "Unknown":
        confidence *= 0.8  # 20% penalty for unknown invoice number
    
    return min(confidence, 1.0) 